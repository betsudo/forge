# Quality gates

### Requirement: Trusted metadata enforcement
PR acceptance SHALL require a conventional title, real linked issue and every
commit's conventional subject, author DCO and valid verified OpenPGP signature.

#### Scenario: Tampered policy or stale head
- **WHEN** a PR changes its own verifier, omits signoff or its live head changes
- **THEN** trusted base policy remains authoritative and incomplete/stale verification fails.

### Requirement: Review and quality boundaries
Quality SHALL run locally through Nix and use pinned actions/read-only PR rights.

#### Scenario: Failed or skipped quality
- **WHEN** required implementation checks fail, cancel or skip
- **THEN** the stable quality gate refuses success; publication remains separately authorized.
