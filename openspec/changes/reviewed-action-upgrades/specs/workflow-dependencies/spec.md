# Workflow dependency upgrade contract

### Requirement: Immutable reviewed action pins

#### Scenario: Workflow inventory
**WHEN** workflow dependencies are upgraded
**THEN** all four reviewed action families SHALL use their verified 40-character
commit pins in every current workflow, including Passport qualification.

### Requirement: Preserve workflow security and artifact contracts

#### Scenario: Upgrade validation
**WHEN** PR and Pages workflows use the new action versions
**THEN** trusted-base checkout, persist-credentials:false, least permissions,
artifact archive layout/names/retention, and manual Pages deployment SHALL remain.
Signed owner commits SHALL satisfy existing issue and DCO policy without bypass.
Actual Pages deployment SHALL remain explicitly untested until authorized.
