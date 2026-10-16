//! Exact legacy JSON3.0 worker; its profile and identity remain unchanged.
pub const REVISION: &str = "3a7ae0361d03e6eed4fc91e31f6600f334f605d5";
pub const PROFILE: &str = "zkir3-3a7ae036/zkir-3.0.0-rc.1/transient-2.1.0/base-1.0.0/serialize-1.1.0/proofs-0.7.1/circuits-6.1.0/stdlib-1.1.0/curves-0.2.0/ir-source-v3-generic/forge-recipe-v1";
pub const FORMAT: &str = "midnight-zkir-v3-json";
pub const SPEC: crate::worker::WorkerSpec = crate::worker::WorkerSpec {
    profile: PROFILE,
    revision: REVISION,
    ledger_revision: REVISION,
    format: FORMAT,
    binary_ir_tag: "ir-source[v3-generic]",
    verifier_key_tag: "verifier-key[v6]",
    json_minor: 0,
    executable_name: "midnight-zkir-forge-zkir3-worker",
    override_env: "MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER",
};
pub fn call(
    action: &str,
    input: &[u8],
    params_dir: Option<&std::path::Path>,
    fetch: bool,
    output: Option<&std::path::Path>,
    expected: Option<&str>,
) -> anyhow::Result<(serde_json::Value, crate::domain::WorkerProvenance)> {
    SPEC.call(action, input, params_dir, fetch, output, expected)
}
pub fn generate(
    input: &[u8],
    k: u8,
    parameter_digest: &str,
    provenance: &crate::domain::WorkerProvenance,
    directory: Option<&std::path::Path>,
    fetch: bool,
) -> anyhow::Result<Vec<(crate::domain::ArtifactKind, Vec<u8>)>> {
    SPEC.generate(input, k, parameter_digest, provenance, directory, fetch)
}
