# Range measurement

### Requirement: Honest amplification receipt
The benchmark SHALL distinguish observed snapshot lengths/allocation, returned
HTTP bytes, wall time and limits from inferred physical I/O or hosted performance.

#### Scenario: Eight resumed ranges
- **WHEN** eight chunks cover a prover file sequentially or two at a time
- **THEN** record eight full requested-file snapshots but only one file's response bytes, with at most two live snapshots.

### Requirement: Preserve integrity first
Measurement SHALL use the existing pinned provider read path without skipping
hashing, changing compiler metadata or trusting a reusable verified marker.

#### Scenario: No qualified safe optimization
- **WHEN** no measured optimization preserves those guarantees
- **THEN** retain current serving behavior and publish its explicit cost and scope.
