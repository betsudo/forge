# Consumer CI key-cache pilot

Status: proposed research and local qualification; no consumer repository changes,
remote cache publication or hosted workflow dispatch. See docs/research/ci-consumers.md.

Reuse the existing Forge snapshot and CI helper as the core. Add a thin optional
composite Action later, rather than another cache implementation. Cache expensive
prover/verifier key derivations across CI runs; continue generating current ZKIR,
executing proofs, verifying and running every selected assertion. Qualify DID
v0.7.0 and Passport's pinned account contract independently before claiming savings.

Deliver locally first: executable benchmark/preflight contract, bounded cache
transport policy, provider-layout proposal and honest evidence. Unsupported exact
profiles fail qualification; a ledger family label never grants compatibility.
