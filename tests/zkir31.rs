use midnight_zkir_forge::{
    descriptor::ArtifactDescriptor,
    engine::{self, ProfileSelector},
    store::Store,
    zkir3, zkir31,
};
use serde_json::Value;
use std::process::{Command, Stdio};
#[test]
fn distinct_minor_and_repository_contracts() {
    let old = include_bytes!("../fixtures/assert-v3.zkir");
    let modern = include_bytes!("../fixtures/assert-v31.zkir");
    assert!(engine::parse(old, Some(ProfileSelector::Zkir31)).is_err());
    assert!(engine::parse(modern, Some(ProfileSelector::Zkir3)).is_err());
    assert!(engine::parse(br#"{"version":{"major":3,"minor":2}}"#, None).is_err());
    assert_eq!(zkir3::SPEC.revision, zkir3::SPEC.ledger_revision);
    assert_ne!(zkir31::SPEC.revision, zkir31::SPEC.ledger_revision);
    assert_eq!(
        zkir31::SPEC.ledger_revision,
        "9a8777c4d035fc7f38ae286bcf5f8656668efd9f"
    );
}
#[test]
#[ignore = "paired official JSON3.1 worker and verified k4 parameters required"]
fn exact_profile_concurrency_and_descriptor() {
    let temp = tempfile::tempdir().unwrap();
    let input = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/assert-v31.zkir");
    let spawn = || {
        Command::new(env!("CARGO_BIN_EXE_midnight-zkir-forge"))
            .arg("--cache-dir")
            .arg(temp.path())
            .args(["--profile", "zkir31", "prepare"])
            .arg(&input)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap()
    };
    let a = spawn();
    let b = spawn();
    let decode = |p: std::process::Child| {
        let r = p.wait_with_output().unwrap();
        assert!(r.status.success(), "{}", String::from_utf8_lossy(&r.stderr));
        serde_json::from_slice::<Value>(&r.stdout).unwrap()
    };
    let a = decode(a);
    let b = decode(b);
    assert_ne!(a["cache"]["hit"], b["cache"]["hit"]);
    assert_eq!(a["artifact_set_id"], b["artifact_set_id"]);
    assert_eq!(a["ledger_revision"], zkir31::SPEC.ledger_revision);
    assert_eq!(a["worker"]["source_revision"], zkir31::REVISION);
    // A portable installer exposes only its stable CLI link. Resolve paired
    // workers beside the actual versioned executable, including on macOS.
    #[cfg(unix)]
    {
        let release = temp.path().join("version/bin");
        std::fs::create_dir_all(&release).unwrap();
        std::fs::copy(
            env!("CARGO_BIN_EXE_midnight-zkir-forge"),
            release.join("midnight-zkir-forge"),
        )
        .unwrap();
        let worker = std::env::var_os("MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                std::path::Path::new(env!("CARGO_BIN_EXE_midnight-zkir-forge"))
                    .parent()
                    .unwrap()
                    .join("midnight-zkir-forge-zkir31-worker")
            });
        std::os::unix::fs::symlink(worker, release.join("midnight-zkir-forge-zkir31-worker"))
            .unwrap();
        let stable = temp.path().join("stable-forge");
        std::os::unix::fs::symlink(release.join("midnight-zkir-forge"), &stable).unwrap();
        let result = Command::new(stable)
            .env_remove("MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER")
            .args(["--profile", "zkir31", "profile"])
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let value: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(value["ledger_revision"], zkir31::SPEC.ledger_revision);
    }
    let store = Store::open(temp.path()).unwrap();
    let (record, _) = store.load(a["bundle_id"].as_str().unwrap()).unwrap();
    let raw = std::fs::read(&input).unwrap();
    let descriptor = ArtifactDescriptor::from_record(&record, &raw).unwrap();
    let encoded = serde_json::to_vec(&descriptor).unwrap();
    assert!(ArtifactDescriptor::decode(&encoded).is_ok());
    let value = serde_json::to_value(descriptor).unwrap();
    assert!(
        String::from_utf8(encoded)
            .unwrap()
            .contains("verifier-key[v7]")
    );
    let mut wrong = value.clone();
    wrong["input_version"]["minor"] = 0.into();
    assert!(ArtifactDescriptor::decode(&serde_json::to_vec(&wrong).unwrap()).is_err());
    let mut wrong = value.clone();
    wrong["record"]["ledger_revision"] = zkir31::REVISION.into();
    assert!(ArtifactDescriptor::decode(&serde_json::to_vec(&wrong).unwrap()).is_err());
    let mut wrong = value;
    wrong["record"]["worker"]["source_revision"] = zkir31::SPEC.ledger_revision.into();
    assert!(ArtifactDescriptor::decode(&serde_json::to_vec(&wrong).unwrap()).is_err());
}
