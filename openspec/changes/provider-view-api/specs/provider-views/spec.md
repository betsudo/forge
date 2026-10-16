# Provider views

### Requirement: Original complete compiler output
Forge SHALL publish only complete bounded verified original compiler output under
its independently supplied raw manifest digest; it SHALL not synthesize compiler metadata.

#### Scenario: Bare export or inconsistent runtime
- **WHEN** compiler manifest/info is absent, versions conflict, files are undeclared or artifact coverage is incomplete
- **THEN** publication fails without a discoverable partial view.

### Requirement: Immutable atomic publication
Forge SHALL stage private copies, verify all declared bytes and publish without
replacement. Existing same-ID views SHALL be fully checked for idempotent success.

#### Scenario: Interrupted or conflicting publication
- **WHEN** copying fails, another writer wins or an existing view is corrupt
- **THEN** no incomplete set becomes ready and no corrupt/changed view is overwritten.

### Requirement: Verified read-only provider HTTP
The provider route SHALL authenticate before lookup, serve only declared safe
paths and verified response bytes, and preserve integrity before HEAD/304/range handling.

#### Scenario: Corrupt published file on a conditional request
- **WHEN** the file has changed after publication and a client sends If-None-Match or HEAD
- **THEN** the request fails instead of reporting a valid immutable cache hit.

### Requirement: End-to-end consumer integrity
Qualification SHALL use exact official providers with default integrity and an
independent manifest pin, while actual proofs/verification/assertions still execute.

#### Scenario: Coordinated manifest and key replacement
- **WHEN** an internally consistent replacement bundle differs from the trusted raw manifest hash
- **THEN** it is rejected by the pinned consumer/view identity, even if its internal checksums agree.
