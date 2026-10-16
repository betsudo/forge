# CLI command

### Requirement: Primary command and alias
Forge SHALL expose zkir-forge as primary and retain midnight-zkir-forge with identical commands and cache semantics.

#### Scenario: Both names
- **WHEN** either installed entrypoint runs
- **THEN** it identifies as zkir-forge and shares profiles and underlying executable.

### Requirement: Installer compatibility
Installers SHALL retain validated inventory, collision refusal, atomic activation and historical rollback while exposing both names.

#### Scenario: Historical release or corrupt new alias
- **WHEN** an old legacy-only release is selected or a new alias differs from its primary bytes
- **THEN** both launchers remain usable for the old release, or the invalid new release refuses before activation.
