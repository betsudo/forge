# Local compiler adapter

### Requirement: Explicit qualified opt-in
The wrapper SHALL default off and require independently anchored exact tool/profile
qualification for local mode without editing Compact or an official executable.

#### Scenario: Off versus mismatched local policy
- **WHEN** off is selected or the supplied qualification disagrees with actual tool bytes
- **THEN** original compiler behavior runs without Forge, or local execution fails before compiler output/cache mutation respectively.

### Requirement: Preserve original compiler manifests
The wrapper SHALL materialize verified private keys at the compiler's keygen
boundary and let the original compiler finalize integrity/runtime metadata.

#### Scenario: Warm compile
- **WHEN** current exact ZKIR hits the qualified cache
- **THEN** private artifacts are materialized before the compiler writes its original manifest and actual proofs/assertions continue.

### Requirement: Fail closed and retain source/output identity
The adapter SHALL reject changed source, unsupported format, unsafe targets,
invalid parameters, incomplete exports and integrity errors without silent fallback.

#### Scenario: Corrupt warm export
- **WHEN** a present cached artifact has wrong bytes
- **THEN** compilation fails without a new success manifest or mutated verifier identity.
