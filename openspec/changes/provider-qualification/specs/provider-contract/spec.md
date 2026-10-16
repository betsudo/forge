# Provider acceptance

### Requirement: Original compiler integrity
Qualification SHALL use original compiler-produced metadata and an explicit
manifest hash, unchanged across verified Forge byte-identical materialization.

#### Scenario: Bare export versus compiler output
- **WHEN** a bare Forge export lacks compiler metadata, or an original compiler bundle is byte-identically materialized
- **THEN** default SDK integrity rejects the bare export and accepts only the complete qualified compiler bundle.

### Requirement: Actual provider retrieval and proof execution
Qualification SHALL use pinned official local and Fetch providers, verify every
returned byte and keep actual proofs/assertions and negative controls executing.

#### Scenario: Local, HTTP and compressed HTTP reads
- **WHEN** current fixture keys are consumed locally or through actual HTTP, including gzip
- **THEN** original canonical artifact bytes and runtime metadata match and fresh valid/invalid/corrupt proof controls still execute.

### Requirement: Fail closed and precise scope
Qualification SHALL reject wrong manifest anchors, corrupted material, missing
metadata and HTML fallback without disabling integrity or relabeling failures as hits.
It SHALL distinguish local Node HTTP evidence from browser/HTTPS/cloud readiness.

#### Scenario: Provider integrity refusal
- **WHEN** a declared object is corrupted or the manifest hash mismatches
- **THEN** both supported provider paths fail explicitly; no availability fallback hides it.
