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
