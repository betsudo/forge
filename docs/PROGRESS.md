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


## 2026-10-16 — issue #11 private installer

- Implemented exact-tag authenticated gh/Python installation, bounded downloads,
  strict manifests/inventories, bounded gzip/tar parsing and safe staged extraction.
  Root CLI, v3 worker and CI helper activate through one pointer under a separate
  binary root; existing Nix launchers are refused rather than overwritten.
- Offline fake-gh e2e passes install/reinstall/upgrade/rollback, checksum/path/
  conflict refusals, live/killed lock recovery, before/after activation termination
  and interrupted first-link retry. Independent review blockers are resolved.
- Candidate tooling builds the exact clean Git commit through locked Nix, copies
  ancillary files from that recorded commit and inspects/relocates native loaders.
  It does not accept arbitrary stale executable inputs as source provenance.
- Pinned private-flake documentation/example and native devShell evaluation pass.
  No binary release exists yet. Native candidate execution, clean no-Nix consumer
  qualification, licensing audit and Linux portable production remain explicit
  gates; no broad portability claim. Receipt: docs/evidence/private-installer-local.json.


## 2026-10-16 — issues #13–#16 research contracts

- Proposed bounded GitHub snapshot/action transport with exact local recipe reuse,
  provider-view qualification and a reproducible genuine-proof benchmark protocol.
  DID v0.7.0 codegen measured 0.4505s for 12 JSON2.0 circuits; keygen savings are
  unmeasured. Passport's required Compact0.35.0 is absent. Historical job durations
  are allocation evidence, not claimed optimization results.
- Named the optional component Forge Proof Relay: exact binary requests, pinned
  server/builtin/parameter context, private HMAC request identities, independently
  verified responses, unchanged miss forwarding and mandatory uncached proving
  coverage. It is a proposal, not runtime cache behavior or an assertion bypass.
- Documented official published-crate availability and explicit worker/profile
  matrix without changing current pins or claiming generic ledger9 support.
- Compared Rust cloud admission, native keygen placement and object/CDN providers
  with dated prices and explicit cost exclusions. Transparent key compression
  preserves decoded identity and exact provider integrity/runtime metadata;
  DID/passport compression measurements remain pending.
- Independent cross-reviews report no remaining blockers after clarifications.
  Research index: docs/research/README.md. OpenSpec structure checks pass; no
  consumer checkout, Compact, hosted workflow, cloud or publication change.


## 2026-10-16 — issue #17 calendar milestone

- Created GitHub milestone 2026.10.0 without an invented deadline and assigned
  issues #1–#17, including newly scoped research issues #13–#16 and version #17.
  Local autonomous goal/acceptance is docs/milestones/2026.10.0.md.
- Product versions are YYYY.M.PATCH (month without leading zeros); current
  CLI/worker/locks/Nix/Compose/OpenAPI agree on 2026.10.0. Backend dependency
  versions/pins and historical receipts remain unchanged.
- Full native bootstrap and both-profile real descriptor parity, HTTP-downloaded
  proof, snapshot and failure-recovery controls pass for the calendar candidate.
  Receipt: docs/evidence/calver-local.json. Review found no version/identity blocker.
- No push, tag, release upload, hosted run or deployment. Portable Linux/other
  architectures and clean no-Nix consumer qualification are separate release gates.


## 2026-10-16 — issue #18 four-platform Nix evaluation correction

- Final evaluation exposed that locked Nixpkgs26.11 drops Intel macOS although
  Forge advertised x86_64-darwin. Added separately revision/hash-locked official
  nixpkgs-26.05-darwin only for Intel macOS; original Nixpkgs/rust-overlay lock
  nodes and Midnight crate pins remain byte-for-byte unchanged.
- All four package and dev-shell derivations now evaluate; independent review
  found no blocker. Receipt: docs/evidence/nix-platform-evaluation.json. Intel
  build/runtime and Linux proof qualification remain distinct pending gates.
- The earlier source09b0b1a macOS ARM64 candidate successfully installed under
  fake-gh local transport and executed real v2/v3 proof controls with /nix and
  checkout runtime reads denied. Its relocated CLI/worker also passed ordinary
  real recovery. The new lock conservatively changes build identity, so a new
  native candidate/receipt follows rather than reusing the earlier claim.


## 2026-10-16 — 2026.10.0 local acceptance

- Built the final lock-aware native candidate from exact signed source a0badb8.
  Actual local fake-gh installation with external Python passed while denying
  /nix and checkout runtime reads. Both v2/v3 genuine proof verification,
  reproducibility and invalid-statement/corrupt-proof controls pass.
- The verified relocated CLI and paired worker separately passed ordinary real
  recovery: accounting rollback, killed-before-COMMIT recovery, export repair,
  warm reconstruction and preserved output identities with real proof controls.
- Final-source full bootstrap, real descriptor premise/parity, HTTP-downloaded
  proof and snapshot suites pass. All four package/main-shell/consumer-shell
  derivations evaluate. Existing Midnight/Nixpkgs/Rust-overlay pins stay unchanged;
  only the separately locked Intel Darwin input was added.
- Acceptance matrix: docs/milestones/2026.10.0-acceptance.md. Complete native/source
  receipt: docs/evidence/milestone-2026.10.0-local.json. Research contracts and exact
  consumer observations are complete; measured CI savings, Linux/Intel runtime,
  clean no-Nix host, license audit and real release download remain explicit gates.
- GitHub milestone includes issues1–18. No push, release/tag/upload, hosted dispatch,
  deployment, Compact/other-checkout edits or shared CLI reinstallation. Installed
  shared Nix CLI remains0.2.0; this increment delivers source and local candidate.


## 2026-10-16 — issues #11/#13 exact consumer integration in progress

- Added isolated Compact0.35.0 JSON3.1 worker pinned to official ZKIR e82d81d2
  and ledger9a8777c4; existing v2/JSON3.0 pins and identity transcripts are unchanged.
  ZKIR source and ledger revisions are separately represented. Verifier serialization
  is v7 only for the new profile. Ledger9 transactions/network remain deferred.
