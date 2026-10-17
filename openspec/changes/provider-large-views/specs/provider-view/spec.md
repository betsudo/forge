# Complete large provider views

### Requirement: Explicit finite policy

#### Scenario: Default refusal and bounded opt-in
**WHEN** the stated condition occurs, Forge SHALL enforce the following.
**THEN** An over-budget complete manifest refuses with provider_limit, no fallback and
no visible partial view. With a sufficient explicit budget the original compiler
manifest and full inventory remain byte identical. Zero and budgets above 64 GiB
refuse before filesystem mutation. Per-file limits remain independent.

### Requirement: Atomic storage failure recovery

#### Scenario: Insufficient space, copy failure and concurrent publication
**WHEN** the stated condition occurs, Forge SHALL enforce the following.
**THEN** Insufficient destination headroom refuses before staging. Corruption or interrupted
copy never creates the immutable target. Retry may publish a fully audited view;
concurrent publication never replaces an existing identity. An invalid existing
target refuses rather than repairing itself.

### Requirement: Actual full consumer delivery

#### Scenario: Passport full account
**WHEN** the stated condition occurs, Forge SHALL enforce the following.
**THEN** Retain the original independently pinned compiler manifest, publish all files,
fetch the selected circuit artifacts concurrently using the official SDK and run
fresh application proofs, verification, assertions and negative controls. Record
persistent, temporary and transferred byte costs separately. Do not generalize
native Mac evidence to native Linux or hosted CI.

A valid provider read refused by the server budget SHALL return HTTP500
provider_limit without fallback/retry; invalid request input remains400. Storage
preflight is not a reservation; operators SHALL serialize publishers per root.
