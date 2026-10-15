# DID and Passport CI cache research

Research: 2026-10-16, read-only GitHub APIs and private downloaded source archives
under Forge `.local/ci-consumers`. No existing consumer checkout or Compact source
changed. No hosted run, cache upload, dependency install or deployment initiated.
Proposals: [consumer cache contract](../../openspec/changes/ci-consumer-cache/design.md).

## Exact consumers and observations

| Consumer | Pinned source | Observed contract |
| --- | --- | --- |
| DID requested 0.7.0 | Tag **v0.7.0**, `4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550` | CI Compact0.31.1; runtime0.16.0; npm ledger-v8 8.1.0; proof-server8.0.3. Contract package manifest still says0.6.0: tag/source identity must win over package-name assumptions. |
| Passport account | main observed `0d7bb0bc834f2d45d9fe2d84c4d022a30d648423` | `compact compile +0.35.0 --feature-zkir-v3`; runtime0.20.0; ledger-v9 1.0.0-rc.5; Midnight.js5.0.0-rc.2; compact-js3.0.0-rc.3. Other probe compilation deliberately lacks the v3 flag. |

Sources: [DID CI](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/.github/workflows/ci.yml),
[DID root manifest](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/package.json),
[DID contract](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/packages/contract/package.json),
[Passport manifest](https://github.com/midnightntwrk/passport/blob/0d7bb0bc834f2d45d9fe2d84c4d022a30d648423/contract/package.json),
[account source](https://github.com/midnightntwrk/passport/blob/0d7bb0bc834f2d45d9fe2d84c4d022a30d648423/contract/contracts/account.compact).
These mixed dependency labels are not evidence that Forge's exact supported
profile can generate interchangeable keys. Qualify independently.

DID `./run.sh core --metrics --metrics-json PATH` owns a composite lint/build/test
lane; `api` is separate and uses Docker proof infrastructure. The contract's
`test:ci` alone is not a sufficient genuine-proof baseline: core explicitly sets
`SKIP_RUNTIME_TESTS=1`. DID already has checked ZK artifact packaging/manifest and
provider paths; integrate its provenance rather than creating an unrelated layout.
Passport `test:toolchain-offline` checks verifier keys, SDK deployment construction
and ledger9 conversion but explicitly makes no proofs/network submissions. Its
`test:auth`, `test:recovery`, `test:p256` and other conformance lanes require their
real configured services; do not relabel offline simulator timing as proof savings.

## Historical allocation is not keygen timing

The exact DID source has successful historical [CI run38682344840](https://github.com/midnightntwrk/midnight-did/actions/runs/38682344840):
main job1144s, core167s, package smoke29s, API909s, coverage23s. A parallel W3C job
lasted100s. API time includes startup, network, proof generation and other work;
no per-keygen measurement was obtained, so none of those909s are claimed saved.
The Passport exact-head run listing returned Scan only. Its inspected top-level
workflows cover Pages and scanning; no proof-bearing contract CI benchmark exists
there to compare yet. These observations do not characterize future workflows.

## Safe local probe and blockers

The installed official Compact0.31.1 emitted DID JSON ZKIR in an isolated output
with `--skip-zk` in **0.4505s** (one observation, no repeated benchmark): 12 files,
JSON version2.0. Example `deactivate.zkir` SHA256
`0104892364fe7c0fe55247099ba0ea138f2eccbad6478524aafc73f3b078e7b6`.
Compiler self-report: ledger-8.0.2, runtime0.16.0. This demonstrates that codegen
can be cheap for this source; it does not measure keygen or support general
claims. No adapter or proof suite was run. Exact Forge binary/key compatibility
with this compiler's tool output has not been independently qualified, so a
cold/warm Forge benchmark would currently be misleading. Public parameters exist
locally but required actual per-circuit k/digests still need discovery/verification.
Compact0.35.0 is absent locally; no substitute compiler was used for Passport.
Managed keys and node_modules are absent in downloaded sources. Remote dependency
installation, compiler acquisition and proof infrastructure provisioning remain
explicit preflight steps; this research did not silently skip or simulate them.

Reproduce DID emission from this checkout after downloading the pinned archive:

```sh
./bootstrap.sh -- "$HOME/.compact/versions/0.31.1/aarch64-darwin/compactc" \
  --skip-zk .local/ci-consumers/did/packages/contract/src/did.compact \
  .local/ci-consumers/did-emitted
```

The above is a research probe, **not a generic cache integration recipe**. Normal
consumer compilation and its manifest checks must remain correct; an arbitrary
post-compile key copy after skip flags may not preserve their contract.

## Recommended strategy

Use existing `midnight-zkir-forge-ci` first; optionally package a thin composite
Action once measured. Exact local derivation recipes remain the reuse authority:
source hash alone omits parameters/backend/options. GitHub transport should use
bounded verified partition/workload snapshots, not one API/archive per ZKIR hash.
Per-source archives increase requests and do not encode recipe identity; per-run
full snapshots without growth guards waste quota. The current generation suffix
plus miss-growth guard addresses immutable GitHub keys. Keep one trusted producer,
restore-only PRs, job-local writers, no merges and no platform/profile-crossing
prefix. Use same-run artifacts for exact producer-to-matrix fanout. Keep Nix/build,
verified parameter and key caches independent. [GitHub cache matching, immutability,
branch access and storage policy](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
are transport constraints, not Forge provenance guarantees.

Default TS/JS integration uses `NodeZkConfigProvider` on materialized exports.
Optional local `FetchZkConfigProvider` view needs exact SDK layout/runtime manifest
qualification; Forge's management/CAS HTTP API is not already this provider API.
Prefer loopback HTTP initially; optional HTTPS uses explicitly supplied trusted
certificate/key or TLS proxy, never disabled verification. Define exact-origin
CORS for browser clients. Keep `zkConfigProvider` (ZKIR and keys) separate from
`proofProvider` (proof server requests), as in the [official provider guide](https://docs.midnight.network/guides/deploy-and-operate).

## Reproducible benchmark protocol

1. Download exact source archives to fresh Forge-private scratch; record SHA and
   archive digest, platform, tool executable digests and complete dependency locks.
2. Preflight selected compiler/runtime/ledger/proof-server and exact Forge
   descriptor; compare fresh genuine binary IR/key identities with generated Forge
   output and verify genuine consumer proofs/negative controls. Unsupported mapping
   blocks the benchmark instead of substituting another backend. Pin every
   parameter name/k/digest after upstream verification.
3. Discover the complete selected circuit roster and preserve compiler manifests,
   current codegen and all selected proofs/assertions. Pin scenario selection and
   fixture data; retain time-dependent/network prerequisites in each receipt.
4. Use fresh private job directories for uncached original keygen, cold Forge,
   warm restored Forge, partial snapshot and unavailable transport. Reset outputs
   consistently; never reuse prior test response paths. Run each lane at least
   three times with equal assertion/proof/verification counts and an explicit
   original uncached control. Report raw runs and median, including variance.
5. Measure codegen, keygen, proof/verify, startup, restore/unpack, hash checks,
   snapshot/compression/upload equivalent and total wall time, plus archive bytes,
   peak disk, per-job stats deltas and source/recipe/key/verifier identities.
   Actual hosted transport requires later authorization and separate measurements.
6. Benefit = uncached total minus cached total with setup/transport included.
   Zero or negative savings are valid results. Test cache absence, corrupt bytes,
   wrong profile, changed circuit, concurrent private consumers and trusted-save
   refusal on PR/failure. Cache hit rate alone cannot establish CI time savings.

Current result: codegen-only feasibility observed; **end-to-end CI improvement is
unmeasured**. Consumer integration and GitHub publication remain follow-up work.

Restore prefixes may relax workload identity only inside the exact compatibility
partition. Proof Relay stores, request bodies and witness-containing material are
excluded from artifact snapshots and every GitHub cache upload.
