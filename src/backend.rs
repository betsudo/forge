//! Official ledger8 adapter. No crypto implementation lives in Forge.
use anyhow::{Context, Result, ensure};
use midnight_base_crypto::data_provider::{FetchMode, MidnightDataProvider, OutputMode};
use midnight_serialize::{tagged_deserialize, tagged_serialize};
use midnight_transient_crypto::proofs::{
    KeyLocation, PARAMS_VERIFIER, ParamsProver, ParamsProverProvider, ProofPreimage,
    ProvingKeyMaterial, Resolver, VerifierKey, Zkir,
};
use midnight_zkir::IrSource;
use std::{
    borrow::Cow,
    io::{self, Read},
    path::Path,
    sync::Arc,
};

use crate::domain::{ArtifactKind, digest};

pub const PROFILE: &str = "ledger8-8.1.3/zkir-2.1.1/transient-2.1.1/base-1.0.2/serialize-1.1.1/proofs-0.7.1/circuits-6.1.0/stdlib-1.1.0/curves-0.2.0/tagged-v1/forge-recipe-v1";
pub const LEDGER_REV: &str = "b5d3e965a18e4cac17fac4f38446fc55c524439a";

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
    let mut reader = provider
        .get_file(
            &name,
            "missing verified parameters; supply --params-dir or explicitly use --fetch-params",
        )
        .await?;
    // get_file verifies upstream's pinned digest before these bytes are used.
    let mut bytes = Vec::new();
    reader.read_to_end(&mut bytes)?;
    Ok(Parameters {
        k,
        digest: digest(&bytes),
        bytes: Arc::new(bytes),
    })
}

pub fn parse(raw: &[u8]) -> Result<IrSource> {
    crate::domain::validate_json(raw)?;
    IrSource::load(raw).context("official ZKIR v2 parser rejected input")
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
