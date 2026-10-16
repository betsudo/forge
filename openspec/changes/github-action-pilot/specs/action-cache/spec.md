# Action cache contract

### Requirement: exact, bounded JSON3.1 reuse

The Action SHALL call existing verified helpers with JSON3.1, declared parameter
files and workload inputs; transport only a bounded snapshot in the exact tool/
profile/worker/parameter partition, and keep job state outside that snapshot.

#### Scenario: cold, warm or corrupt restore

- **WHEN** a remote snapshot is absent, valid or corrupt
- **THEN** absence starts cold, valid bytes restore into an absent private store,
  corruption fails explicitly, and ordinary proofs/assertions still execute.

### Requirement: explicit trusted save

The Action SHALL separate restore/save phases and admit writes only after explicit
test success, successful prior steps, trusted push/manual branch and bounded
generation growth; PRs SHALL remain restore-only.

#### Scenario: failed tests, PR or unchanged store

- **WHEN** save is requested after failure, from a PR or without generation growth
- **THEN** no remote save occurs and the reason remains visible.

### Requirement: native installed portability evidence

The qualification SHALL run an exact-source bundle in a native x86_64 Linux
consumer without Nix, build checkout or Rust tooling as an unprivileged user,
with actual installed proof/recovery and invalid-statement/corrupt-proof controls.

#### Scenario: an unqualified platform

- **WHEN** source checks pass without an installed native consumer receipt
- **THEN** portability remains unqualified; ARM emulation and flake evaluation
  cannot substitute for the missing native receipt.
