# Progress

## 2026-10-15 — iteration 1: local factory and contract

- Read the supplied starter/product spec, factory vault bootstrap/runtime/porting
  guidance, Oxid factory setup, Midnight initiative context and SDK Rust's
  developed OpenSpec workflow (the primary sdk-rust checkout is older).
- Created issues #1 and #2 in input-output-hk/midnight-zkir-forge as requested.
- Adopted Nix, spec-driven local delivery, signed DCO commits, one writer,
  supervision disabled, no push/remote CI. Added the product spec and explicit
  latest-stable-ledger8 owner amendment. Bootstrap validation in progress.
- Official tag audit: latest stable ledger8 is 8.1.3, ZKIR 2.1.1. Ledger 8.2.0-rc.1
  is a prerelease, not the selected stable baseline.
- First cache slice is one circuit per bundle; wider SPEC.md scope stays planned.

## 2026-10-15 — iteration 2: real local cache

- Resolved official ledger8 8.1.3 commit and exact midnight-zk versions in
  Cargo.lock; profile checker rejects incompatible drift. No ledger crate is
  needed by this key-generation adapter. No fork or cryptographic copy.
- Implemented import/prepare/ensure/inspect/resolve/export/evict/stats/profile/
  qualify. Default store is ~/.midnight-zkir-forge, with CLI/env overrides.
- SQLite immediate transactions serialize writers across processes. Verified
  content-addressed blobs and copied persistent exports have separate lifetimes.
  Derived eviction preserves sources and identities; archived recipes remain
  available for regeneration identity checks.
- Independent review found and corrected export path recipe collisions,
  cross-bundle duplicate generation and stale derivation readiness. Final
  review reports no remaining source blockers for identity/concurrency.
- All six fast Rust tests and all three real backend tests pass. Real controls:
  valid proof, invalid statement, corrupted proof, byte-reproducible generation,
  renamed-circuit dedup, warm reuse, eviction/regeneration identity, corruption
  refusal, forced identity conflict and simultaneous processes (one miss/hit).
- The real process test caught first-open WAL transition contention; new stores
  use default rollback journaling with FULL sync. No stale-job lease is claimed.
- Explicit CLI acceptance killed a writer while holding the SQLite transaction,
  confirmed no ready publication, regenerated, resolved one artifact and checked
  structured nonzero failure. Passed.
- Formatting, Clippy -D warnings, local policy/profile/spec structure and known-
  bad commit-policy controls pass. The first check script was edited during its
  execution and failed at a stale shell offset; the complete settled rerun passed.
- Debug-binary minimal-assert measurement: cold 154.10ms, warm 15.78ms process
  wall (9.76x); ensure phase 118.42ms/5.55ms; peak process RSS 18.78MB/15.88MB.
  This is one tiny genuine circuit, excluding compilation/other processes;
  no large-contract speedup or memory qualification is implied.
- Nix binary-distribution Rust 1.98.1 and Oxid's pinned nixpkgs/Pi baseline
  replace the initial slow fresh toolchain download. Pi audit passes at 0.84.0.
- Standalone Nix release build/install is running; final installed-binary evidence
  and vault checkpoint follow. No code pushed, PR, hosted CI or supervision run.

## 2026-10-15 — installed MVP checkpoint

- Implementation commit: f75dc26 (GPG verified, DCO signed). Standalone Nix
  package builds and tests successfully. Installed at ~/.local/bin/
  midnight-zkir-forge, GC-rooted by ~/.local/share/midnight-zkir-forge/current.
- Installed binary passes uncached qualification and CLI crash-recovery controls.
  Default ~/.midnight-zkir-forge was created and repeated prepare returned a hit.
- Installed release measurement: cold process wall 136.20ms,
  warm 13.98ms (9.74x for this fixture);
  ensure phase 107.00ms / 4.56ms.
  Peak process RSS 15.47MB cold and
  13.43MB warm. These supersede the debug
  example for installed CLI timing; not a large-circuit or multi-host claim.
- Nix flake evaluation passes on aarch64-darwin; other declared systems were
  omitted by the native check and are unqualified. Pi audit still passes.
