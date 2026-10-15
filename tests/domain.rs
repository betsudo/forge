use midnight_zkir_forge::{backend, domain::*};
#[test]
fn rejects_ambiguous_json_and_unsafe_names() {
    assert!(backend::parse(br#"{"version":{"major":2,"major":2,"minor":0}}"#).is_err());
    for name in ["../escape", "/tmp/key", "a/b", ".", "", "a\\b"] {
        assert!(validate_name(name).is_err(), "{name}");
    }
    assert!(validate_name("circuit_1-read").is_ok());
    assert!(validate_id("../escape").is_err());
}
#[test]
fn exact_bytes_and_domain_separation() {
    assert_ne!(digest(b"{}"), digest(b"{}\n"));
    assert_ne!(
        identity("bundle/v1", &["a"]).unwrap(),
        identity("derive/v1", &["a"]).unwrap()
    );
    assert_eq!(
        digest(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}
