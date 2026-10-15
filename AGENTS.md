# Midnight ZKIR Forge

Read SPEC.md and docs/PROGRESS.md. Build a local artifact cache first.
Use official ledger8 8.1.3 sources and its midnight-zk dependency pins; no
ledger9/ZKIR3. Do not modify Compact or any other checkout.
Run through ./bootstrap.sh; Nix owns the toolchain. Default cache is
~/.midnight-zkir-forge, overridable with --cache-dir or MIDNIGHT_ZKIR_FORGE_DIR.
Cache artifacts, never test outcomes. Verify bytes on hits; preserve actual
verifier identities through eviction. Keep tests executing proofs/assertions.
One local writer and one backend generation at a time initially. Delegate
independent review when useful; independent identity/concurrency review is
required before release readiness. No supervision loop until owner asks.
No push, merge, remote CI, deployment, releases or credential mutations.
Conventional GPG-signed commits with DCO using configured identity only;
include Assisted-by: AI. ADRs remain proposed until owner acceptance.
Private vault paths are research inputs, never runtime dependencies.
