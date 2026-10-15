use midnight_zkir_forge::{application, backend, store::Store};
#[tokio::test]
#[ignore = "requires verified official parameters; run cargo test --test real_backend -- --ignored"]
async fn fresh_proof_and_regeneration() {
    let result = application::qualify(None, false).await.unwrap();
    assert_eq!(result["valid_proof_verified"], true);
    assert_eq!(result["invalid_statement_rejected"], true);
    assert_eq!(result["corrupt_proof_rejected"], true);
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let input = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert.zkir");
    let record = application::import(&store, &input, None).unwrap();
    let id = &record.bundle_id.0;
    let cold = application::ensure_artifacts(&store, id, "fixture", None, false, None)
        .await
        .unwrap();
    assert_eq!(cold["cache"]["hit"], false);
    let warm = application::ensure_artifacts(&store, id, "fixture", None, false, None)
        .await
        .unwrap();
    assert_eq!(warm["cache"]["hit"], true);
    let renamed = application::import(&store, &input, Some("renamed")).unwrap();
    let shared =
        application::ensure_artifacts(&store, &renamed.bundle_id.0, "renamed", None, false, None)
            .await
            .unwrap();
    assert_eq!(shared["cache"]["hit"], true);
    assert_eq!(shared["derivation_id"], cold["derivation_id"]);
    assert_eq!(shared["artifact_set_id"], cold["artifact_set_id"]);
    store.evict(&renamed.bundle_id.0, false).unwrap();
    store.evict(id, false).unwrap();
    let regenerated = application::ensure_artifacts(&store, id, "fixture", None, false, None)
        .await
        .unwrap();
    assert_eq!(cold["artifact_set_id"], regenerated["artifact_set_id"]);
    let stats = store.stats().unwrap();
    assert_eq!(stats["totals"]["misses"], 2);
    assert_eq!(stats["totals"]["hits"], 2);
    let (r, _) = store.load(id).unwrap();
    let ir = backend::parse(&store.read(&r.source).unwrap()).unwrap();
    let params = backend::parameters(&ir, None, false).await.unwrap();
    let resolver = backend::LocalResolver {
        ir: store.read(&r.artifacts[0]).unwrap(),
        prover: store.read(&r.artifacts[1]).unwrap(),
        verifier: store.read(&r.artifacts[2]).unwrap(),
    };
    backend::qualify(&params, &resolver).await.unwrap();
    std::fs::write(
        store.object_path(&r.artifacts[1].digest).unwrap(),
        b"corrupt",
    )
    .unwrap();
    assert!(
        application::ensure_artifacts(&store, id, "fixture", None, false, None)
            .await
            .is_err()
    );
    assert_eq!(store.stats().unwrap()["totals"]["errors"], 1);
}

#[test]
#[ignore = "real multi-process keygen; needs verified official parameters"]
fn processes_join_one_generation() {
    let temp = tempfile::tempdir().unwrap();
    let binary = env!("CARGO_BIN_EXE_midnight-zkir-forge");
    let fixture = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert.zkir");
    let spawn = || {
        std::process::Command::new(binary)
            .arg("--cache-dir")
            .arg(temp.path())
            .arg("prepare")
            .arg(&fixture)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .unwrap()
    };
    let a = spawn();
    let b = spawn();
    let a = a.wait_with_output().unwrap();
    let b = b.wait_with_output().unwrap();
    assert!(a.status.success(), "{}", String::from_utf8_lossy(&a.stderr));
    assert!(b.status.success(), "{}", String::from_utf8_lossy(&b.stderr));
    let a: serde_json::Value = serde_json::from_slice(&a.stdout).unwrap();
    let b: serde_json::Value = serde_json::from_slice(&b.stdout).unwrap();
    assert_ne!(a["cache"]["hit"], b["cache"]["hit"]);
    assert_eq!(a["artifact_set_id"], b["artifact_set_id"]);
    let store = Store::open(temp.path()).unwrap();
    let stats = store.stats().unwrap();
    assert_eq!(stats["totals"]["misses"], 1);
    assert_eq!(stats["totals"]["hits"], 1);
    assert_eq!(stats["files"].as_array().unwrap().len(), 4);
    for file in stats["files"].as_array().unwrap() {
        assert_eq!(file["hits"], 1);
        assert_eq!(file["misses"], 1);
    }
}

#[tokio::test]
#[ignore = "real identity-conflict regeneration; needs verified official parameters"]
async fn regenerated_identity_conflict_never_repoints() {
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let input = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert.zkir");
    let r = application::import(&store, &input, None).unwrap();
    let first = application::ensure_artifacts(&store, &r.bundle_id.0, "fixture", None, false, None)
        .await
        .unwrap();
    store.evict(&r.bundle_id.0, false).unwrap();
    let recipe = first["derivation_id"].as_str().unwrap();
    let original: String = store
        .db
        .query_row(
            "SELECT record FROM derivations WHERE id=?1",
            [recipe],
            |r| r.get(0),
        )
        .unwrap();
    let mut prior: serde_json::Value = serde_json::from_str(&original).unwrap();
    let expected = "0".repeat(64);
    prior["artifact_set_id"] = expected.clone().into();
    store
        .db
        .execute(
            "UPDATE derivations SET record=?1 WHERE id=?2",
            rusqlite::params![prior.to_string(), recipe],
        )
        .unwrap();
    let error = application::ensure_artifacts(&store, &r.bundle_id.0, "fixture", None, false, None)
        .await
        .unwrap_err();
    assert!(format!("{error:#}").contains("artifact_identity_changed"));
    assert!(!store.load(&r.bundle_id.0).unwrap().1);
    let retained: String = store
        .db
        .query_row(
            "SELECT record FROM derivations WHERE id=?1",
            [recipe],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        serde_json::from_str::<serde_json::Value>(&retained).unwrap()["artifact_set_id"],
        expected
    );
}
