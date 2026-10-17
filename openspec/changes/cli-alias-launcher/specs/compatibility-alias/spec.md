# Compatibility launcher

### Requirement: One full CLI implementation
Cargo SHALL build one primary CLI and a lightweight compatibility launcher;
installed Nix/portable aliases SHALL retain their existing packaging semantics.

#### Scenario: Legacy invocation
- **WHEN** midnight-zkir-forge runs beside the primary zkir-forge
- **THEN** it executes the primary with exact OS arguments/environment and inherited stdio/exit behavior.

### Requirement: Explicit trusted sibling
The launcher SHALL select its sibling without PATH fallback and refuse missing
or self-referential primaries rather than recurse or select an unrelated command.

#### Scenario: Unrelated cwd or symlink
- **WHEN** the launcher runs through a symlink from an unrelated directory
- **THEN** it finds the primary beside the real launcher executable.

#### Scenario: Incomplete or recursive installation
- **WHEN** the sibling is absent or refers to the launcher itself
- **THEN** it fails clearly without consulting PATH or recurring.
