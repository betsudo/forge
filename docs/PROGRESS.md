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
  both dependency graphs. Nix build/install and installed evidence pending.
- No consumer checkout, long-running validation, push, PR, hosted CI or
  supervision was modified or started by this work.