- Midnight vault initiative/index updated. README contains reinstall/PATH,
  Python test integration, lifecycle, statistics and uncached qualification.
- Local MVP complete. Issues #1/#2 remain as remote tracking; no code push,
  PR, hosted CI, deployment, automated merge or persistent supervision occurred.
- Next slices: broader real consumer fixtures, multi-circuit manifests, explicit
  purge/GC/retention and JSON-lines mode; HTTP only after those local contracts.

## 2026-10-15 — issue #3: exact consumer ZKIR3 cache

- Saved the consumer starter prompt in the Midnight vault and linked it from
  the global skill. Issue #3 and a planning-only signed OpenSpec commit own
  this increment. User explicitly authorized v3 after the original deferral.
- Read-only consumer configuration inspection found v3 pinned separately to
  official 3a7ae0361d03e6eed4fc91e31f6600f334f605d5. It is not ledger8
  b5d3e96's bundled RC; both use the same crate version but different binary
  tags. Exact consumer v3 uses ir-source[v3-generic], transient2.1.0,
  base1.0.0, serialize1.1.0 and the existing registry proof/circuit pins.
- Built an isolated worker Cargo workspace/lock with inspect/plan/generate/
  qualification operations, preserving the root v2 graph. Parent authenticates
  worker profile, source, binary/build fingerprints, parameter plan and output
  hashes, then publishes under existing SQLite ownership.
- Runtime discovery: this exact v3 parser accepts JSON3.0 and rejects3.1.
  Attempting minor1 qualification exposed that boundary; no coercion or fallback
  was added. The modern split repository/default graph remains unsupported.
- All eight fast tests, both real v3 tests and all three v2 real regression
  tests pass. New v3 coverage includes fresh valid/invalid proof controls,
  proofs using warm exported artifacts and regenerated exports, exact identity,
  concurrent processes (one generation/one hit), corruption and wrong versions.
- Explicit v3 crash acceptance passed. Worker parent liveness polls every50ms;
  no strict zero-overlap/real-time cancellation claim is made after owner death.
  Orphan workers cannot publish readiness. Independent review found no confirmed
  identity or compatibility defect; the cached-export proof gap was covered.
- The pre-upgrade v2 default export resolves with the same path and unchanged
  manifest. Conservative new build fingerprints may cause one new derivation;
  source inventory and old exported paths survive the upgrade.
- Formatting, spec/profile/negative commit-policy checks and Clippy pass for
  both dependency graphs. Nix build/install and installed evidence pass.
- No consumer checkout, long-running validation, push, PR, hosted CI or
  supervision was modified or started by this work.

### Installed ZKIR3 receipt

- Installed CLI 0.2.0 at `~/.local/bin/midnight-zkir-forge`, backed by
  `/nix/store/88f65288m3a03i7p1cgw2c6nrvliwmb7-midnight-zkir-forge-0.2.0`.
  Worker is retained by the package and the existing GC root.
- Installed-path qualification caught macOS retaining the launcher symlink in
  `current_exe`. The installer now links the worker beside the CLI in
  `~/.local/bin`; repeated qualification through that exact path passes.
- Installed fresh v3 qualification verifies a real proof, rejects invalid
  statement/corrupt proof controls and confirms byte reproduction. Installed
  warm and regenerated exports also verify real proofs and negative controls.
- Installed crash-recovery controls pass; the old v2 export still resolves and
  its manifest is unchanged. Installed uncached v2 qualification passes too.
- V3 minimal assert fixture: cold process wall 879.02ms, warm 193.63ms
  (4.54x in this observation). This includes one-shot worker startup and
  executable hashing and is not a large-circuit or general performance claim.
- Receipts: `docs/evidence/zkir3-{profile,qualification,installation,benchmark,
  installed-acceptance,local-checks,v2-regression}.json`. Temporary experiment
  exports were removed after recording results.
- Midnight vault starter prompt and initiative note updated; global skill links
  the prompt and explains exact v3 scope, profile assertions and uncached fallback.
  Skill validation passes. Delivery stays local, with no consumer test edits.

