# HTTP delivery requirements

### Requirement: Explicit bounded materialization
The service SHALL reuse the existing store/application identity rules and SHALL
perform generation only for an explicit materialization POST, with bounded
admission and blocking work outside the HTTP executor.

#### Scenario: Warm request
- **WHEN** the same supported source/profile is materialized twice
- **THEN** the second request returns a verified hit with the same artifact identity.

#### Scenario: Saturation
- **WHEN** another HTTP materialization owns admission
- **THEN** an additional generation request receives 429 without queue growth.

### Requirement: Safe exact HTTP bytes
The service SHALL accept bounded raw uploads, reject server-path inputs, return
no server-local paths, and verify immutable objects before streaming them.

#### Scenario: Download
- **WHEN** a client uses GET, HEAD, conditional GET or a valid single byte range
- **THEN** bytes, digest ETag, length and range metadata describe the exact object.

#### Scenario: Corruption
- **WHEN** a stored object differs from its digest
- **THEN** even a conditional request fails instead of serving corrupt bytes or 304.

### Requirement: Local owner security
The service SHALL bind loopback by default, require a token for remote binding,
protect configured APIs, bound uploads and suppress filesystem paths in errors.

#### Scenario: Remote mode without token
- **WHEN** a non-loopback listener is configured without a token file
- **THEN** startup fails before exposing the service.

### Requirement: Reviewable delivery
The repository SHALL provide a branded Pages site, basic workflow definitions,
local e2e checks and a non-root Linux container package with persistent storage.

#### Scenario: Local validation
- **WHEN** contributors run the documented checks
- **THEN** docs links, transport behavior and real proof controls can be verified
  without pushing code, deploying Pages or publishing a container.