- Parent concurrent requests join one generation; strict descriptor premises reject
  swapped source/ledger revisions and minors. Local three-profile snapshot/helper
  controls prove restored warm exports, reject invalid/corrupt proofs, preserve
  evicted identities and reject a changed worker31 provenance. Local three-profile
  recovery controls pass; final installed-candidate receipts remain pending.
- Exact DID/Passport compiler artifact and genuine application preimage qualification
  receipts are in docs/evidence/did-* and passport-*. All52 Passport codegen outputs
  match across three full runs. These are compatibility measurements; final paired
  release-binary transport-inclusive benchmarks remain pending.
- Independent parent identity/concurrency review found and resolved the separate
  repository revision issue. No further blocking finding in the reviewed Rust paths.
  No Compact/other checkout edits, publication or shared CLI replacement.


## 2026-10-16 — portable producer and benchmark qualification follow-up

- Linux relocation bundles the exact ELF loader/library closure, verifies its bytes
  before execution and refuses inherited loader overrides after trusted Python
  startup. Runtime-source attribution checks canonical exact Nix output paths and
  source digests; alternate-store, dotted-path and symlink controls pass.
- Common source collector supplies full upstream runtime sources, locked Nixpkgs
  recipes/patches and exact Forge source bundle. macOS uses Apple's libiconv BSD/APSL
  notices; it is not attributed as GNU LGPL libiconv. Component receipts are
  docs/evidence/linux-runtime-regression.json and darwin-runtime-source-audit.json.
- Cargo collector authenticates registry archives, exact Git revisions and pinned
  missing-license supplements; preserves Rust standard-library notices. Independent
  review fixes distinguish actual license files from attribution-only NOTICE and
  include nested notices for Git-root packages. Eight offline refusal/coverage
  controls pass. Final per-candidate notice inventories remain producer output.
- Producer freezes committed packaging helpers before its Nix build. Installer
  e2e covers optional-worker inventory refusal, upgrade and legacy rollback. HTTP
  downloaded artifacts prove and reject invalid/corrupt proofs for all three profiles.
- Benchmark runners now invoke the actual helper for unavailable snapshots and
  include its elapsed time. Passport explicitly pairs generation/proof workers.
  Independent benchmark review found no other blocking timing/control issue.
  Final optimized-binary runs and clean-host installed receipts remain pending.

## 2026-10-16 — final native candidate and disk cleanup

- Signed source c40e45b produced the three-profile macOS ARM64 bundle. External
  Python installed it through fake GitHub transport with Nix and checkout reads
  denied. All three genuine proof/negative controls and installed recovery suites
  pass: docs/evidence/private-installer-darwin-three-profile.json. This remains
  restricted-host evidence; the actual Nix-free macOS host/VM is unavailable.
- Full local bootstrap passed, including both isolated workers and fast process
  suites: docs/evidence/qualification-full-check-c40e45b.json. Public k4 parameters
  in the prepared clean-Mac consumer kit match all three qualification receipts.
- No obsolete worktrees exist for this session. Removed completed compilation
  caches and three superseded native bundles (about 2.2 GiB); retained current
  candidate, binaries, consumer kit, benchmark inputs and all evidence. No shared
  Nix/Docker pruning or other checkout changes. Final Linux qualification and
  sequential transport-inclusive benchmark runs remain in progress.

- Linux producer smoke exposed Nix's `LD_FOR_BUILD` build-tool variable matching
  the deliberate strict runtime `LD_*` guard. Producer now removes only that
  build-only variable from its explicit smoke environment; ordinary installer
  behavior and actual loader-override refusals are unchanged. Independent narrow
  review found no blocker; fake-GitHub installer failure/recovery suite passes.
  Cached Linux producer will qualify this fix after the benchmark window.

## 2026-10-16 — final DID benchmark

- Optimized portable c40e45b candidate completed three repetitions of all five
  exact DID v0.7.0 lanes. All12 circuit artifact triples match the official tool;
  every lane ran fresh deactivate execution, five assertions, genuine proof,
  verification and two negative controls. Independent evidence review found
  no blocker in identity, counts, partition policy or timing arithmetic.
- Median total seconds: uncached6.857, cold9.325, warm-restored2.492,
  partial-restored10.247, unavailable11.585. Warm local saving4.366s; negative
  results in other lanes are retained. Source receipts/raw repetitions and
  candidate provenance are docs/evidence/did-cache-benchmark*.json.
- Timings include local compression/restore/helper work, exclude declared prior-job
  seed manufacture, and disclose external shared-host compiler load. They exclude
  actual GitHub network latency and do not establish whole-CI savings.

## 2026-10-16 — final Passport benchmark and consumer pin

- All15 selected Passport lanes passed:30fresh genuine proofs,30verifications,
  60negative controls and270application assertions. Exact official artifacts,
  paired-worker identity, helper partitions/restore/miss and timing arithmetic
  passed independent review. Raw/audit receipts: docs/evidence/passport-benchmark*.json.
- Median seconds: uncached3.934, cold6.499, warm4.338, partial6.811, unavailable6.537.
  Warm is0.403s slower; preserve that negative result. Full52-circuit codegen and
  hosted network transport remain separate. Shared-host load is disclosed.
- Consumer flake example now pins reviewed local6c6490d with JSON3.1 support and
  the Intel correction. All four shell derivations evaluate through a local Git
  override; pin is not remotely fetchable until separately authorized publication.
  docs/evidence/consumer-example-pin.json distinguishes evaluation from runtime.

## 2026-10-16 — clean Linux recovery parameter isolation

- Actual unprivileged Nix-free Linux recovery exposed a harness omission: direct
  JSON3 worker proof checks did not receive the explicit parameter directory.
  Developer-host checks had valid ambient parameters, but did not prove this
  isolation premise. The worker calls now receive --params-dir explicitly.
