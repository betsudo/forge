# Provider admission

### Requirement: Bounded normal burst admission
Provider views SHALL allow a three-artifact burst to wait for capacity with no
more than two active verified streams, eight waiters and ten seconds of waiting.

#### Scenario: Three concurrent circuit fetches
- **WHEN** the SDK requests prover, verifier and binary IR concurrently and an active read completes within the wait
- **THEN** all three succeed without an artificial immediate429.

#### Scenario: Queue overflow or expired wait
- **WHEN** all eight waiting slots are occupied or the bounded wait expires
- **THEN** return429 provider_reads_busy with Retry-After and no queued generation.

### Requirement: Cancellation and cache isolation
Provider admission SHALL release cancelled waiting slots, retain active verification
permits until blocking work/streaming ends, and remain independent of the cache.

#### Scenario: Waiting cancellation
- **WHEN** a caller cancels before an active permit is assigned
- **THEN** its waiting capacity is returned without starting verification.

#### Scenario: Active cancellation
- **WHEN** the caller cancels during blocking verification
- **THEN** capacity remains owned by that task until it actually stops.
