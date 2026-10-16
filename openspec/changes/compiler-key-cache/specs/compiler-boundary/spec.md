# Compiler key-cache integration

### Requirement: Explicit opt-in and original behavior
A future compiler integration SHALL default to original key generation, with
explicit local or fetch selection and independently qualified configuration.

#### Scenario: Reuse is off or skipped generation conflicts
- **WHEN** no opt-in is supplied, or an explicit cache mode conflicts with --skip-zk
- **THEN** the original tool runs without Forge initialization, or the contradictory explicit options fail before materialization respectively.

### Requirement: Preserve current source and compiler integrity
The integration SHALL use current exact JSON ZKIR and materialize verified private
binary IR/prover/verifier files before normal compiler integrity-manifest generation.

#### Scenario: Batch reuse and partial publication failure
- **WHEN** compile-many requests current circuits or a copy fails midway
- **THEN** deterministic current-source outputs are prepared before manifest generation, or compilation fails without presenting a new complete manifest; stale/binary-only sources never substitute for current ZKIR.

### Requirement: Exact compatibility and safe fallback
The integration SHALL compare complete descriptor facts and actual bytes against
independent compiler/backend/worker/parameter policy. It SHALL preserve hard errors
for corruption, authentication, unknown schema and incompatible identity.

#### Scenario: Fetch is unavailable versus incompatible
- **WHEN** a documented availability outcome occurs with explicit generate fallback, or a present artifact has a wrong profile/digest
- **THEN** only the former may use the original qualified generator; the latter fails even when fallback was requested.

### Requirement: Honest qualification and unchanged tests
The delivered contract SHALL distinguish proposed flags from actual supported
interfaces and preserve real proof/verification/assertion/negative-control execution.

#### Scenario: Existing v2 adapter and newer JSON3.1 consumer
- **WHEN** the current test adapter only qualifies an older v2 tool/build
- **THEN** documentation refuses a JSON3.1 integration claim and requires separate exact consumer qualification without weakening its guard.
