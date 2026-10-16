//! Benchmark-only genuine generated DID proof; never caches a result.
use anyhow::{Context, Result, ensure};
use midnight_serialize::{tagged_deserialize, tagged_serialize};
use midnight_transient_crypto::proofs::{
    PARAMS_VERIFIER, Proof, ProofPreimage, ProverKey, VerifierKey, Zkir,
};
use midnight_zkir::IrSource;
use std::{env, fs, path::Path, time::Instant};
#[tokio::main]
async fn main() -> Result<()> {
    let a: Vec<String> = env::args().skip(1).collect();
    ensure!(
        a.len() == 5,
        "usage: prove-did-fixture SOURCE PROVER VERIFIER PREIMAGE PARAMS_DIR"
    );
    let ir = midnight_zkir_forge::backend::parse(&fs::read(&a[0])?)?;
    let params =
        midnight_zkir_forge::backend::parameters(&ir, Some(Path::new(&a[4])), false).await?;
    let bytes = fs::read(&a[3])?;
    let mut input = bytes.as_slice();
    let preimage: ProofPreimage = tagged_deserialize(&mut input).context("consumer preimage")?;
    ensure!(input.is_empty(), "trailing preimage");
    let pk: ProverKey<IrSource> = tagged_deserialize(&mut fs::read(&a[1])?.as_slice())?;
    let vk: VerifierKey = tagged_deserialize(&mut fs::read(&a[2])?.as_slice())?;
    let started = Instant::now();
    let (proof, pis, _) = ir.prove(rand::thread_rng(), &params, pk, &preimage).await?;
    let proof_ms = started.elapsed().as_secs_f64() * 1000.;
    let started = Instant::now();
    vk.verify(&PARAMS_VERIFIER, &proof, pis.iter().copied())?;
    let verify_ms = started.elapsed().as_secs_f64() * 1000.;
    ensure!(!pis.is_empty(), "empty public statement");
    let mut wrong = pis.clone();
    wrong[0] = wrong[0] + 1.into();
    ensure!(
        vk.verify(&PARAMS_VERIFIER, &proof, wrong.into_iter())
            .is_err(),
        "wrong binding accepted"
    );
    let mut encoded = Vec::new();
    tagged_serialize(&proof, &mut encoded)?;
    let proof_bytes = encoded.len();
    *encoded.last_mut().context("empty proof")? ^= 1;
    if let Ok(corrupt) = tagged_deserialize::<Proof>(&mut encoded.as_slice()) {
        ensure!(
            vk.verify(&PARAMS_VERIFIER, &corrupt, pis.iter().copied())
                .is_err(),
            "corrupt proof accepted"
        );
    }
    println!(
        "{}",
        serde_json::json!({"proofs":1,"verifications":1,"negative_controls":2,"proof_ms":proof_ms,"verify_ms":verify_ms,"proof_bytes":proof_bytes,"public_inputs":pis.len(),"k":params.k,"parameter_digest":params.digest})
    );
    Ok(())
}
