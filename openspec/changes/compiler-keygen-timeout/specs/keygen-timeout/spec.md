# Keygen deadline requirements

### Requirement: Explicit finite keygen deadline
The wrapper SHALL accept only integer deadlines 1..86400 seconds, default 180,
and apply the selected value to each local prepare without weakening qualification.

#### Scenario: Larger qualified generation
- **WHEN** local mode selects a valid explicit deadline
- **THEN** the hook uses that deadline for prepare and keeps independent tool/parameter checks.

#### Scenario: Invalid deadline
- **WHEN** the deadline is zero, negative, noninteger, boolean or above the maximum
- **THEN** it refuses before compiler cleanup or generation.

### Requirement: Failure contains all owned generation processes
The wrapper SHALL kill and reap the timed-out Forge process group, refuse success,
and permit an explicit clean retry without skipping proofs or changing identity.

#### Scenario: Worker outlives its parent
- **WHEN** a deliberately slow generation process and its worker exceed the deadline
- **THEN** neither remains running, no completed hook/final manifest is reported, and retry works.

#### Scenario: Native off path
- **WHEN** off mode runs
- **THEN** it retains native compiler generation without Forge cache initialization or this prepare deadline.
