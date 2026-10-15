use anyhow::Result;
use serde::{
    Deserialize, Serialize,
    de::{self, MapAccess, SeqAccess, Visitor},
};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, fmt};

pub fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
pub fn identity(domain: &str, value: &impl Serialize) -> Result<String> {
    let mut bytes = domain.as_bytes().to_vec();
    bytes.push(0);
    bytes.extend(serde_json::to_vec(value)?);
    Ok(digest(&bytes))
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BundleId(pub String);
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DerivationId(pub String);
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArtifactSetId(pub String);

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, clap::ValueEnum)]
#[serde(rename_all = "snake_case")]
pub enum ArtifactKind {
    Source,
    BinaryIr,
    Prover,
    Verifier,
}
impl ArtifactKind {
    pub fn extension(self) -> &'static str {
        match self {
            Self::Source => "zkir",
            Self::BinaryIr => "bzkir",
            Self::Prover => "prover",
            Self::Verifier => "verifier",
        }
    }
    pub fn folder(self) -> &'static str {
        match self {
            Self::Source | Self::BinaryIr => "zkir",
            _ => "keys",
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Artifact {
    pub kind: ArtifactKind,
    pub digest: String,
    pub size: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub format: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub worker: Option<WorkerProvenance>,
    pub schema: u32,
    pub bundle_id: BundleId,
    pub name: String,
    pub source: Artifact,
    pub derivation_id: Option<DerivationId>,
    pub artifact_set_id: Option<ArtifactSetId>,
    pub profile: Option<String>,
    pub build_fingerprint: Option<String>,
    pub ledger_revision: Option<String>,
    pub parameter_digest: Option<String>,
    pub k: Option<u8>,
    pub artifacts: Vec<Artifact>,
    pub generation_ms: Option<f64>,
}
pub fn validate_name(name: &str) -> Result<()> {
    crate::require!(
        !name.is_empty()
            && name.len() <= 128
            && name
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-'),
        crate::error::Kind::InvalidInput,
        "invalid circuit name: use 1–128 ASCII letters, digits, underscores or hyphens"
    );
    Ok(())
}
pub fn validate_id(id: &str) -> Result<()> {
    crate::require!(
        id.len() == 64
            && id
                .bytes()
                .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase()),
        crate::error::Kind::InvalidInput,
        "invalid bundle id"
    );
    Ok(())
}

// The official parser uses Value; reject duplicate object keys before handing it bytes.
pub fn validate_json(raw: &[u8]) -> Result<()> {
    struct Strict;
    impl<'de> Deserialize<'de> for Strict {
        fn deserialize<D: de::Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
            d.deserialize_any(StrictVisitor)
        }
    }
    struct StrictVisitor;
    impl<'de> Visitor<'de> for StrictVisitor {
        type Value = Strict;
        fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
            f.write_str("JSON without duplicate fields")
        }
        fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> std::result::Result<Strict, A::Error> {
            let mut names = BTreeSet::new();
            while let Some(name) = a.next_key::<String>()? {
                if !names.insert(name) {
                    return Err(de::Error::custom("duplicate JSON field"));
                }
                a.next_value::<Strict>()?;
            }
            Ok(Strict)
        }
        fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> std::result::Result<Strict, A::Error> {
            while a.next_element::<Strict>()?.is_some() {}
            Ok(Strict)
        }
        fn visit_bool<E: de::Error>(self, _: bool) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
        fn visit_i64<E: de::Error>(self, _: i64) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
        fn visit_u64<E: de::Error>(self, _: u64) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
        fn visit_f64<E: de::Error>(self, _: f64) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
        fn visit_str<E: de::Error>(self, _: &str) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
        fn visit_unit<E: de::Error>(self) -> std::result::Result<Strict, E> {
            Ok(Strict)
        }
    }
    let mut parser = serde_json::Deserializer::from_slice(raw);
    Strict::deserialize(&mut parser)?;
    parser.end()?;
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WorkerProvenance {
    pub profile: String,
    pub source_revision: String,
    pub build_fingerprint: String,
    pub executable_sha256: String,
}
