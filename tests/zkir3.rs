use midnight_zkir_forge::{
    application,
    engine::{self, ProfileSelector},
    store::Store,
};
use serde_json::Value;
use std::process::{Command, Stdio};
fn cli() -> &'static str {
    env!("CARGO_BIN_EXE_midnight-zkir-forge")
}
fn fixture() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert-v3.zkir")
}
#[test]
fn rejects_wrong_profile_and_unknown_versions() {
    assert!(
        engine::parse(
            include_bytes!("../fixtures/assert.zkir"),
            Some(ProfileSelector::Zkir3)
        )
        .is_err()
    );
    assert!(
        engine::parse(
            include_bytes!("../fixtures/assert-v3.zkir"),
            Some(ProfileSelector::Ledger8V2)
        )
        .is_err()
    );
    assert!(engine::parse(br#"{"version":{"major":4,"minor":0}}"#, None).is_err());
    let raw = br#"{"version":{"major":3,"minor":0},"version":{"major":2,"minor":0}}"#;
    assert!(engine::parse(raw, None).is_err());
}
fn run(root: &std::path::Path, args: &[&str]) -> Value {
    let result = Command::new(cli())
        .arg("--cache-dir")
        .arg(root)
        .args(args)
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    serde_json::from_slice(&result.stdout).unwrap()
}
#[test]
#[ignore = "real v3 proof/cache qualification; verified parameters required"]
fn real_v3_proofs_cache_identity_and_profile_separation() {
    let result = Command::new(cli())
        .args(["--profile", "zkir3", "qualify"])
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let proof: Value = serde_json::from_slice(&result.stdout).unwrap();
    for key in [
        "reproducible",
        "valid_proof_verified",
        "invalid_statement_rejected",
        "corrupt_proof_rejected",
    ] {
        assert_eq!(proof[key], true, "{key}");
    }
    let temp = tempfile::tempdir().unwrap();
    let path = fixture();
    let input = path.to_str().unwrap();
    let cold = run(
        temp.path(),
        &["--profile", "zkir3", "prepare", input, "--name", "same"],
    );
    let warm = run(temp.path(), &["prepare", input, "--name", "same"]);
    assert_eq!(cold["cache"]["hit"], false);
    assert_eq!(warm["cache"]["hit"], true);
    assert_eq!(cold["artifact_set_id"], warm["artifact_set_id"]);
    let worker = std::env::var_os("MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| {
            std::path::Path::new(cli())
                .parent()
                .unwrap()
                .join("midnight-zkir-forge-zkir3-worker")
        });
    let prove_export = |result: &Value| {
        let output = Command::new(&worker)
            .args([
                "qualify-export",
                "--output",
                result["export"]["base"].as_str().unwrap(),
                "--circuit-name",
                "same",
            ])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert_eq!(
            serde_json::from_slice::<Value>(&output.stdout).unwrap()["used_exported_artifacts"],
            true
        );
    };
    prove_export(&warm);

    assert_eq!(
        cold["worker"]["source_revision"],
        midnight_zkir_forge::zkir3::REVISION
    );
    let v2path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert.zkir");
    let v2 = run(
        temp.path(),
        &["prepare", v2path.to_str().unwrap(), "--name", "same"],
    );
    assert_ne!(v2["bundle_id"], cold["bundle_id"]);
    assert_ne!(v2["derivation_id"], cold["derivation_id"]);
    let get_ir = |result: &Value| {
        result["export"]["files"]
            .as_array()
            .unwrap()
            .iter()
            .find(|f| f["kind"] == "binary_ir")
            .unwrap()["sha256"]
            .clone()
    };
    assert_ne!(get_ir(&v2), get_ir(&cold));
    let id = cold["bundle_id"].as_str().unwrap();
    run(temp.path(), &["evict", id]);
    let regenerated = run(temp.path(), &["ensure", id]);
    assert_eq!(regenerated["cache"]["hit"], false);
    assert_eq!(cold["artifact_set_id"], regenerated["artifact_set_id"]);
    prove_export(&regenerated);
    let mut unsupported: Value =
        serde_json::from_slice(include_bytes!("../fixtures/assert-v3.zkir")).unwrap();
    unsupported["version"]["minor"] = 1.into();
    let unsupported_path = temp.path().join("unsupported.zkir");
    std::fs::write(&unsupported_path, unsupported.to_string()).unwrap();
    let refused = Command::new(cli())
        .arg("--cache-dir")
        .arg(temp.path())
        .arg("prepare")
        .arg(unsupported_path)
        .output()
        .unwrap();
    assert!(!refused.status.success());

    // Corruption is refused, including when the worker would be able to regenerate.
    let store = Store::open(temp.path()).unwrap();
    let (record, _) = store.load(id).unwrap();
    std::fs::write(
        store.object_path(&record.artifacts[1].digest).unwrap(),
        b"corrupt",
    )
    .unwrap();
    let bad = Command::new(cli())
        .arg("--cache-dir")
        .arg(temp.path())
        .args(["ensure", id])
        .output()
        .unwrap();
    assert!(!bad.status.success());
    assert_eq!(
        serde_json::from_slice::<Value>(&bad.stdout).unwrap()["error"]["code"],
        "integrity_error"
    );
}
#[test]
#[ignore = "real v3 concurrent process keygen; verified parameters required"]
fn processes_join_v3_generation() {
    let temp = tempfile::tempdir().unwrap();
    let path = fixture();
    let spawn = || {
        Command::new(cli())
            .arg("--cache-dir")
            .arg(temp.path())
            .arg("prepare")
            .arg(&path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap()
    };
    let a = spawn();
    let b = spawn();
    let a = a.wait_with_output().unwrap();
    let b = b.wait_with_output().unwrap();
    assert!(a.status.success(), "{}", String::from_utf8_lossy(&a.stderr));
    assert!(b.status.success(), "{}", String::from_utf8_lossy(&b.stderr));
    let a: Value = serde_json::from_slice(&a.stdout).unwrap();
    let b: Value = serde_json::from_slice(&b.stdout).unwrap();
    assert_ne!(a["cache"]["hit"], b["cache"]["hit"]);
    assert_eq!(a["artifact_set_id"], b["artifact_set_id"]);
}
#[test]
fn old_v2_record_fields_remain_absent() {
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let input = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert.zkir");
    let record = application::import(&store, &input, None).unwrap();
    let json = serde_json::to_value(record).unwrap();
    assert!(json.get("format").is_none());
    assert!(json.get("worker").is_none());
}
