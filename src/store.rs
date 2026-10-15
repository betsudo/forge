use crate::domain::{Artifact, Record, digest, validate_id};
use anyhow::{Context, Result, bail, ensure};
use rusqlite::{Connection, OptionalExtension, Transaction, TransactionBehavior, params};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::{Read, Write},
    path::{Path, PathBuf},
    time::Duration,
};

pub const SCHEMA_SQL: &str = "PRAGMA synchronous=FULL;
            CREATE TABLE IF NOT EXISTS bundles(id TEXT PRIMARY KEY, record TEXT NOT NULL, ready INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS derivations(id TEXT PRIMARY KEY, record TEXT NOT NULL, ready INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS artifact_sets(id TEXT PRIMARY KEY, record TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), bundle TEXT NOT NULL, requested_path TEXT NOT NULL, operation TEXT NOT NULL, outcome TEXT NOT NULL, elapsed_ms REAL NOT NULL, generation_ms REAL, estimated_saved_ms REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS file_requests(request_id INTEGER NOT NULL, kind TEXT NOT NULL, digest TEXT NOT NULL, bytes INTEGER NOT NULL, outcome TEXT NOT NULL);";

pub struct Store {
    pub root: PathBuf,
    pub db: Connection,
}

pub fn managed_dir(path: &Path) -> Result<()> {
    // The cache is private to the local Unix user, never a shared untrusted directory.
    if let Ok(meta) = fs::symlink_metadata(path) {
        ensure!(
            meta.is_dir() && !meta.file_type().is_symlink(),
            "managed directory is not a regular directory: {}",
            path.display()
        );
    } else {
        fs::create_dir_all(path)?;
    }
    Ok(())
}
fn regular_file(path: &Path) -> Result<()> {
    let meta = fs::symlink_metadata(path)?;
    ensure!(
        meta.is_file() && !meta.file_type().is_symlink(),
        "not a regular managed file: {}",
        path.display()
    );
    Ok(())
}
impl Store {
    pub fn open(root: &Path) -> Result<Self> {
        let existed = root.exists();
        managed_dir(root)?;
        #[cfg(unix)]
        if !existed {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(root, fs::Permissions::from_mode(0o700))?;
        }
        let root = fs::canonicalize(root)?;
        for name in ["objects", "exports", "staging"] {
            managed_dir(&root.join(name))?;
        }
        let database = root.join("index.sqlite3");
        if database.symlink_metadata().is_ok() {
            regular_file(&database)?;
        }
        let db = Connection::open(database)?;
        db.busy_timeout(Duration::from_secs(3600))?;
        db.execute_batch(SCHEMA_SQL)?;
        Ok(Self { root, db })
    }
    pub fn lock(&self) -> Result<Transaction<'_>> {
        Transaction::new_unchecked(&self.db, TransactionBehavior::Immediate).map_err(|error| {
            let busy = matches!(&error, rusqlite::Error::SqliteFailure(code, _) if matches!(code.code, rusqlite::ErrorCode::DatabaseBusy | rusqlite::ErrorCode::DatabaseLocked));
            let kind = if busy { crate::error::Kind::Busy } else { crate::error::Kind::InternalError };
            anyhow::Error::new(error).context(kind)
        })
    }
    pub fn load(&self, id: &str) -> Result<(Record, bool)> {
        validate_id(id)?;
        let row: Option<(String, bool)> = self
            .db
            .query_row("SELECT record,ready FROM bundles WHERE id=?1", [id], |r| {
                Ok((r.get(0)?, r.get(1)?))
            })
            .optional()?;
        let (record, ready) = row
            .context("bundle not registered")
            .context(crate::error::Kind::NotFound)?;
        Ok((
            serde_json::from_str(&record).context(crate::error::Kind::IntegrityError)?,
            ready,
        ))
    }
    pub fn save(&self, record: &Record, ready: bool) -> Result<()> {
        if ready && let Some(id) = &record.derivation_id {
            self.db.execute("INSERT INTO derivations(id,record,ready) VALUES(?1,?2,1) ON CONFLICT(id) DO UPDATE SET record=excluded.record,ready=1",params![id.0,serde_json::to_string(record)?])?;
        }
        if let Some(id) = &record.artifact_set_id {
            self.db.execute(
                "INSERT OR IGNORE INTO artifact_sets(id,record) VALUES(?1,?2)",
                params![id.0, serde_json::to_string(record)?],
            )?;
        }
        self.db.execute("INSERT INTO bundles(id,record,ready) VALUES(?1,?2,?3) ON CONFLICT(id) DO UPDATE SET record=excluded.record,ready=excluded.ready", params![record.bundle_id.0,serde_json::to_string(record)?,ready])?;
        self.db.execute("UPDATE derivations SET ready=EXISTS(SELECT 1 FROM bundles WHERE bundles.ready=1 AND json_extract(bundles.record,'$.derivation_id')=derivations.id)",[])?;
        Ok(())
    }
    pub fn object_path(&self, digest: &str) -> Result<PathBuf> {
        validate_id(digest)?;
        Ok(self.root.join("objects").join(digest))
    }
    pub fn read(&self, artifact: &Artifact) -> Result<Vec<u8>> {
        (|| {
            let path = self.object_path(&artifact.digest)?;
            regular_file(&path)?;
            let file = fs::File::open(path)?;
            crate::require!(
                file.metadata()?.len() == artifact.size,
                crate::error::Kind::IntegrityError,
                "integrity_error: size mismatch for {}",
                artifact.digest
            );
            let mut bytes = Vec::new();
            file.take(
                artifact
                    .size
                    .checked_add(1)
                    .context("artifact size overflow")?,
            )
            .read_to_end(&mut bytes)?;
            crate::require!(
                bytes.len() as u64 == artifact.size && digest(&bytes) == artifact.digest,
                crate::error::Kind::IntegrityError,
                "integrity_error: {}",
                artifact.digest
            );
            Ok(bytes)
        })()
        .context(crate::error::Kind::IntegrityError)
    }
    pub fn put(&self, bytes: &[u8]) -> Result<String> {
        let hash = digest(bytes);
        let path = self.object_path(&hash)?;
        let expected = Artifact {
            kind: crate::domain::ArtifactKind::Source,
            digest: hash.clone(),
            size: bytes.len() as u64,
        };
        if path.symlink_metadata().is_ok() {
            verify_file(&path, &expected)?;
            return Ok(hash);
        }
        let mut temp = tempfile::NamedTempFile::new_in(self.root.join("staging"))?;
        temp.write_all(bytes)?;
        temp.as_file().sync_all()?;
        match temp.persist_noclobber(&path) {
            Ok(_) => {}
            Err(e) => {
                if e.error.kind() != std::io::ErrorKind::AlreadyExists {
                    return Err(e.error.into());
                }
                verify_file(&path, &expected)?;
            }
        }
        sync_dir(&self.root.join("objects"))?;
        Ok(hash)
    }
    pub fn verify(&self, artifact: &Artifact) -> Result<()> {
        verify_file(&self.object_path(&artifact.digest)?, artifact)
            .context(crate::error::Kind::IntegrityError)
    }
    pub fn export(&self, record: &Record, output: Option<&Path>) -> Result<Value> {
        let set = record
            .artifact_set_id
            .as_ref()
            .context("artifacts not generated")?;
        let default = self
            .root
            .join("exports")
            .join(&record.bundle_id.0)
            .join(&record.derivation_id.as_ref().context("missing recipe")?.0)
            .join(&set.0);
        let destination = std::path::absolute(output.unwrap_or(&default))?;
        let destination = destination.as_path();
        let descriptor = crate::descriptor::ArtifactDescriptor::from_record(
            record,
            &self.read(&record.source)?,
        )?;
        let descriptor_bytes = serde_json::to_vec_pretty(&descriptor)?;
        let all: Vec<&Artifact> = std::iter::once(&record.source)
            .chain(record.artifacts.iter())
            .collect();
        for artifact in &all {
            self.verify(artifact)?;
        }
        if destination.symlink_metadata().is_ok() {
            managed_dir(destination)?;
            managed_dir(&destination.join("zkir"))?;
            managed_dir(&destination.join("keys"))?;
            for artifact in &all {
                let target = destination.join(artifact.kind.folder()).join(format!(
                    "{}.{}",
                    record.name,
                    artifact.kind.extension()
                ));
                verify_file(&target, artifact)
                    .context("export_integrity_error")
                    .context(crate::error::Kind::IntegrityError)?;
            }
            regular_file(&destination.join("manifest.json"))
                .context(crate::error::Kind::IntegrityError)?;
            ensure!(
                fs::read(destination.join("manifest.json"))? == export_manifest(record)?,
                crate::error::Kind::IntegrityError
            );
            let sidecar = destination.join("descriptor.json");
            if sidecar.symlink_metadata().is_ok() {
                regular_file(&sidecar).context(crate::error::Kind::IntegrityError)?;
                let bytes = fs::read(&sidecar)?;
                crate::descriptor::ArtifactDescriptor::decode(&bytes)?;
                ensure!(
                    bytes == descriptor_bytes,
                    crate::error::Kind::IntegrityError
                );
            } else {
                let mut stage = tempfile::NamedTempFile::new_in(destination)?;
                stage.write_all(&descriptor_bytes)?;
                stage.as_file().sync_all()?;
                stage.persist_noclobber(&sidecar).map_err(|e| e.error)?;
                sync_dir(destination)?;
            }
        } else {
            let parent = destination.parent().context("export has no parent")?;
            managed_dir(parent)?;
            let staging = tempfile::tempdir_in(parent)?;
            for folder in ["zkir", "keys"] {
                fs::create_dir(staging.path().join(folder))?;
            }
            for artifact in &all {
                let target = staging.path().join(artifact.kind.folder()).join(format!(
                    "{}.{}",
                    record.name,
                    artifact.kind.extension()
                ));
                fs::copy(self.object_path(&artifact.digest)?, &target)?;
                fs::File::open(&target)?.sync_all()?;
                verify_file(&target, artifact)?;
            }
            let mut manifest = fs::File::create(staging.path().join("manifest.json"))?;
            manifest.write_all(&export_manifest(record)?)?;
            manifest.sync_all()?;
            let mut sidecar = fs::File::create(staging.path().join("descriptor.json"))?;
            sidecar.write_all(&descriptor_bytes)?;
            sidecar.sync_all()?;
            sync_dir(&staging.path().join("zkir"))?;
            sync_dir(&staging.path().join("keys"))?;
            sync_dir(staging.path())?;
            crate::filesystem::publish_directory(staging.path(), destination)?;
        }
        let base = fs::canonicalize(destination)?;
        let files:Vec<Value>=all.iter().map(|a|json!({"kind":a.kind,"sha256":a.digest,"bytes":a.size,"path":base.join(a.kind.folder()).join(format!("{}.{}",record.name,a.kind.extension()))})).collect();
        Ok(
            json!({"base":base,"lifetime":"persistent_until_owner_removal","files":files,"descriptor":descriptor}),
        )
    }
    pub fn evict(&self, id: &str, dry_run: bool) -> Result<Value> {
        let tx = self.lock()?;
        let (record, _) = self.load(id)?;
        let mut others = self
            .db
            .prepare("SELECT record FROM bundles WHERE id != ?1 AND ready=1")?;
        let mut protected = std::collections::BTreeSet::new();
        for row in others.query_map([id], |r| r.get::<_, String>(0))? {
            let r: Record = serde_json::from_str(&row?)?;
            protected.insert(r.source.digest);
            for a in r.artifacts {
                protected.insert(a.digest);
            }
        }
        // Source is never evicted, including pathological cross-kind equality.
        protected.insert(record.source.digest.clone());
        let mut removed = Vec::new();
        for a in &record.artifacts {
            if !protected.contains(&a.digest) && self.object_path(&a.digest)?.exists() {
                removed.push(a.digest.clone());
            }
        }
        drop(others);
        if !dry_run {
            self.save(&record, false)?;
            // Commit unavailability before unlink: interruption can leak blobs,
            // but can never advertise a partial key set as ready.
            tx.commit()?;
            let cleanup = self.lock()?;
            // No interleaving writer may be harmed: re-evaluate reachability.
            for hash in &removed {
                if !self.referenced_ready(hash)? {
                    let path = self.object_path(hash)?;
                    if path.symlink_metadata().is_ok() {
                        regular_file(&path)?;
                        fs::remove_file(path)?;
                    }
                }
            }
            sync_dir(&self.root.join("objects"))?;
            cleanup.commit()?;
        }
        Ok(
            json!({"bundle_id":id,"dry_run":dry_run,"candidate_objects":removed,"source_retained":true,"identity_retained":true,"exports_retained":true}),
        )
    }
    fn referenced_ready(&self, hash: &str) -> Result<bool> {
        let mut stmt = self.db.prepare("SELECT record,ready FROM bundles")?;
        for row in stmt.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, bool>(1)?)))? {
            let (text, ready) = row?;
            let r: Record = serde_json::from_str(&text)?;
            if r.source.digest == hash || (ready && r.artifacts.iter().any(|a| a.digest == hash)) {
                return Ok(true);
            }
        }
        Ok(false)
    }
    pub fn metric(&self, event: &Metric<'_>, artifacts: &[Artifact]) -> Result<()> {
        let tx = self.lock()?;
        self.record_metric(event, artifacts)?;
        tx.commit()?;
        Ok(())
    }
    /// Caller owns the operation transaction so success and accounting commit together.
    pub(crate) fn record_metric(&self, event: &Metric<'_>, artifacts: &[Artifact]) -> Result<()> {
        ensure!(
            !self.db.is_autocommit(),
            "metric requires operation transaction"
        );
        self.db.execute("INSERT INTO requests(bundle,requested_path,operation,outcome,elapsed_ms,generation_ms,estimated_saved_ms) VALUES(?1,?2,?3,?4,?5,?6,?7)",params![event.bundle,event.path,event.operation,event.outcome,event.elapsed_ms,event.generation_ms,event.saved_ms])?;
        let id = self.db.last_insert_rowid();
        for a in artifacts {
            self.db.execute(
                "INSERT INTO file_requests VALUES(?1,?2,?3,?4,?5)",
                params![id, a.kind.extension(), a.digest, a.size, event.outcome],
            )?;
        }
        Ok(())
    }
    pub fn stats(&self) -> Result<Value> {
        let mut requests=self.db.query_row("SELECT count(*),coalesce(sum(outcome='hit'),0),coalesce(sum(outcome='miss'),0),coalesce(sum(outcome='error'),0),coalesce(sum(generation_ms),0),coalesce(sum(estimated_saved_ms),0),coalesce(sum(elapsed_ms),0) FROM requests",[],|r|Ok(json!({"requests":r.get::<_,u64>(0)?,"hits":r.get::<_,u64>(1)?,"misses":r.get::<_,u64>(2)?,"errors":r.get::<_,u64>(3)?,"generation_ms":r.get::<_,f64>(4)?,"estimated_generation_avoided_ms":r.get::<_,f64>(5)?,"total_request_ms":r.get::<_,f64>(6)?})))?;
        let count = requests["hits"].as_u64().unwrap() + requests["misses"].as_u64().unwrap();
        requests["hit_rate"] = if count == 0 {
            Value::Null
        } else {
            json!(requests["hits"].as_u64().unwrap() as f64 / count as f64)
        };
        let mut stmt=self.db.prepare("SELECT r.bundle,r.requested_path,f.kind,f.digest,count(*),sum(f.outcome='hit'),sum(f.outcome='miss'),sum(f.outcome='error'),max(f.bytes),sum(CASE WHEN f.outcome='hit' THEN f.bytes ELSE 0 END) FROM file_requests f JOIN requests r ON f.request_id=r.id GROUP BY r.bundle,r.requested_path,f.kind,f.digest ORDER BY r.bundle,r.requested_path,f.kind")?;
        let files=stmt.query_map([],|r|Ok(json!({"bundle_id":r.get::<_,String>(0)?,"requested_path":r.get::<_,String>(1)?,"kind":r.get::<_,String>(2)?,"sha256":r.get::<_,String>(3)?,"requests":r.get::<_,u64>(4)?,"hits":r.get::<_,u64>(5)?,"misses":r.get::<_,u64>(6)?,"errors":r.get::<_,u64>(7)?,"bytes":r.get::<_,u64>(8)?,"hit_bytes":r.get::<_,u64>(9)?})))?.collect::<std::result::Result<Vec<_>,_>>()?;
        let mut stmt=self.db.prepare("SELECT at,bundle,requested_path,operation,outcome,elapsed_ms,generation_ms,estimated_saved_ms FROM requests ORDER BY id DESC LIMIT 100")?;
        let recent=stmt.query_map([],|r|Ok(json!({"at":r.get::<_,String>(0)?,"bundle_id":r.get::<_,String>(1)?,"requested_path":r.get::<_,String>(2)?,"operation":r.get::<_,String>(3)?,"outcome":r.get::<_,String>(4)?,"elapsed_ms":r.get::<_,f64>(5)?,"generation_ms":r.get::<_,Option<f64>>(6)?,"estimated_generation_avoided_ms":r.get::<_,f64>(7)?})))?.collect::<std::result::Result<Vec<_>,_>>()?;
        Ok(
            json!({"schema":1,"storage":{"cas_bytes":directory_bytes(&self.root.join("objects"))?,"export_bytes":directory_bytes(&self.root.join("exports"))?,"sqlite_main_bytes":fs::metadata(self.root.join("index.sqlite3"))?.len(),"sqlite_wal_bytes":fs::metadata(self.root.join("index.sqlite3-wal")).map(|m|m.len()).unwrap_or(0),"staging_bytes":directory_bytes(&self.root.join("staging"))?},"totals":requests,"files":files,"recent_requests":recent,"estimate_basis":"last measured generation for this exact derivation; timings include parameter verification, locking, integrity checks and export, but exclude final transaction commit and process overhead; not a test-pass cache"}),
        )
    }
}
pub struct Metric<'a> {
    pub bundle: &'a str,
    pub path: &'a str,
    pub operation: &'a str,
    pub outcome: &'a str,
    pub elapsed_ms: f64,
    pub generation_ms: Option<f64>,
    pub saved_ms: f64,
}
fn sync_dir(path: &Path) -> Result<()> {
    fs::File::open(path)?.sync_all()?;
    Ok(())
}

