//! Real proof control for the minimal assert fixture downloaded by HTTP e2e.
//! This is not a general-purpose circuit prover.
use anyhow::{Context, Result, ensure};
use midnight_zkir_forge::{backend, domain::digest};
use serde_json::{Value, json};
use std::path::PathBuf;
#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<()> {
    let directory = PathBuf::from(
        std::env::args_os()
            .nth(1)
            .context("fixture export directory required")?,
    );
    let manifest: Value = serde_json::from_slice(&std::fs::read(directory.join("manifest.json"))?)?;
    ensure!(
        manifest["profile"] == backend::PROFILE,
        "exact v2 profile required"
    );
    let mut artifacts = Vec::new();
    for (kind, folder, extension) in [
        ("binary_ir", "zkir", "bzkir"),
        ("prover", "keys", "prover"),
        ("verifier", "keys", "verifier"),
    ] {
        let bytes = std::fs::read(directory.join(folder).join(format!("proof.{extension}")))?;
        let entry = manifest["artifacts"]
            .as_array()
            .context("artifact inventory missing")?
            .iter()
            .find(|v| v["kind"] == kind)
            .context("artifact missing")?;
        ensure!(
            entry["digest"] == digest(&bytes) && entry["size"] == bytes.len(),
            "download integrity mismatch"
        );
        artifacts.push(bytes);
    }
    let ir = backend::parse(include_bytes!("../fixtures/assert.zkir"))?;
    let params = backend::parameters(
        &ir,
        std::env::var_os("MIDNIGHT_PP")
            .map(PathBuf::from)
            .as_deref(),
        false,
    )
    .await?;
    backend::qualify(
        &params,
        &backend::LocalResolver {
            ir: artifacts.remove(0),
            prover: artifacts.remove(0),
            verifier: artifacts.remove(0),
        },
    )
    .await?;
    println!(
        "{}",
        json!({"valid_proof_verified":true,"invalid_statement_rejected":true,"corrupt_proof_rejected":true,"used_downloaded_artifacts":true})
    );
    Ok(())
}
