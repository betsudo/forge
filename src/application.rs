use crate::{
    backend,
    domain::*,
    engine,
    store::{Metric, Store, read_input},
};
use anyhow::{Context, Result, ensure};
use rusqlite::OptionalExtension;
use serde_json::{Value, json};
use std::{fs, path::Path, time::Instant};

pub fn import(store: &Store, input: &Path, name: Option<&str>) -> Result<Record> {
    import_with_profile(store, input, name, None)
}

pub fn import_with_profile(
    store: &Store,
    input: &Path,
    name: Option<&str>,
    profile: Option<engine::ProfileSelector>,
) -> Result<Record> {
    let bytes = read_input(input)?;
    let name = name
        .or_else(|| input.file_stem().and_then(|n| n.to_str()))
        .context("input needs a UTF-8 name or --name")?;
    import_bytes_with_profile(store, &bytes, name, profile)
}

/// Register exact uploaded bytes without accepting any server-local input path.
pub fn import_bytes_with_profile(
    store: &Store,
    bytes: &[u8],
    name: &str,
    profile: Option<engine::ProfileSelector>,
) -> Result<Record> {
    ensure!(bytes.len() <= 16 * 1024 * 1024, "input exceeds 16 MiB");
    let circuit = engine::parse(bytes, profile)?;
    validate_name(name)?;
    let source = Artifact {
        kind: ArtifactKind::Source,
        digest: digest(bytes),
        size: bytes.len() as u64,
    };
    let id = BundleId(identity(
        "midnight-zkir-forge/bundle/v1",
        &(name, circuit.format(), &source.digest),
    )?);
    let tx = store.lock()?;
    let existing = store
        .db
        .query_row("SELECT record FROM bundles WHERE id=?1", [&id.0], |r| {
            r.get::<_, String>(0)
        })
        .optional()?;
    let record = if let Some(text) = existing {
        let r: Record = serde_json::from_str(&text)?;
        store.read(&r.source)?;
        r
    } else {
        store.put(bytes)?;
        let r = Record {
            format: if matches!(circuit, engine::Circuit::V3(_)) {
                Some(circuit.format().to_owned())
            } else {
                None
            },
            worker: None,
            schema: 1,
            bundle_id: id,
            name: name.to_owned(),
            source,
            derivation_id: None,
            artifact_set_id: None,
            profile: None,
            build_fingerprint: None,
            ledger_revision: None,
            parameter_digest: None,
            k: None,
            artifacts: vec![],
            generation_ms: None,
        };
        store.save(&r, false)?;
        r
    };
    tx.commit()?;
    Ok(record)
}

pub async fn ensure_artifacts(
    store: &Store,
    id: &str,
    requested_path: &str,
    params_dir: Option<&Path>,
    fetch: bool,
    output: Option<&Path>,
) -> Result<Value> {
    ensure_with_profile(store, id, requested_path, params_dir, fetch, output, None).await
}