## 2026-10-15 — issue #4: documentation and initial HTTP service

- Owner authorized a Midnight styled Pages site, basic CI/e2e definitions, HTTP
  transport and Docker packaging. Signed planning commit `51318ca` records
  `openspec/changes/http-docs-container/`; workflow files stay local until push.
- Static documentation uses official brand-hub black/white/blue, relative assets,
  no runtime CDN and mobile navigation/copy controls. Desktop and mobile browser
  interaction review passes. Static build, links and ten OpenAPI routes pass.
- HTTP `serve` defaults to loopback; non-loopback binding requires a token file.
  Exact raw single-circuit uploads, synchronous materialization, inventories,
  source/objects, stats/profiles, health and OpenAPI are implemented. Downloads
  verify bytes before streaming/HEAD/conditional/range responses; GET never
  generates. Server-local paths and upstream diagnostics are excluded.
- Storage/crypto runs off the HTTP executor, with two bounded upload buffers,
  eight work/stream slots and one HTTP materializer. Existing SQLite leases
  serialize CLI/HTTP publication. Body deadlines and SIGTERM shutdown are wired.
  This is single-owner admission control, not a CPU/memory sandbox or durable
  job supervisor; archives, provider views, namespaces and hosted policy remain
  future scope. Parameters stay offline unless the operator opts in.
- Local full checks pass: eight fast Rust tests, both-graph Clippy/formatting,
  spec/profile/commit policy, real-process HTTP fast e2e and docs validation.
  All three real v2 tests and both real v3 tests pass again. HTTP real e2e
  downloads warm key/IR bytes for both pins and uses those exact files for real
  proofs and invalid controls. It also checks slow-upload saturation, SQLite
  contention/admission, responsive liveness, corruption before304, auth and ranges.
- Independent review identified pre-admission upload buffering and missing Nix
  embedded contract source; both fixed. Settled code/proof review found no
  additional confirmed blocker. Receipts: `docs/evidence/http-{e2e,review}.json`.
- CI uses pinned actions, lock/toolchain-keyed Rust caching and bounded jobs;
  expensive verified-parameter proof e2e requires a manual opt-in. Pages
  publication is a separate manual workflow. YAML, action references and
  Compose configuration validated locally; no remote runs were dispatched.
- Linux Nix OCI outputs evaluate on x86_64/aarch64. Image includes both official
  backends, non-root UID65532, persistent cache and mounted parameters/token;
  Compose publishes localhost only. Image build/runtime smoke is NOT qualified:
  this Darwin Nix host has no Linux builder, despite Docker Desktop availability.
  `scripts/check-container.py` is ready for a loaded Linux image.
- Native ARM macOS Nix package builds/tests successfully. Installed output:
  `/nix/store/jsgn4b0ia9l2mzq30bpaxjp62ckgzzjv-midnight-zkir-forge-0.2.0`,
  implementation `d473862`, GC-rooted through the existing local installer.
  The actual `~/.local/bin` launcher serves authenticated HTTP successfully.
  Installed release HTTP e2e repeats both profiles' genuine downloaded-warm-key
  proofs/negative controls, admission, corruption, auth and range checks.
  Receipts: `docs/evidence/http-installation.json` and
  `docs/evidence/http-installed-e2e.json`.
- Preview built at `.local/site` and served locally at127.0.0.1:8087. Global
  skill and Midnight initiative knowledge updated, skill validator passes.
  No push, Pages deployment, image publication or supervision occurred.

## 2026-10-15 — issue #5: Compact and GitHub CI research

- Inspected Compact's current compiler hook, v2 adapter, qualification runner,
  Nix setup and CI source read-only. Current adapter's build allowlist still
  expects `340e0b3b…`; installed Forge reports `6b62bbf3…`. Exact v2 backend
  matches, but consumer build qualification must be updated before use. Its v3
  route remains explicitly uncached despite Forge now supporting the matching pin.