- Independent narrow review found no blocker. The actual installed9359068 Linux
  candidate passed all three recovery profiles with no MIDNIGHT_PP, no mounts,
  no Nix/build checkout, uid1000 and network disabled. Separate fresh-parameter
  HTTPS proof/negative controls also passed all three profiles. Final receipts
  and archive/source/notices audit are undergoing independent review.
- Candidate source and the external recovery-harness SHA are recorded separately;
  this test-only fix changes no runtime payload, key identity or cache behavior.

## 2026-10-16 — final Linux ARM64 qualification

- Candidate source9359068 passed unprivileged installed three-profile proof and
  recovery controls in actual Nix-free Debian12/Python3.11.2, native ARM64 with
  recorded Linux7.0.14-linuxkit kernel, no mounted checkout and no network.
  Explicit parameter isolation passes without MIDNIGHT_PP. Separate fresh HTTPS
  acquisition/proof/negative controls pass for each of the three profiles.
- Independent review verified archive/checksums and782payload files,415native
  Cargo package notices, runtime/source correspondence and all-launcher corruption
  and loader-override refusals. Receipts: private-installer-linux-three-profile.json
  and private-installer-linux-runtime-audit.json. No Intel/universal Linux claim.
- Linux final assets and raw receipts are retained. Cleanup of exact owned
  containers/volume is authorized after evidence copying; no global pruning.
  macOS final build remains active and actual clean-Mac qualification is pending.

- Post-review Linux cleanup removed only the three session-owned containers and
  session-owned Nix volume, retaining all final assets and raw receipts. Disk free
  increased14to20GiB; reused images and unrelated resources were untouched.
  Exact cleanup inventory/digests are retained in the runtime audit receipt.

## 2026-10-16 — final macOS candidate and clean-host handoff

- The9359068 macOS compile succeeded, but packaging correctly refused after a
  concurrent evidence commit changed HEAD. Retried packaging from clean signed
  a65d3f0 using the completed cached build, keeping HEAD fixed until completion.
- Latest relocated macOS26.2 ARM64 bundle passed installation and all3 genuine
  proof/negative/reproducibility/recovery profiles with external Python, verified
  temporary parameters outside checkout, and Nix/checkout reads denied. Final
  receipt and independent audit: private-installer-darwin-a65d3f0-*.json. Review
  verified777payload files,422Cargo notice identities and exact source companion.
- Historical c40 benchmark receipts remain immutable and explicitly attributed to
  that payload. New main CLI bytes differ; both workers are identical. No latest
  payload timing claim is inferred from those measurements.
- Refreshed the11-file clean-Mac consumer kit with a65 assets and the explicit-
  parameter recovery harness; all checksums verify. Kit receipt records actual
  minimum macOS26.2 and strict --require-nix-free --recovery command. A real Nix-
  free Mac/VM is unavailable, so #11 and the overall goal remain open.
- Removed the completed478MiB debug target and empty failed packaging directory;
  preserved all final assets, c40 benchmark payload, exact inputs and evidence.
  Linux-owned resources were already cleaned; no shared Nix/Docker pruning.

## 2026-10-16 — clean-Mac VM staging resumed

- Owner freed space; host capacity became69–75GiB free after initially still
  reporting16GiB. Confirmed native Apple hypervisor support. The last actual
  Nix-free Mac gate can now be attempted using a temporary local VM.
- Started pinned vanilla Tahoe image download into a session-owned Tart home,
  with automatic pruning disabled and a10GiB free-space floor. Official Tart
  2.41.1 is hash-pinned and packaged through Nix; existing Forge/Nix pins remain
  unchanged. No global VM tool/profile or host credential configuration changed.
- Staged official PSF Python3.14.8 for the guest, verifying SHA and trusted Apple
  installer signature; not installed on host. Independent VM-plan review found
  no blocker. Record real guest Nix/Cargo/rustc absence, OS/mounts/Gatekeeper facts
  and launch argv without host-directory sharing before running frozen a65 assets.
- Preflight: docs/evidence/private-installer-macos-vm-preflight.json. Download is
  active; no actual guest qualification result exists yet. Run network-denied
  real proof/recovery and separate fresh HTTPS controls after boot, retain/review
  receipts, then remove only the owned VM/cache. #11 remains open.

## 2026-10-16 — clean-Mac qualification deferred by owner

- Owner requested skipping this VM step for now and explicitly documenting what
  was not tested. Stopped the queued continuation before interrupting the owned
  download; confirmed both processes and the controller terminated. No guest
  boot, installation, proof/recovery or fresh HTTPS tests ran.
- Removed only the owned Tart home, checkpoint/interrupted cache and staged
  Python package. Kept final candidates, consumer kit, scripts/logs and existing
  evidence. Receipt: private-installer-macos-deferred.json.
- Linux ARM64 clean Nix-free qualification and macOS ARM64 restricted-host
  qualification remain valid with their original scopes. Actual Nix-free macOS,
  Intel runtime and authenticated release download remain unqualified. The
  clean-Mac task stays unchecked as a deferred publication gate; current local
  work is complete under the revised owner scope. No publication or Compact edits.

## 2026-10-16 — PR #20 hosted runner disk correction

- PR #19 checks passed. PR #20's first run38866220648 exhausted runner disk;
  its check annotation reports System.IO.IOException, No space left on device.
  The runner could not retain ordinary job logs. This is not a proof failure.
- Disable Cargo dev/test debug symbols and incremental compilation in CI only.
  Use a fresh lean cache partition, including the isolated JSON3.1 lockfile, so
  restores cannot reintroduce earlier large build trees. Preserve all checks
  and the separately opt-in genuine-proof job. Compact is unchanged.

## 2026-10-16 — CI correction passed and product feedback recorded

- Signed d90377b passed hosted run38867598283, including all ordinary checks and
  cache save. The owner account then merged PR19 and updated PR20 with main;
  merge head d3ab2e8 has an identical file tree and passed run38869892304 in2m.
  No merge was performed by this CI-fix session. Genuine-proof hosted job remains
  explicitly opt-in; existing local proof evidence keeps its original scope.
