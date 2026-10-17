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

#[cfg(unix)]
#[test]
fn cargo_alias_uses_its_real_sibling_and_preserves_os_invocation() {
    use std::{
        fs,
        os::unix::fs::{PermissionsExt, symlink},
    };
    let root = tempfile::tempdir().unwrap();
    let bins = root.path().join("bin space");
    fs::create_dir(&bins).unwrap();
    let alias = bins.join("midnight-zkir-forge");
    fs::copy(env!("CARGO_BIN_EXE_midnight-zkir-forge"), &alias).unwrap();
    let link = root.path().join("legacy-link");
    symlink(&alias, &link).unwrap();
    // An unrelated PATH entry must never be selected for a missing sibling.
    let unrelated = root.path().join("zkir-forge");
    fs::write(&unrelated, "#!/bin/sh\nexit 42\n").unwrap();
    fs::set_permissions(&unrelated, fs::Permissions::from_mode(0o700)).unwrap();
    let missing = Command::new(&link)
        .env("PATH", root.path())
        .output()
        .unwrap();
    assert_eq!(missing.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&missing.stderr).contains("install both commands"));
    let primary = bins.join("zkir-forge");
    fs::hard_link(&alias, &primary).unwrap();
    let recursive = Command::new(&link).output().unwrap();
    assert_eq!(recursive.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&recursive.stderr).contains("compatibility launcher"));
    fs::remove_file(&primary).unwrap();
    fs::write(
        &primary,
        "#!/bin/sh\nprintf '%s\\n' \"$TEST_FORGE_ALIAS\" \"$@\"\nexit 7\n",
    )
    .unwrap();
    fs::set_permissions(&primary, fs::Permissions::from_mode(0o700)).unwrap();
    let result = Command::new(&link)
        .current_dir(root.path())
        .env("TEST_FORGE_ALIAS", "inherited")
        .args(["space argument", "ключ"])
        .output()
        .unwrap();
    assert_eq!(result.status.code(), Some(7));
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "inherited\nspace argument\nключ\n"
    );
}
