use std::process::Command;
#[test]
fn primary_and_legacy_share_help_version_profile_and_store() {
    let names = [
        env!("CARGO_BIN_EXE_zkir-forge"),
        env!("CARGO_BIN_EXE_midnight-zkir-forge"),
    ];
    for args in [["--version"], ["--help"]] {
        let results = names.map(|name| Command::new(name).args(args).output().unwrap());
        assert!(results.iter().all(|r| r.status.success()));
        assert_eq!(results[0].stdout, results[1].stdout);
        assert!(String::from_utf8_lossy(&results[0].stdout).contains("zkir-forge"));
    }
    let profiles = names.map(|name| Command::new(name).arg("profile").output().unwrap());
    assert!(profiles.iter().all(|r| r.status.success()));
    assert_eq!(profiles[0].stdout, profiles[1].stdout);
    let cache = tempfile::tempdir().unwrap();
    let imported = names.map(|name| {
        let out = Command::new(name)
            .arg("--cache-dir")
            .arg(cache.path())
            .args(["import", "fixtures/assert.zkir"])
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        serde_json::from_slice::<serde_json::Value>(&out.stdout).unwrap()
    });
    assert_eq!(imported[0]["bundle_id"], imported[1]["bundle_id"]);
    assert!(imported[0]["bundle_id"].as_str().is_some());
}
