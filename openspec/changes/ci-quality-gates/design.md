# Trusted review and stable quality contexts

A read-only pull_request_target workflow checks out only the exact base SHA and
runs only its verifier. No PR code checkout, Nix evaluation, cache, artifact,
package installation or PR-controlled shell interpolation is allowed in that job.
API results are bounded/paginated, every commit and live head SHA must agree with
the event and GitHub must report a valid verified OpenPGP signature. DCO must
match commit author identity; at least one explicit same-repository issue reference
must exist on PR and every commit. Reject PR numbers masquerading as issues.
Validate PR title against the same Conventional Commit grammar as local hooks.
PR quality still runs untrusted PR code under pull_request with read-only rights,
no secrets and credentials disabled. A stable always-run aggregate fails if its
required quality job fails, cancels or skips. Do not introduce path-based bypasses.
Introduction only takes effect after the verifier reaches the base branch; owner
must configure required checks and signed-commit/review rules separately. API
signature verification is GitHub's attestation, not an independently managed key
allowlist. DCO is a declaration, not proof of legal rights. Dependency alerts and
static analysis are scoped explicitly; do not claim vulnerability-free software.
