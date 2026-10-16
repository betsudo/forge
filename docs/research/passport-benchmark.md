# Passport account benchmark

This is an isolated local artifact-stage experiment against Passport commit
`0d7bb0bc834f2d45d9fe2d84c4d022a30d648423`. No consumer checkout, Compact
source, hosted cache or localnet is modified. The official compiler is acquired
into owned scratch rather than installed into the shared Compact manager.

## Exact compatibility boundary

The pinned source requires Compact 0.35.0 with `--feature-zkir-v3`, runtime
0.20.0 and npm ledger-v9 1.0.0-rc.5. The official native compiler identifies
itself as `0.35.0 (debb05f94 2026-09-29)` and its bundled `zkir-v3` as
`midnight-zkir 3.1.0-rc.1`. Actual account emission contains 52 JSON3.1 circuits.
The selected `deposit_unshielded.zkir` is 4975 bytes, SHA256
`e1384ddb55763bd0a3226bbad3337b83a4e076087f212dbe0281e6db671dce1d`.
Its official backend reports k9, 331 rows. This observation supersedes the older
36-operation roster described by the consumer's historical upgrade report.

The existing Forge JSON3.0 worker is deliberately ineligible. The compiler's
[shipped release notes](https://github.com/midnightntwrk/compact/releases/tag/compactc-v0.35.0)
identify split `midnight-zkir` tag `zkir-3.1.0-rc.1`, whose annotated tag peels to
[`e82d81d25aabcc5f5092e2bd559083487f577914`](https://github.com/midnightntwrk/midnight-zkir/tree/e82d81d25aabcc5f5092e2bd559083487f577914).
That exact workspace patches base/serialize/transient/storage to official ledger
`9a8777c4d035fc7f38ae286bcf5f8656668efd9f`, and its lock pins proofs0.8.2,
circuits7.2.4, stdlib2.3.5 and curves0.3.1. Forge's additional isolated
`workers/zkir31` follows these sources and seeds dependency resolution from the
official tag's lock. Existing v2/3.0 backend pins remain intact.

Actual serialization is `ir-source[v3-generic]`,
`prover-key[v7](ir-source[v3-generic])`, and `verifier-key[v7]`. These are observed
upstream tags, not proof that another dependency graph is interchangeable. The
new profile label is `midnight-zkir-v3.1-json`; no ledger9 transaction-support
claim follows from circuit-artifact compatibility.

## Workload and retained checks

The selected key/proof roster is the actual account's `deposit_unshielded` and
`activate_initial_device_with_jubjub`. The first performs permissionless funding;
the second checks bootstrap commitment and a non-small-order JubJub device key.
Neither is a synthetic Forge fixture. Each lane constructs a fresh account state,
executes both generated async contract circuits under exact runtime0.20.0,
asserts their balance/activation/round/auth-nonce behavior, and obtains each
`callProofDataTrace` entry through the official serializer. Each execution has
nine state and transcript assertions. Witness/preimage bytes stay in private scratch and
are excluded from artifact snapshots and committed evidence.

`prove-preimage` loads current source and the chosen actual binary IR/keys,
requires decoded IR to equal current source, generates a new genuine proof,
verifies it, and rejects a changed public statement and corrupted proof encoding.
Each lane therefore executes two actual proofs, two positive verifications and
four negative controls. Test outcomes and proofs are never cached.

Three repetitions compare official uncached key generation, cold Forge, warm
restored Forge, a partial snapshot with only the deposit circuit materialized,
and unavailable transport. All three output files are compared byte-for-byte
against freshly generated official compiler-tool outputs. Local gzip snapshot
creation, extraction and Forge integrity-checked restore are timed. The unavailable
lane invokes the real CI helper key/restore path for an absent snapshot, requires
`restored=false` with `reason=cache_miss`, and includes planning and attempted
restore process time before normal keygen/proofs. Corruption and wrong-profile cases are separate
refusal controls, never silently treated as availability misses.

Full account codegen was measured separately three times: **400.918s, 297.993s,
and 304.043s** (median **304.043s**). Every run produced the same exact52-file
ZKIR roster and hashes. [Raw codegen receipt](../evidence/passport-codegen.json).
Reproduce with `scripts/bench-passport-codegen.py` through the Nix bootstrap.
Artifact lanes reuse its exact current emitted roster, measuring the copy, runtime
execution, key preparation, proof/verification and local transport. Their totals
are not full consumer CI totals and do not include a fabricated GitHub upload or
network latency. Dependency installation is reported separately. Shared host load
and local process startup/validation costs can dominate small circuits.

## Reproduction

Run `scripts/bench-passport.py --help` through `./bootstrap.sh --`. Supply the
pinned downloaded source, exact compiler directory, current Forge and paired3.1
worker, verified parameter directory, current emitted account directory, absent
owned work path under `.local/qualification/passport`, and evidence output.
The runner verifies committed consumer-file hashes, the complete emitted ZKIR roster
and hashes, and the independently qualified official compiler executable hashes
before doing work. It sets the generation-worker environment from the explicit
proof-worker argument and checks every prepared descriptor against that worker
executable digest. It installs
the consumer's exact existing npm lock in scratch without dependency upgrades or
package lifecycle scripts. No changes are made to consumer source or shared
Compact installations.

Result receipt and measured values are added only after all lane/proof checks pass.

```sh
MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER="$PWD/.local/qualification/passport/bin/midnight-zkir-forge-zkir31-worker" \
./bootstrap.sh -- python3 scripts/bench-passport.py \
  --source .local/ci-consumers/passport \
  --compiler-dir .local/qualification/passport/tools/compiler \
  --binary target/debug/midnight-zkir-forge \
  --worker .local/qualification/passport/bin/midnight-zkir-forge-zkir31-worker \
  --emitted .local/qualification/passport/emitted/account \
  --params-dir "$HOME/.cache/midnight/zk-params" \
  --work .local/qualification/passport/benchmark \
  --output docs/evidence/passport-benchmark.json
```

The runner removes each measured lane after preserving its receipt and retains
only the first cold keyset through integrity-refusal controls. On successful
completion it also removes that keyset, runtime dependencies and preimages.
Source archives and compiler/worker tools can then be removed after final
acceptance; they are reacquirable pinned inputs, not runtime dependencies.
