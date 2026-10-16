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
Forge restoration. Every Forge lane includes actual CI helper key planning. Warm and partial
lanes restore through the helper, checking the exact partition and worker scope;
saved snapshots carry the planned partition and declared parameter digests. The
unavailable lane times the helper's actual absent-local-transport `cache_miss`
result. This is not a simulated network or authentication outage. Raw planning
and helper restore process timings are retained separately from the complete
restore/extraction and total wall times. GitHub cache lookup, authentication, upload/download latency
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

## Measured local result — 2026-10-16

[Raw 15-lane receipt](../evidence/did-cache-benchmark.json) and
[candidate/count provenance](../evidence/did-cache-benchmark-provenance.json) use
the optimized relocated macOS ARM64 candidate from signed source `c40e45b` and
the optimized helper recorded in `did-proof-helper-build.json`. All 12 circuits'
artifacts match fresh official output in every repetition. Across the five lanes,
15 fresh genuine proofs, 15 positive verifications, 30 proof negative controls
and 75 application assertions ran.

| Lane | Median total (s) | Hits / requests per job |
| --- | ---: | ---: |
| uncached | 6.857 | official batch |
| cold | 9.325 | 0 / 12 |
| warm-restored | 2.492 | 12 / 12 |
| partial-restored | 10.247 | 1 / 12 |
| unavailable | 11.585 | 0 / 12 |

Warm restored saved **4.366 s (63.7%)** against the uncached median in this
selected local workload. Cold, partial and unavailable paths were slower than
uncached; caching is not automatically a win when generation plus snapshot
publication dominates. Warm restore included a median 0.903 s of extraction and
verified helper restoration of a 19.24 MB compressed snapshot. Cold snapshot
creation and compression medians were 0.798 s and 0.363 s. Component medians
are independently computed and need not add to the total median.

Measurements ran sequentially within Forge, on a shared developer host with an
external trust-registry key compiler active; a lightweight installer suite briefly
overlapped early runs. Lanes were ordered, not randomized, and OS caches were
not flushed. Retain all raw repetitions and observed variation; this is neither
an isolated hardware comparison nor a whole hosted-CI speedup. GitHub network,
authentication and upload/download time remains unmeasured. The 4.366 s local
median saving is the available budget for additional hosted transport overhead,
not a promised CI reduction.
