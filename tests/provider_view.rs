use midnight_zkir_forge::provider_view;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::fs;
fn fixture() -> (tempfile::TempDir, String) {
    let dir = tempfile::tempdir().unwrap();
    let info = json!({"compiler-version":"0.35.0","compiler-commit":"exact","language-version":"0.27.0","runtime-version":"0.20.0","circuits":[{"name":"test","proof":true}]});
    let mut manifest = json!({"manifest-version":"1","compiler-version":"0.35.0","compiler-commit":"exact","language-version":"0.27.0","runtime-version":"0.20.0"});
    for (path, bytes) in [
        (
            "compiler/contract-info.json",
            serde_json::to_vec(&info).unwrap(),
        ),
        ("contract/index.js", b"// original runtime".to_vec()),
        ("zkir/test.zkir", b"{}".to_vec()),
        ("zkir/test.bzkir", vec![1]),
        ("keys/test.prover", vec![2]),
        ("keys/test.verifier", vec![3]),
    ] {
        let (folder, file) = path.split_once('/').unwrap();
        fs::create_dir_all(dir.path().join(folder)).unwrap();
        fs::write(dir.path().join(path), &bytes).unwrap();
        if manifest.get(folder).is_none() {
            manifest[folder] = json!({"type":"directory"});
        }
        manifest[folder][file] =
            json!({"type":"file","size":bytes.len(),"hash":hex::encode(Sha256::digest(&bytes))});
    }
    let raw = serde_json::to_vec_pretty(&manifest).unwrap();
    let id = hex::encode(Sha256::digest(&raw));
    fs::write(dir.path().join("compiler/contract-manifest.json"), raw).unwrap();
    (dir, id)
}
#[test]
fn aggregate_budget_counts_metadata_and_is_explicit_at_every_entrypoint() {
    use midnight_zkir_forge::error::{Kind, classify};
    let (source, id) = fixture();
    let total = provider_view::verify(source.path(), &id).unwrap()["bytes"]
        .as_u64()
        .unwrap();
    let root = tempfile::tempdir().unwrap();
    let small = provider_view::Limits::new(total - 1).unwrap();
    for error in [
        provider_view::publish_with_limits(source.path(), &id, root.path(), small).unwrap_err(),
        provider_view::verify_with_limits(source.path(), &id, small).unwrap_err(),
        provider_view::read_with_limits(source.path(), &id, "keys/test.prover", small).unwrap_err(),
    ] {
        assert_eq!(classify(&error), Kind::ProviderLimit);
        assert!(!classify(&error).availability_fallback());
        assert!(format!("{error:#}").contains("--provider-max-view-bytes"));
    }
    assert_eq!(fs::read_dir(root.path()).unwrap().count(), 0);
    let exact = provider_view::Limits::new(total).unwrap();
    provider_view::publish_with_limits(source.path(), &id, root.path(), exact).unwrap();
    assert!(provider_view::verify_with_limits(&root.path().join(&id), &id, exact).is_ok());
    assert!(provider_view::publish_with_limits(source.path(), &id, root.path(), small).is_err());
    assert!(provider_view::verify(&root.path().join(&id), &id).is_ok());
}
#[test]
fn opt_in_never_relaxes_per_file_cap_or_publishes_failed_copies() {
    use midnight_zkir_forge::error::{Kind, classify};
    let (source, _) = fixture();
    let manifest_path = source.path().join("compiler/contract-manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(&manifest_path).unwrap()).unwrap();
    let original = fs::read(&manifest_path).unwrap();
    manifest["keys"]["test.prover"]["size"] = json!(1024u64.pow(3) + 1);
    let raw = serde_json::to_vec(&manifest).unwrap();
    fs::write(&manifest_path, &raw).unwrap();
    let id = hex::encode(Sha256::digest(&raw));
    let root = tempfile::tempdir().unwrap();
    let error = provider_view::publish_with_limits(
        source.path(),
        &id,
        root.path(),
        provider_view::Limits::new(provider_view::MAX_VIEW_BYTES).unwrap(),
    )
    .unwrap_err();
    assert_eq!(classify(&error), Kind::ProviderLimit);
    assert_eq!(fs::read_dir(root.path()).unwrap().count(), 0);
    fs::write(&manifest_path, &original).unwrap();
    let id = hex::encode(Sha256::digest(&original));
    // Fails after other files have been staged; retry leaves no partial identity.
    fs::write(source.path().join("zkir/test.bzkir"), [9]).unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
    assert_eq!(fs::read_dir(root.path()).unwrap().count(), 0);
    fs::write(source.path().join("zkir/test.bzkir"), [1]).unwrap();
    provider_view::publish(source.path(), &id, root.path()).unwrap();
    assert_eq!(fs::read_dir(root.path()).unwrap().count(), 1);
}
#[test]
fn preserves_original_bytes_and_reuses_only_verified_views() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    let value = provider_view::publish(source.path(), &id, root.path()).unwrap();
    assert_eq!(value["reused"], false);
    assert_eq!(
        fs::read(source.path().join("compiler/contract-manifest.json")).unwrap(),
        fs::read(
            root.path()
                .join(&id)
                .join("compiler/contract-manifest.json")
        )
        .unwrap()
    );
    assert_eq!(
        provider_view::publish(source.path(), &id, root.path()).unwrap()["reused"],
        true
    );
    fs::write(root.path().join(&id).join("keys/test.verifier"), [4]).unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
    assert!(provider_view::verify(&root.path().join(&id), &id).is_err());
    assert!(
        provider_view::read(
            &root.path().join(&id),
            &id,
            "compiler/contract-manifest.json"
        )
        .is_ok()
    );
    assert!(provider_view::read(&root.path().join(&id), &id, "keys/test.verifier").is_err());
}
#[test]
fn fails_on_incomplete_extra_and_changed_files() {
    for mutation in 0..3 {
        let (source, id) = fixture();
        let root = tempfile::tempdir().unwrap();
        match mutation {
            0 => fs::remove_file(source.path().join("compiler/contract-info.json")).unwrap(),
            1 => fs::write(source.path().join("extra"), [0]).unwrap(),
            _ => fs::write(source.path().join("contract/index.js"), [0]).unwrap(),
        };
        assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
        assert!(!root.path().join(&id).exists());
    }
}
#[test]
fn refuses_wrong_identity_and_undeclared_requests() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    assert!(provider_view::publish(source.path(), &"0".repeat(64), root.path()).is_err());
    provider_view::publish(source.path(), &id, root.path()).unwrap();
    for path in [
        "../keys/test.prover",
        "missing",
        "compiler/../contract/index.js",
    ] {
        assert!(provider_view::read(&root.path().join(&id), &id, path).is_err());
    }
}
#[cfg(unix)]
#[test]
fn rejects_symlinks() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    fs::remove_file(source.path().join("keys/test.prover")).unwrap();
    std::os::unix::fs::symlink(
        source.path().join("keys/test.verifier"),
        source.path().join("keys/test.prover"),
    )
    .unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
}
#[test]
fn no_replace_for_existing_empty_view() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    fs::create_dir(root.path().join(&id)).unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
    assert_eq!(fs::read_dir(root.path().join(&id)).unwrap().count(), 0);
}
#[test]
fn response_snapshot_survives_later_mutation() {
    use std::io::Read;
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    provider_view::publish(source.path(), &id, root.path()).unwrap();
    let (mut file, _, _) =
        provider_view::read(&root.path().join(&id), &id, "keys/test.prover").unwrap();
    fs::write(root.path().join(&id).join("keys/test.prover"), [9]).unwrap();
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes).unwrap();
    assert_eq!(bytes, vec![2]);
}
fn repin(source: &std::path::Path, edit: impl FnOnce(&mut serde_json::Value)) -> String {
    let path = source.join("compiler/contract-manifest.json");
    let mut value: serde_json::Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
    edit(&mut value);
    let raw = serde_json::to_vec(&value).unwrap();
    let id = hex::encode(Sha256::digest(&raw));
    fs::write(path, raw).unwrap();
    id
}
#[test]
fn malformed_manifest_hash_is_integrity_error_not_input_error() {
    use midnight_zkir_forge::error::{Kind, classify};
    let (source, _) = fixture();
    let id = repin(source.path(), |m| {
        m["keys"]["test.prover"]["hash"] = json!("bad")
    });
    for error in [
        provider_view::verify(source.path(), &id).unwrap_err(),
        provider_view::read(source.path(), &id, "keys/test.prover").unwrap_err(),
    ] {
        assert_eq!(classify(&error), Kind::IntegrityError);
        assert!(!classify(&error).availability_fallback());
    }
}
#[test]
fn refuses_metadata_mismatch_nested_manifest_and_limits() {
    for mutation in 0..3 {
        let (source, _) = fixture();
        let id = repin(source.path(), |value| match mutation {
            0 => value["runtime-version"] = "incompatible".into(),
            1 => value["keys"]["test.prover"]["size"] = (1024u64 * 1024 * 1024 + 1).into(),
            _ => value["contract"]["nested"] = json!({"type":"directory"}),
        });
        let root = tempfile::tempdir().unwrap();
        assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
    }
}
#[test]
fn rejects_duplicate_manifest_fields() {
    let (source, _) = fixture();
    let path = source.path().join("compiler/contract-manifest.json");
    let raw = fs::read_to_string(&path)
        .unwrap()
        .replacen('{', "{\"manifest-version\":\"1\",", 1);
    let id = hex::encode(Sha256::digest(raw.as_bytes()));
    fs::write(path, raw).unwrap();
    let root = tempfile::tempdir().unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
}
#[test]
fn concurrent_publication_verifies_winner() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    std::thread::scope(|scope| {
        let a = scope.spawn(|| provider_view::publish(source.path(), &id, root.path()));
        let b = scope.spawn(|| provider_view::publish(source.path(), &id, root.path()));
        assert!(a.join().unwrap().is_ok());
        assert!(b.join().unwrap().is_ok());
    });
    assert!(provider_view::read(&root.path().join(&id), &id, "keys/test.verifier").is_ok());
}
#[test]
fn provider_and_cache_roots_are_disjoint() {
    let root = tempfile::tempdir().unwrap();
    assert!(provider_view::separate_roots(root.path(), root.path()).is_err());
    assert!(
        provider_view::separate_roots(&root.path().join("cache/views"), &root.path().join("cache"))
            .is_err()
    );
    assert!(
        provider_view::separate_roots(&root.path().join("views"), &root.path().join("cache"))
            .is_ok()
    );
}
#[cfg(unix)]
#[test]
fn refuses_nonregular_manifest_without_blocking() {
    use std::os::unix::ffi::OsStrExt;
    let (source, id) = fixture();
    let path = source.path().join("compiler/contract-manifest.json");
    fs::remove_file(&path).unwrap();
    let raw = std::ffi::CString::new(path.as_os_str().as_bytes()).unwrap();
    assert_eq!(unsafe { libc::mkfifo(raw.as_ptr(), 0o600) }, 0);
    let root = tempfile::tempdir().unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
}
#[test]
fn commit_metadata_is_optional_but_paired() {
    let (source, _) = fixture();
    let info_path = source.path().join("compiler/contract-info.json");
    let mut info: serde_json::Value =
        serde_json::from_slice(&fs::read(&info_path).unwrap()).unwrap();
    info.as_object_mut().unwrap().remove("compiler-commit");
    let bytes = serde_json::to_vec(&info).unwrap();
    fs::write(info_path, &bytes).unwrap();
    let id = repin(source.path(), |value| {
        value.as_object_mut().unwrap().remove("compiler-commit");
        value["compiler"]["contract-info.json"] =
            json!({"type":"file","size":bytes.len(),"hash":hex::encode(Sha256::digest(&bytes))});
    });
    let root = tempfile::tempdir().unwrap();
    assert!(provider_view::publish(source.path(), &id, root.path()).is_ok());
    let id = repin(source.path(), |value| {
        value["compiler-commit"] = "one-sided".into()
    });
    assert!(provider_view::publish(source.path(), &id, root.path()).is_err());
}

