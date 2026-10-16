# Provider reads and recovery

### Requirement: Fresh requested bytes and explicit full audit
Reads SHALL validate pinned metadata/tree and requested-file bytes before serving; publish/reuse and explicit verify-view SHALL verify all declared bytes.

#### Scenario: Corrupt sibling versus corrupt requested key
- **WHEN** an unrelated key has corrupt bytes or the requested key is corrupt
- **THEN** unrelated verified reads may succeed, full audit/republication refuses corruption, and requested GET/HEAD/304/range refuses corrupt bytes.

### Requirement: Isolated bounded admission
Provider verification and streaming SHALL retain dedicated permits independently of cache work, including cancellation.

#### Scenario: Cancelled blocking read
- **WHEN** a request is cancelled while its blocking verifier runs
- **THEN** its permit remains held until verification stops; cache work retains its own admission.

### Requirement: Explicit root and compiler crash recovery
Explicit cache roots SHALL work without HOME; compiler staging SHALL remain outside the final output tree and on the same filesystem.

#### Scenario: Killed keygen hook
- **WHEN** a hook dies during staging and the compile is retried
- **THEN** leftover staging does not pollute output inventory, sources and verifier identities stay protected, and native manifest/proof checks can complete.
