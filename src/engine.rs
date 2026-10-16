use crate::{
    backend,
    domain::{WorkerProvenance, validate_json},
    zkir3, zkir31,
};
use anyhow::{Context, Result, bail};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum ProfileSelector {
    Ledger8V2,
    Zkir3,
    Zkir31,
}
pub enum Circuit {
    V2(midnight_zkir::IrSource),
    V3(Vec<u8>),
    V31(Vec<u8>),
}
impl ProfileSelector {
    pub fn worker(self) -> Option<&'static crate::worker::WorkerSpec> {
        match self {
            Self::Ledger8V2 => None,
            Self::Zkir3 => Some(&zkir3::SPEC),
            Self::Zkir31 => Some(&zkir31::SPEC),
        }
    }
}
impl Circuit {
    pub fn worker(&self) -> Option<&'static crate::worker::WorkerSpec> {
        match self {
            Self::V2(_) => None,
            Self::V3(_) => Some(&zkir3::SPEC),
            Self::V31(_) => Some(&zkir31::SPEC),
        }
    }

    pub fn format(&self) -> &'static str {
        match self {
            Self::V2(_) => "midnight-zkir-v2-json",
            Self::V3(_) => zkir3::FORMAT,
            Self::V31(_) => zkir31::FORMAT,
        }
    }
}
pub fn parse(raw: &[u8], selected: Option<ProfileSelector>) -> Result<Circuit> {
    validate_json(raw).context(crate::error::Kind::InvalidInput)?;
    let json: serde_json::Value =
        serde_json::from_slice(raw).context(crate::error::Kind::InvalidInput)?;
    let major = json["version"]["major"]
        .as_u64()
        .context("unsupported_zkir_version: expected a version object")
        .context(crate::error::Kind::UnsupportedZkirVersion)?;
    match major {
        2 => {
            crate::require!(
                selected.is_none_or(|p| p == ProfileSelector::Ledger8V2),
                crate::error::Kind::ProfileFormatMismatch,
                "profile_format_mismatch: zkir3 requires major 3"
            );
            Ok(Circuit::V2(backend::parse(raw)?))
        }
        3 => {
            crate::require!(
                selected != Some(ProfileSelector::Ledger8V2),
                crate::error::Kind::ProfileFormatMismatch,
                "profile_format_mismatch: ledger8-v2 requires major 2"
            );
            let minor = json["version"]["minor"]
                .as_u64()
                .context(crate::error::Kind::UnsupportedZkirVersion)?;
            let selector = match minor {
                0 => ProfileSelector::Zkir3,
                1 => ProfileSelector::Zkir31,
                _ => return Err(anyhow::anyhow!(crate::error::Kind::UnsupportedZkirVersion)),
            };
            crate::require!(
                selected.is_none_or(|p| p == selector),
                crate::error::Kind::ProfileFormatMismatch,
                "exact source minor/profile mismatch"
            );
            selector
                .worker()
                .unwrap()
                .call("inspect", raw, None, false, None, None)?;
            Ok(if minor == 0 {
                Circuit::V3(raw.to_vec())
            } else {
                Circuit::V31(raw.to_vec())
            })
        }
        _ => Err(anyhow::anyhow!("unsupported_zkir_version: {major}")
            .context(crate::error::Kind::UnsupportedZkirVersion)),
    }
}
pub enum Parameters {
    V2(backend::Parameters),
    V3 {
        backend: &'static crate::worker::WorkerSpec,
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
            Self::V3 { backend, .. } => backend.profile,
        }
    }
    pub fn revision(&self) -> &str {
        match self {
            Self::V2(_) => backend::LEDGER_REV,
            Self::V3 { backend, .. } => backend.ledger_revision,
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
        Circuit::V3(raw) | Circuit::V31(raw) => {
            let backend = ir.worker().unwrap();
            let (value, provenance) = backend.call("plan", raw, directory, fetch, None, None)?;
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
                backend,
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
            Circuit::V3(raw) | Circuit::V31(raw),
            Parameters::V3 {
                backend,
                k,
                digest,
                provenance,
                directory,
                fetch,
            },
        ) => {
            crate::require!(
                ir.worker().is_some_and(|w| w.profile == backend.profile),
                crate::error::Kind::ProfileFormatMismatch,
                "generation profile mismatch"
            );
            backend.generate(raw, *k, digest, provenance, directory.as_deref(), *fetch)
        }
        _ => bail!(crate::error::Kind::ProfileFormatMismatch),
    }
}
