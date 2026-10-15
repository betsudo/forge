# GitHub cache + Forge: independent architecture research

Research date: 2026-10-15. This is a proposed integration, not an implemented
workflow or a hosted-service readiness claim. No Compact checkout was changed,
no workflow was run, and no cache, credential or repository setting was changed.

## Recommendation

Use GitHub Actions cache as transport for **trusted, quiescent Forge store
snapshots**, with a job-local writable copy. Forge remains responsible for exact
source/profile/parameter identity and per-hit byte verification. Every consumer
job still proves, verifies and executes assertions. Begin with one trusted warmup
producer and restore-only consumers; use workflow artifacts to fan out the same
prepared snapshot within a run. A public HTTP Forge service is unnecessary for
this first CI optimization.

## Current upstream behavior, checked against official sources

- GitHub scopes caches by branch; pull requests can read their base/default
  branch caches, while PR merge-ref saves cannot seed the base branch. Cache
  contents have no authenticity guarantee and may be readable by fork authors.
  Low-trust default-branch triggers have read-only defaults. Current docs expose
  `cache-mode: read`, `write`, `write-only`, and `none`; do not grant low-trust
  writers an override. Storage defaults to 10 GB/repository, idle entries expire
  after seven days, and least-recently-accessed eviction handles capacity.
  Additional configured storage is billable; quotas and budgets can make the
  service read-only. These are current GitHub.com facts, not assumptions about
  GHES or this organization's settings. [GitHub dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).
