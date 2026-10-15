# Tasks

- [x] 1. Record issue and snapshot/CI identity, ownership and publication contract.
- [x] 2. Implement verified directory snapshots and atomic no-replace restore.
- [x] 3. Implement local key/baseline/report/prepare-save helpers and examples.
- [x] 4. Run fast hostile-input/contention/race e2e and both-profile real proof e2e.
- [x] 5. Obtain independent identity/concurrency/security review; address findings.
- [x] 6. Validate Nix package/install, document scope and sign local commits.

Evidence: `docs/evidence/snapshot-ci-e2e.json`, `docs/evidence/snapshot-ci-review.md`;
usage: `docs/ci-cache.md`. Native Nix/install checkpoint follows task 6.

Installed Nix evidence: `docs/evidence/snapshot-ci-installation.json` and
`snapshot-ci-installed-e2e.json`; both-profile restored proofs pass on aarch64-darwin.
