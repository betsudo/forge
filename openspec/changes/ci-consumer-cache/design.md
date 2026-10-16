# Design

## Two identity layers

The local CAS already deduplicates exact source bytes and full derivation recipes.
Do not equate a source digest with a usable key: parameters, compiler generation
options and exact backend/serialization/worker identity matter. Transport one
bounded, verified snapshot per platform/tool/profile/parameter partition and
workload; restore-prefix fallback never escapes that partition. Start with the
existing helper generation suffix and save only actual generation growth after
successful tests. Avoid one GitHub cache entry per circuit until transfer data
shows snapshot waste exceeds per-object API/archive overhead. No database merge.

Build/compiler artifacts, public parameters and Forge keys remain separate caches.
Compiler runs produce current ZKIR and ordinary runtime output. A consumer-owned
adapter may replace keygen only after exact compatibility and independently checked
binary IR/manifest behavior are qualified. Merely running --skip-zk then copying
keys is not a generic supported integration. Compact remains unchanged.

## Action and CLI

Existing forge-ci key/restore/baseline/report/prepare-save remain the portable
local contract. A future repository-local composite Action exposes restore and
save phases; the ordinary test step stays between them. Pin Forge and Action
revisions, split actions/cache restore/save, job-local writable stores, trusted
producer only, restore-only PR consumers. The Action never reports tests passed
on its own and does not interpret a cache hit as permission to skip a command.
Private Forge access requires explicitly provisioned repository read access;
GITHUB_TOKEN in another repository does not automatically read this private repo.

## Optional provider serving

Default to materialized NodeZkConfigProvider-compatible directories. Optional
loopback service exposes a prequalified immutable provider view, with exact
keys/{circuitId}.prover, keys/{circuitId}.verifier and SDK-version-specific ZKIR
path. Current Forge management/CAS routes are not silently claimed compatible
with FetchZkConfigProvider. Validate using the exact installed SDK; a suffix or
class name does not prove wire compatibility. HTTP loopback is initial scope;
HTTPS is opt-in through supplied certificate/key or an explicit local TLS proxy,
with normal certificate trust, hostname checks and no verification bypass.
Browser callers need exact-origin CORS; never wildcard credentialed access.

## Benchmark

Run untouched consumers only in private downloaded scratch under Forge .local.
Preflight source SHA, compiler/runtime/ledger/proof-server, SDK dependencies,
verified parameters, compatibility descriptors and complete circuit roster.
Measure identical uncached, cold, warm, partial-hit and unavailable-cache cases;
keep all proofs/verifications/assertion counts equal and include negative controls.
Record compile/codegen, keygen, proof, verify, restore/save/compression, bytes,
peak disk, key/verifier identities and total wall time. Run multiple repetitions
and report raw results/median. No numeric acceptance speedup before measurement.

Restore prefixes may relax workload identity only inside the exact compatibility
partition. Proof Relay stores, request bodies and witness-containing material are
excluded from artifact snapshots and every GitHub cache upload.
