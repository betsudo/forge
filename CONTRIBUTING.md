# Contributing locally

Run `./bootstrap.sh --configure-git` once, then use `./bootstrap.sh --check`. All builds and tests run locally for this MVP.

The delivery loop is issue → OpenSpec contract → implementation → targeted
checks → signed DCO commit → review evidence. When publishing is authorized,
continue with a draft PR linked to that issue; a local commit does not imply a PR.
No hosted CI or remote code mutation is part of the current loop.

Following SDK Rust's spec-driven workflow, behavioral changes have a local
`openspec/changes/<name>/` proposal, design, requirement/scenario specs and tasks
before qualifying the implementation. `SPEC.md` is the product scope; capability
specs state testable contracts and tasks link evidence. Update them when scope
changes. Keep completed changes available; archive only when delivered evidence
is recorded. Structural validation is not proof of semantic correctness.

ADRs are needed only for material decisions whose rationale does not fit the
change design (incompatible identity/serialization changes, upstream patches,
cryptographic boundaries). Drafts use `draft-<slug>.md` until owner acceptance.
Do not duplicate each requirement in an ADR.

Use `codex/issue-N-description` branches and Conventional Commit subjects, e.g.
`feat(cache): add verified local reuse`. Every authored commit uses `git commit
-S -s` with the existing configured identity and `Assisted-by: AI`, and references
its issue. If signing fails, report it; never invent an identity or unsigned fallback.

PRs use the [review/CI quality policy](docs/ci-quality-gates.md). Every commit must
link a real same-repository issue and carry an author-matching DCO and verified
OpenPGP signature. PR titles are conventional too; use the PR template. Local
hooks help, while the trusted-base GitHub gate enforces every PR commit after
owner-authorized activation. Required branch settings are documented separately;
local workflow files alone cannot prevent merging.
