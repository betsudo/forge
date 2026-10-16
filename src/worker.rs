//! File-based private worker boundary; never mix its crypto types with ledger8 v2.
use crate::domain::{ArtifactKind, WorkerProvenance, digest};
use anyhow::{Context, Result};
use serde_json::Value;
use std::{
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
};

/// An explicitly compiled and pinned process boundary; no dynamic plugin loading.
#[derive(Debug)]
pub struct WorkerSpec {
    pub profile: &'static str,
    pub revision: &'static str,
    pub ledger_revision: &'static str,
    pub format: &'static str,
    pub binary_ir_tag: &'static str,
    pub verifier_key_tag: &'static str,
    pub json_minor: u64,
    pub executable_name: &'static str,
    pub override_env: &'static str,
}
impl WorkerSpec {
    fn executable(&self) -> Result<PathBuf> {
        if let Some(path) = std::env::var_os(self.override_env) {
            return Ok(path.into());
        }
        Ok(std::env::current_exe()?
            .canonicalize()?
            .parent()
            .context("CLI has no parent")?
            .join(self.executable_name))
    }
    pub fn call(
        &self,
        action: &str,
        input: &[u8],
        params_dir: Option<&Path>,
        fetch: bool,
        output: Option<&Path>,
        expected: Option<&str>,
    ) -> Result<(Value, WorkerProvenance)> {
        let executable = self.executable()?;
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
        crate::domain::validate_json(&result.stdout)
            .context(crate::error::Kind::WorkerProfileMismatch)?;
        let value: Value = serde_json::from_slice(&result.stdout)
            .context("invalid worker response")
            .context(crate::error::Kind::WorkerProfileMismatch)?;
        crate::require!(
            value["protocol"] == 1
                && value["profile"] == self.profile
                && value["source_revision"] == self.revision
                && value["format"] == self.format
                && value["binary_ir_tag"] == self.binary_ir_tag
                && value["build_fingerprint"]
                    .as_str()
                    .is_some_and(|v| v.len() == 64
                        && v.bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))),
            crate::error::Kind::WorkerProfileMismatch,
            "incomplete worker envelope"
        );
        if !result.status.success() {
            crate::require!(
                value["protocol"] == 1
                    && value["profile"] == self.profile
                    && value["source_revision"] == self.revision
                    && value["format"] == self.format,
                crate::error::Kind::WorkerProfileMismatch,
                "untrusted worker error envelope"
            );
            let fields = value.as_object().expect("worker object");
            crate::require!(
                fields.len() == 7 && value["failure"].as_object().is_some_and(|v| v.len() == 1),
                crate::error::Kind::WorkerProfileMismatch,
                "unexpected worker error fields"
            );
            let kind: crate::error::Kind = serde_json::from_value(value["failure"]["kind"].clone())
                .context(crate::error::Kind::WorkerProfileMismatch)?;
            return Err(anyhow::anyhow!(
                "ZKIR3 worker {action} failed: {}",
                String::from_utf8_lossy(&result.stderr)
            )
            .context(kind));
        }
        written?;
        crate::require!(
            value["protocol"] == 1
                && value["profile"] == self.profile
                && value["source_revision"] == self.revision
                && value["format"] == self.format,
            crate::error::Kind::WorkerProfileMismatch,
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
                profile: self.profile.to_owned(),
                source_revision: self.revision.to_owned(),
                build_fingerprint: fingerprint,
                executable_sha256,
            },
        ))
    }
    pub fn generate(
        &self,
        input: &[u8],
        k: u8,
        parameter_digest: &str,
        provenance: &WorkerProvenance,
        directory: Option<&Path>,
        fetch: bool,
    ) -> Result<Vec<(ArtifactKind, Vec<u8>)>> {
        let staging = tempfile::tempdir()?;
        let (response, actual) = self.call(
            "generate",
            input,
            directory,
            fetch,
            Some(staging.path()),
            Some(parameter_digest),
        )?;
        crate::require!(
            actual == *provenance
                && response["k"] == k
                && response["parameter_sha256"] == parameter_digest,
            crate::error::Kind::WorkerProfileMismatch,
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
            crate::require!(
                listed["sha256"] == digest(&bytes) && listed["bytes"] == bytes.len(),
                crate::error::Kind::IntegrityError,
                "worker artifact integrity_error"
            );
            outputs.push((kind, bytes));
        }
        Ok(outputs)
    }
}
