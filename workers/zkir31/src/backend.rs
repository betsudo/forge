//! Official consumer-pinned ZKIR3 adapter, built in an isolated dependency graph.
use anyhow::{Context, Result, ensure};
use midnight_base_crypto::data_provider::{FetchMode, MidnightDataProvider, OutputMode};
use midnight_serialize::{tagged_deserialize, tagged_serialize};
use midnight_transient_crypto::proofs::{
    KeyLocation, PARAMS_VERIFIER, ParamsProver, ParamsProverProvider, ProofPreimage,
    ProvingKeyMaterial, Resolver, VerifierKey, Zkir,
};
use midnight_zkir_v3::IrSource;
use std::{
    borrow::Cow,
    io::{self, Read},
    path::Path,
    sync::Arc,
};

use crate::{ArtifactKind, digest};

pub const PROFILE: &str = "zkir31-e82d81d2/zkir-3.1.0-rc.1/transient-3.0.0/base-1.1.0/serialize-1.2.0/proofs-0.8.2/circuits-7.2.4/stdlib-2.3.5/curves-0.3.1/ir-source-v3-generic/forge-recipe-v1";
pub const LEDGER_REV: &str = "e82d81d25aabcc5f5092e2bd559083487f577914";

pub struct Parameters {
    pub k: u8,
    pub digest: String,
    bytes: Arc<Vec<u8>>,
}
impl ParamsProverProvider for Parameters {
    async fn get_params(&self, k: u8) -> io::Result<ParamsProver> {
        if k != self.k {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "parameter size mismatch",
            ));
        }
        ParamsProver::read(self.bytes.as_slice())
    }
}

pub async fn parameters(
    ir: &IrSource,
    directory: Option<&Path>,
    fetch: bool,
) -> Result<Parameters> {
    let mut provider = MidnightDataProvider::new(
        if fetch {
            FetchMode::OnDemand
        } else {
            FetchMode::Synchronous
        },
        OutputMode::Log,
        vec![],
    )?;
    if let Some(directory) = directory {
        provider.dir = directory.to_owned();
    }
    let k = ir.k();
    let name = MidnightDataProvider::name_k(k);
    let path = provider.dir.join(&name);
    let present = match std::fs::symlink_metadata(&path) {
        Ok(metadata) => {
            ensure!(
                metadata.is_file() && !metadata.file_type().is_symlink(),
                crate::error::Kind::InvalidParameters
            );
            true
        }
        Err(error) if error.kind() == io::ErrorKind::NotFound => false,
        Err(error) => {
            return Err(anyhow::Error::new(error).context(crate::error::Kind::InternalError));
        }
    };
    let mut reader = provider
        .get_file(
            &name,
            "missing verified parameters; supply --params-dir or explicitly use --fetch-params",
        )
        .await
        .map_err(|error| {
            let kind = if error.kind() == io::ErrorKind::InvalidData {
                crate::error::Kind::InvalidParameters
            } else if !present && error.kind() == io::ErrorKind::NotFound {
                crate::error::Kind::ParametersUnavailable
            } else {
                crate::error::Kind::InternalError
            };
            anyhow::Error::new(error).context(kind)
        })?;
    // get_file verifies upstream's pinned digest before these bytes are used.
    let mut bytes = Vec::new();
    reader
        .read_to_end(&mut bytes)
        .context(crate::error::Kind::InvalidParameters)?;
    Ok(Parameters {
        k,
        digest: digest(&bytes),
        bytes: Arc::new(bytes),
    })
}

pub fn parse(raw: &[u8]) -> Result<IrSource> {
    let value: serde_json::Value =
        serde_json::from_slice(raw).context(crate::error::Kind::InvalidInput)?;
    ensure!(
        value["version"]["major"] == 3 && value["version"]["minor"] == 1,
        crate::error::Kind::ProfileFormatMismatch
    );
    IrSource::load(raw)
        .context("official pinned ZKIR v3 parser rejected input")
        .context(crate::error::Kind::InvalidInput)
}

pub async fn generate(ir: &IrSource, params: &Parameters) -> Result<Vec<(ArtifactKind, Vec<u8>)>> {
    let (pk, vk) = ir.keygen(params).await.context("official key generation")?;
    let mut result = Vec::new();
    let mut bytes = Vec::new();
    tagged_serialize(ir, &mut bytes)?;
    result.push((ArtifactKind::BinaryIr, bytes));
    let mut bytes = Vec::new();
    tagged_serialize(&pk, &mut bytes)?;
    result.push((ArtifactKind::Prover, bytes));
    let mut bytes = Vec::new();
    tagged_serialize(&vk, &mut bytes)?;
    result.push((ArtifactKind::Verifier, bytes));
    validate_outputs(&result)?;
    Ok(result)
}

pub fn validate_outputs(outputs: &[(ArtifactKind, Vec<u8>)]) -> Result<()> {
    for (kind, bytes) in outputs {
        let mut input = bytes.as_slice();
        match kind {
            ArtifactKind::Source => {
                parse(bytes)?;
            }
            ArtifactKind::BinaryIr => {
                let _: IrSource = tagged_deserialize(&mut input)?;
            }
            ArtifactKind::Prover => {
                let pk: midnight_transient_crypto::proofs::ProverKey<IrSource> =
                    tagged_deserialize(&mut input)?;
                pk.init()?;
            }
            ArtifactKind::Verifier => {
                let vk: VerifierKey = tagged_deserialize(&mut input)?;
                vk.init()?;
            }
        }
        if *kind != ArtifactKind::Source {
            ensure!(input.is_empty(), "trailing artifact bytes");
        }
    }
    Ok(())
}

