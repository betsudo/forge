//! Verified directory snapshots. GitHub cache/artifacts own compression/transport.
use crate::{
    application, backend,
    domain::{ArtifactKind, Record, WorkerProvenance, identity, validate_id, validate_name},
    store::SCHEMA_SQL,
    zkir3, zkir31,
};
use anyhow::{Context, Result, ensure};
use rusqlite::{Connection, OpenFlags, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File},
    io::{Read, Write},
    path::{Path, PathBuf},
    time::Duration,
};
pub const DEFAULT_MAX_BYTES: u64 = 10 * 1024 * 1024 * 1024;
const MAX_FILES: usize = 100_000;
const MAX_MANIFEST: u64 = 16 * 1024 * 1024;
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Entry {
    path: String,
    bytes: u64,
    sha256: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Producer {
    build_fingerprint: String,
    profile: String,
    ledger_revision: String,
    worker: Option<WorkerProvenance>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    worker31: Option<WorkerProvenance>,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    schema: u32,
    format: String,
    producer: Producer,
    partition: Option<String>,
    files: Vec<Entry>,
    snapshot_id: String,
}
impl Manifest {
    fn id(&self) -> Result<String> {
        identity(
            "midnight-zkir-forge/snapshot/v1",
            &(
                self.schema,
                &self.format,
                &self.producer,
                &self.partition,
                &self.files,
            ),
        )
    }
}
#[derive(Default, Serialize)]
struct Summary {
    bundles: u64,
    ready: u64,
    profiles: BTreeSet<String>,
    parameter_digests: BTreeSet<String>,
    formats: BTreeSet<String>,
    has_v3: bool,
    has_v31: bool,
}
pub struct Scope {
    pub profile: Option<crate::engine::ProfileSelector>,
    pub parameters: Vec<String>,
}
fn check_scope(summary: &Summary, scope: &Scope) -> Result<()> {
    if let Some(profile) = scope.profile {
        let (profile, format) = match profile {
            crate::engine::ProfileSelector::Ledger8V2 => {
                (backend::PROFILE, "midnight-zkir-v2-json")
            }
            crate::engine::ProfileSelector::Zkir3 => (zkir3::PROFILE, zkir3::FORMAT),
            crate::engine::ProfileSelector::Zkir31 => (zkir31::PROFILE, zkir31::FORMAT),
        };
        crate::require!(
            summary.profiles.iter().all(|p| p == profile)
                && summary.formats.iter().all(|p| p == format),
            crate::error::Kind::SnapshotPartitionMismatch,
            "snapshot_partition_mismatch: profile outside scope"
        );
    }
    for p in &scope.parameters {
        validate_id(p)?;
    }
    if !scope.parameters.is_empty() {
        crate::require!(
            summary
                .parameter_digests
                .iter()
                .all(|p| scope.parameters.contains(p)),
            crate::error::Kind::SnapshotPartitionMismatch,
            "snapshot_partition_mismatch: parameters outside scope"
        );
    }
    Ok(())
}
fn producer(v3: bool, v31: bool) -> Result<Producer> {
    let worker = if v3 {
        Some(zkir3::call("profile", &[], None, false, None, None)?.1)
    } else {
        None
    };
    Ok(Producer {
        build_fingerprint: application::build_fingerprint(),
        profile: backend::PROFILE.to_owned(),
        ledger_revision: backend::LEDGER_REV.to_owned(),
        worker,
        worker31: if v31 {
            Some(zkir31::call("profile", &[], None, false, None, None)?.1)
        } else {
            None
        },
    })
}
fn regular(path: &Path, directory: bool) -> Result<()> {
    let m = fs::symlink_metadata(path)?;
    crate::require!(
        !m.file_type().is_symlink() && if directory { m.is_dir() } else { m.is_file() },
        crate::error::Kind::SnapshotUnsafePath,
        "snapshot_unsafe_path: non-regular file/directory"
    );
    Ok(())
}
fn destination(path: &Path) -> Result<PathBuf> {
    let name = path
        .file_name()
        .context("snapshot destination needs a filename")?;
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let result = fs::canonicalize(parent)?.join(name);
    crate::require!(
        fs::symlink_metadata(&result).is_err_and(|e| e.kind() == std::io::ErrorKind::NotFound),
        crate::error::Kind::SnapshotDestinationExists,
        "snapshot_destination_exists"
    );
    Ok(result)
}
fn disjoint(a: &Path, b: &Path) -> Result<()> {
    crate::require!(
        !a.starts_with(b) && !b.starts_with(a),
        crate::error::Kind::SnapshotUnsafePath,
        "snapshot_unsafe_path: source and destination overlap"
    );
    Ok(())
}
fn safe_path(path: &str) -> Result<()> {
    crate::require!(
        !path.contains('\\') && path.len() < 1024,
        crate::error::Kind::SnapshotUnsafePath,
        "snapshot_unsafe_path"
    );
    let parts: Vec<_> = path.split('/').collect();
    crate::require!(
        parts
            .iter()
            .all(|p| !p.is_empty() && *p != "." && *p != ".."),
        crate::error::Kind::SnapshotUnsafePath,
        "snapshot_unsafe_path"
    );
    match parts.as_slice() {
        ["index.sqlite3"] => {}
        ["objects", hash] => validate_id(hash)?,
        [
            "exports",
            bundle,
            recipe,
            set,
            "manifest.json" | "descriptor.json",
        ] => {
            validate_id(bundle)?;
            validate_id(recipe)?;
            validate_id(set)?;
        }
        ["exports", bundle, recipe, set, folder, file] => {
            validate_id(bundle)?;
            validate_id(recipe)?;
            validate_id(set)?;
            let (name, extension) = file
                .rsplit_once('.')
                .context(crate::error::Kind::SnapshotUnsafePath)?;
            validate_name(name)?;
            crate::require!(
                matches!(
                    (*folder, extension),
                    ("zkir", "zkir" | "bzkir") | ("keys", "prover" | "verifier")
                ),
                crate::error::Kind::SnapshotUnsafePath,
                "snapshot_unsafe_path"
            );
        }
        _ => anyhow::bail!(crate::error::Kind::SnapshotUnsafePath),
    }
    Ok(())
}
fn walk(
    root: &Path,
    path: &Path,
    entries: &mut Vec<PathBuf>,
    depth: usize,
    seen: &mut usize,
) -> Result<()> {
    crate::require!(
        depth <= 7,
        crate::error::Kind::SnapshotUnsafePath,
        "snapshot_unsafe_path: excessive depth"
    );
    regular(path, true)?;
    for item in fs::read_dir(path)? {
        let path = item?.path();
        *seen += 1;
        crate::require!(
            *seen <= MAX_FILES,
            crate::error::Kind::SnapshotLimit,
            "snapshot_limit: too many entries"
        );
        let m = fs::symlink_metadata(&path)?;
        crate::require!(
            !m.file_type().is_symlink(),
            crate::error::Kind::SnapshotUnsafePath,
            "snapshot_unsafe_path: symlink"
        );
        if m.is_dir() {
            let relative = path
                .strip_prefix(root)?
                .to_str()
                .context(crate::error::Kind::SnapshotUnsafePath)?;
            let parts: Vec<_> = relative.split('/').collect();
            crate::require!(
                parts.first() == Some(&"exports") && parts.len() <= 5,
                crate::error::Kind::SnapshotUnsafePath,
                "snapshot_unsafe_path: unexpected directory"
            );
            for id in parts.iter().skip(1).take(3) {
                validate_id(id)?;
            }
            if parts.len() == 5 {
                crate::require!(
                    matches!(parts[4], "zkir" | "keys"),
                    crate::error::Kind::SnapshotUnsafePath,
                    "snapshot_unsafe_path: unexpected export directory"
                );
            }
            walk(root, &path, entries, depth + 1, seen)?;
        } else {
            regular(&path, false)?;
            let relative = path
                .strip_prefix(root)?
                .to_str()
                .context("snapshot_unsafe_path: non-UTF8")?;
            safe_path(relative)?;
            entries.push(path);
            crate::require!(
                entries.len() <= MAX_FILES,
                crate::error::Kind::SnapshotLimit,
                "snapshot_limit: too many files"
            );
        }
    }
    Ok(())
}
fn payload(root: &Path, snapshot: bool) -> Result<Vec<PathBuf>> {
    regular(root, true)?;
    if snapshot {
        for item in fs::read_dir(root)? {
            let item = item?;
            let name = item.file_name();
            crate::require!(
                matches!(
                    name.to_str(),
                    Some("objects" | "exports" | "index.sqlite3" | "snapshot.json")
                ),
                crate::error::Kind::SnapshotUnsafePath,
                "snapshot_unsafe_path: unknown root entry"
            );
        }
    }
    regular(&root.join("index.sqlite3"), false)?;
    let mut files = vec![root.join("index.sqlite3")];
    let mut seen = 1;
    for dir in ["objects", "exports"] {
        walk(root, &root.join(dir), &mut files, 0, &mut seen)?;
    }
    files.sort();
    Ok(files)
}
fn copy_file(source: &Path, target: &Path, remaining: u64) -> Result<Entry> {
    regular(source, false)?;
    let mut input = File::open(source)?;
    let size = input.metadata()?.len();
    crate::require!(
        size <= remaining,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: byte budget exceeded"
    );
    let mut output = File::options().create_new(true).write(true).open(target)?;
    let mut hash = Sha256::new();
    let mut count = 0u64;
    let mut buffer = [0u8; 128 * 1024];
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        count = count
            .checked_add(n as u64)
            .context(crate::error::Kind::SnapshotLimit)?;
        crate::require!(
            count <= remaining,
            crate::error::Kind::SnapshotLimit,
            "snapshot_limit: source grew"
        );
        output.write_all(&buffer[..n])?;
        hash.update(&buffer[..n]);
    }
    crate::require!(
        count == size,
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: source size changed"
    );
    output.sync_all()?;
    Ok(Entry {
        path: String::new(),
        bytes: count,
        sha256: hex::encode(hash.finalize()),
    })
}
fn hash_file(path: &Path) -> Result<(u64, String)> {
    regular(path, false)?;
    let mut input = File::open(path)?;
    let mut hash = Sha256::new();
    let mut count = 0u64;
    let mut buffer = [0u8; 128 * 1024];
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
        count += n as u64;
    }
    Ok((count, hex::encode(hash.finalize())))
}
pub(crate) fn record_valid(record: &Record) -> Result<()> {
    crate::require!(
        record.schema == 1,
        crate::error::Kind::SnapshotSchemaMismatch,
        "snapshot_schema_mismatch"
    );
    validate_name(&record.name)?;
    validate_id(&record.bundle_id.0)?;
    crate::require!(
        record.source.kind == ArtifactKind::Source && record.source.size <= 16 * 1024 * 1024,
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: source metadata"
    );
    validate_id(&record.source.digest)?;
    let format = record.format.as_deref().unwrap_or("midnight-zkir-v2-json");
    crate::require!(
        matches!(
            format,
            "midnight-zkir-v2-json" | "midnight-zkir-v3-json" | "midnight-zkir-v3.1-json"
        ),
        crate::error::Kind::SnapshotProfileMismatch,
        "snapshot_profile_mismatch"
    );
    crate::require!(
        record.bundle_id.0
            == identity(
                "midnight-zkir-forge/bundle/v1",
                &(&record.name, format, &record.source.digest)
            )?,
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: bundle identity"
    );
    crate::require!(
        record
            .generation_ms
            .is_none_or(|n| n.is_finite() && n >= 0.0),
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: generation timing"
    );
    if let Some(set) = &record.artifact_set_id {
        validate_id(&set.0)?;
        crate::require!(
            record.artifacts.len() == 3,
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: incomplete artifacts"
        );
        let kinds: BTreeSet<_> = record
            .artifacts
            .iter()
            .map(|a| a.kind.extension())
            .collect();
        crate::require!(
            kinds == BTreeSet::from(["bzkir", "prover", "verifier"]),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: artifact kinds"
        );
        for a in &record.artifacts {
            validate_id(&a.digest)?;
        }
        crate::require!(
            set.0 == identity("midnight-zkir-forge/artifacts/v1", &record.artifacts)?,
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: artifact identity"
        );
        let worker_spec = match format {
            zkir3::FORMAT => Some(&zkir3::SPEC),
            zkir31::FORMAT => Some(&zkir31::SPEC),
            _ => None,
        };
        let v3 = worker_spec.is_some();
        let profile = worker_spec.map_or(backend::PROFILE, |s| s.profile);
        let rev = worker_spec.map_or(backend::LEDGER_REV, |s| s.ledger_revision);
        crate::require!(
            record.profile.as_deref() == Some(profile)
                && record.ledger_revision.as_deref() == Some(rev),
            crate::error::Kind::SnapshotProfileMismatch,
            "snapshot_profile_mismatch"
        );
        let fingerprint = record
            .build_fingerprint
            .as_ref()
            .context("snapshot_integrity_error: build missing")?;
        validate_id(fingerprint)?;
        let param = record
            .parameter_digest
            .as_ref()
            .context("snapshot_integrity_error: params missing")?;
        validate_id(param)?;
        let k = record.k.context("snapshot_integrity_error: k missing")?;
        let mut recipe = identity(
            "midnight-zkir-forge/derive/v1",
            &(
                &record.source.digest,
                profile,
                rev,
                fingerprint,
                k,
                param,
                "library-keygen/default-options/no-rng",
            ),
        )?;
        if v3 {
            let worker = record
                .worker
                .as_ref()
                .context("snapshot_integrity_error: worker missing")?;
            crate::require!(
                worker.profile == profile
                    && worker.source_revision == worker_spec.expect("worker profile").revision,
                crate::error::Kind::SnapshotProfileMismatch,
                "snapshot_profile_mismatch"
            );
            validate_id(&worker.build_fingerprint)?;
            validate_id(&worker.executable_sha256)?;
            recipe = identity("midnight-zkir-forge/derive-worker/v1", &(&recipe, worker))?;
        } else {
            crate::require!(
                record.worker.is_none(),
                crate::error::Kind::SnapshotProfileMismatch,
                "snapshot_profile_mismatch"
            );
        }
        crate::require!(
            record.derivation_id.as_ref().map(|d| d.0.as_str()) == Some(recipe.as_str()),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: recipe identity"
        );
    } else {
        crate::require!(
            record.artifacts.is_empty()
                && record.derivation_id.is_none()
                && record.profile.is_none()
                && record.worker.is_none()
                && record.build_fingerprint.is_none()
                && record.ledger_revision.is_none()
                && record.parameter_digest.is_none()
                && record.k.is_none()
                && record.generation_ms.is_none(),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: partial record"
        );
    }
    Ok(())
}
fn validate_payload(root: &Path, inventory: &[Entry]) -> Result<Summary> {
    let map: BTreeMap<_, _> = inventory.iter().map(|e| (e.path.as_str(), e)).collect();
    crate::require!(
        map.len() == inventory.len(),
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: duplicate inventory path"
    );
    for entry in inventory {
        safe_path(&entry.path)?;
        if let Some(hash) = entry.path.strip_prefix("objects/") {
            crate::require!(
                hash == entry.sha256,
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: CAS filename"
            );
        }
    }
    let db =
        Connection::open_with_flags(root.join("index.sqlite3"), OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    db.execute_batch("PRAGMA trusted_schema=OFF; PRAGMA query_only=ON;")?;
    let mode: String = db.query_row("PRAGMA journal_mode", [], |r| r.get(0))?;
    crate::require!(
        mode == "delete",
        crate::error::Kind::SnapshotSchemaMismatch,
        "snapshot_schema_mismatch: standalone DELETE database required"
    );
    let expected = Connection::open_in_memory()?;
    expected.execute_batch(SCHEMA_SQL)?;
    let schema = |connection: &Connection| -> Result<Vec<(String, String, Option<String>)>> {
        let mut query = connection.prepare(
            "SELECT name,type,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY name",
        )?;
        Ok(query
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
            .collect::<rusqlite::Result<_>>()?)
    };
    crate::require!(
        schema(&db)? == schema(&expected)?,
        crate::error::Kind::SnapshotSchemaMismatch,
        "snapshot_schema_mismatch: unexpected schema/constraints"
    );
    let integrity: String = db.query_row("PRAGMA integrity_check", [], |r| r.get(0))?;
    crate::require!(
        integrity == "ok",
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: SQLite check"
    );
    let verify = |record: &Record, ready: bool| -> Result<()> {
        record_valid(record)?;
        for a in std::iter::once(&record.source).chain(record.artifacts.iter().filter(|_| ready)) {
            let path = format!("objects/{}", a.digest);
            let entry = map
                .get(path.as_str())
                .context("snapshot_integrity_error: referenced CAS missing")?;
            crate::require!(
                entry.bytes == a.size && entry.sha256 == a.digest,
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: CAS metadata"
            );
        }
        if ready {
            crate::require!(
                record.artifact_set_id.is_some(),
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: ready record incomplete"
            );
        }
        Ok(())
    };
    let mut summary = Summary::default();
    let mut recipes = BTreeMap::new();
    let mut derivations = BTreeSet::new();
    for table in ["bundles", "derivations", "artifact_sets"] {
        let sql = if table == "artifact_sets" {
            "SELECT id,record,0,length(id),length(record) FROM artifact_sets"
        } else if table == "bundles" {
            "SELECT id,record,ready,length(id),length(record) FROM bundles"
        } else {
            "SELECT id,record,ready,length(id),length(record) FROM derivations"
        };
        let mut statement = db.prepare(sql)?;
        let mut rows = statement.query([])?;
        while let Some(row) = rows.next()? {
            crate::require!(
                row.get::<_, u64>(3)? == 64 && row.get::<_, u64>(4)? <= MAX_MANIFEST,
                crate::error::Kind::SnapshotLimit,
                "snapshot_limit: record metadata"
            );
            let id: String = row.get(0)?;
            let record: Record = serde_json::from_str(&row.get::<_, String>(1)?)?;
            let flag: i64 = row.get(2)?;
            crate::require!(
                flag == 0 || flag == 1,
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: ready flag"
            );
            let ready = flag == 1;
            verify(&record, ready)?;
            if let (Some(recipe), Some(set)) = (&record.derivation_id, &record.artifact_set_id) {
                if let Some(previous) = recipes.insert(recipe.0.clone(), set.0.clone()) {
                    crate::require!(
                        previous == set.0,
                        crate::error::Kind::IntegrityError,
                        "snapshot_integrity_error: contradictory recipe outputs"
                    );
                }
                if table == "derivations" {
                    derivations.insert(recipe.0.clone());
                }
            }
            let expected = match table {
                "bundles" => Some(&record.bundle_id.0),
                "derivations" => record.derivation_id.as_ref().map(|d| &d.0),
                _ => record.artifact_set_id.as_ref().map(|s| &s.0),
            };
            crate::require!(
                expected == Some(&id),
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: database key"
            );
            summary.formats.insert(
                record
                    .format
                    .clone()
                    .unwrap_or_else(|| "midnight-zkir-v2-json".to_owned()),
            );
            summary.has_v3 |= record.format.as_deref() == Some(zkir3::FORMAT);
            summary.has_v31 |= record.format.as_deref() == Some(zkir31::FORMAT);
            if let Some(p) = record.profile {
                summary.profiles.insert(p);
            }
            if let Some(p) = record.parameter_digest {
                summary.parameter_digests.insert(p);
            }
            if table == "bundles" {
                summary.bundles += 1;
                summary.ready += u64::from(ready);
            }
        }
    }
    crate::require!(
        recipes.keys().all(|recipe| derivations.contains(recipe)),
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: derivation history missing"
    );
    let inconsistent:u64=db.query_row("SELECT count(*) FROM derivations d WHERE d.ready != EXISTS(SELECT 1 FROM bundles b WHERE b.ready=1 AND json_extract(b.record,'$.derivation_id')=d.id)",[],|r|r.get(0))?;
    crate::require!(
        inconsistent == 0,
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: ready reference mismatch"
    );
    for table in ["bundles", "derivations"] {
        let sql = format!(
            "SELECT count(*) FROM {table} r WHERE json_extract(r.record,'$.artifact_set_id') IS NOT NULL AND NOT EXISTS(SELECT 1 FROM artifact_sets a WHERE a.id=json_extract(r.record,'$.artifact_set_id'))"
        );
        let missing: u64 = db.query_row(&sql, [], |r| r.get(0))?;
        crate::require!(
            missing == 0,
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: artifact history missing"
        );
    }
    let mut export_paths = BTreeSet::new();
    for entry in inventory
        .iter()
        .filter(|e| e.path.ends_with("/manifest.json"))
    {
        crate::require!(
            entry.bytes <= MAX_MANIFEST,
            crate::error::Kind::SnapshotLimit,
            "snapshot_limit: export manifest too large"
        );
        let manifest_bytes = fs::read(root.join(&entry.path))?;
        let record: Record = serde_json::from_slice(&manifest_bytes)?;
        record_valid(&record)?;
        crate::require!(
            manifest_bytes == crate::store::export_manifest(&record)?,
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: noncanonical export manifest"
        );
        let recipe = &record
            .derivation_id
            .as_ref()
            .context("snapshot_integrity_error: export recipe missing")?
            .0;
        let set = &record
            .artifact_set_id
            .as_ref()
            .context("snapshot_integrity_error: export identity missing")?
            .0;
        crate::require!(
            recipes.get(recipe) == Some(set),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: export recipe history mismatch"
        );
        let base = format!("exports/{}/{recipe}/{set}", record.bundle_id.0);
        crate::require!(
            entry.path == format!("{base}/manifest.json"),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: export path"
        );
        let sidecar = format!("{base}/descriptor.json");
        if let Some(entry) = map.get(sidecar.as_str()) {
            ensure!(
                entry.bytes <= MAX_MANIFEST,
                crate::error::Kind::SnapshotLimit
            );
            let bytes = fs::read(root.join(&sidecar))?;
            let actual = crate::descriptor::ArtifactDescriptor::decode(&bytes)?;
            let expected = crate::descriptor::ArtifactDescriptor::from_record(
                &record,
                &fs::read(root.join(format!("objects/{}", record.source.digest)))?,
            )?;
            ensure!(
                serde_json::to_value(actual)? == serde_json::to_value(expected)?,
                crate::error::Kind::IntegrityError
            );
            export_paths.insert(sidecar);
        }
        for a in std::iter::once(&record.source).chain(record.artifacts.iter()) {
            let path = format!(
                "{base}/{}/{}.{}",
                a.kind.folder(),
                record.name,
                a.kind.extension()
            );
            let e = map
                .get(path.as_str())
                .context("snapshot_integrity_error: export file missing")?;
            crate::require!(
                e.bytes == a.size && e.sha256 == a.digest,
                crate::error::Kind::IntegrityError,
                "snapshot_integrity_error: export bytes"
            );
            export_paths.insert(path);
        }
    }
    for entry in inventory
        .iter()
        .filter(|e| e.path.starts_with("exports/") && !e.path.ends_with("/manifest.json"))
    {
        crate::require!(
            export_paths.contains(&entry.path),
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: undeclared export file"
        );
    }
    Ok(summary)
}
fn sync_tree(root: &Path) -> Result<()> {
    for item in fs::read_dir(root)? {
        let p = item?.path();
        if fs::symlink_metadata(&p)?.is_dir() {
            sync_tree(&p)?;
        }
    }
    File::open(root)?.sync_all()?;
    Ok(())
}
pub fn create(
    root: &Path,
    output: &Path,
    max_bytes: u64,
    wait_seconds: u64,
    partition: Option<String>,
    scope: &Scope,
) -> Result<Value> {
    crate::require!(
        max_bytes > 0,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: budget must be positive"
    );
    if let Some(p) = &partition {
        validate_id(p)?;
    }
    regular(root, true)?;
    let root = fs::canonicalize(root)?;
    let output = destination(output)?;
    disjoint(&root, &output)?;
    regular(&root.join("index.sqlite3"), false)?;
    let db = Connection::open_with_flags(
        root.join("index.sqlite3"),
        OpenFlags::SQLITE_OPEN_READ_WRITE,
    )?;
    db.busy_timeout(Duration::from_secs(wait_seconds))?;
    let transaction = rusqlite::Transaction::new_unchecked(&db, TransactionBehavior::Immediate)
        .context("snapshot_busy: cannot acquire store writer lease")?;
    let staging = tempfile::tempdir_in(output.parent().unwrap())?;
    for dir in ["objects", "exports"] {
        fs::create_dir(staging.path().join(dir))?;
    }
    {
        let source = Connection::open_with_flags(
            root.join("index.sqlite3"),
            OpenFlags::SQLITE_OPEN_READ_ONLY,
        )?;
        let pages: u64 = source.query_row("PRAGMA page_count", [], |r| r.get(0))?;
        let size: u64 = source.query_row("PRAGMA page_size", [], |r| r.get(0))?;
        crate::require!(
            pages
                .checked_mul(size)
                .is_some_and(|bytes| bytes <= max_bytes),
            crate::error::Kind::SnapshotLimit,
            "snapshot_limit: database byte budget exceeded"
        );
        let mut target = Connection::open(staging.path().join("index.sqlite3"))?;
        {
            let backup = rusqlite::backup::Backup::new(&source, &mut target)
                .context("snapshot backup begin")?;
            crate::require!(
                matches!(
                    backup.step(-1).context("snapshot backup step")?,
                    rusqlite::backup::StepResult::Done
                ),
                crate::error::Kind::SnapshotBusy,
                "snapshot_busy: database backup incomplete"
            );
        }
        target
            .execute_batch("PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;")
            .context("snapshot normalize backup")?;
    }
    File::open(staging.path().join("index.sqlite3"))?.sync_all()?;
    let (bytes, hash) = hash_file(&staging.path().join("index.sqlite3"))?;
    crate::require!(
        bytes <= max_bytes,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: byte budget exceeded"
    );
    let mut total = bytes;
    let mut entries = vec![Entry {
        path: "index.sqlite3".to_owned(),
        bytes,
        sha256: hash,
    }];
    for source in payload(&root, false)?
        .into_iter()
        .filter(|p| p.file_name() != Some(std::ffi::OsStr::new("index.sqlite3")))
    {
        let relative = source
            .strip_prefix(&root)?
            .to_str()
            .context(crate::error::Kind::SnapshotUnsafePath)?
            .to_owned();
        let target = staging.path().join(&relative);
        fs::create_dir_all(target.parent().unwrap())?;
        let mut entry = copy_file(&source, &target, max_bytes - total)?;
        total += entry.bytes;
        entry.path = relative;
        entries.push(entry);
    }
    entries.sort_by(|a, b| a.path.cmp(&b.path));
    let summary = validate_payload(staging.path(), &entries)?;
    check_scope(&summary, scope)?;
    let mut manifest = Manifest {
        schema: 1,
        format: "midnight-zkir-forge/snapshot/v1".to_owned(),
        producer: producer(summary.has_v3, summary.has_v31)?,
        partition,
        files: entries,
        snapshot_id: String::new(),
    };
    manifest.snapshot_id = manifest.id()?;
    let bytes = serde_json::to_vec_pretty(&manifest)?;
    crate::require!(
        bytes.len() as u64 <= MAX_MANIFEST && total + bytes.len() as u64 <= max_bytes,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: manifest exceeds budget"
    );
    let mut file = File::options()
        .create_new(true)
        .write(true)
        .open(staging.path().join("snapshot.json"))?;
    file.write_all(&bytes)?;
    file.sync_all()?;
    sync_tree(staging.path())?;
    crate::filesystem::publish_directory(staging.path(), &output)
        .context(crate::error::Kind::SnapshotPublishFailed)?;
    transaction
        .rollback()
        .context("snapshot release read-only lease")?;
    Ok(
        json!({"schema":1,"snapshot_id":manifest.snapshot_id,"path":output,"partition":manifest.partition,"bytes":total+bytes.len() as u64,"files":manifest.files.len(),"summary":summary,"producer":manifest.producer}),
    )
}
pub fn restore(
    input: &Path,
    root: &Path,
    max_bytes: u64,
    expected_id: Option<&str>,
    partition: Option<&str>,
    scope: &Scope,
) -> Result<Value> {
    crate::require!(
        max_bytes > 0,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: budget must be positive"
    );
    regular(input, true)?;
    let input = fs::canonicalize(input)?;
    let target = destination(root)?;
    disjoint(&input, &target)?;
    let manifest_path = input.join("snapshot.json");
    regular(&manifest_path, false)?;
    crate::require!(
        fs::metadata(&manifest_path)?.len() <= MAX_MANIFEST,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: manifest too large"
    );
    let mut bytes = Vec::new();
    File::open(manifest_path)?
        .take(MAX_MANIFEST + 1)
        .read_to_end(&mut bytes)?;
    crate::require!(
        bytes.len() as u64 <= MAX_MANIFEST,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit"
    );
    crate::domain::validate_json(&bytes)?;
    let manifest: Manifest = serde_json::from_slice(&bytes)?;
    crate::require!(
        manifest.schema == 1 && manifest.format == "midnight-zkir-forge/snapshot/v1",
        crate::error::Kind::SnapshotSchemaMismatch,
        "snapshot_schema_mismatch"
    );
    validate_id(&manifest.snapshot_id)?;
    crate::require!(
        manifest.snapshot_id == manifest.id()?
            && expected_id.is_none_or(|id| id == manifest.snapshot_id),
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: snapshot identity"
    );
    if let Some(p) = &manifest.partition {
        validate_id(p)?;
    }
    crate::require!(
        partition.is_none_or(|p| manifest.partition.as_deref() == Some(p)),
        crate::error::Kind::SnapshotPartitionMismatch,
        "snapshot_partition_mismatch"
    );
    crate::require!(
        manifest.producer
            == producer(
                manifest.producer.worker.is_some(),
                manifest.producer.worker31.is_some()
            )?,
        crate::error::Kind::SnapshotProfileMismatch,
        "snapshot_profile_mismatch: producer differs"
    );
    crate::require!(
        !manifest.files.is_empty() && manifest.files.len() <= MAX_FILES,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: inventory count"
    );
    let actual: Vec<_> = payload(&input, true)?
        .iter()
        .map(|p| p.strip_prefix(&input).unwrap().to_str().unwrap().to_owned())
        .collect();
    let listed: Vec<_> = manifest.files.iter().map(|e| e.path.clone()).collect();
    crate::require!(
        actual == listed,
        crate::error::Kind::IntegrityError,
        "snapshot_integrity_error: missing, extra, duplicate or unsorted inventory"
    );
    let staging = tempfile::tempdir_in(target.parent().unwrap())?;
    for dir in ["objects", "exports", "staging"] {
        fs::create_dir(staging.path().join(dir))?;
    }
    let mut total = bytes.len() as u64;
    crate::require!(
        total <= max_bytes,
        crate::error::Kind::SnapshotLimit,
        "snapshot_limit: byte budget exceeded"
    );
    for expected in &manifest.files {
        safe_path(&expected.path)?;
        validate_id(&expected.sha256)?;
        crate::require!(
            expected.bytes <= max_bytes - total,
            crate::error::Kind::SnapshotLimit,
            "snapshot_limit: byte budget exceeded"
        );
        let output = staging.path().join(&expected.path);
        fs::create_dir_all(output.parent().unwrap())?;
        let actual = copy_file(&input.join(&expected.path), &output, max_bytes - total)?;
        crate::require!(
            actual.sha256 == expected.sha256 && actual.bytes == expected.bytes,
            crate::error::Kind::IntegrityError,
            "snapshot_integrity_error: file differs"
        );
        total += actual.bytes;
    }
    let summary = validate_payload(staging.path(), &manifest.files)?;
    check_scope(&summary, scope)?;
    crate::require!(
        summary.has_v3 == manifest.producer.worker.is_some()
            && summary.has_v31 == manifest.producer.worker31.is_some(),
        crate::error::Kind::SnapshotProfileMismatch,
        "snapshot_profile_mismatch: worker declaration"
    );
    sync_tree(staging.path())?;
    crate::filesystem::publish_directory(staging.path(), &target)
        .context(crate::error::Kind::SnapshotPublishFailed)?;
    Ok(
        json!({"schema":1,"snapshot_id":manifest.snapshot_id,"manifest_sha256":hex::encode(Sha256::digest(&bytes)),"cache_dir":target,"partition":manifest.partition,"bytes":total,"summary":summary,"producer":manifest.producer}),
    )
}