- Full compiler CI does not yet provision Forge. Bounded Rust checks are not
  proof/keygen lanes and are poor candidates for additional Forge setup. Preserve
  hermetic Nix builds and use signed compiler/Forge binary substitution there.
- Read-only historical completed job APIs show 455s compiler build, 297s compiler
  tests and 54s E2E in an 860s Linux job; bounded Rust jobs 97s/39s. These Oct8
  runs are different revisions from the current local consumer, not a new CI
  benchmark. Cache API reports 11 entries totaling 10,864,395,704 bytes, with two
  Linux target archives consuming about 7.60 GB. No cache/settings were mutated.
- Proposed separate Nix/Cargo/verified-parameter/Forge layers, a trusted stopped
  store producer, restore-only PR consumers, exact same-run workflow artifacts,
  one publisher, partitioned immutable growth keys and an explicit byte budget.
  Keep proofs, verification, assertions and uncached controls in every mode.
- Local bounded Forge-only relocation probe passes for both minimal profile
  fixtures: SQLite integrity, warm reuse, unchanged artifact identity, current
  relocated paths, export digests and per-job stats deltas. No Linux/large-cache/
  live-snapshot or Compact qualification claim is made. Reproducible research
  probe takes explicit checkout/binary/output paths and uses private temp stores.
- Saved main proposal, official-source cache review, non-active YAML example and
  API/source/snapshot evidence under `docs/research` and `docs/evidence/compact-ci*`.
  Independent review found no blocker; action/runner requirements, miss-count
  naming and conservative workload key coverage clarified. YAML/shell/embedded
  Python, links, JSON and unchanged inspected source hashes validate.
- Consumer HEAD advanced concurrently from df7367fc to 67a3403f through unrelated
  performance docs/patch changes; no inspected integration/workflow file changed.
  This session made no writes, ran no builds/tests and dispatched no CI in Compact.
  Global skill and Midnight vault gain research links; delivery remains local.

## 2026-10-15 — issue #6: verified snapshots and CI helpers

- Implemented writer-leased standalone SQLite backup plus bounded CAS/export
  directory inventory. Restore validates identities, schema, ready references,
  canonical exports and current producer/profile/parameter scope, then atomically
  publishes to an absent explicit root. No overwrite/merge or Compact amendment.
- Added Nix-packaged `midnight-zkir-forge-ci`: exact tool/platform/profile/worker/
  actual-parameter partition, declared workload and immutable generation keys;
  restore, post-restore baseline, job-only report, bounded trusted-growth save
  planning. No remote upload or test-result caching. Workflow conditions and
  GitHub scopes supply authority; environment/test-success declarations do not.
- Full local bootstrap checks pass, including formatting, locked unit tests,
  Clippy, policy/profile/spec checks, fast snapshot/HTTP e2e and Pages validation.
  Real snapshot suite passes for both exact profiles: cold save, relocation, warm
  artifact proof verification, invalid-statement/corrupt-proof controls and evicted
  identity regeneration. Wrong-scope/noncanonical export/contradictory metadata
  regressions rehash their envelopes to exercise deeper invariants.
- Independent review addressed bounded traversal, exact schema, ready/partial
  generation records, cross-table output identities, immutable export bytes and
  writer-lease release with existing readers. Final reviewer reports no blockers.
- Evidence: docs/evidence/snapshot-ci-e2e.json and snapshot-ci-review.md.
  Usage: docs/ci-cache.md and Pages snapshot section. Skill/vault handoff updated.
- Native execution is aarch64-darwin; Linux atomic-publication runtime is not
  qualified by this receipt. Cargo's SQLite backup feature/direct libc declaration
  changes the Forge build fingerprint; Compact's old build allowlist remains
  untouched and needs separate consumer qualification. Nix install receipt follows.

## 2026-10-15 — issue #6 installed checkpoint

- Implementation `d0f3829` is GPG verified with DCO and AI attribution.
- Native Nix build/package tests/install pass. CLI and CI helper are installed
  together in ~/.local/bin, GC-rooted by the existing local installer.
  Output: `/nix/store/8hv68ld7yndf9r8ncqppcy8kp5n4cvqc-midnight-zkir-forge-0.2.0`.