pub fn read_input(path: &Path) -> Result<Vec<u8>> {
    let file = fs::File::open(path).context("open circuit input")?;
    ensure!(file.metadata()?.is_file(), "input must be a regular file");
    let mut bytes = Vec::new();
    file.take(16 * 1024 * 1024 + 1).read_to_end(&mut bytes)?;
    if bytes.len() > 16 * 1024 * 1024 {
        bail!("input exceeds MVP limit of 16 MiB");
    }
    Ok(bytes)
}

pub(crate) fn export_manifest(record: &Record) -> Result<Vec<u8>> {
    let mut immutable = serde_json::to_value(record)?;
    immutable.as_object_mut().unwrap().remove("generation_ms");
    Ok(serde_json::to_vec_pretty(&immutable)?)
}

fn directory_bytes(path: &Path) -> Result<u64> {
    let mut bytes = 0;
    for entry in fs::read_dir(path)? {
        let entry = entry?;
        let meta = entry.file_type()?;
        if meta.is_dir() {
            bytes += directory_bytes(&entry.path())?;
        } else if meta.is_file() {
            bytes += entry.metadata()?.len();
        }
    }
    Ok(bytes)
}

fn verify_file(path: &Path, artifact: &Artifact) -> Result<()> {
    regular_file(path)?;
    let mut file = fs::File::open(path)?;
    crate::require!(
        file.metadata()?.len() == artifact.size,
        crate::error::Kind::IntegrityError,
        "integrity_error: size mismatch for {}",
        artifact.digest
    );
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 128 * 1024];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    crate::require!(
        hex::encode(hasher.finalize()) == artifact.digest,
        crate::error::Kind::IntegrityError,
        "integrity_error: digest mismatch for {}",
        artifact.digest
    );
    Ok(())
}