- Product feedback is assessed in docs/research/ci-pilot-review.md: prioritize
  actual x86_64 Linux portable-runtime qualification, a thin JSON3.1 Action and
  enrolled-consumer hosted cache-transfer measurements. Preserve legacy profiles;
  park relay/hosting/provider service expansion. A two-week trial has not started
  and no design partner has been claimed. Linked Claude audit is sign-in gated;
  detailed findings await accessible text. Compact remains unchanged.

## 2026-10-16 — issue #21 JSON3.1 Action and native qualification implementation

- Owner authorized native x86_64 Linux installer qualification and a thin Action,
  signed pushes and a review PR without merging. Contract is github-action-pilot.
- Composite restore/save Action delegates partitioning, byte verification, baseline,
  reporting and trusted-growth admission to installed helpers; pinned cache v5
  transports only snapshots. Metadata stays outside cache and PRs cannot save.
- Local installed JSON3.1 cold/warm lanes each execute fresh genuine proof and
  invalid-statement/corrupt-proof controls;13phase/input/trust controls pass.
  Native platform preflight is bypassed only by this labeled developer-host test.
  Receipt: github-action-local.json. Independent review found no blocker; matrix
  index now distinguishes immutable save generation across matrix jobs.
- Native PR workflow builds an exact committed candidate through Nix, tests all3
  installed profiles offline as UID1000 in clean x86_64 Debian12 without Nix/Rust/
  checkout mounts, then separate verified fresh HTTPS acquisition. A following
  actual composite smoke executes JSON3.1 proof controls and enforces PR no-save.
  Actual native result remains pending; no release or cache-speedup claim yet.
- Browser retry allowed the public audit to render after the owner-described
  network delay; the anonymous embedded dashboard still says it has no contents
  and sign-in is needed for artifact data. Detailed findings remain inaccessible.
  The pasted product review is recorded; relay/hosting and consumer trial stay
  outside this implementation. Compact and existing profile pins are unchanged.

## 2026-10-16 — native x86_64 installed qualification passed

- Signed48d9181 passed native run38872428954 in26m27s and ordinary CI38872428794.
  Clean native x86_64 Debian12/Python UID1000 passed all3 installed profiles'
  offline proof/reproducibility/negative/recovery controls and separate fresh
  verified HTTPS controls. Actual composite transport/proof/PR-no-save smoke
  passed using the Nix-installed CLI. Exact workflow checkpoint and artifact
  identity: private-installer-linux-x86_64-checkpoint.json.
- Local260MB artifact download failed with a network read timeout after partial
  transfer; no local full-archive/raw-receipt audit is claimed. The final workflow
  splits small evidence from candidate/source artifacts, uses the verified portable
  archive for combined Action smoke and streams exact Nix build logs. Relevant
  path filters avoid heavy qualification on future docs-only PRs. Independent
  review found no blocker in these orchestration-only changes; final actual
  portable-composite result remains its own run. Compact/payload pins unchanged.

## 2026-10-16 — repository home moved to betsudo/forge

- Owner authorized copying signed history, retained branches and tags into
  betsudo/forge. Original checkout and repository remain intact. Tracking:
  https://github.com/betsudo/forge/issues/1.
- Owner confirmed public visibility is acceptable. Current installer, Action,
  Nix consumer and container/docs entrypoints now use the new home.
- Historical issues, PRs and immutable qualification receipts retain their
  original links; GitHub metadata, release assets and settings are not migrated.
- Backend pins, package names, default cache and Compact remain unchanged.
  No release or Pages deployment is part of the copy.

## 2026-10-16 — Passport CI measurement preparation (betsudo/forge #2)

- Owner selected Passport JSON3.1 as the first target. The earlier two selected
  circuits and exact consumer commit remain the starting premise; the negative
  local warm result is retained. No consumer checkout was modified.
- Added a standard-library offline five-lane whole-job comparison reporter over
  a predeclared plan, exact identity/parameter/runner premises, unique hosted job
  URLs, raw evidence digests and matching declared correctness counts. It checks
  job-local hit/miss/error counters and actual transport-byte declarations.
- Reports all paired savings and per-lane medians/nearest-rank p95, preserving
  regressions and the agreed threshold. It does not verify producer-declared
  proof counts or infer billed minutes/money. Raw evidence needs independent audit.
- Local validation through bootstrap: five test groups including28 refusal
  cases, CLI no-overwrite/no-output-on-invalid-input and derived-statistic overflow
  control passed. OpenSpec, existing four fast Action controls, site build/check
  and diff checks passed. Synthetic fixtures are not proof/performance evidence.
- Independent review identified stage-sum wording and serialization-before-create
  fixes; both are applied and the overflow refusal is exercised. Runtime/cache
  code and dependency pins are unchanged, so no cryptographic retest is claimed.
- Contract and producer guidance: openspec/changes/ci-trial-reporting and
  docs/ci-trial.md. Linux Passport tool/worker byte qualification, reviewed frozen
  plan, actual hosted producer/collector and the two-week study remain follow-up.
- Migration main b35efea CI38899359224 passed. The earlier final source2d938c4
  native run38878440021 also passed (portable Action, all3profile proof/recovery,
  fresh HTTPS); it was correctness qualification, not a hosted warm-cache saving.
- No push, workflow dispatch, release, deployment, cache upload or VM work in this
  increment. Compact, shared installed CLI and other checkouts remain unchanged.

## 2026-10-16 — next-ten planning pause

- Owner paused implementation and set priorities: Compact compiler flag/provider
  synergy first, local CLI keygen reuse second, CI reuse third. Reporter work
  remains locally complete/unpublished and does not supersede that ordering.
- Reused betsudo/forge issue #2 and created/replanned #3–#11 with concrete
  acceptance criteria, dependencies and execution boundaries. Milestone:
  2026.10.0 — Compact integration and Forge reuse, with no promised deadline.
