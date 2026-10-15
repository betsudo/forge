# Tasks

- [x] Audit existing identity and specify additive descriptor/typed-error contract.
- [x] Implement shared strict descriptor, CLI/export/HTTP parity and legacy-sidecar handling.
- [x] Implement typed errors including authoritative parameter/worker boundaries and safe status mapping.
- [x] Add premise controls, descriptor parity/strictness and error taxonomy tests.
- [x] Run both-profile real exported/downloaded proof, lifecycle, snapshot and recovery checks locally.
- [x] Record process cold/warm times and statistics deltas separately.
- [x] Obtain independent coding-agent review and sign focused local commits.

Consumer reference: MediaNoxLabs/compact#643 only. No Compact edits, shared-cache
removal, push/release/deployment or dependency upgrades in this increment.

Evidence: docs/evidence/compiler-compatibility-local.json; native aarch64-darwin.
ArtifactDescriptor intentionally exposes decode() as its only deserialization entrypoint.
