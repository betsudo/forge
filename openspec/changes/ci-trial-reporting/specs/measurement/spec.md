# Hosted comparison receipts

### Requirement: Comparable complete inputs
The reporter SHALL require exact plan-byte identity, matching consumer/tool/
profile/parameter/runner premises, unique hosted job identities and all five lanes
for each of at least three repetitions, with unchanged nonzero correctness counts.

#### Scenario: Missing lane or changed proof count
- **WHEN** one repetition omits a lane or reports fewer proof/verification/assertion controls
- **THEN** reporting fails without publishing a comparison.

### Requirement: Measured transport and full-job timing
The reporter SHALL reject non-finite or negative timings, stage-duration sums exceeding whole-job time,
request errors and contradictory warm/partial cache evidence; it SHALL use whole-job
time including setup and actual upload/download work for the comparison.

#### Scenario: Local timings substituted for hosted transport
- **WHEN** a warm row lacks actual downloaded bytes or a complete hosted job receipt
- **THEN** the row is refused rather than interpreted as a CI saving.

### Requirement: Negative results and interpretation limits
The reporter SHALL retain every paired result and report median and p95, including
regressions, against the predeclared threshold. It SHALL distinguish declared
correctness counts from cryptographic or independent evidence verification.

#### Scenario: Warm cache is slower
- **WHEN** complete comparable warm jobs take longer than their uncached controls
- **THEN** negative saving is retained and the adoption threshold is not met.
