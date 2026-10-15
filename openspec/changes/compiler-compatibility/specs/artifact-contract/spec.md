# Artifact compatibility requirements

### Requirement: descriptor parity and strictness

Forge SHALL expose one typed v1 descriptor across CLI, persistent export sidecars
and HTTP, including all actual source, recipe, parameter, worker and output facts.

#### Scenario: exact cold then warm context

- **WHEN** identical supported source/context is materialized twice
- **THEN** verified reuse preserves descriptors/IDs across transports and actual
  proof, verification and positive/negative assertions still execute.

#### Scenario: incomplete or conflicting descriptor

- **WHEN** a field is missing/duplicated, a version unsupported, v3 worker absent,
  or identity/inventory facts disagree
- **THEN** strict descriptor validation refuses the input without availability fallback.

### Requirement: independently qualified compatibility

Consumers SHALL compare descriptor facts against independent policy; Forge SHALL
retain conservative recipe/build/worker/actual-parameter partitioning.

#### Scenario: change one identity premise

- **WHEN** source, backend revision/profile, serialization, options, build/worker
  provenance or actual parameter bytes changes independently
- **THEN** an incompatible hit is refused or has a distinct derivation; source-only
  equality cannot authorize reuse and equal outputs do not imply equal recipes.

### Requirement: backwards-compatible immutable exports

Existing identity recipes, Record schema, export manifests and pinned regeneration
checks SHALL remain intact; descriptor sidecars are additive and verified.

#### Scenario: legacy export and snapshot

- **WHEN** legacy exports lack a sidecar or an existing snapshot contains no sidecars
- **THEN** existing immutable bytes remain unchanged, compatible inventory is accepted,
  and sidecars may only be added after verifying all their source premises.

### Requirement: typed safe fallback outcomes

Domain failures SHALL map through explicit types to stable CLI/HTTP codes/statuses,
with distinct availability, invalid material, compatibility, corruption, identity,
authentication, busy and internal outcomes.

#### Scenario: missing versus corrupt parameters

- **WHEN** verified parameter material is absent versus present but invalid
- **THEN** absence is parameters_unavailable and corruption is invalid_parameters;
  the latter never becomes service-unavailable through diagnostic substring matching.

#### Scenario: unsafe hit versus unavailable service

- **WHEN** artifacts/provenance are corrupt or incompatible, authentication fails,
  or transport is busy/unavailable
- **THEN** only documented availability outcomes permit consumer-controlled fresh
  generation; integrity/compatibility/auth refusals fail explicitly, with no private
  diagnostics in HTTP output.
