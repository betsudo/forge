# Proposed backend qualification requirements

### Requirement: explicit immutable profiles

Forge SHALL retain existing pins and SHALL identify every added profile by exact official provenance, complete dependency/options/serialization/parameter identity and worker executable. JSON major or display version SHALL NOT alone authorize reuse.

#### Scenario: ambiguous ZKIR3

- **WHEN** multiple profiles accept the same JSON major but differ in dialect, tags or graph
- **THEN** explicit qualified selection is required; no conversion or silent fallback occurs.

### Requirement: independent graph and identity retention

Incompatible graphs SHALL use separately locked workers. Registry migration SHALL preserve historical recipe/output records and actual pinned verifier identities.

#### Scenario: equivalent published package

- **WHEN** a Git dependency is replaced with a reviewed published package
- **THEN** complete graph/content qualification is required and changed build provenance produces its own conservative recipe identity.

### Requirement: evidence-limited support

Every advertised platform/profile SHALL pass real consumer fixture proving with cold and warm exported/downloaded keys, negative controls, recovery and regeneration checks. Circuit artifact support SHALL NOT imply ledger transaction/network support.

#### Scenario: build-only candidate

- **WHEN** a new worker compiles but lacks consumer proof evidence
- **THEN** it is marked buildable only and cannot claim consumer or ledger9 transaction compatibility.