- Installed root build fingerprint: `b5cba5ea11a4725ea00262c68506fd340dc7c39cdd7aa9e9f18fb80ea2223c0d`.
  The installed wrapper produces matching key provenance. The installed binary
  passes the complete snapshot/helper e2e with genuine restored warm v2/v3 proof
  verification, negative controls and eviction/regeneration identity checks.
- Evidence: snapshot-ci-installation.json and snapshot-ci-installed-e2e.json in
  docs/evidence. Pages links/anchors validate after adding snapshot documentation;
  global skill validates and Midnight vault handoff is updated.
- All issue #6 tasks complete locally. Linux runtime and Compact consumer
  requalification remain separate scope. No push, PR, hosted CI, upload, Pages
  deployment, image publication or supervision was performed.

## 2026-10-15 — issue #7: documentation language and architecture

- Reviewed official Midnight provider guide, Midnight.js API and ZKIR repository.
  Adopted prover key/verifier key, ZKIR, NodeZkConfigProvider, FetchZkConfigProvider
  and the distinction between ZK config retrieval and ProofProvider. No new SDK
  compatibility or drop-in HTTP provider claim is made.
- Enclosed the existing Forge mark in an oval; removed local-first labeling and
  positioned Forge around key generation, reuse and distribution. Added offline
  SVG architecture, CLI prepare and HTTP sequence diagrams with accessible text.
- Documented actual CLI arguments/files → JSON stdout conventions, stderr/error
  exceptions, lack of public stdin/JSON-RPC streaming, HTTP metadata/bytes boundary
  and current fetch-provider layout limitation in the site and API convention guide.
- Documentation-only increment: no runtime, profile, Compact or workflow changes.
- Validation: Pages build/link/anchor checks pass; all four SVG files parse.
  Browser inspection at 1440px and 390px confirms loaded diagrams and no page
  overflow. Diagrams scroll within their own figure on small screens.

## 2026-10-15 — issue #8: portable local development skill

- Added root SKILL.md with Nix setup, exact profile/parameter compatibility,
  current-input prepare integration, provider directory consumption and cold/warm
  validation while preserving real proofs, verification and assertions.
- README provides a direct agent handoff. Existing global Forge skill links the
  portable repository entrypoint. No global skill replacement or runtime change.
- Skill validator and referenced-file checks pass. Documentation only; Compact
  and other consumer checkouts remain untouched. Delivery is a signed local commit.

## 2026-10-15 — issue #9: simplify local recovery

- Shared atomic no-replace directory publication for exports/snapshots; removed
  duplicate eviction readiness SQL and repeated export-manifest parsing. Relative
  export destinations resolve against the caller's working directory. No new
  dependency, daemon, scheduler, backend pin or API surface.
- Success accounting now shares ensure/resolve/HTTP-download transactions, removing
  a second writer lease and rolling back new readiness if accounting fails. Failed
  error accounting preserves the original cause. Request timings explicitly
  exclude final COMMIT/process overhead; measure wall time separately.
- Bounded source reads and streaming existing-object verification refuse oversized
  corrupt CAS before unbounded allocation. Sparse-file regression passes.
- Full bootstrap suite, Clippy, three v2 and two v3 real backend tests, both-profile
  real snapshot/HTTP suites and new failure-recovery e2e pass locally. Recovery
  exercises metrics/file-metrics faults, export obstacles, interrupted final COMMIT
  with an already published export, rollback/reopen/retry, damaged-export owner
  repair, warm reconstruction and real proof/negative controls with pinned outputs.
- Independent review reports no remaining blockers. Evidence and scope are in
  docs/evidence/local-recovery-*; operator guidance is docs/recovery.md. Native
  platform is aarch64-darwin; no Linux, power-loss or actual disk-full claim.
- Source delivery only: installed Nix executable remains at the earlier checkpoint;
  use target/debug/midnight-zkir-forge for this tested increment or rerun the
  existing installer when adopting it. Compact and other checkouts untouched;
  no push, PR, hosted CI, deployment, image publication or supervision.