- Ranked queue: docs/planning/next-ten-2026-10-16.md. Hosted delivery design is
  the small Rust/Wasm Worker/D1/R2/CDN candidate, native Rust Lambda as an
  alternative; native CLI/CI workers generate keys. No hosted deployment planned
  by this action. Current official-source refresher is linked in the plan.
- CI trial remains unstarted/unscheduled and negative results remain valid;
  compiler/local usefulness is assessed independently of CI savings.
- No code implementation, dispatch, VM work, consumer/Compact edits or release
  occurred during planning. Historical evidence stays source-specific.

## 2026-10-16 — compiler integration contract (#3), local backlog resumed

- Owner resumed the current backlog locally, with Cloudflare deferred. Kept
  priority order: compiler/provider contract, local reuse, then CI. No push or
  external workflow execution is implied by the resume.
- Audited current Compact source05a7885f read-only. All8 inspected source file
  digests and existing unrelated working changes are recorded in
  docs/evidence/compact-compiler-boundary.json. No Compact files/builds/tests changed.
- Defined proposed off/local/fetch compiler opt-in, independently qualified policy,
  original uncached behavior and typed safe fallback. Actual flags/fetch support
  are not claimed. Key materialization belongs before normal compiler integrity
  manifest generation; post-compile injection is not equivalent.
- Existing test shim remains v2-only with an older exact-build guard. Contract
  explicitly preserves it, current ZKIR, private outputs, proof/assertion runs,
  parameter verification and verifier identity across eviction.
- OpenSpec structure and diff checks passed. Independent source/contract review
  found no blocker; fixed minor reference spacing. Documentation-only contract
  delivery does not claim a compiler runtime integration or measured speedup.
- Next local work: pinned Node/Fetch provider qualification under issue#4.

## 2026-10-16 — local SDK provider qualification (#4 partial delivery)

- Pinned official Node/Fetch providers5.0.0-rc.2 and runtime0.20.0 in a private
  test-only npm project with lockfile. Node/npm are Nix-owned. Current packages
  require compiler integrity metadata by default: bare Forge exports are rejected.
- Real native macOS ARM64 Compact0.35.0 fixture normal compilation precedes
  cold/warm Forge JSON3.1 comparisons. Official and cached source/binary IR/keys
  match exactly; copied private key files leave original compiler manifest/info
  unchanged. No compiler or other checkout was edited or built.
- Local, HTTP, gzip HTTP and authenticated HTTP SDK reads each execute a fresh
  contract call, actual proof and verification. Total4proofs/4verifications,
  8proof negative controls and12state/trace assertions. All13 provider/HTTP
  refusal/HEAD/ETag controls passed after locked npm ci.
- Independent review found no blocker; moved generated-contract import before
  binding the fixture listener and publish the receipt after scratch cleanup.
  Final receipt: docs/evidence/provider-sdk-local.json, including harness/lock/
  compiler/CLI/worker/metadata/parameter identities and original publisher package
  integrity. Local stores, preimages and copied proof artifacts are removed.
- This is a qualified Node/loopback HTTP fixture, not production Forge provider
  serving, Linux Passport, browser/TLS/CDN, hosted deployment or a speedup claim.
  Issue#4 remains open for those appropriate production/browser/transport gates.
- Source guide: docs/providers/qualification.md; compiler flag remains proposed.
  Nix package was built without reinstalling the shared CLI or changing pins.

## 2026-10-16 — provider-view API and compiler-facing local adapter (#4/#6)

- Added local `publish-view` with independently supplied raw compiler-manifest
  SHA256, bounded strict complete inventory/runtime metadata checks, private copies,
  atomic no-replace publication and verified idempotency. Explicit provider roots
  remain separate from cache snapshots. Existing v2/v3/JSON3.1 pins are unchanged.
- Added explicit `serve --provider-root` GET/HEAD `/views/{id}/{file}`. Existing
  authentication/admission apply; full view validation precedes HEAD/304/ranges.
  Responses stream a verified private descriptor, avoiding verify/reopen races.
  Initial identity encoding only, no browser/CORS/TLS/CDN or public-service claim.
- Added Forge-owned `scripts/compiler-local.py`, default off, opt-in local mode.
  Actual compiler owns its output and emits original metadata after a process-only
  qualified keygen hook. Initial support is source-specific Compact0.35/JSON3.1,
  not an upstream flag or arbitrary Passport/consumer integration. Exact tool,
  worker, descriptor, source, parameter and artifact pins are independently checked.
- Independent identity/reliability review found source swaps could pass an overly
  broad final hash check and a successful compiler could skip the hook. Fixed exact
  path/hash and roster checking, official probe availability, hook completion and
  final manifest checks; reject protected-input/output overlap. Added regressions.
- Nix package built locally (shared installation unchanged). Final receipt
  `docs/evidence/provider-view-adapter-local.json`: native macOS ARM64, fresh4-lane
  official SDK baseline plus off/cold/warm5-lane runs, totaling19genuine proofs/
  verifications and38invalid-statement/corrupt-proof rejections. Compiler output
  inventory is byte-identical across off/cold/warm; original raw manifest identity
  is `0cd0ef3e79d9f2e1250e95cf4198e305b519a3ac71b4ab8f40da041e8bd4dc46`.
  Local adapter cold stats show1miss/0hits; warm stats1miss/1hit, zeroerrors.
  Node lanes read original complete bundles; the additional Fetch lane reads the
  actual authenticated Forge view. No CI speedup is claimed from this small fixture.
- All12actual API controls and4adapter refusal/recovery controls passed, including
  corrupted private export refusal, byte-restored retry, wrong receipt preserving
  existing output, changed source refusal, corrupt HEAD/conditional/range refusal
  and restored view recovery. The compiler cleans failed outputs, so the harness
  establishes changed IR through an independent native compile before refusal.
  A valid JSON content type is supplied when testing method405 after media checks.