pub struct LocalResolver {
    pub ir: Vec<u8>,
    pub prover: Vec<u8>,
    pub verifier: Vec<u8>,
}
impl Resolver for LocalResolver {
    async fn resolve_key(&self, _: KeyLocation) -> io::Result<Option<ProvingKeyMaterial>> {
        Ok(Some(ProvingKeyMaterial {
            prover_key: self.prover.clone(),
            verifier_key: self.verifier.clone(),
            ir_source: self.ir.clone(),
        }))
    }
}

/// Qualification only: the service never caches proofs or passing test results.
pub async fn qualify(params: &Parameters, resolver: &LocalResolver) -> Result<()> {
    let vk: VerifierKey = tagged_deserialize(&mut resolver.verifier.as_slice())?;
    let preimage = ProofPreimage {
        binding_input: 42.into(),
        communications_commitment: None,
        inputs: vec![1.into()],
        private_transcript: vec![],
        public_transcript_inputs: vec![],
        public_transcript_outputs: vec![],
        key_location: KeyLocation(Cow::Borrowed("forge-qualification")),
    };
    let (proof, _) = preimage
        .prove::<IrSource>(&mut rand::thread_rng(), params, resolver)
        .await?;
    vk.verify(&PARAMS_VERIFIER, &proof, [42.into()].into_iter())?;
    ensure!(
        vk.verify(&PARAMS_VERIFIER, &proof, [43.into()].into_iter())
            .is_err(),
        "invalid statement accepted"
    );
    let mut encoded = Vec::new();
    tagged_serialize(&proof, &mut encoded)?;
    let last = encoded.last_mut().context("empty proof encoding")?;
    *last ^= 1;
    if let Ok(corrupt) =
        tagged_deserialize::<midnight_transient_crypto::proofs::Proof>(&mut encoded.as_slice())
    {
        ensure!(
            vk.verify(&PARAMS_VERIFIER, &corrupt, [42.into()].into_iter())
                .is_err(),
            "corrupt proof accepted"
        );
    }

    Ok(())
}

/// Explicit local benchmark helper: a new genuine consumer proof on every invocation.
/// No request bodies, witnesses, proofs or passing outcomes enter the Forge store.
pub async fn prove_preimage(
    ir: &IrSource,
    params: &Parameters,
    resolver: &LocalResolver,
    bytes: &[u8],
) -> Result<serde_json::Value> {
    let mut input = bytes;
    let preimage: ProofPreimage = tagged_deserialize(&mut input)?;
    ensure!(input.is_empty(), "trailing preimage bytes");
    let restored: IrSource = tagged_deserialize(&mut resolver.ir.as_slice())?;
    ensure!(&restored == ir, "binary IR differs from current source");
    let pk = tagged_deserialize(&mut resolver.prover.as_slice())?;
    let vk: VerifierKey = tagged_deserialize(&mut resolver.verifier.as_slice())?;
    let started = std::time::Instant::now();
    let (proof, pis, _) = ir
        .prove(&mut rand::thread_rng(), params, pk, &preimage)
        .await?;
    let proof_ms = started.elapsed().as_secs_f64() * 1000.;
    let started = std::time::Instant::now();
    vk.verify(&PARAMS_VERIFIER, &proof, pis.iter().copied())?;
    let verify_ms = started.elapsed().as_secs_f64() * 1000.;
    let mut wrong = pis.clone();
    ensure!(!wrong.is_empty(), "missing public statement");
    wrong[0].0 += midnight_transient_crypto::curve::Fr::from(1).0;
    ensure!(
        vk.verify(&PARAMS_VERIFIER, &proof, wrong.into_iter())
            .is_err(),
        "invalid statement accepted"
    );
    let mut encoded = Vec::new();
    tagged_serialize(&proof, &mut encoded)?;
    let proof_bytes = encoded.len();
    *encoded.last_mut().context("empty proof")? ^= 1;
    if let Ok(corrupt) =
        tagged_deserialize::<midnight_transient_crypto::proofs::Proof>(&mut encoded.as_slice())
    {
        ensure!(
            vk.verify(&PARAMS_VERIFIER, &corrupt, pis.iter().copied())
                .is_err(),
            "corrupt proof accepted"
        );
    }
    Ok(
        serde_json::json!({"proof_ms":proof_ms,"verify_ms":verify_ms,"proof_bytes":proof_bytes,
        "public_inputs":pis.len(),"valid_proof_verified":true,"invalid_statement_rejected":true,
        "corrupt_proof_rejected":true,"proof_count":1,"verification_count":1,"negative_controls":2}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn profile_accepts_only_qualified_json_minor() {
        let fixture = include_bytes!("../fixtures/assert.zkir");
        assert!(parse(fixture).is_ok());
        let mut value: serde_json::Value = serde_json::from_slice(fixture).unwrap();
        for minor in [0, 2, 99] {
            value["version"]["minor"] = serde_json::json!(minor);
            let error = parse(&serde_json::to_vec(&value).unwrap()).unwrap_err();
            assert_eq!(
                crate::error::classify(&error),
                crate::error::Kind::ProfileFormatMismatch
            );
        }
    }
}