pub async fn ensure_with_profile(
    store: &Store,
    id: &str,
    requested_path: &str,
    params_dir: Option<&Path>,
    fetch: bool,
    output: Option<&Path>,
    profile: Option<engine::ProfileSelector>,
) -> Result<Value> {
    let start = Instant::now();
    let tx = store.lock()?;
    let lock_wait_ms = start.elapsed().as_secs_f64() * 1000.0;
    let result = ensure_locked(store, id, params_dir, fetch, output, profile).await;
    match result {
        Ok((mut response, record, hit, generation_ms)) => {
            let elapsed = start.elapsed().as_secs_f64() * 1000.0;
            let saved = if hit {
                record.generation_ms.unwrap_or(0.0)
            } else {
                0.0
            };
            store.record_metric(
                &Metric {
                    bundle: id,
                    path: requested_path,
                    operation: "ensure",
                    outcome: if hit { "hit" } else { "miss" },
                    elapsed_ms: elapsed,
                    generation_ms: Some(generation_ms),
                    saved_ms: saved,
                },
                &std::iter::once(record.source.clone())
                    .chain(record.artifacts.iter().cloned())
                    .collect::<Vec<_>>(),
            )?;
            tx.commit()?;
            response["lock_wait_ms"] = json!(lock_wait_ms);
            response["cache"] = json!({"hit":hit,"elapsed_ms":elapsed,"generation_ms":generation_ms,"estimated_generation_avoided_ms":saved});
            Ok(response)
        }
        Err(error) => {
            if let Err(rollback) = tx.rollback() {
                return Err(error.context(format!("rollback also failed: {rollback:#}")));
            }
            let artifacts = store
                .load(id)
                .map(|(r, _)| {
                    std::iter::once(r.source)
                        .chain(r.artifacts)
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            let accounting = store.metric(
                &Metric {
                    bundle: id,
                    path: requested_path,
                    operation: "ensure",
                    outcome: "error",
                    elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
                    generation_ms: None,
                    saved_ms: 0.0,
                },
                &artifacts,
            );
            match accounting {
                Ok(()) => Err(error),
                Err(accounting) => {
                    Err(error.context(format!("error accounting also failed: {accounting:#}")))
                }
            }
        }
    }
}
async fn ensure_locked(
    store: &Store,
    id: &str,
    params_dir: Option<&Path>,
    fetch: bool,
    output: Option<&Path>,
    profile: Option<engine::ProfileSelector>,
) -> Result<(Value, Record, bool, f64)> {
    let (mut record, ready) = store.load(id)?;
    let input = store.read(&record.source)?;
    let ir = engine::parse(&input, profile)?;
    let params = engine::parameters(&ir, params_dir, fetch).await?;
    let recipe = DerivationId(identity(
        "midnight-zkir-forge/derive/v1",
        &(
            &record.source.digest,
            params.profile(),
            params.revision(),
            build_fingerprint(),
            params.k(),
            params.digest(),
            "library-keygen/default-options/no-rng",
        ),
    )?);
    let recipe = if let Some(worker) = params.worker() {
        DerivationId(identity(
            "midnight-zkir-forge/derive-worker/v1",
            &(&recipe, worker),
        )?)
    } else {
        recipe
    };
    let same_recipe = record.derivation_id.as_ref() == Some(&recipe);
    let indexed: Option<(String, bool)> = store
        .db
        .query_row(
            "SELECT record,ready FROM derivations WHERE id=?1",
            [&recipe.0],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    let previous = indexed
        .as_ref()
        .map(|(text, _)| serde_json::from_str::<Record>(text))
        .transpose()?;
    let hit = (ready && same_recipe) || indexed.as_ref().is_some_and(|(_, ready)| *ready);
    if !(ready && same_recipe)
        && hit
        && let Some(cached) = &previous
    {
        record.derivation_id = cached.derivation_id.clone();
        record.artifact_set_id = cached.artifact_set_id.clone();
        record.profile = cached.profile.clone();
        record.build_fingerprint = cached.build_fingerprint.clone();
        record.ledger_revision = cached.ledger_revision.clone();
        record.parameter_digest = cached.parameter_digest.clone();
        record.k = cached.k;
        record.artifacts = cached.artifacts.clone();
        record.generation_ms = cached.generation_ms;
        record.worker = cached.worker.clone();
    }
    let mut generation_ms = 0.0;
    if hit {
        // A corrupt ready entry is an explicit failure, never a silent re-key.
        for artifact in &record.artifacts {
            store.verify(artifact)?;
        }
        store.save(&record, true)?;
    } else {
        let clock = Instant::now();
        let outputs = engine::generate(&ir, &params).await?;
        generation_ms = clock.elapsed().as_secs_f64() * 1000.0;
        let artifacts: Vec<Artifact> = outputs
            .iter()
            .map(|(kind, bytes)| Artifact {
                kind: *kind,
                digest: digest(bytes),
                size: bytes.len() as u64,
            })
            .collect();
        let set = ArtifactSetId(identity("midnight-zkir-forge/artifacts/v1", &artifacts)?);
        let expected = previous
            .as_ref()
            .and_then(|r| r.artifact_set_id.as_ref())
            .or({
                if same_recipe {
                    record.artifact_set_id.as_ref()
                } else {
                    None
                }
            });
        if let Some(expected) = expected {
            ensure!(
                *expected == set,
                "artifact_identity_changed: regenerated output differs; original identity retained"
            );
        }
        for (_, bytes) in &outputs {
            store.put(bytes)?;
        }
        record.derivation_id = Some(recipe);
        record.artifact_set_id = Some(set);
        record.profile = Some(params.profile().to_owned());
        record.worker = params.worker().cloned();
        record.build_fingerprint = Some(build_fingerprint());
        record.ledger_revision = Some(params.revision().to_owned());
        record.parameter_digest = Some(params.digest().to_owned());
        record.k = Some(params.k());
        record.artifacts = artifacts;
        record.generation_ms = Some(generation_ms);
        store.save(&record, true)?;
    }
    let paths = store.export(&record, output)?;
    Ok((
        json!({"schema":1,"bundle_id":record.bundle_id,"derivation_id":record.derivation_id,"artifact_set_id":record.artifact_set_id,"format":ir.format(),"worker":record.worker,"profile":record.profile,"build_fingerprint":record.build_fingerprint,"ledger_revision":record.ledger_revision,"export":paths}),
        record,
        hit,
        generation_ms,
    ))
}

pub fn resolve(
    store: &Store,
    id: &str,
    kind: Option<ArtifactKind>,
    output: Option<&Path>,
) -> Result<Value> {
    let clock = Instant::now();
    let tx = store.lock()?;
    let (record, ready) = store.load(id)?;
    ensure!(ready, "artifacts unavailable; run ensure explicitly");
    let mut export = store.export(&record, output)?;
    let selected: Vec<Artifact> = if let Some(kind) = kind {
        export["files"]
            .as_array_mut()
            .unwrap()
            .retain(|f| f["kind"] == serde_json::to_value(kind).unwrap());
        std::iter::once(&record.source)
            .chain(record.artifacts.iter())
            .filter(|a| a.kind == kind)
            .cloned()
            .collect()
    } else {
        std::iter::once(&record.source)
            .chain(record.artifacts.iter())
            .cloned()
            .collect()
    };
    store.record_metric(
        &Metric {
            bundle: id,
            path: "",
            operation: "resolve",
            outcome: "hit",
            elapsed_ms: clock.elapsed().as_secs_f64() * 1000.0,
            generation_ms: Some(0.0),
            saved_ms: 0.0,
        },
        &selected,
    )?;
    tx.commit()?;
    Ok(
        json!({"schema":1,"bundle_id":record.bundle_id,"artifact_set_id":record.artifact_set_id,"export":export}),
    )
}

pub fn build_fingerprint() -> String {
    let mut bytes = include_bytes!("../Cargo.lock").to_vec();
    bytes.extend(include_bytes!("backend.rs"));
    bytes.extend(include_bytes!("engine.rs"));
    bytes.extend(include_bytes!("zkir3.rs"));
    bytes.extend(include_bytes!("../Cargo.toml"));
    bytes.extend(include_bytes!("../flake.lock"));
    bytes.extend(env!("FORGE_RUSTC_VERSION").as_bytes());
    bytes.extend(include_bytes!("domain.rs"));
    bytes.extend(std::env::consts::ARCH.as_bytes());
    bytes.extend(std::env::consts::OS.as_bytes());
    digest(&bytes)
}

pub async fn qualify(params_dir: Option<&Path>, fetch: bool) -> Result<Value> {
    let raw = include_bytes!("../fixtures/assert.zkir");
    let ir = backend::parse(raw)?;
    let params = backend::parameters(&ir, params_dir, fetch).await?;
    let clock = Instant::now();
    let first = backend::generate(&ir, &params).await?;
    let cold_ms = clock.elapsed().as_secs_f64() * 1000.0;
    let second = backend::generate(&ir, &params).await?;
    ensure!(
        first == second,
        "backend generation is not byte reproducible"
    );
    let resolver = backend::LocalResolver {
        ir: first[0].1.clone(),
        prover: first[1].1.clone(),
        verifier: first[2].1.clone(),
    };
    backend::qualify(&params, &resolver).await?;
    Ok(
        json!({"schema":1,"profile":backend::PROFILE,"k":params.k,"parameter_sha256":params.digest,"generation_ms":cold_ms,"reproducible":true,"valid_proof_verified":true,"invalid_statement_rejected":true,"corrupt_proof_rejected":true,"artifacts":first.iter().map(|(k,b)|json!({"kind":k,"sha256":digest(b),"bytes":b.len()})).collect::<Vec<_>>()}),
    )
}

pub fn default_cache_dir() -> Result<std::path::PathBuf> {
    Ok(std::env::var_os("HOME")
        .context("HOME missing; supply --cache-dir")?
        .into())
    .map(|home: std::path::PathBuf| home.join(".midnight-zkir-forge"))
}

pub fn absolute_input(path: &Path) -> Result<String> {
    Ok(fs::canonicalize(path)?.to_string_lossy().into_owned())
}
