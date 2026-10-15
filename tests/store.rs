use midnight_zkir_forge::{application, domain::*, store::Store};
#[test]
fn exact_import_and_tamper_refusal() {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path().join("cache");
    let store = Store::open(&root).unwrap();
    let input = temp.path().join("assert.zkir");
    std::fs::write(&input, include_bytes!("../fixtures/assert.zkir")).unwrap();
    let first = application::import(&store, &input, None).unwrap();
    let second = application::import(&store, &input, None).unwrap();
    assert_eq!(first.bundle_id, second.bundle_id);
    std::fs::write(
        store.object_path(&first.source.digest).unwrap(),
        b"tampered",
    )
    .unwrap();
    assert!(application::import(&store, &input, None).is_err());
}
#[test]
fn transaction_crash_rollback_and_eviction_keeps_shared_blob() {
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let source_bytes = include_bytes!("../fixtures/assert.zkir");
    let source_hash = store.put(source_bytes).unwrap();
    let output_hash = store.put(b"fixture-output").unwrap();
    let make = |name: &str| Record {
        schema: 1,
        bundle_id: BundleId(digest(name.as_bytes())),
        name: name.into(),
        source: Artifact {
            kind: ArtifactKind::Source,
            digest: source_hash.clone(),
            size: source_bytes.len() as u64,
        },
        derivation_id: Some(DerivationId(digest(b"recipe"))),
        artifact_set_id: Some(ArtifactSetId(digest(b"set"))),
        profile: Some("store-test-only".into()),
        build_fingerprint: None,
        ledger_revision: None,
        parameter_digest: None,
        k: None,
        artifacts: vec![Artifact {
            kind: ArtifactKind::Prover,
            digest: output_hash.clone(),
            size: 14,
        }],
        generation_ms: None,
    };
    let a = make("a");
    let b = make("b");
    {
        let _tx = store.lock().unwrap();
        store.save(&a, true).unwrap();
    } // drop = interrupted publication
    assert!(store.load(&a.bundle_id.0).is_err());
    store.save(&a, true).unwrap();
    store.save(&b, true).unwrap();
    store.evict(&a.bundle_id.0, false).unwrap();
    assert!(store.object_path(&output_hash).unwrap().exists());
    assert!(!store.load(&a.bundle_id.0).unwrap().1);
    assert!(store.load(&b.bundle_id.0).unwrap().1);
    store.evict(&b.bundle_id.0, false).unwrap();
    assert!(!store.object_path(&output_hash).unwrap().exists());
    assert!(store.object_path(&source_hash).unwrap().exists());
}
#[cfg(unix)]
#[test]
fn refuses_managed_symlinks() {
    use std::os::unix::fs::symlink;
    let temp = tempfile::tempdir().unwrap();
    let outside = temp.path().join("outside");
    std::fs::create_dir(&outside).unwrap();
    let root = temp.path().join("cache");
    symlink(&outside, &root).unwrap();
    assert!(Store::open(&root).is_err());
}

#[test]
fn retiring_last_recipe_reference_invalidates_index() {
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let input = temp.path().join("assert.zkir");
    std::fs::write(&input, include_bytes!("../fixtures/assert.zkir")).unwrap();
    let mut record = application::import(&store, &input, None).unwrap();
    let old = digest(b"old");
    record.derivation_id = Some(DerivationId(old.clone()));
    store.save(&record, true).unwrap();
    record.derivation_id = Some(DerivationId(digest(b"new")));
    store.save(&record, true).unwrap();
    let ready: bool = store
        .db
        .query_row("SELECT ready FROM derivations WHERE id=?1", [old], |r| {
            r.get(0)
        })
        .unwrap();
    assert!(!ready);
}
