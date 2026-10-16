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
against freshly generated official compiler-tool outputs. All Forge lanes include real CI-helper key planning against the same exact
profile/parameter partition. Snapshots declare that partition and verified
parameter digests; warm/partial lanes use the actual helper restore policy.
Local gzip snapshot creation, extraction and integrity-checked restore are timed.
Planning and helper-restore process time remain separate raw fields; the lane
total includes both. The official uncached baseline invokes no Forge helper. The unavailable
lane invokes the real CI helper key/restore path for an absent snapshot, requires
`restored=false` with `reason=cache_miss`, and includes planning and attempted
restore process time before normal keygen/proofs. Corruption and wrong-profile cases are separate
refusal controls, never silently treated as availability misses.

Full account codegen was measured separately three times: **400.918s, 297.993s,
and 304.043s** (median **304.043s**). Every run produced the same exact 52-file
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

## Measured result

The final optimized, relocated macOS ARM64 candidate ran all 15 lanes successfully.
Each lane retained both genuine account proofs, both positive verifications, four
negative controls and 18 state/transcript assertions: **30 proofs, 30 positive
verifications, 60 negative controls and 270 assertions** in total.

| Lane | Median selected artifact/proof workflow |
| --- | ---: |
| Official uncached batch keygen | 3.934s |
| Cold Forge, including new snapshot/compression | 6.499s |
| Warm restored Forge | 4.338s |
| Partial restored Forge, one hit/one miss | 6.811s |
| Absent local transport, normal generation | 6.537s |

**Warm restoration was 0.403s slower (10.3%) for this selected workload.** It
eliminated key generation, but its verified preparation/worker/export work,
helper planning and local snapshot restoration cost enough to erase that saving.
Median warm preparation was 1.118s, planning 0.163s and restore 0.610s; median
uncached batch keygen was 1.637s. Actual proving remained around 1.92s per lane
in either case. These phase medians are separate summaries, not an additive
reconstruction of the median total. This result does not justify enabling Forge
for this narrow workload purely for speed, nor predict the full 52-key account
build or hosted CI/network performance.

The host remained shared: an existing trust-registry Compact compilation was
active and untouched. Root and Linux qualification held their own heavy work
during the measured window. The earlier codegen measurements also ran under
shared build load. No isolated-capacity performance claim is made.

[Unmodified raw measurement receipt](../evidence/passport-benchmark.json) and
[provenance/requirement audit](../evidence/passport-benchmark-audit.json) record
raw repetitions, per-job statistics, helper/transport costs, output/parameter
identities and the verified signed c40e45b source/archive. The measured CLI and
paired worker are the same optimized portable bytes as the installer candidate;
the later producer-only change does not replace the measured Rust payload.
Independent receipt review found no blocker. All measured stores, snapshots,
preimages and runtime dependency copies were removed after evidence capture.

```sh
./bootstrap.sh -- python3 scripts/bench-passport.py \
  --source .local/ci-consumers/passport \
  --compiler-dir .local/qualification/passport/tools/compiler \
  --binary .local/qualification/native-runtime/midnight-zkir-forge-v2026.10.0-aarch64-apple-darwin/bin/midnight-zkir-forge \
  --worker .local/qualification/native-runtime/midnight-zkir-forge-v2026.10.0-aarch64-apple-darwin/bin/midnight-zkir-forge-zkir31-worker \
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
