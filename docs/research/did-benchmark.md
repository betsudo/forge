# DID v0.7.0 local key-cache benchmark

This qualification uses the exact upstream tag `v0.7.0`, commit
`4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550`. Its package manifests still report
0.6.0; source commit and lock contents identify this experiment. Compact and the
consumer source tree remain unchanged. The benchmark builds current generated
JavaScript and JSON ZKIR on every lane and only substitutes independently
qualified key generation. It does not skip contract execution, proof generation,
proof verification or assertions.

## Compatibility gate

The official Compact 0.31.1 distribution embeds ZKIR 2.1.0 and emits twelve JSON ZKIR 2.0 circuits. Fresh
compiler `zkir compile` output and Forge's existing pinned ledger8 8.1.3 backend
produce byte-identical binary IR, prover keys and verifier keys for **all twelve**.
The compiler's own ledger-8.0.2 label and the application's npm ledger-v8 8.1.0
label are not treated as evidence of interchangeability: the independently
observed byte equality is the artifact compatibility gate. Full inventory,
source hashes, serialization tags, exact parameter digests and backend identity
are in [the compiler compatibility receipt](../evidence/did-compiler-compatibility.json).
Ten circuits use k11; `setVerificationMethod` and
`setVerificationMethodRelation` use k12.

The genuine proof workload executes the freshly generated DID `deactivate`
circuit using its upstream signing implementation and fixed, public fixture
secrets/timestamp. The original contract authorization checks execute. Five
explicit assertions check the before/after active/deactivated/version state.
The exact consumer compact-runtime 0.16.0 converts its actual `CircuitResults`
into a serialized proof preimage. The benchmark helper decodes that preimage
with the existing official backend, creates a fresh cryptographic proof, verifies
it against the returned complete public statement, rejects a changed binding,
and rejects a corrupt proof. No proof response is cached.

The minimal fixture's npm lock is checked package by package against the exact
consumer `pnpm-lock.yaml`, including integrity strings. In particular,
onchain-runtime-v3 is **3.0.0**, rather than a newer version permitted by the
runtime package's semver range. The fixture does not install or execute the
consumer's complete application dependency graph. It is a selected genuine
contract-proof workload, not the complete DID localnet API suite, transaction
submission, proof-server 8.0.3 endpoint qualification, or hosted CI measurement.

## Measured lanes

The reproducible runner prepares all twelve circuit keys and creates one fresh
`deactivate` proof per lane, with equal positive verification, negative controls
and runtime assertion counts. Each of these lanes runs at least three times:

| Lane | Key generation and transport |
| --- | --- |
| uncached | Original compiler `zkir compile-many` batch, twelve fresh key pairs. |
| cold | Empty Forge store, twelve misses, validated snapshot and gzip save. |
| warm restored | Fresh store restored from the previous cold job's verified compressed snapshot, twelve hits; no redundant save. |
| partial restored | Only `deactivate` restored from a prior-job snapshot, one hit and eleven misses, followed by a grown snapshot save. |
| unavailable | Actual CI helper restore against an absent snapshot returns `restored=false` / `cache_miss`, then twelve misses and a snapshot save. Integrity or profile errors are never treated as availability. |

The runner records code generation, contract execution, key preparation, proof
and verification, snapshot/compression, restore/extraction, compressed/raw bytes,
50 ms sampled job-directory disk high-water mark, process wall time and raw
per-request Forge statistics. Job statistics subtract inherited snapshot
counters. Creating the partial prior-job seed is excluded from the current job's
wall time; its measured duration is retained separately. Runtime dependency
installation and shared public parameter provisioning are setup costs recorded
separately. OS filesystem caches are not flushed and the host is shared with
other developer work. This is not an isolated CI hardware performance claim.

Corrupt consumer prover bytes and a wrong selected profile must fail with typed
non-fallback errors. A whitespace change to exact ZKIR source bytes must miss,
even when the resulting mathematical circuit is identical. These additional
controls run outside timed lanes. All byte identities are compared with fresh
original compiler output, including reproducibility across repetitions.

Transport measurements cover local archive compression/extraction and verified
Forge restoration. The unavailable lane includes actual CI helper key planning
and the failed-availability restore attempt in its process and total wall times. GitHub cache lookup, authentication, upload/download latency
and bandwidth are not measured; there is no hosted run or upload. Any estimated
hosted benefit must subtract that additional transport cost from the local
saving. Negative savings are valid results.

## Reproduction and cleanup

Use a fresh read-only downloaded archive of the pinned source under Forge's
`.local/ci-consumers/did`, the installed official compiler, and the verified k11
and k12 public parameters. The source file manifest rejects changed consumer
files. Use the paired qualified release CLI (replace the placeholder below). Build
the optimized benchmark helper through Nix and run the harness through the
same shell; record each executable hash and declared build mode:

```sh
./bootstrap.sh -- cargo build --locked --release --example prove-did-fixture
./bootstrap.sh -- python3 scripts/bench-did.py \
  --source .local/ci-consumers/did \
  --compiler-dir "$HOME/.compact/versions/0.31.1/aarch64-darwin" \
  --binary /path/to/qualified-release/bin/midnight-zkir-forge \
  --forge-build-mode release \
  --prover ./target/release/examples/prove-did-fixture \
  --prover-build-mode release \
  --params-dir "$HOME/.cache/midnight/zk-params" \
  --work .local/qualification/did/reproduction \
  --output .local/qualification/did/reproduction.json
```

The work directory must be absent and inside Forge's own
`.local/qualification/did`. Each completed lane immediately removes its store,
exports, generated keys and outputs. Only the compressed cold seed survives until
its corresponding warm restore. The runner removes the remaining owned work
(including installed dependencies and private proof preimages) on normal exit or
Python exceptions. It never deletes shared parameters, installed compilers,
existing consumer checkouts, unrelated containers or global caches. A forcibly
killed process can require explicit cleanup of that exact owned work directory.