- Local checks: all non-ignored Rust tests passed; provider-view12tests; adapter
  12tests; Cargo formatting/Clippy with warnings denied; existing HTTP, recovery,
  snapshot, factory/commit/OpenSpec and docs checks passed. Expensive unrelated
  ignored backend qualifications were not rerun; real proofs above cover this
  exact new compiler/provider cohort. Owned scratch keys/caches/tokens/preimages
  are cleaned on success and failure. No additional worktree was created.
- Research/usage: `docs/research/compiler-metadata-guarantees.md` and
  `docs/providers/local-adapter.md`. Guarantee requires complete original compiler
  output plus an independently trusted manifest pin; self-consistent hashes alone
  do not establish compiler provenance. Every request currently verifies the whole
  view, a deliberate read-throughput limit requiring measurement on large bundles.
- Compact/other checkouts unchanged; Cloudflare deferred; no push, deployment,
  remote workflow, merge or release. Local source-specific qualification is not
  Linux/full Passport/browser qualification or release readiness.

## 2026-10-16 — trusted CI review and quality gates (#11)

- Inspected midnight-did reference workflows at revision
  `4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550`: trusted-base commit integrity,
  conventional PR metadata, stable quality contexts and security boundaries.
  Added Forge-specific OpenSpec and `docs/ci-quality-gates.md`.
- Added a read-only trusted-base PR gate: conventional PR title and every commit,
  explicit real same-repo issue references on PR and every commit, matching author
  DCO, GitHub-verified valid OpenPGP signatures. Enumerates every commit (bounded
  at250), rechecks live base/head/metadata and refuses stale/partial verification.
  No execution of PR code, cache/artifact restoration or privileged write token.
- Independent review hardened event/live base SHA/ref/repository consistency and
  issue repository identity to reject transferred-issue redirects. Signature trust
  is GitHub's verification, not a local key allowlist. Issue relevance remains review.
- Added stable `Forge quality gate` covering mandatory ordinary checks and any
  explicitly requested real proofs; failed/cancelled/skipped required checks fail.
  Added pinned-Nix actionlint1.7.12 to existing local/CI check entrypoint, dependency
  update proposals for Actions/allCargo graphs/providerSDK npm, and PR template.
  No automatic merging, compatibility pin changes or application code changes.
- Local validation passed:28API policy controls plus grammar controls, original
  commit-hook policy tests, actionlint across workflows, OpenSpec and documentation
  build/link checks. Existing Rust/proof checks were not repeated for workflow/docs/
  Node policy-only changes. No hosted API enforcement/workflow was dispatched.
- Gate activation needs trusted-base bootstrap followed by owner-configured branch
  rules (required contexts, approvals, signed commits, no force pushes/deletions).
  These settings were documented, not mutated; first introduction PR cannot use a
  verifier absent from its base. Bot PRs do not bypass signing/DCO/issue rules.
  Audits/secret scans/coverage/fuzzing need scoped baselines before additional gates.
- Signed local delivery only. Compact unchanged, Cloudflare deferred, no push,
  branch-settings changes, merge, deployment or release.

## 2026-10-17 — primary `zkir-forge` command (#11, PR12)

- Added primary Cargo/Nix CLI `zkir-forge`, shared-source compatibility entrypoint
  `midnight-zkir-forge`, explicit primary help/version/usage and Nix mainProgram.
  Installed Nix legacy command points to the primary executable. Worker/helper,
  package/library names, cache/env variables and asset stems remain stable.
- Portable packaging copies the final relocated/signed executable into both regular
  command files; inventory refuses different alias bytes. Old schema1 legacy-only
  releases remain supported. The installed primary launcher uses a stable managed
  target that survives historical rollback. Both launcher collisions refuse before
  portable activation; independent review prompted equivalent Nix pre-build guards.
- Updated active docs/site/skill examples, default CI-helper selection and tests.
  Historical qualification receipts remain immutable; new executable bytes still
  require exact qualification rather than editing an old allowlist.
- Local Rust tests (including both names/help/version/profile/shared store), Clippy,
  formatting/profile gates passed. Installer fixture checks cover old/new/reinstall/
  rollback, corrupt alias and both-name collisions; Nix launcher fixtures cover
  managed upgrade and4collision refusals before build. CLI/HTTP/recovery/snapshot,
  Action/reporter, OpenSpec/docs/actionlint and commit/PR policy checks passed.
- Shared installation and default store were not modified. PR12 will receive signed
  commits and exact-head CI checks. Compact remains unchanged; no merge/deployment.

## 2026-10-17 — PR12 review fixes (#4/#6)

- Provider reads now validate fresh pinned manifest/metadata and exact bounded
  inventory, then hash/copy only the requested representation. Unrelated corrupt
  bytes no longer block unrelated reads. Full `verify-view`, staging/publication,
  existing-target reuse and concurrent-winner reuse still audit every byte; no
  persistent verified marker exists. Requested HEAD/304/range checks remain strict.
- Dedicated two-permit provider verification/stream admission avoids opening the
  cache store or using cache-work permits. Cancellation retains a blocking task's
  permit until it stops, then the response owns it through streaming. Two1GiB
  snapshots bound provider spool use; ranges still verify the whole requested file.
- Explicit publish cache roots now work without HOME; verify-view requires no cache
  root. Compiler staging is private and outside its final output, with same-device
  checks before copying and mountpoint preflight before compiler cleanup. SIGKILL
  may leave owned private sibling staging, but retry cannot include it in manifests.
  Old inside-output leftovers require a fresh owned output, not wildcard deletion.
- Independent identity/concurrency review passed, including all full-publication
  paths and cancellation ownership. Rust tests include13provider-view cases and
  2admission/cancellation cases;13adapter cases include a killed child after staging,
  exact private permissions, no inside-output stage and successful retry. Local
  Rust/Clippy/format, CLI/HTTP/recovery/snapshot, OpenSpec/docs/actionlint checks pass.
