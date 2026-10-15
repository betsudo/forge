use crate::{
    backend,
    domain::{WorkerProvenance, validate_json},
    zkir3,
};
use anyhow::{Context, Result, bail, ensure};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum ProfileSelector {
    Ledger8V2,
    Zkir3,
}
pub enum Circuit {
    V2(midnight_zkir::IrSource),
    V3(Vec<u8>),
}
impl Circuit {
    pub fn format(&self) -> &'static str {
        match self {
            Self::V2(_) => "midnight-zkir-v2-json",
            Self::V3(_) => zkir3::FORMAT,
        }
    }
}
pub fn parse(raw: &[u8], selected: Option<ProfileSelector>) -> Result<Circuit> {
    validate_json(raw)?;
    let json: serde_json::Value = serde_json::from_slice(raw)?;
    let major = json["version"]["major"]
        .as_u64()
        .context("unsupported_zkir_version: expected a version object")?;
    match major {
        2 => {
            ensure!(
                selected != Some(ProfileSelector::Zkir3),
                "profile_format_mismatch: zkir3 requires major 3"
            );
            Ok(Circuit::V2(backend::parse(raw)?))
        }
        3 => {
            ensure!(
                selected != Some(ProfileSelector::Ledger8V2),
                "profile_format_mismatch: ledger8-v2 requires major 2"
            );
            zkir3::call("inspect", raw, None, false, None, None)?;
            Ok(Circuit::V3(raw.to_vec()))
        }
        _ => bail!("unsupported_zkir_version: {major}"),
    }
}
pub enum Parameters {
    V2(backend::Parameters),
    V3 {
        k: u8,
        digest: String,
        provenance: WorkerProvenance,
        directory: Option<std::path::PathBuf>,
        fetch: bool,
    },
}
impl Parameters {
    pub fn k(&self) -> u8 {
        match self {
            Self::V2(p) => p.k,
            Self::V3 { k, .. } => *k,
        }
    }
    pub fn digest(&self) -> &str {
        match self {
            Self::V2(p) => &p.digest,
            Self::V3 { digest, .. } => digest,
        }
    }
    pub fn profile(&self) -> &str {
        match self {
            Self::V2(_) => backend::PROFILE,
            Self::V3 { .. } => zkir3::PROFILE,
        }
    }
    pub fn revision(&self) -> &str {
        match self {
            Self::V2(_) => backend::LEDGER_REV,
            Self::V3 { .. } => zkir3::REVISION,
        }
    }
    pub fn worker(&self) -> Option<&WorkerProvenance> {
        match self {
            Self::V2(_) => None,
            Self::V3 { provenance, .. } => Some(provenance),
        }
    }
}
pub async fn parameters(ir: &Circuit, directory: Option<&Path>, fetch: bool) -> Result<Parameters> {
    match ir {
        Circuit::V2(ir) => Ok(Parameters::V2(
            backend::parameters(ir, directory, fetch).await?,
        )),
        Circuit::V3(raw) => {
            let (value, provenance) = zkir3::call("plan", raw, directory, fetch, None, None)?;
            let k = value["k"]
                .as_u64()
                .context("worker k missing")?
                .try_into()?;
            let digest = value["parameter_sha256"]
                .as_str()
                .context("worker parameter hash missing")?
                .to_owned();
            crate::domain::validate_id(&digest)?;
            Ok(Parameters::V3 {
                k,
                digest,
                provenance,
                directory: directory.map(Path::to_owned),
                fetch,
            })
        }
    }
}
pub async fn generate(
    ir: &Circuit,
    params: &Parameters,
) -> Result<Vec<(crate::domain::ArtifactKind, Vec<u8>)>> {
    match (ir, params) {
        (Circuit::V2(ir), Parameters::V2(p)) => backend::generate(ir, p).await,
        (
            Circuit::V3(raw),
            Parameters::V3 {
                k,
                digest,
                provenance,
                directory,
                fetch,
            },
        ) => zkir3::generate(raw, *k, digest, provenance, directory.as_deref(), *fetch),
        _ => bail!("profile_format_mismatch: mixed backend plan"),
    }
}
