# Private release installation requirements

### Requirement: authenticated exact-version selection

The installer SHALL require an explicit release tag and use existing gh credentials
for the fixed private Forge repository, without changing visibility or permissions.

#### Scenario: authorized read-only user

- **WHEN** a read-authorized user requests a published exact tag
- **THEN** only that release's matching native bundle/checksums are downloaded.

#### Scenario: missing access or interrupted download

- **WHEN** authentication, access or transfer fails
- **THEN** installation fails clearly without exposing credentials or changing activation.

### Requirement: macOS and Linux portable matched payloads

Release bundles SHALL pair CLI, exact v3 worker and CI helper for a qualified native
macOS/Linux ARM64/x86_64 target, and run without Nix at consumer runtime.

#### Scenario: target unavailable or incompatible

- **WHEN** the native target is unqualified, absent or below the recorded runtime baseline
- **THEN** installation refuses without fallback to a different platform or emulation.

#### Scenario: Nix-free qualification

- **WHEN** a target is proposed for publication
- **THEN** its relocated bundle passes startup, real v2/v3 proof and recovery controls
  in an environment with no Nix store or build checkout before support is claimed.

### Requirement: verify before executing

The installer SHALL verify unique expected checksums, optional independent digest,
strict archive inventory, manifest and runtime/version pairing before smoke execution.

#### Scenario: hostile or incomplete payload

- **WHEN** checksums conflict, paths escape, archive links/special files appear or inventory is incomplete
- **THEN** no payload is executed or activated and the previous version remains intact.

### Requirement: safe activation and recovery

The installer SHALL stage complete releases and switch a single active pointer,
serialize installers, preserve prior releases and refuse unrelated command conflicts.

#### Scenario: interrupted upgrade

- **WHEN** interruption occurs before activation
- **THEN** the old version remains active; after activation an idempotent retry converges
  to the complete verified new version without a mixed CLI/worker installation.

#### Scenario: initial install, repeat and rollback

- **WHEN** initial link creation is interrupted or an exact version is requested again
- **THEN** verified managed links can be completed; selecting a prior version restores
  it without touching circuit caches, parameters, Nix GC roots or shell profiles.

### Requirement: immutable pin through Nix

The repository flake SHALL remain usable as an immutable private input for macOS
and Linux, exposing the CLI with matching worker/helper as one default package.

#### Scenario: locked consumer flake

- **WHEN** an authorized user references a full commit and locks the input
- **THEN** Nix evaluates the corresponding native package/dev shell without a token in
  the input URL; this path explicitly requires Nix rather than claiming portability.
