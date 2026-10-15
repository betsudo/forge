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