## 2026-10-15 — issue #9 installed recovery qualification

- Rebuilt implementation `3b330e8` through the locked Nix installer; all ten
  package fast tests pass. The five opt-in real backend tests remain ignored
  during package checks; installed real recovery was executed separately.
- Installed CLI, CI helper and pinned worker are GC-rooted by the normal launcher
  links. New output: `/nix/store/9lcrz2k3j6nw3y3rzc7rjyn50jdl1j05-midnight-zkir-forge-0.2.0`.
- Installed CLI passes both-profile recovery: primary errors survive accounting
  faults, successful accounting rolls back with metadata, relative exports work,
  export obstacles are correctable, reader-blocked COMMIT termination reopens
  cleanly, counters do not commit early, and copied exports rebuild on warm hits.
  Pinned output identities and real proof/negative controls pass for v2 and v3.
- Recovery explicitly selected the installed v3 worker. Normal installed worker
  discovery also passes without the override. V2 proof controls use the locked
  fixture verifier consuming installed-CLI-generated artifacts; v3 uses the
  installed worker's qualify-export. No debug CLI generated recovery artifacts.
- Receipt: docs/evidence/local-recovery-installation.json (source commit, Nix
  output, executable hashes/profiles, parameter digest and full recovery result).
- This supersedes the prior source-only checkpoint. Native platform remains
  aarch64-darwin; Linux, power-loss and actual disk-full recovery are unqualified.
  All probes use private stores; Compact and other checkouts remain untouched.
- Owner additionally authorized publishing the completed history to main after
  this signed evidence commit. No manual workflow dispatch, Pages deployment,
  image publication or supervision is part of that publication.

## 2026-10-15 — issue #10: hosted CI and Pages publication

- Initial main CI https://github.com/input-output-hk/midnight-zkir-forge/actions/runs/38749437847 passes at `bffeb356fbaac0cc2325e22c24d657bce3603b7a`. Linux fast
  checks include profile/spec/policy validation, Rust tests/Clippy and recovery,
  snapshot, HTTP and documentation e2e. No failures or runtime fixes were needed.
  The manual real-proof lane is skipped; Linux proof/container qualification
  remains distinct from these passing fast tests.
- Enabled Actions-based Pages while preserving private repository/site access.
  Owner-authorized workflow https://github.com/input-output-hk/midnight-zkir-forge/actions/runs/38752102625 passes build and deployment.
  URL: https://curly-adventure-gken1jg.pages.github.io/ (GitHub sign-in/repository access required).
- Deployment 7095437980 reports success; all nine files in its uploaded artifact
  match the locally validated site bytes. Receipt: docs/evidence/pages-publication.json.
- README/site/workflow guide now link the deployed site and record current scope.
  Non-blocking action-runtime deprecation annotations are recorded; no unrelated
  action upgrades were introduced. Compact and other checkouts remain untouched.


## 2026-10-16 — issue #12 compiler contract

- Added one strict path-free descriptor shared by CLI, export sidecars and HTTP.
  Its validated decode entrypoint rejects ambiguous/unknown fields and inconsistent
  identities. Existing identity transcripts and immutable legacy manifest bytes stay
  intact; missing verified sidecars can be added atomically. Snapshot validation
  accepts old exports and checks new sidecars.
- Typed errors originate at parameter/backend/store/worker boundaries, keeping
  absent parameters distinct from corrupt bytes. CLI public JSON and HTTP are
  sanitized; private diagnostics remain on stderr. Policy never parses strings.
- Native full bootstrap, strict premise controls and real both-profile HTTP,
  snapshot and recovery suites pass. Real proofs, verification and negative
  controls execute on warm exports/downloads. Timing and request deltas are in
  docs/evidence/compiler-compatibility-local.json; tiny fixtures are not consumer
  speedup claims. Independent agent review completed; Nix worker source closure
  builds with the shared typed-error module.
- Local source delivery only; installed CLI is unchanged. No Compact edits,
  consumer qualification claim, push, release, deployment or hosted run.