- Updated real SDK harness to preserve unrelated reads on sibling corruption while
  explicit full audit refuses, and to compile/prove with a leftover sibling stage.
  Fresh qualification and exact-head hosted results are recorded in PR12 after run.
- Created follow-ups in2026.10.0: #13duplicate Cargo binary compilation,
  #14configurable keygen timeout, #15broader exact consumer qualification. No
  automatic unqualified-circuit fallback, Compact edits, cloud work or merge.

## 2026-10-17 — next local milestone defined (#30)

- PR12 merged as 7273d75a329fef65d7b22d6bc0b543e60d5bfbfd. Its final
  review found no blockers; additional admission/range follow-ups are #28/#29.
- Created 2026.10.1 — Qualified local key reuse, milestone2 and tracking issue30.
  Ordered #14 timeout, #15 exact selected Passport qualification, #6/#7 local
  integration/recovery, #28 bounded provider admission, #29 measured range cost
  and #13 duplicate CLI build removal. These issues moved into the new milestone.
- Charter: docs/planning/2026.10.1-local-reuse.md. Completion requires fresh
  genuine proof/control evidence and independent identity/concurrency review;
  partial local evidence cannot close Linux or hosted qualification gates.
- Autonomous work is local and finite, with OpenSpec, Nix, issue-linked signed
  DCO commits and isolated stores. No scheduled supervision, push, PR publication,
  merge, release, deployment, shared-installation/cache change or Compact edits.
  Existing official pins remain fixed; Cloudflare and clean-Mac VM stay deferred.
- Planning changes only; no new consumer qualification or performance result is
  claimed. The first implementation issue is #14 (bounded keygen timeout).

## 2026-10-17 — bounded adapter keygen timeout (#14/#30)

- Added local --keygen-timeout-seconds, integer1..86400/default180, validated
  before compiler cleanup and rechecked in private hook config. Each prepare
  includes lease waiting; profile checks/native off compilation are unchanged.
- Captured commands own POSIX process groups. Deadline/Python interruption kills
  CLI plus backend descendants and reaps before refusal. Abrupt hook termination
  remains a recovery case, not a promised SIGKILL/SIGTERM cleanup guarantee.
- All15adapter controls pass through Nix, including actual slow worker startup,
  timeout/no completed marker/no output, terminated late worker and explicit retry;
  invalid CLI values preserve existing output. OpenSpec/docs build/link checks pass.
- Independent review found no blocker; narrowed interruption claims and added hook
  entrypoint/CLI sentinel controls in response. No broader consumer qualification
  or speedup claim, pin/Compact/shared-installation/cache change or publication.

## 2026-10-17 — lightweight Cargo compatibility launcher (#13/#30)

- Replaced full primary-source inclusion with a std-only Unix sibling exec.
  Resolves real executable location, refuses missing/self-referential primaries,
  never searches PATH and preserves OS args/environment/stdio/signals/status.
  Nix shared symlinks and portable identical-byte aliases are unchanged.
- Two dual-name/isolated-install controls passed: profiles/store/help/version,
  missing primary/PATH decoy, hardlink recursion, symlink/unrelated cwd, Unicode/
  space arguments, inherited environment and nonzero status. Independent review
  found no blocker. Both Cargo bins must be installed together; documented.
- Same-host sequential warm debug rebuild/link: full alias56,539,752bytes/3.223s,
  launcher684,232bytes/0.839s. This is not a clean/release build benchmark. Receipt:
  docs/evidence/cli-alias-build-local.json. Exact package/worker/installer checks
  remain part of the milestone qualification; no new Linux runtime claim yet.

## 2026-10-17 — bounded provider SDK bursts (#28/#30)

- Retained two active verification/stream permits; added eight waiting slots and
  ten-second timeout. Overflow/expiry returns existing429provider_reads_busy and
  Retry-After:1. No cache DB/work admission coupling, keygen or persistent marker.
- Deterministic unit controls cover three-artifact admission, queue overflow, wait
  timeout/cancellation, active cancellation ownership and restored capacity. All
  four pass, plus13provider-view tests and root Clippy. Independent ownership/
  concurrency review found no blocker. SDK harness now fetches3artifacts via
  Promise.all; exact-package real SDK proof qualification remains a separate gate.
- HTTP/OpenAPI/provider limits match implementation. Installer fixtures, OpenSpec
  and documentation checks pass. No platform/hosted readiness claim or publication.

## 2026-10-17 — fresh package and range-cost evidence (#13/#28/#29/#30)

- Fresh Nix package xywbgzg14vn44qpqdlxk7v7bd36vbwa9 built with existing pins.
  Full bootstrap check passes. Installed killed-writer CLI acceptance and real
  recovery across ledger8-v2/zkir3/zkir31 pass, plus real installed snapshot and
  downloaded-artifact HTTP proof controls. No shared installation was changed.
- Exact minimal compiler/provider qualification passes19genuine proof lanes
  (4baseline+3adapter lanes of5),38negative proof controls,12API control groups
  and5adapter controls. SDK requests binary IR/prover/verifier via Promise.all;
  genuine executions/proofs remain. Independent evidence/hash review passes.
- Actual24,648,297-byte Passport activation prover key:8ranges return one file's
  bytes while producing197,186,376logical snapshot bytes; reader peak1file
  sequential/2concurrent. Three-repetition loopback medians165/917/378ms for
  full/sequential/two-concurrent modes on a shared warm host. Not physical device
  counters or hosted throughput. Keep full-file verification; no trusted marker.
- A private reduced-export carrier retains all circuit bodies/pure exports and
  compiler-produced complete carrier metadata. Its2ZKIR+6artifact hashes match
  unchanged-account qualification; fresh2SDK proofs/2verifications/4negative
  controls/18assertions include exact worker/SDK/generator provenance. This does
  not qualify full52-account HTTP. Original full output exceeds4GiB serving
  budget; limits stay unchanged. Full local Node adapter qualification continues.
