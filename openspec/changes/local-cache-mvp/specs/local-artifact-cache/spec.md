# local-artifact-cache Specification

## ADDED Requirements

### Requirement: Exact compatible artifact reuse

Forge SHALL cache files under an explicit ledger8 recipe and SHALL NOT cache
passing test outcomes. Input, recipe and actual artifact identity SHALL differ.

#### Scenario: Repeated unchanged circuit

- **WHEN** a caller ensures the same circuit and verified parameter recipe twice
- **THEN** the second request returns hash-verified copied paths without keygen
  and records a hit for each requested derived file

#### Scenario: Input or recipe changes

- **WHEN** exact input bytes or generation-affecting inputs change
- **THEN** the previous entry is not treated as a matching hit

### Requirement: Integrity and regeneration preserve verifier identity

Forge SHALL reject corrupt ready files and SHALL preserve output digests after
eviction. A changed regenerated set SHALL fail without replacing pinned identity.

#### Scenario: Derived eviction

- **WHEN** derived blobs are evicted and ensured again
- **THEN** source and small manifests survive, and identical output is required

#### Scenario: Corrupt warm artifact

- **WHEN** an artifact has been modified or truncated
- **THEN** a hit fails and no partial ready export is returned

### Requirement: Concurrent local callers share generation

Forge SHALL serialize local writers across processes; process death SHALL
release ownership without leaving partial artifacts marked ready.

#### Scenario: Two simultaneous ensure requests

- **WHEN** two processes ensure one missing recipe
- **THEN** one generates and the other verifies the resulting hit

### Requirement: Local defaults and machine-readable results

Forge SHALL default to ~/.midnight-zkir-forge, accept an explicit override,
and emit JSON results to stdout and diagnostics to stderr. Copied exports SHALL
have an explicit persistent lifetime and SHALL survive cache eviction.

#### Scenario: Test integration

- **WHEN** an agent ensures a circuit
- **THEN** absolute artifact paths and digests are returned for test setup;
  the consumer still executes proof verification and assertions

### Requirement: Efficiency is observable

Forge SHALL record request outcomes, per-file hits/misses/failures, bytes,
generation and request timings; avoided generation is a labelled estimate.

#### Scenario: Warm request after a measured miss

- **WHEN** stats are queried after one miss and one hit
- **THEN** per-file counts agree and the measured generation baseline is shown

### Requirement: Real backend qualification

The pinned official stack SHALL generate readable keys, prove a valid fixture,
reject an invalid statement and reproduce the exact artifact bytes on regeneration.

#### Scenario: Uncached qualification

- **WHEN** the local qualification suite runs with verified official parameters
- **THEN** it generates fresh keys and executes actual proof verification
