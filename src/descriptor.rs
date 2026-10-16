//! Additive, path-free descriptor. Existing Record and identity transcripts stay intact.
use crate::domain::{Record, digest, validate_json};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::Value;
pub const KEYGEN_RECIPE: &str = "library-keygen/default-options/no-rng";
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Serialization {
    pub binary_ir: String,
    pub prover_key: String,
    pub verifier_key: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct ArtifactDescriptor {
    pub schema: u32,
    pub input_format: String,
    pub input_version: Value,
    pub materialized: bool,
    pub serialization: Option<Serialization>,
    pub keygen_recipe: Option<String>,
    pub record: Record,
}
fn serialization(format: Option<&str>) -> Serialization {
    let v3 = matches!(
        format,
        Some(crate::zkir3::FORMAT) | Some(crate::zkir31::FORMAT)
    );
    let ir = if v3 {
        "ir-source[v3-generic]"
    } else {
        "ir-source[v2]"
    };
    Serialization {
        binary_ir: ir.into(),
        prover_key: format!("prover-key[v7]({ir})"),
        verifier_key: if format == Some(crate::zkir31::FORMAT) {
            "verifier-key[v7]"
        } else {
            "verifier-key[v6]"
        }
        .into(),
    }
}
impl ArtifactDescriptor {
    pub fn from_record(record: &Record, source: &[u8]) -> Result<Self> {
        ensure!(
            digest(source) == record.source.digest && source.len() as u64 == record.source.size,
            crate::error::Kind::IntegrityError
        );
        validate_json(source).context(crate::error::Kind::IntegrityError)?;
        let input: Value = serde_json::from_slice(source)?;
        let mut record = record.clone();
        record.generation_ms = None;
        let materialized = record.artifact_set_id.is_some();
        let result = Self {
            schema: 1,
            input_format: record
                .format
                .clone()
                .unwrap_or_else(|| "midnight-zkir-v2-json".into()),
            input_version: input
                .get("version")
                .context(crate::error::Kind::IntegrityError)?
                .clone(),
            materialized,
            serialization: materialized.then(|| serialization(record.format.as_deref())),
            keygen_recipe: materialized.then(|| KEYGEN_RECIPE.into()),
            record,
        };
        result.validate()?;
        Ok(result)
    }
    pub fn validate(&self) -> Result<()> {
        let kind = crate::error::Kind::IntegrityError;
        crate::snapshot::record_valid(&self.record).context(kind)?;
        let worker = match self.record.format.as_deref() {
            Some(crate::zkir3::FORMAT) => Some(&crate::zkir3::SPEC),
            Some(crate::zkir31::FORMAT) => Some(&crate::zkir31::SPEC),
            _ => None,
        };
        let v3 = worker.is_some();
        ensure!(
            self.schema == 1 && self.record.generation_ms.is_none(),
            kind
        );
        ensure!(
            self.input_format
                == self
                    .record
                    .format
                    .as_deref()
                    .unwrap_or("midnight-zkir-v2-json"),
            kind
        );
        ensure!(
            self.input_version.as_object().is_some_and(|v| v.len() == 2)
                && self.input_version["minor"].is_u64(),
            kind
        );
        ensure!(self.input_version["major"] == if v3 { 3 } else { 2 }, kind);
        ensure!(
            worker.is_none_or(|w| self.input_version["minor"] == w.json_minor),
            kind
        );
        ensure!(
            self.materialized == self.record.artifact_set_id.is_some(),
            kind
        );
        ensure!(
            self.serialization
                == self
                    .materialized
                    .then(|| serialization(self.record.format.as_deref())),
            kind
        );
        ensure!(
            self.keygen_recipe.as_deref() == self.materialized.then_some(KEYGEN_RECIPE),
            kind
        );
        Ok(())
    }
    pub fn decode(bytes: &[u8]) -> Result<Self> {
        validate_json(bytes).context(crate::error::Kind::IntegrityError)?;
        // Deserialization is intentionally private: callers must use this validated entrypoint.
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Wire {
            schema: u32,
            input_format: String,
            input_version: Value,
            materialized: bool,
            serialization: Option<Serialization>,
            keygen_recipe: Option<String>,
            record: Record,
        }
        let wire: Wire =
            serde_json::from_slice(bytes).context(crate::error::Kind::IntegrityError)?;
        let value = Self {
            schema: wire.schema,
            input_format: wire.input_format,
            input_version: wire.input_version,
            materialized: wire.materialized,
            serialization: wire.serialization,
            keygen_recipe: wire.keygen_recipe,
            record: wire.record,
        };
        value.validate()?;
        ensure!(
            serde_json::to_value(&value)? == serde_json::from_slice::<Value>(bytes)?,
            crate::error::Kind::IntegrityError
        );
        Ok(value)
    }
}
