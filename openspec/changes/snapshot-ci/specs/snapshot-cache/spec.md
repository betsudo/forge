# Snapshot cache requirements

### Requirement: Consistent preserved state
Snapshots SHALL hold store-wide SQLite ownership while backing up committed
metadata and copying verified CAS/exports, preserving actual verifier identities.

#### Scenario: Concurrent writer
- **WHEN** another writer holds ownership
- **THEN** snapshot waits within its configured timeout or fails without publishing.

### Requirement: Verified atomic restoration
Restore SHALL reject incompatible, corrupt, incomplete or unsafe payloads and
SHALL atomically publish only into a new explicitly selected cache directory.

#### Scenario: Raced destination
- **WHEN** a destination already exists or another restore wins publication
- **THEN** restore refuses to replace or merge it and never exposes partial state.

#### Scenario: Relocation
- **WHEN** a compatible snapshot is restored under a different absolute root
- **THEN** prepare verifies a warm hit and returns current-root paths and the
  original artifact identity; actual proofs and negative controls still execute.

### Requirement: Bounded exact CI planning
CI helpers SHALL partition cache keys by exact provenance/parameters/workload,
report inherited-metric deltas and keep tests independent of transport hits.

#### Scenario: PR or no growth
- **WHEN** publication planning sees an untrusted event/ref or no new generation
- **THEN** no snapshot is prepared for upload and a structured reason is returned.

#### Scenario: Budget
- **WHEN** a candidate snapshot exceeds the explicit byte budget
- **THEN** no snapshot is published and genuine test results remain independent.
