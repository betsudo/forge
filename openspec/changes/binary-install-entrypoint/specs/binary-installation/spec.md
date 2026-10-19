# Binary installation entry point

### Requirement: delegate exact-version verified installation

`install.sh` SHALL delegate unchanged arguments and exit status to the existing
release installer, including exact release selection and all integrity checks.

#### Scenario: local or CI installation

- **WHEN** an explicit published tag and isolated prefix are supplied from any cwd
- **THEN** matching verified CLI/workers/helper install without a source build.

#### Scenario: absent release, corrupt bundle or conflicting executable

- **WHEN** the existing installer refuses the requested installation
- **THEN** the entry point returns nonzero without source or latest-version fallback.

### Requirement: explicit successful Actions PATH registration

PATH command-file writes SHALL require `--github-path` and valid command-file and
single-line bin-path inputs; they SHALL follow successful verified installation.

#### Scenario: Actions consumer

- **WHEN** a verified installation succeeds with explicit PATH registration
- **THEN** exactly its absolute PREFIX/bin is appended for subsequent steps.

#### Scenario: missing context, newline path or failed installation

- **WHEN** context is invalid, the bin path contains a line break, or install fails
- **THEN** no PATH record is emitted; invalid context refuses before activation.
