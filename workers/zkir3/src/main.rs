//! Private one-shot worker. Its isolated Cargo graph matches the pinned consumer.
mod backend;
#[path = "../../../src/error.rs"]
#[allow(dead_code)]
mod error;
use anyhow::{Result, ensure};
use clap::Parser;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::{Read, Write},
    path::PathBuf,
    time::Instant,
};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ArtifactKind {
    Source,
    BinaryIr,
    Prover,
    Verifier,
}
pub fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
#[derive(Parser)]
struct Args {
    #[arg(value_parser=["profile","inspect","plan","generate","qualify","qualify-export"])]
    action: String,
    #[arg(long)]
    parent_pid: Option<u32>,
    #[arg(long)]
    params_dir: Option<PathBuf>,
    #[arg(long)]
    fetch_params: bool,
    #[arg(long)]
    expected_params: Option<String>,
    #[arg(long)]
    output: Option<PathBuf>,
    #[arg(long)]
    circuit_name: Option<String>,
}
fn fingerprint() -> String {
    let mut bytes = include_bytes!("../Cargo.lock").to_vec();
    bytes.extend(include_bytes!("../Cargo.toml"));
    bytes.extend(include_bytes!("main.rs"));
    bytes.extend(include_bytes!("backend.rs"));
    bytes.extend(include_bytes!("../../../src/error.rs"));
    bytes.extend(std::env::consts::ARCH.as_bytes());
    bytes.extend(std::env::consts::OS.as_bytes());
    digest(&bytes)
}
fn profile() -> Value {
    json!({"protocol":1,"profile":backend::PROFILE,"source_revision":backend::LEDGER_REV,"build_fingerprint":fingerprint(),"format":"midnight-zkir-v3-json","binary_ir_tag":"ir-source[v3-generic]"})
}
#[tokio::main(flavor = "current_thread")]
async fn main() {
    let args = Args::parse();
    #[cfg(unix)]
    if let Some(parent) = args.parent_pid {
        std::thread::spawn(move || {
            loop {
                // Stop orphan work after a killed owner; only the owner publishes CAS readiness.
                if unsafe { libc::getppid() } as u32 != parent {
                    std::process::exit(1);
                }
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
        });
    }
    match run(args).await {
        Ok(value) => println!("{value}"),
        Err(error) => {
            eprintln!("{error:#}");
            let mut response = profile();
            response["failure"] = json!({"kind":crate::error::classify(&error)});
            println!("{response}");
            std::process::exit(1);
        }
    }
}
async fn run(args: Args) -> Result<Value> {
    if args.action == "profile" {
        return Ok(profile());
    }
    let mut raw = Vec::new();
    if args.action == "qualify" || args.action == "qualify-export" {
        raw.extend(include_bytes!("../fixtures/assert.zkir"));
    } else {
        std::io::stdin()
            .take(16 * 1024 * 1024 + 1)
            .read_to_end(&mut raw)?;
        ensure!(raw.len() <= 16 * 1024 * 1024, "input too large");
    }
    let ir = backend::parse(&raw)?;
    if args.action == "inspect" {
        return Ok(profile());
    }
    let params = backend::parameters(&ir, args.params_dir.as_deref(), args.fetch_params).await?;
    if let Some(expected) = &args.expected_params {
        crate::require!(
            *expected == params.digest,
            crate::error::Kind::InvalidParameters,
            "parameter_identity_changed"
        );
    }
    let mut result = profile();
    result["k"] = json!(params.k);
    result["parameter_sha256"] = json!(params.digest);
    if args.action == "plan" {
        return Ok(result);
    }
    if args.action == "qualify-export" {
        let directory = args
            .output
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("export base missing"))?;
        let name = args
            .circuit_name
            .as_deref()
            .ok_or_else(|| anyhow::anyhow!("circuit name missing"))?;
        ensure!(
            !name.is_empty()
                && name
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-'),
            "invalid fixture circuit name"
        );
        let manifest: Value =
            serde_json::from_slice(&std::fs::read(directory.join("manifest.json"))?)?;
        ensure!(
            manifest["profile"] == backend::PROFILE,
            "export profile mismatch"
        );
        let mut bytes = Vec::new();
        for (kind, folder, extension) in [
            ("binary_ir", "zkir", "bzkir"),
            ("prover", "keys", "prover"),
            ("verifier", "keys", "verifier"),
        ] {
            let data = std::fs::read(directory.join(folder).join(format!("{name}.{extension}")))?;
            let entry = manifest["artifacts"]
                .as_array()
                .ok_or_else(|| anyhow::anyhow!("manifest artifact list"))?
                .iter()
                .find(|a| a["kind"] == kind)
                .ok_or_else(|| anyhow::anyhow!("manifest artifact missing"))?;
            ensure!(
                entry["digest"] == digest(&data) && entry["size"] == data.len(),
                "export integrity mismatch"
            );
            bytes.push(data);
        }
        backend::qualify(
            &params,
            &backend::LocalResolver {
                ir: bytes[0].clone(),
                prover: bytes[1].clone(),
                verifier: bytes[2].clone(),
            },
        )
        .await?;
        result["valid_proof_verified"] = json!(true);
        result["invalid_statement_rejected"] = json!(true);
        result["corrupt_proof_rejected"] = json!(true);
        result["used_exported_artifacts"] = json!(true);
        return Ok(result);
    }
    let clock = Instant::now();
    let first = backend::generate(&ir, &params).await?;
    result["generation_ms"] = json!(clock.elapsed().as_secs_f64() * 1000.0);
    if args.action == "qualify" {
        let second = backend::generate(&ir, &params).await?;
        ensure!(
            first == second,
            "backend generation is not byte reproducible"
        );
        backend::qualify(
            &params,
            &backend::LocalResolver {
                ir: first[0].1.clone(),
                prover: first[1].1.clone(),
                verifier: first[2].1.clone(),
            },
        )
        .await?;
        result["qualified_minor_versions"] = json!([0]);
        result["reproducible"] = json!(true);
        result["valid_proof_verified"] = json!(true);
        result["invalid_statement_rejected"] = json!(true);
        result["corrupt_proof_rejected"] = json!(true);
    } else {
        let directory = args
            .output
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("generate needs private output directory"))?;
        ensure!(directory.is_dir(), "output directory must exist");
        for (kind, bytes) in &first {
            let name = match kind {
                ArtifactKind::BinaryIr => "circuit.bzkir",
                ArtifactKind::Prover => "circuit.prover",
                ArtifactKind::Verifier => "circuit.verifier",
                ArtifactKind::Source => unreachable!(),
            };
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(directory.join(name))?;
            file.write_all(bytes)?;
            file.sync_all()?;
        }
    }
    result["artifacts"] = json!(
        first
            .iter()
            .map(|(kind, bytes)| json!({"kind":kind,"sha256":digest(bytes),"bytes":bytes.len()}))
            .collect::<Vec<_>>()
    );
    Ok(result)
}