- Evidence: provider-api-burst-local.json, provider-range-cost-local.json,
  passport-range-fixture{-proofs}-local.json and installed-cli-*-2026.10.1.json.
  Range guide documents scopes and reproducibility. Compact/pins/other checkouts,
  shared CLI/default store, Cloudflare and publication remain unchanged.

## 2026-10-17 — local handoff routing and qualification scope (#6/#30)

- Repository skill now lists the exact JSON3.1 profile and distinguishes bare
  exports from complete compiler provider views/limits. Global skill, vault home
  and consumer starter prompt point to betsudo/forge and preserve original-proof
  requirements. Both skill frontmatters pass the official skill validator using
  temporary pinned-Nix PyYAML; product/dependency pins are unchanged.
- Read-only shared CLI check reports0.2.0. It was not reinstalled; current tested
  candidate has a separate workspace-local Nix GC root. Personal handoff marks
  full52consumer qualification in progress, not delivered from selected2proofs.
- Full local bootstrap, fresh package and smaller-provider evidence are retained.
  The52official output pairs are complete; independent Forge artifact matching
  continues. Removed completed-session owned build intermediates after preserving
  the tested range reader/alias artifact; no shared artifact store was deleted.

## 2026-10-17 — selected-workload result retained (#7/#30)

- Re-ran the existing exact selected2Passport benchmark with the current fresh
  Nix CLI/worker.15lanes (5x3),30actual proofs/30verifications,60negative
  controls and270assertions pass. Changed exact source produces a new derivation,
  corrupt CAS and wrong profile refuse without availability fallback.
- Warm local archive restore median5365.489ms versus4154.748ms uncached: saving
  -1210.741ms (~29.1%slower). Preserve this negative result. The copied current
  emitted codegen, selected2standalone keygen, transport planning/restore/save and
  proof scope are explicit; full52keygen/compiler/modern provider and hostedCI
  are not inferred. Concurrent developer-host load is disclosed.
- Independent receipt review recomputed every median/total, checked all correctness
  counts/tool/harness/referenced-codegen hashes and found no blocker. Companion
  provenance pins CI helper/preimage generator. All owned stores/snapshots/runtime
  dependency/preimage copies were cleaned after capture. Full52local adapter
  qualification remains a separate ongoing gate. No push or Compact changes.

## 2026-10-17 — full local Passport qualification complete (#15/#6/#7/#30)

- All 52 independent official/Forge artifact sets match for unchanged Passport
  account 0d7bb0bc; exact source closure, compiler, JSON3.1 worker, eight parameter
  models, SDK lock and harness hashes are retained. Trusted policy raw SHA-256:
  `4e94e57bf7467a5db580600be3e660691752f363123a1aab2fe8ea92abacc602`.
- Full cold and warm compiler outputs preserve all 213 original files, including
  manifest `433e83a1…` and runtime metadata. Cold52miss/0hit/0error; warm adds
  52hits/0miss/0error and zero measured generation. Node provider remains pinned
  to the same original compiler manifest. No pruning or synthetic metadata.
- Native/cold/warm and five positive recovery groups pass16actual proofs,
  16verifications,32negative controls and144state/trace assertions across two
  selected application circuits. Corrupt CAS/export refusals, explicit repair,
  missing-export reconstruction, eviction/regeneration and concurrent callers
  preserve actual identity. Wrong profile/policy refuse before compiler cleanup.
- One shared-host observation: cold compile1619.463s, warm650.756s (~59.8%less);
  proof-test harness3.002s/2.883s and whole lanes1628.216s/659.432s. Native/off
  ~1379s uses a lower-precision process-start/manifest-mtime proxy, not a precise
  monotonic benchmark. Per-file bytes/counters and keygen/request timings remain
  separate. Earlier selected-two archive saving stays negative; no hosted claim.
- Independent final evidence review verified hashes, complete inventory, counts,
  resource boundaries and actual scratch cleanup; no blocker in the stated native
  scope. Full baseline, independent/adapter stores, cold/warm outputs and private
  proof/preimage copies are removed. The tested Nix root and small source/tools/
  receipts remain. No obsolete worktrees; shared CLI/default cache unchanged.
- Setup/renewal: docs/providers/passport-local.md. Acceptance and exact deferred
  gates: docs/milestones/2026.10.1.md. General/site/repository/global-skill and
  Midnight-vault handoff updated. Site build/link/API checks pass. Complete
  provider publication refuses the actual12.18GBbundle under the unchanged4GiB
  limit, with no visible partial view; #31 tracks the actionable large-view gate.
- Local #30 scope is complete. Broader #6/#7/#13 Linux gates, clean Nix-free Mac,
  full-account Fetch/HTTP, hosted CI study, Ledger9 transactions and Cloudflare
  stay open. No Compact/other-checkout/pin edits, shared install, push, PR, merge,
  workflow dispatch, release or deployment occurred.

## 2026-10-17 — bounded large provider views (#31)

- Retain the 4 GiB aggregate default; publish/verify/serve now accept an explicit
  integer-byte budget bounded at 64 GiB. Original manifest and every declared file
  count; fixed 1 GiB/file, metadata/file-count limits and two active HTTP snapshots
  remain unchanged. Typed provider_limit is nonfallback and actionable on stderr.
- Destination fstatvfs preflight requires declared copy bytes plus 64 MiB reserve.
  provider_storage_unavailable is a hard refusal; the check is not a reservation.
  Existing views still receive a full audit, and publication remains synced,
  atomic and no-replace. Malformed compiler metadata retains integrity_error.
- 36 ordinary Rust tests pass (7 parameter-dependent controls remain explicitly
  ignored in the ordinary suite), including 16 provider tests and bounded HTTP
  admission/cancellation. Clippy all-targets passes. Independent identity/
  concurrency review found and confirmed the metadata-classification fix.
- Added the full Passport provider harness and explicit budget/storage guide.
  Actual full-manifest Fetch/proof/interruption evidence is still in progress;
  native Linux/hosted CI and clean-host installation are not inferred. Compact,
  official pins, shared installation/default cache and other checkouts unchanged.
