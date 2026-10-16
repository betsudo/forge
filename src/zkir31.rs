//! Independently pinned official Compact0.35 JSON3.1 graph.
pub const REVISION: &str = "e82d81d25aabcc5f5092e2bd559083487f577914";
pub const PROFILE: &str = "zkir31-e82d81d2/zkir-3.1.0-rc.1/transient-3.0.0/base-1.1.0/serialize-1.2.0/proofs-0.8.2/circuits-7.2.4/stdlib-2.3.5/curves-0.3.1/ir-source-v3-generic/forge-recipe-v1";
pub const FORMAT: &str = "midnight-zkir-v3.1-json";
pub const SPEC: crate::worker::WorkerSpec = crate::worker::WorkerSpec {
    profile: PROFILE,
    revision: REVISION,
    ledger_revision: "9a8777c4d035fc7f38ae286bcf5f8656668efd9f",
    format: FORMAT,
    binary_ir_tag: "ir-source[v3-generic]",
    verifier_key_tag: "verifier-key[v7]",
    json_minor: 1,
    executable_name: "midnight-zkir-forge-zkir31-worker",
    override_env: "MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER",
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
