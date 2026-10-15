//! File-based private worker boundary; never mix its crypto types with ledger8 v2.
use crate::domain::{ArtifactKind, WorkerProvenance, digest};
use anyhow::{Context, Result, ensure};
use serde_json::Value;
use std::{
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
};

pub const REVISION: &str = "3a7ae0361d03e6eed4fc91e31f6600f334f605d5";
pub const PROFILE: &str = "zkir3-3a7ae036/zkir-3.0.0-rc.1/transient-2.1.0/base-1.0.0/serialize-1.1.0/proofs-0.7.1/circuits-6.1.0/stdlib-1.1.0/curves-0.2.0/ir-source-v3-generic/forge-recipe-v1";
pub const FORMAT: &str = "midnight-zkir-v3-json";
fn executable() -> Result<PathBuf> {
    if let Some(path) = std::env::var_os("MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER") {
        return Ok(path.into());
    }
    Ok(std::env::current_exe()?
        .parent()
        .context("CLI has no parent")?
        .join("midnight-zkir-forge-zkir3-worker"))
}
pub fn call(
    action: &str,
    input: &[u8],
    params_dir: Option<&Path>,
    fetch: bool,
    output: Option<&Path>,
    expected: Option<&str>,
) -> Result<(Value, WorkerProvenance)> {
    let executable = executable()?;
    let executable_sha256=digest(&std::fs::read(&executable).with_context(||format!("ZKIR3 worker unavailable at {}; rebuild using scripts/install-local.sh or build the worker",executable.display()))?);
    let mut command = Command::new(&executable);
    command
        .arg(action)
        .arg("--parent-pid")
        .arg(std::process::id().to_string())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if let Some(path) = params_dir {
        command.arg("--params-dir").arg(path);
    }
    if fetch {
        command.arg("--fetch-params");
    }
    if let Some(path) = output {
        command.arg("--output").arg(path);
    }
    if let Some(hash) = expected {
        command.arg("--expected-params").arg(hash);
    }
    let mut child = command.spawn().context("start pinned ZKIR3 worker")?;
    let written = child.stdin.take().context("worker stdin")?.write_all(input);
    let result = child.wait_with_output()?;
    ensure!(
        result.status.success(),
        "ZKIR3 worker {action} failed: {}",
        String::from_utf8_lossy(&result.stderr)
    );
    written?;
    let value: Value = serde_json::from_slice(&result.stdout).context("invalid worker response")?;
    ensure!(
        value["protocol"] == 1
            && value["profile"] == PROFILE
            && value["source_revision"] == REVISION
            && value["format"] == FORMAT,
        "worker_profile_mismatch: unexpected v3 backend"
    );
    let fingerprint = value["build_fingerprint"]
        .as_str()
        .context("worker fingerprint missing")?
        .to_owned();
    crate::domain::validate_id(&fingerprint)?;
    Ok((
        value,
        WorkerProvenance {
            profile: PROFILE.to_owned(),
            source_revision: REVISION.to_owned(),
            build_fingerprint: fingerprint,
            executable_sha256,
        },
    ))
}
pub fn generate(
    input: &[u8],
    k: u8,
    parameter_digest: &str,
    provenance: &WorkerProvenance,
    directory: Option<&Path>,
    fetch: bool,
) -> Result<Vec<(ArtifactKind, Vec<u8>)>> {
    let staging = tempfile::tempdir()?;
    let (response, actual) = call(
        "generate",
        input,
        directory,
        fetch,
        Some(staging.path()),
        Some(parameter_digest),
    )?;
    ensure!(
        actual == *provenance
            && response["k"] == k
            && response["parameter_sha256"] == parameter_digest,
        "worker_identity_changed: re-plan required"
    );
    let mut outputs = Vec::new();
    for (kind, name) in [
        (ArtifactKind::BinaryIr, "circuit.bzkir"),
        (ArtifactKind::Prover, "circuit.prover"),
        (ArtifactKind::Verifier, "circuit.verifier"),
    ] {
        let bytes = std::fs::read(staging.path().join(name))?;
        let listed = response["artifacts"]
            .as_array()
            .context("worker artifact inventory missing")?
            .iter()
            .find(|a| a["kind"] == serde_json::to_value(kind).unwrap())
            .context("worker output missing")?;
        ensure!(
            listed["sha256"] == digest(&bytes) && listed["bytes"] == bytes.len(),
            "worker artifact integrity_error"
        );
        outputs.push((kind, bytes));
    }
    Ok(outputs)
}
