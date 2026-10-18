# Bounded verified transfer lifetime

### Requirement: Independent finite transfer deadline

#### Scenario: Stalled or trickling client
**WHEN** a verified body remains unconsumed beyond its configured total lifetime
**THEN** Forge SHALL stop its producer without requiring another body poll,
release its file/permit after in-flight blocking work finishes, and allow later
provider requests. Progress SHALL NOT extend the deadline. Memory buffering
SHALL be bounded per response.

### Requirement: Original integrity and storage bounds

#### Scenario: Cancellation, expiry or corrupted source
**WHEN** a client disconnects or times out
**THEN** no partial-success claim SHALL replace actual proof/assertion execution.
All requested-file verification SHALL precede headers/range/conditional delivery.
Two active provider spools and the2GiB aggregate cap SHALL remain, including
blocking work after cancellation. Corrupt files SHALL refuse before response.

### Requirement: Finite operator configuration

#### Scenario: Invalid timeout
**WHEN** the timeout is zero or exceeds3600seconds
**THEN** refuse serve startup; base SHALL default to 300 seconds. A zero
minimum byte rate SHALL also refuse before storage startup, including library calls.

#### Scenario: Slow large response
**WHEN** a verified CAS or provider response has length L and configured positive rate R
**THEN** its total lifetime SHALL be min(3600, base + ceil(L/R)) seconds, using
saturating arithmetic; default R SHALL be 1048576 bytes/second. A default 1GiB
response SHALL receive 1324 seconds; range length SHALL determine its allowance.
Progress SHALL NOT reset this deadline. Expiry SHALL log response size and lifetime.

#### Scenario: Producer ends without delivering all bytes
**WHEN** the channel closes with declared bytes remaining
**THEN** the reader SHALL fail with UnexpectedEof rather than report clean EOF.
