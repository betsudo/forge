# Version policy

### Requirement: Calendar release identifier

Forge SHALL use YYYY.M.PATCH product versions consistently across CLI, worker,
package metadata and candidate manifests, without changing dependency versions.

#### Scenario: First calendar candidate

- **WHEN** preparing the October 2026 candidate
- **THEN** its product version is 2026.10.0 and a future published tag would be
  v2026.10.0, while official backend pins retain their existing versions.

### Requirement: Explicit local acceptance

Forge SHALL distinguish local milestone acceptance from publication and platform
qualification, preserving historical evidence and exposing remaining release gates.

#### Scenario: Unavailable target qualification

- **WHEN** a native target passes but another target has not executed
- **THEN** the report names the tested platform and pending targets without
  claiming universal support or starting a hosted job/deployment.