#[test]
fn explicit_cache_publish_and_full_audit_work_without_home() {
    let (source, id) = fixture();
    let root = tempfile::tempdir().unwrap();
    let cli = env!("CARGO_BIN_EXE_zkir-forge");
    let published = std::process::Command::new(cli)
        .env_remove("HOME")
        .arg("--cache-dir")
        .arg(root.path().join("cache"))
        .arg("publish-view")
        .arg(source.path())
        .arg("--manifest-sha256")
        .arg(&id)
        .arg("--provider-root")
        .arg(root.path().join("views"))
        .output()
        .unwrap();
    assert!(
        published.status.success(),
        "{}",
        String::from_utf8_lossy(&published.stderr)
    );
    let target = root.path().join("views").join(&id);
    let audit = || {
        std::process::Command::new(cli)
            .env_remove("HOME")
            .arg("verify-view")
            .arg(&target)
            .arg("--manifest-sha256")
            .arg(&id)
            .output()
            .unwrap()
    };
    assert!(audit().status.success());
    fs::write(target.join("keys/test.prover"), [9]).unwrap();
    assert!(provider_view::read(&target, &id, "contract/index.js").is_ok());
    assert!(!audit().status.success());
    assert!(provider_view::read(&target, &id, "keys/test.prover").is_err());
}
