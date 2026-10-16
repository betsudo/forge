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
