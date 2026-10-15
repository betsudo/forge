# Proposed proof-response cache requirements

### Requirement: explicit operation and exact compatibility

The relay SHALL be opt-in and SHALL admit only exact supported `/prove` requests with complete pinned backend, parameter, key/resolver and protocol context. It SHALL NOT cache check results or test outcomes.

#### Scenario: changed proving premise

- **WHEN** any request byte, binding override, witness/public input, key, parameter, backend feature or namespace differs
- **THEN** the request misses or is refused; similarity never permits a hit.

#### Scenario: unresolved dependency

- **WHEN** builtin key/resolver provenance or independent verifier support is unknown
- **THEN** the request is forwarded without cache admission.

### Requirement: verified byte-preserving responses

The relay SHALL preserve exact forwarded request/response bytes, cache only complete successful verified proofs and reverify integrity and proof validity on every hit.

#### Scenario: miss and repeat

- **WHEN** an eligible request misses and later repeats exactly
- **THEN** the first call reaches the upstream, the verified response is atomically published, and the repeat returns its exact bytes after verification.

#### Scenario: failure or corruption

- **WHEN** upstream errors/truncates, verification fails, publication crashes or stored bytes are corrupt
- **THEN** no invalid hit is exposed; corruption fails explicitly and no test success is recorded.

### Requirement: private bounded operation and coverage

The relay SHALL isolate local namespaces, avoid witness/body logging and persistence by default, bound resources, support purge/bypass and keep its store outside shared GitHub caches. Persisted request identity SHALL use HMAC-SHA256 under a local secret excluded from snapshots. Qualification SHALL retain genuine uncached proof generation and positive/negative verification assertions.

#### Scenario: coverage and replay

- **WHEN** cached proof responses are enabled for application tests
- **THEN** contract execution/assertions/verification still run, fresh-randomness callers bypass, and a mandatory uncached lane tests the actual prover.