- `actions/cache` has separate restore/save actions, exact-match output and
  fallback prefixes. Its archive version incorporates paths and compression, so
  changing paths can cause misses. Current upstream main documents v6; v5 moved
  to Node 24 and requires runner >=2.327.1. Existing v4 pins should be reviewed,
  not silently upgraded from a research branch. [Official action README](https://github.com/actions/cache/blob/main/README.md).
- Cache entries are immutable. A new run-specific key can save growth after
  restoring an older snapshot, at the cost of additional full archives and quota
  pressure. Cross-OS archives do not make their contents portable. [Official
  cache workarounds](https://github.com/actions/cache/blob/main/tips-and-workarounds.md).
- Workflow artifacts are the explicit mechanism for passing output between
  dependent jobs; jobs consume a producer's named artifact after its successful
  completion. Use that for one-run fanout and report retention, rather than
  relying on a global cache to deliver a producer's exact output. [GitHub
  storing/sharing workflow data](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow).

Do not budget from the action README's abbreviated historical quota paragraph;
the GitHub reference now documents configurable paid storage. Measure this
repository's actual settings before enabling any paid increase.

## Local implementation evidence and implications

| Evidence | Implication for CI |
| --- | --- |
| `src/store.rs:38` canonicalizes the current root; `:50` creates objects/exports/staging; `:53` opens `index.sqlite3`; `:67` starts an immediate transaction. | One local writer is supported. Each runner restores its own directory; no network filesystem shared SQLite. |
| `src/application.rs:170` holds ownership while resolving parameters, looking up a recipe, generating, verifying and publishing; `src/store.rs:275` also locks for metrics. | Stop every CLI/HTTP process before copying a complete store. A SQLite-only backup cannot atomically snapshot its external CAS. There is no supported snapshot/merge command yet. |
| `src/store.rs:108` verifies object size/hash; `:146` verifies CAS and existing exports before use. | Always invoke Forge on restored data. GitHub's exact cache-hit flag never substitutes for Forge integrity checks. |
| `src/application.rs:176` recipes contain source digest, exact profile/revision, build fingerprint, parameter k/digest and generation options; `:188` adds worker provenance. | A broad compatible snapshot may contain many circuits safely, but Forge still determines whether each derivation is reusable. Wrong profiles must fail or use a separately explicit uncached path. |
| `src/application.rs:331` fingerprints lockfiles, backend/dispatcher/domain code, flake lock, rustc, OS and architecture; `src/zkir3.rs:70` validates worker identity. | Partition first implementation by platform and exact Forge build/profile; do not promise portable hits across architectures or different worker binaries. |
| `src/store.rs:204` returns canonical absolute export paths; `:329` manifests serialize records without timing. Records contain artifact metadata, not export roots. | Re-run prepare/ensure after restoring to obtain paths on this runner. Never cache prior CLI response JSON as a path authority. |
| `src/store.rs:295` exposes historical file/request totals; `src/application.rs:122` stores requested paths. | Snapshot totals are historical baselines, not the current job's efficiency. Capture before/after totals and upload the delta/report separately; cached databases can disclose file paths. |
| `.github/workflows/ci.yml:31` and `:57` cache target/Cargo directories with lock/platform keys, but no Forge store or parameter directory. | Existing CI accelerates compilation only. Both jobs can race to save the same immutable key; the first saved archive need not include the other job's outputs. |

## Suggested cache layout and identity

Keep four independently sized layers: Nix/build dependencies; Cargo registry/git
and target; verified public parameters; Forge store snapshots. Caching target
does not persist `/nix/store` closures. Review Nix binary substitution separately;
do not upload arbitrary `/nix/store` trees through the dependency-cache action.

For Forge use a repository-relative path such as `.ci/forge-store`, explicitly
passed through `--cache-dir` or `MIDNIGHT_ZKIR_FORGE_DIR`. Suggested conceptual key:

```text
forge-store-v1-{os}-{arch}-{forge-build/profile-set-hash}-{parameter-manifest-hash}-{circuit-manifest-hash}
```

The generated manifest should sort each actual ZKIR relative name + byte digest;
the profile manifest should contain full revisions and serialization tags,
lockfiles/toolchain identity, worker identity and actual parameter digests/k.
Do not key only on the source branch name, a label such as ledger8, or the crate
version: existing v3 RCs share a version while using different binary tags.
Assert nonempty input discovery; an empty `hashFiles` result must not silently
collapse distinct jobs onto one cache key. Include compiler and flags when
caching generated compiler outputs; Forge's artifact recipe itself starts from
the exact emitted ZKIR bytes.

Allow a fallback prefix **only through the same platform/build/profile/parameter
partition**, omitting the circuit-set digest, so unchanged circuits survive a
small source change. Forge still checks each circuit. A restored older snapshot
must be saved under a new primary key when new circuits were generated; saving
under the matched immutable fallback key would lose that growth. Prefer
circuit-manifest keys initially. If circuits are emitted dynamically and no
stable manifest is available before restore, a run-id suffix is possible but
requires a bounded retention/churn policy.

Parameter files deserve a distinct exact-manifest cache. Restore them into an
explicit params directory and retain upstream digest verification on use. A
cache miss must permit the configured verified fetch or a clear offline error;
it must never make a test pass without running. No tokens belong in any cache.

## Writer, snapshot and fanout sequence

1. A trusted default-branch producer restores the newest compatible baseline,
   compiles current circuits, prepares them serially, then runs a representative
   genuine proof/verification control for each exact backend profile.
2. Stop all Forge clients/server and ensure no in-flight worker remains. Copy
   the **complete quiescent store** into a new staging directory. Preserve any
   database sidecars if present; never copy only `index.sqlite3` from a live
   process. Do not delete database tables to reset stats. A future supported
   snapshot command can produce a compact, privacy-filtered archive.
3. Inspect archive size and file inventory. Current copied exports duplicate
   CAS bytes; archive size can exceed unique artifact size. Pruning exports or
   metrics should wait for a defined/tested snapshot contract. Do not cache
   token mounts, proof witnesses, credentials or arbitrary user-home directories.
4. Save once from the trusted producer under the new immutable key after
   qualification. Concurrent producers for the same key must be serialized or
   accept a skipped losing save; they cannot merge databases. Do not let every
   matrix consumer publish a different partial snapshot under one key.
5. Upload the prepared snapshot as a named workflow artifact for this run's
   dependent jobs. Each consumer unpacks to an isolated writable local copy,
   runs Forge to verify/recreate paths, and executes all proofs/assertions.
   Consumer stats are uploaded separately, never merged into the shared store.

PR workflows should use restore-only operations, no privileged token, no Forge
service credential, and no promotion of their modified snapshots. Code that
controls a cache's database can replace both claimed digests and objects:
**matching hashes detect corruption, not a malicious producer**. A successful
self-consistent proof is likewise not provenance for the intended circuit.
Require trusted producer scope, exact expected source/profile selection and
independent verifier expectations. Never run untrusted PR code in a privileged
`pull_request_target` cache-publishing job. Do not expose private circuit sources
or artifact inventories through fork-readable caches.

## Measurement and implementation gates

Compare cold, restored-but-miss, partial-hit and warm workloads on the same
representative Compact circuit set. Record archive compressed bytes,
restore/unpack/save time, compile time, Forge lock/verify/generation time,
proof/verify time, peak disk use and before/after request counters. The decision
metric is end-to-end saved wall time after transfer/verification overhead, not
hit percentage alone. Tiny fixtures do not establish CI savings; large prover
keys can make GitHub archive transport slower than regeneration.

Before implementation, qualify Linux build + genuine consumer proofs, a
quiescent snapshot relocated to a different absolute root, stale compatible
snapshot extension, missing/corrupt objects, wrong backend/parameter manifests,
two simultaneous producers, and cache-unavailable behavior. Cold baseline and
corruption controls must stay runnable independently of caching.

HTTP can become a later immutable-object transport once authentication,
authorization, provenance/promotion, retention, privacy, egress costs and
availability contracts exist. Current single-owner bounded HTTP admission is
not a multi-tenant public CI cache policy. Start with local per-job Forge;
do not place a long-lived public service on the critical path yet.
