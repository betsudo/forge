# Compact integration and GitHub CI cache research

Research date: 2026-10-15. Tracking: [issue #5](https://github.com/input-output-hk/midnight-zkir-forge/issues/5).
This is a proposal, not a Compact integration change or a CI speedup claim.
Compact was inspected read-only; no tests, builds or workflow runs were started there.

## Recommendation

Extend Compact's existing test-scoped adapter rather than adding a new caching
path to each test. First qualify the current Forge build on Linux and macOS;
then use one local Forge store per CI job, restored from a trusted, stopped-store
snapshot. Keep Nix/Cargo build caches, public parameters and Forge snapshots
separate. Use workflow artifacts for exact same-run fanout. Keep actual compiler
execution, mock compilation, proof generation, verification, assertions, negative
controls and an explicit uncached qualification lane.

Do not start with a public HTTP cache. The implemented single-owner HTTP subset
is useful for one trusted runner/host, but it does not yet supply namespaces,
trusted publisher promotion, HTTP provider views, distributed scheduling or a
public CI retention/availability policy. There is no remote-cache CLI mode.

## What exists in Compact today

The inspected checkout is `/Users/ysh/.codex/worktrees/recording-effect-prototype/compact`,
origin `MediaNoxLabs/compact`, upstream `LFDT-Minokawa/compact`.
HEAD advanced from `df7367fca86cce5264e276c94f977d0ca7b9c4d6` to
`67a3403f9b65fd525c3b1da812ef5cd28d5c4be8` during read-only research by this
session. The intervening changes were confined to historical-performance docs
and a patch; inspected adapter/workflow files did not change. Other work and
uncommitted files were preserved. File hashes are recorded in the evidence.

| Integration point | Observed behavior | Proposed action |
| --- | --- | --- |
| `compiler/passes.ss:150–190` | Emits current `.zkir`, calls `zkir compile-many` or `zkir-v3 compile-many`, then generates the contract manifest. | Keep the artifact replacement before normal manifest generation. A blanket post-compile copy after `--skip-zk` is not equivalent for every consumer. |
| `tools/compact-rust-backend/forge_circuits.py` | Wraps v2 `compile`/`compile-many`; uses argument arrays, current source bytes, verified persistent exports and private output copies. | Reuse this adapter. Never link mutable tests directly to Forge CAS/exports. |
| Adapter `compile_circuit` | Executes actual ZKIR2.1.1 `mock-compile` every time, checks k/rows and independent binary-IR equality; no key generation in mock mode. | Retain this check and label its timing separately from keygen/hits. |
| Adapter `validate_export` | Checks exact source, profile/build/revision, manifest/artifact hashes and actual `bls_midnight_2p{k}` parameter digest. | Preserve checks; qualify new build identities instead of removing them. |
| `compiler/go`, `run-e2e-tests.sh`, `run-debug-test.sh` | Already enter the test shim. Python gates use the same helper. | Add CI provisioning/configuration once for these routes. |
| `compactc-launcher.sh:33` | Allows a test-scoped shim directory ahead of bundled tools. | Keep normal installed compiler behavior unchanged. A second v3 launcher can live in the same scoped directory after qualification. |
| Adapter `command` and `test_forge_harness.py:69` | Deliberately leave `zkir-v3` uncached; Forge build 0.2.0 now supports the matching v3 pin. | Extend the adapter to separately qualify and route v3; it is not enabled by upgrading Forge alone. |
| `compiler/go:26` | Avoids the shim inside `NIX_BUILD_TOP`; hermetic builders retain original keygen. | Use Nix/Attic substitution for hermetic compiler builds, not network calls to a mutable Forge service inside a derivation. |

Local source links: [adapter](</Users/ysh/.codex/worktrees/recording-effect-prototype/compact/tools/compact-rust-backend/forge_circuits.py>),
[compiler hook](</Users/ysh/.codex/worktrees/recording-effect-prototype/compact/compiler/passes.ss:150>),
[existing integration guide](</Users/ysh/.codex/worktrees/recording-effect-prototype/compact/doc/rust/guides/forge-circuit-cache.md>),
[qualification runner](</Users/ysh/.codex/worktrees/recording-effect-prototype/compact/tools/compact-rust-backend/check_forge_circuit_cache.py>).
Private local paths are research inputs, never workflow/runtime dependencies.

## Immediate compatibility blockers

1. **The current consumer rejects the installed Forge build.** Its `BUILD` is
   `340e0b3bd94394d987c1b2a073bb411afb755e7164934ca15e8d8cb02b77b879`;
   installed Forge reports
   `6b62bbf3ec49e334405e416eeb1a7dd1fe73a20095406ea602efa947f5b5a57a`.
   The v2 backend profile/revision matches, but the adapter explicitly checks
   build identity. This conclusion follows from the guard and live read-only
   `profile` output; no consumer run was attempted. Updating the expected value
   requires fresh real-consumer qualification, not a string-only bypass.
2. **One Darwin fingerprint cannot qualify Linux.** Forge's fingerprint includes
   Rust/OS/architecture/lockfiles; v3 also includes the worker build and actual
   executable digest. Use a reviewed per-platform qualification manifest, pinned
   Forge source/build provenance, and genuine consumer proof receipts. Do not
   accept whatever identity the current executable reports as self-qualification.
3. **V3 is a separate consumer change.** Compact and Forge both pin official
   ledger `3a7ae0361d03e6eed4fc91e31f6600f334f605d5`, JSON3.0 and
   `ir-source[v3-generic]`. Compact calls the tool `zkir-v3`; its current adapter
   only intercepts `zkir`. Add separate real-tool discovery, exact profile
   assertions, fresh mock-compile comparison, private copies and proof controls.
   Actual generated compiler sources still use `.zkir` filenames; suffix alone
   does not select v2/v3. JSON3.1 and other same-version RCs stay refused.
4. **CI does not provision Forge.** The inspected full compiler workflow calls
   the now-default shim routes but has no Forge checkout/install or qualified
   executable configuration. The source does not show `COMPACT_ZKIR_MODE=uncached`
   around those routes either. This is a static wiring gap, not an observed
   current-head CI failure. Provision a pinned qualified tool and set
   `COMPACT_ZKIR_FORGE_BIN`, or explicitly select the genuine uncached route.
5. **Forge code is delivered locally.** Its new commits have not been pushed or
   published. A hosted workflow cannot fetch these local commits. Publish a
   reviewed revision/tool closure only after owner authorization; this research
   does not dispatch, push or publish it.

The official Compact tutorial confirms compilation creates `compiler`,
`contract`, `keys` and `zkir` output directories, but uses a different example
release. That tutorial is layout context, not authority for this checkout's
exact dependency pins. [Midnight compilation tutorial](https://docs.midnight.network/examples/dapps/bboard#compile-the-contract).

## What the existing CI data says

Read-only GitHub API observations were collected on 2026-10-15. These completed
runs are from 2026-10-08 and **different commits from the inspected local HEAD**.
They establish historical allocation, not a benchmark of the proposed adapter.

| Historical job/step | Elapsed |
| --- | ---: |
| Compiler Build / Linux job | 860s |
| Its Build compiler step | 455s |
| Its Run compiler tests step | 297s |
| Its Test E2E step | 54s |
| Compiler Build / macOS job | 712s |
| Bounded Rust core job | 97s |
| Bounded Rust MSRV job | 39s |

Sources: [Compiler Build run 37856976470](https://github.com/MediaNoxLabs/compact/actions/runs/37856976470)
(commit `32e314770da10cc62dab30dcfeb340ec4c6bcb64`),
[bounded Rust run 37825247684](https://github.com/MediaNoxLabs/compact/actions/runs/37825247684)
(commit `20cd967eecd967cef2c184277e73892eeb546752`).
Step timestamps and cache inventory summary are in
[local research evidence](../evidence/compact-ci-research.json).

Inference: optimize Nix compiler substitution/build reuse first, and measure
keygen inside the full test lanes. The bounded workflow explicitly omits proof
qualification; adding Forge there would usually add setup cost without removing
key generation. Do not claim the 297s compiler-test step is entirely keygen.

The inspected full workflow already uses the project's Attic/IOG Nix cache;
its cache hook is non-fatal. The Apple Silicon path uses `skip_cache: true` for
Attic setup, while base substituters remain configured. Investigate cache
coverage and misses rather than blindly storing `/nix/store` in Actions cache.
The bounded Rust lane already partitions core/MSRV, profiles/features and source
revision in its target cache. Preserve that separation.

The repository cache API returned **11 caches, 10,864,395,704 bytes** (10.86GB
in decimal units). The largest two Linux target archives were 4.51 GB and 3.08 GB;
the largest four Linux/macOS archives totaled about 9.62 GB and were scoped to
`refs/pull/504/merge`. This is substantial pressure relative to GitHub's default
10GB budget. The actual configured budget/billing settings were not queried;
no cache was deleted and no storage limit was changed.

GitHub currently documents a configurable 10 GB default, seven-day inactivity
expiry and capacity eviction; extra configured usage is billable. Size budgets
and measurements are preferable to adding an unbounded full-store archive per
matrix job. [Official cache policy](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#usage-limits-and-eviction-policy).

## Cache layers and identity

| Layer | Contents and key boundary | Reuse policy |
| --- | --- | --- |
| Nix | Signed closures for compiler, Forge plus v3 worker, toolchain and dependencies; exact derivation/system. | Existing trusted binary cache; publish authorized trusted builds once. Keep compiler derivations hermetic. |
| Cargo | Registry/git downloads separate from target; OS/arch, rustc, locks, features, flags/debug profile, native dependency/toolchain identity. | Cargo still rebuilds current source and executes tests. Target cache is not a test-result cache. |
| Parameters | Exact verified public parameter files, scheme and a digest/size manifest. | Restore before Forge; upstream hash verification remains required even on a cache hit. Forge needs actual parameters to compute a warm recipe. |
| Forge | Consistent database plus external CAS and persistent exports; platform, exact tool/profile/worker and parameter partition. | One trusted snapshot producer; isolated writable job-local restores; Forge rechecks every requested circuit. |
| Same-run artifacts | Current compiler/runtime archives, generated provider layouts or a stopped Forge snapshot, manifest/provenance and job reports. | Explicit `needs:` producer dependency; unpack private copies for each consumer. No global cache race for an exact run's output. |

Use two related keys, not a single lockfile key forever:

```text
partition = SHA256(platform + exact Forge/profile/worker provenance + params manifest + schema)
primary   = forge-v1-{partition}-{workload-inputs-hash}
fallback  = forge-v1-{partition}-
```

`workload-inputs-hash` includes the compiler/test dependency cone, selected
scenario list, relevant scripts, flags and lockfiles, with sorted paths and exact
bytes. Assert discovery is nonempty. After compilation, also record actual
emitted ZKIR digests in the receipt; Forge itself always keys the emitted bytes.
Do not drop platform/profile/parameter identity from fallback prefixes. Do not
use a broad `forge-` fallback across trust/profile boundaries.

GitHub cache entries are immutable. A lockfile-only exact key can permanently
restore the first incomplete circuit population without saving later growth.
For deterministic complete workload keys, restore the compatible old snapshot,
run the full selected workload, and save the expanded store under the **new
primary** key only after success. A miss is permission to generate, never to
skip tests. If workloads add circuits without changing their declared key,
fix the key contract or use bounded producer generations with a run suffix;
do not create a large new archive merely because stats counters changed.
[Official action cache update pattern](https://github.com/actions/cache/blob/main/tips-and-workarounds.md#update-a-cache).

Keep one writer per partition and one publisher, rather than every matrix job
trying to save a different partial database under the same key. There is no
supported store-merge operation. Budget snapshot count/bytes and inspect churn
before permitting PR-scoped scratch saves; strict restore-only PR consumers are
the initial recommendation. Same-PR scratch reuse is an optional later policy,
never a source for trusted default-branch seeds.

## Snapshot consistency and a bounded local result

A SQLite backup by itself does not snapshot external object files. Stop all
producer CLI/HTTP/worker processes, then copy the entire private store, including
any SQLite sidecars, into a staging directory. Snapshot only successful normal
runs; corruption/eviction experiments belong in other stores. Do not merge
SQLite files, copy a running database and CAS independently, or delete exports/
tables as an undocumented shrink operation. No supported snapshot/prune command
exists yet; a tested dedicated snapshot operation is a useful future feature.

The bounded experiment used **private stopped stores**, the installed ARM macOS
Forge and one minimal fixture for each profile. Both stores were copied to a
different canonical absolute root. Both restored requests were verified hits,
kept the same artifact identity and returned paths under the new root; all
export hashes and SQLite integrity checks passed. Each restored stats counter
increased by one logical hit. This qualifies that narrow relocation primitive,
not Linux, large caches, live snapshots, GitHub upload/download or Compact itself.
[Experiment receipt](../evidence/compact-ci-snapshot-probe.json).
Reproduce this bounded probe, with verified parameters already present:

```sh
./bootstrap.sh -- python3 docs/research/probe-forge-snapshot.py \
  --compact-root /absolute/path/to/compact \
  --binary "$HOME/.local/bin/midnight-zkir-forge" --output /tmp/forge-snapshot-probe.json
```

Never reuse serialized old CLI response paths after restore. Invoke Forge again
for current runner paths. Stats in the database already contain prior history;
report before/after deltas and store job receipts separately. Source JSON and
requested local paths can be present in the archive. CAS plus copied exports
also duplicate large keys, and cryptographic bytes may compress poorly.
Measure the real compressed archive and transfer cost before widening the set.

## Trust and fallback behavior

Caches are not signed provenance. An attacker controlling database plus objects
can replace claimed digests and keys coherently; successful hash checks do not
authenticate the intended circuit publisher. Use a trusted default-branch producer,
pinned source/tool provenance, expected source/profile/verifier identities and
independent genuine proof controls. PR jobs get no cache-publishing credential
or remote Forge token. Never run untrusted PR code in a privileged cache seeder.

GitHub documents base/default-branch cache reads by PRs, PR merge-ref isolation,
restore-only operations and the current `cache-mode` workflow/job key. Explicit
`cache-mode: read` adds least privilege where supported; separate restore/save
actions and trusted-event/ref guards remain the baseline. Keep public test
circuits only in fork-readable caches; no tokens, witness data or private source.
[Official cache access/security rules](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#restrictions-for-accessing-a-cache).

| Situation | Behavior |
| --- | --- |
| Cache unavailable/expired | Start an empty job-local store and generate; all tests execute. |
| Compatible partial snapshot | Forge hits unchanged circuits and generates missing derivations. |
| Wrong profile/build/parameter declaration | Refuse or select a separately explicit uncached lane; never rewrite identities. |
| Restored corruption | Fail the integrity control. A reviewed policy may quarantine the whole private snapshot and retry from empty with a visible degraded-cache receipt; never silently accept or re-key the corrupt entry. |
| PR changes shim/compiler | Test that PR in an unprivileged job, but do not promote its cache to a trusted seed. |
| No verified parameter file | Use explicitly authorized upstream verified acquisition, or fail offline. A Forge restore alone is insufficient. |
| No qualified Forge executable | Run an explicitly selected genuine uncached lane, or fail qualification; no automatic stale-output fallback. |

## Proposed rollout and acceptance

1. **Qualification and baseline.** Publish a reviewed Forge revision when
   authorized; package/substitute it once per target platform. Add per-platform
   build qualification to Compact without weakening source/profile/parameter
   checks. Record current-head cold/uncached/warm full-case timing on Linux.
   Existing two-circuit consumer guide results are useful historical context,
   not a current-build or CI qualification. Tiny cases already showed little
   benefit; prioritize representative heavier circuits.
2. **V2 job-local pilot.** Wire `COMPACT_ZKIR_FORGE_BIN`,
   `MIDNIGHT_ZKIR_FORGE_DIR` and `MIDNIGHT_PP` into one proof-bearing lane.
   Keep `COMPACT_ZKIR_MODE=uncached` for a distinct genuine keygen control.
   Do not add a Forge process to bounded source/type-check lanes.
3. **Trusted snapshots and fanout.** Seed on successful trusted default-branch
   pushes/manual owner runs, restore-only PR consumers, exact same-run artifacts
   for siblings, one publisher and a strict byte/count budget. Keep each job's
   mutable store local, even when several consumers share the same seed.
4. **V3 consumer pilot.** Extend the existing launcher dispatch, prove both
   profiles with actual newly emitted Compact circuits, compare fresh binary IR,
   verify private copies/manifests, test wrong 3.1/profile refusal and uncached
   controls. Forge's minimal v3 qualification does not itself qualify Compact's
   whole v3 application surface.
5. **Scale after measured benefit.** Consider per-cone snapshots or immutable
   HTTP object fetch only when archive transfer/duplication is the bottleneck.
   Preserve one serialized keygen owner per local store; parallel jobs use their
   own stores. A shared remote service would add queuing and new trust policy.

Acceptance compares cold, compatible partial, fully warm and explicit uncached
runs with the **same selected assertions/proof/negative-control counts**. Capture:
compiler/codegen time; parameter/cache transfer; Forge process/ensure/lock/verify/
generation time; proof/verification and Python historical-authentication time;
compressed bytes and peak disk; per-job stats deltas; source/tool/profile/params
and artifact/verifier identities; cache read/save outcome and total critical path.

```text
net benefit = uncached end-to-end wall time - cached end-to-end wall time
```

Include Forge provisioning, restore/unpack and save costs. Upload time and summed
matrix CPU-minutes can matter even when a parallel save is off the critical path.
Do not infer savings from hit percentage, mock-compile timing or the minimal
Forge fixture. Historical Python reconstruction/authentication and actual proof
costs are independent work; Forge cannot eliminate them.

The example hashes all tracked files as a conservative first-pilot workload
boundary. This intentionally includes docs-only changes; the same partition
fallback can still reuse unchanged circuits. Narrow to a tested dependency cone
only after validating its input coverage. Its run/attempt suffix is saved only
when the normal non-evicting pilot records new generation misses and remains
within its byte budget, avoiding new archives for stats-only changes. The v5
cache action pin was checked against its official release ref; it requires a
Node 24-compatible runner at least 2.327.1. No action versions were changed in
active workflows by this research.

Research-only [workflow fragment](examples/compact-forge-cache.yml.example)
illustrates cache mechanics after qualification. It is not wired into either
repository and deliberately does not pretend to solve publication/qualification
or consumer ownership changes. See the independent
[GitHub cache architecture review](github-cache-review.md) for detailed policies.
