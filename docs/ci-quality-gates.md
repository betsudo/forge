# Review and CI quality gates

Prepared locally; not pushed or activated in GitHub. No settings were changed.
Inspired by midnight-did at revision `4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550`:
[trusted-base integrity](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/.github/workflows/pr-commit-integrity.yml),
[PR checks](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/.github/workflows/pr-check.yml),
[quality](https://github.com/midnightntwrk/midnight-did/blob/4e7f6b0f69bf4e2c8506a9693f8d0c3dfe68e550/.github/workflows/quality.yml).

## Mandatory checks after activation

**PR integrity gate** requires a conventional PR title; an explicit `Refs #N`,
`Fixes #N`, `Closes #N` or `Resolves #N` line in PR body and every commit; a real
same-repository issue (not a PR or transferred issue in another repo); conventional
subjects; matching author name/email DCO; GitHub-reported valid verified OpenPGP
signatures on every commit. No bot/merge exemption. Use `git commit -S -s` and
include `Assisted-by: AI` when applicable. Keep PRs under251commits so no commit
is silently omitted. A reviewer must still assess issue relevance and spec scope.

Types: feat, fix, docs, test, refactor, perf, build, ci, chore, style, revert.
Optional lowercase scope, optional breaking `!`, nonempty subject.

**Forge quality gate** aggregates existing locked Nix builds, formatting/Clippy,
profile/spec/docs checks, Rust tests, Python failure/e2e controls and new workflow
lint/policy tests. Failed, cancelled or skipped ordinary checks cannot pass.
Explicitly requested real proof runs must also pass; expensive proof qualification
remains manual. Static checks or cache hits never substitute for proofs/assertions.

## Trusted-base boundary

The integrity workflow uses `pull_request_target` with read-only contents/PR/issue
permissions. It checks out only the exact event base SHA without credentials and
runs only its verifier. PR input enters environment/API fields, never shell code.
It never builds, installs, caches, downloads PR artifacts or executes PR code.
Live head, base and metadata are rechecked to refuse stale results. Quality runs
separately under `pull_request` with read-only permissions and no credentials.
Actions are pinned by SHA. GitHub's signature verification is the authority here,
not an independent GPG key allowlist. DCO is an attestation, not legal verification.

## Owner activation and repository rules

The introduction PR is a bootstrap boundary: its base does not yet contain this
verifier, so the trusted-base job cannot pass until the reviewed verifier lands
on the base. Do not work around this by executing PR code in the target workflow.
After owner-authorized delivery, configure main-branch rules to require:

1. PRs, an independent approval, dismissal of stale approvals and approval of the
   latest push. Assign actual owners/teams to CODEOWNERS before requiring code-owner
   review, especially for workflows, policies and compatibility pins.
2. `PR integrity gate` and `Forge quality gate`, from GitHub Actions; require
   branches up to date. Optional manual proof jobs are not permanently required.
3. Signed commits; no force pushes or deletion; rules apply to admins with minimal
   bypass actors. Review Actions/token/fork-approval settings too.

No merge queue or remote settings are configured here. Prefer delivery preserving
reviewed signed commits and DCO. Squash/rebase can create new commits: verify their
signatures/trailers separately. Dependabot proposals do not bypass policy; a human
provides reviewed, issue-linked signed delivery when bot metadata is insufficient.
Never auto-merge compiler/crypto updates without exact qualification.

## Validation and subsequent security gates

`./bootstrap.sh --check` includes policy negative controls and actionlint. Fast checks:

```sh
./bootstrap.sh -- node scripts/test-commit-policy.mjs
./bootstrap.sh -- node scripts/test-pr-integrity.mjs
./bootstrap.sh -- actionlint
```

Dependency updates cover Actions, all three Cargo graphs and test-only SDK npm.
Nix locks still require reviewed explicit updates. No hosted check or advisory
audit ran for this increment. Advisory auditing, secret scans, coverage thresholds,
fuzzing and release provenance should establish baselines for the pinned official
graphs before becoming gates. Do not invent coverage targets or blanket advisory
exceptions. These review gates do not establish release readiness.
