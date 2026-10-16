use midnight_zkir_forge::{
    application,
    descriptor::ArtifactDescriptor,
    domain::*,
    error::{self, Kind},
    store::Store,
};
#[test]
fn strict_lazy_descriptor_and_error_policy() {
    let temp = tempfile::tempdir().unwrap();
    let store = Store::open(temp.path()).unwrap();
    let source = include_bytes!("../fixtures/assert.zkir");
    let record = application::import_bytes_with_profile(&store, source, "proof", None).unwrap();
    let descriptor = ArtifactDescriptor::from_record(&record, source).unwrap();
    let value = serde_json::to_value(&descriptor).unwrap();
    assert!(ArtifactDescriptor::decode(&serde_json::to_vec(&value).unwrap()).is_ok());
    for mutate in ["missing", "unknown", "nested", "version", "identity"] {
        let mut bad = value.clone();
        match mutate {
            "missing" => {
                bad.as_object_mut().unwrap().remove("serialization");
            }
            "unknown" => bad["unqualified"] = true.into(),
            "nested" => bad["record"]["source"]["ignored"] = true.into(),
            "version" => bad["input_version"]["minor"] = serde_json::Value::Null,
            _ => bad["record"]["source"]["digest"] = "0".repeat(64).into(),
        }
        assert!(
            ArtifactDescriptor::decode(&serde_json::to_vec(&bad).unwrap()).is_err(),
            "{mutate}"
        );
    }
    let mut duplicate = serde_json::to_string(&value).unwrap();
    duplicate.insert_str(1, "\"schema\":1,");
    assert!(ArtifactDescriptor::decode(duplicate.as_bytes()).is_err());
    let plain = anyhow::anyhow!("parameter server down or integrity issue: diagnostic only");
    assert_eq!(error::classify(&plain), Kind::InternalError);
    let invalid = plain
        .context(Kind::InvalidParameters)
        .context("accounting also failed");
    assert_eq!(error::classify(&invalid), Kind::InvalidParameters);
    assert!(!error::classify(&invalid).availability_fallback());
    assert!(Kind::ParametersUnavailable.availability_fallback());
    assert_eq!(Kind::InvalidParameters.status(), 422);
    assert_eq!(Kind::ParametersUnavailable.status(), 503);
}

#[test]
fn identity_premises_are_not_interchangeable() {
    use midnight_zkir_forge::{backend, descriptor::KEYGEN_RECIPE};
    let source = digest(b"isolated source control");
    let build = digest(b"isolated build control");
    let params = digest(b"isolated parameter control");
    let recipe = |s: &str, p: &str, r: &str, b: &str, k: u8, q: &str, o: &str| {
        identity("midnight-zkir-forge/derive/v1", &(s, p, r, b, k, q, o)).unwrap()
    };
    let baseline = recipe(
        &source,
        backend::PROFILE,
        backend::LEDGER_REV,
        &build,
        4,
        &params,
        KEYGEN_RECIPE,
    );
    let cases = [
        recipe(
            &digest(b"different source"),
            backend::PROFILE,
            backend::LEDGER_REV,
            &build,
            4,
            &params,
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            "isolated alternate profile",
            backend::LEDGER_REV,
            &build,
            4,
            &params,
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            backend::PROFILE,
            "isolated alternate revision",
            &build,
            4,
            &params,
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            backend::PROFILE,
            backend::LEDGER_REV,
            &digest(b"different build"),
            4,
            &params,
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            backend::PROFILE,
            backend::LEDGER_REV,
            &build,
            5,
            &params,
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            backend::PROFILE,
            backend::LEDGER_REV,
            &build,
            4,
            &digest(b"different actual parameter bytes"),
            KEYGEN_RECIPE,
        ),
        recipe(
            &source,
            backend::PROFILE,
            backend::LEDGER_REV,
            &build,
            4,
            &params,
            "isolated alternate options/serialization",
        ),
    ];
    assert!(cases.iter().all(|changed| changed != &baseline));
    let worker = WorkerProvenance {
        profile: midnight_zkir_forge::zkir3::PROFILE.into(),
        source_revision: midnight_zkir_forge::zkir3::REVISION.into(),
        build_fingerprint: build,
        executable_sha256: digest(b"worker one"),
    };
    let before = identity(
        "midnight-zkir-forge/derive-worker/v1",
        &(&DerivationId(baseline.clone()), &worker),
    )
    .unwrap();
    let mut changed = worker;
    changed.executable_sha256 = digest(b"worker two");
    assert_ne!(
        before,
        identity(
            "midnight-zkir-forge/derive-worker/v1",
            &(&DerivationId(baseline), &changed)
        )
        .unwrap()
    );
}

#[tokio::test]
#[ignore = "real supported descriptor premise controls; verified parameters required"]
async fn materialized_descriptor_rejects_conflicting_premises() {
    use midnight_zkir_forge::engine::ProfileSelector;
    for (selector, source) in [
        (
            ProfileSelector::Ledger8V2,
            include_bytes!("../fixtures/assert.zkir").as_slice(),
        ),
        (
            ProfileSelector::Zkir3,
            include_bytes!("../fixtures/assert-v3.zkir").as_slice(),
        ),
    ] {
        let temp = tempfile::tempdir().unwrap();
        let store = Store::open(temp.path()).unwrap();
        let record =
            application::import_bytes_with_profile(&store, source, "proof", Some(selector))
                .unwrap();
        let response = application::ensure_with_profile(
            &store,
            &record.bundle_id.0,
            "fixture",
            None,
            false,
            None,
            Some(selector),
        )
        .await
        .unwrap();
        let original = response["descriptor"].clone();
        assert!(ArtifactDescriptor::decode(&serde_json::to_vec(&original).unwrap()).is_ok());
        for field in [
            "serialization",
            "options",
            "build",
            "params",
            "output",
            "worker",
        ] {
            if field == "worker" && selector == ProfileSelector::Ledger8V2 {
                continue;
            }
            let mut bad = original.clone();
            match field {
                "serialization" => bad["serialization"]["binary_ir"] = "unqualified tag".into(),
                "options" => bad["keygen_recipe"] = "different generation options".into(),
                "build" => bad["record"]["build_fingerprint"] = "0".repeat(64).into(),
                "params" => bad["record"]["parameter_digest"] = "0".repeat(64).into(),
                "worker" => {
                    bad["record"].as_object_mut().unwrap().remove("worker");
                }
                _ => bad["record"]["artifact_set_id"] = "0".repeat(64).into(),
            }
            assert!(
                ArtifactDescriptor::decode(&serde_json::to_vec(&bad).unwrap()).is_err(),
                "{field}"
            );
        }
        let mut changed = source.to_vec();
        changed.push(b'\n');
        let second =
            application::import_bytes_with_profile(&store, &changed, "proof", Some(selector))
                .unwrap();
        let different = application::ensure_with_profile(
            &store,
            &second.bundle_id.0,
            "changed",
            None,
            false,
            None,
            Some(selector),
        )
        .await
        .unwrap();
        assert_ne!(response["bundle_id"], different["bundle_id"]);
        assert_ne!(response["derivation_id"], different["derivation_id"]);
        assert_eq!(different["cache"]["hit"], false);
    }
}
