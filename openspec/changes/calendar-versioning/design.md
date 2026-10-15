# Version policy

Use YYYY.M.PATCH: four-digit year, month 1–12 without leading zero, and a zero-based
patch counter for that month. Thus October 2026 starts at 2026.10.0 and January
2027 starts at 2027.1.0. This remains valid Cargo/SemVer syntax. A calendar rollover
does not promise API compatibility; release notes and descriptor/schema versions
carry that contract. Optional prereleases use -rc.N. Published Git tags would use
v2026.10.0, but creating/publishing a tag requires separate authorization.

CLI, worker, local-package lock entries, Nix package/container metadata, Compose
examples and OpenAPI product version must agree. Official Midnight dependency
versions and profile labels must not be changed to the Forge product version.
Historical receipts and old published-commit pins stay factual and unchanged.
Nix derives package version from Cargo.toml rather than another literal.

The GitHub milestone 2026.10.0 groups baseline issues #1–#10, installer/compiler
issues #11–#12 and research/version issues #13–#17. Acceptance is documented in
docs/milestones/2026.10.0.md. Baseline issue inclusion is not a new claim that all
full-service proposals have been implemented. No due date is invented.

Autonomous work remains bounded to local specs, implementation, independent review,
Nix checks and signed DCO commits; issue/milestone metadata is authorized. No push,
hosted CI dispatch, release upload, deployment or Compact checkout modification.
