# Tasks

- [x] Inspect existing Forge helpers and official GitHub/Midnight cache/provider guidance.
- [x] Pin DID v0.7.0 and Passport account sources and inspect tool/dependency/test contracts.
- [x] Record historical exact-SHA CI allocation without attributing it to keygen.
- [x] Specify snapshot partition strategy, optional Action and provider-view boundaries.
- [x] Implement local benchmark preflight/receipt runner with explicit unsupported gates.
- [x] Qualify exact DID compiler-generated circuits and genuine proof-bearing test lane.
- [x] Obtain Compact0.35.0/Passport exact backend mapping, all52 codegen identities and two genuine account proof-bearing circuits; full consumer CI is not claimed.
- [x] Measure uncached/cold/warm/partial/unavailable transport-inclusive timings.
- [ ] Add thin Action/provider view only after local contracts pass; no hosted dispatch.
- [x] Independent review of parent identity/concurrency and both final benchmark receipts; release/platform gates remain separate.

The thin Action/provider view is an optional future implementation gate, not a
claim made by this local benchmark increment. The existing CLI helpers are used
and measured directly. No hosted GitHub cache transfer or full consumer CI run
is represented by these artifact-stage measurements.

Final receipts: `docs/evidence/did-cache-benchmark*.json` and
`docs/evidence/passport-benchmark.json` and `passport-benchmark-audit.json`. Both use the optimized portable
macOS ARM64 c40e45b payload. Raw repetitions retain shared-host load variation
and negative savings; Compact and consumer checkouts are unchanged.
