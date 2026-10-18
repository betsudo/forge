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
**THEN** refuse serve startup; default SHALL be300seconds. This is a transfer
lifetime, not a keygen timeout or a hosted-service availability promise.
