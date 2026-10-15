# zkir3-cache Specification

## ADDED Requirements

### Requirement: Select an exact supported v3 backend

Forge SHALL expose a distinct pinned v3 profile and SHALL reject incompatible
versions or profile selections without coercing input or falling back to v2.

#### Scenario: Consumer requests a supported v3 circuit

- **WHEN** the exact input and selected backend are compatible
- **THEN** the result identifies the profile, input format, parameter digest and
  actual generated output digests and supplies usable local copied paths

#### Scenario: A newer or different v3 implementation is requested

- **WHEN** its binary format or generation recipe differs from the supported pin
- **THEN** Forge refuses that compatibility claim rather than guessing from a
  shared JSON major version

### Requirement: Separate profiles and preserve existing identities

Forge SHALL distinguish v2/v3 input and derivation identities, retain old v2
records/exports and preserve pinned actual output identity through eviction.

#### Scenario: Both formats use the same circuit filename

- **WHEN** v2 and v3 circuits are prepared in one store
- **THEN** their profiles and binary IR artifacts cannot be confused or reused
  across profiles

#### Scenario: An old v2 record is opened after upgrade

- **WHEN** its recorded files are intact
- **THEN** explicit resolve remains usable without triggering key generation

### Requirement: Warm hits retain actual proof testing

Forge SHALL cache only artifacts. Qualification SHALL prove a genuine v3
fixture, reject invalid statements/proofs and verify byte reproduction.

#### Scenario: Repeated v3 ensure and regeneration

- **WHEN** the same v3 circuit is prepared twice, evicted and prepared again
- **THEN** the warm request skips generation, the regenerated identity matches,
  metrics reflect requests and consumer proof/assertion work remains live

#### Scenario: Concurrent v3 requests

- **WHEN** two local processes prepare one missing v3 recipe
- **THEN** one generates and the other verifies a hit without partial publication
