# GitHub CI and Pages

Main CI is active. Documentation publication uses an explicitly dispatched Pages
workflow; image publication and hosted Forge service deployment remain separate.

- `.github/workflows/ci.yml`: pull requests and pushes to `main` run locked
  Nix-toolchain checks, fast Rust tests, Clippy, recovery/snapshot/HTTP source/auth/error e2e and
  documentation validation. The job has a 35-minute limit and cancels superseded
  runs. A lockfile/toolchain-keyed Rust cache avoids repeated dependency builds.
  Fast checks do not generate proofs or download proving parameters.
- The same workflow's manual `real_proofs` input opts into a separate 40-minute
  job. It fetches parameters through upstream verification, runs both profiles'
  genuine proof/invalid-control/cache-regeneration tests and HTTP proof e2e.
  A cold GitHub runner may exceed that budget; a timeout is not a passing result.
- `.github/workflows/pages.yml`: manual only, builds/checks `.local/site`, uploads
  the Pages artifact, then deploys to the `github-pages` environment. Configure
  Pages to use GitHub Actions and retain any configured environment protections.
  Publication is a separate owner-authorized action.

Every external action is pinned to an official repository commit, resolved from
its release tag during local preparation. Checkout does not persist credentials.
Routine checks have read-only repository permissions; only the Pages deploy job
receives Pages write and OIDC permission. There are no scheduled workflows,
registry credentials, image pushes or release jobs.

The [documentation site](https://curly-adventure-gken1jg.pages.github.io/) was published after the initial Linux main CI
passed on 2026-10-15. Repository and site visibility remain private. The deployment
artifact matches all nine locally validated site files. See
[delivery evidence](../docs/evidence/pages-publication.json). The real-proof CI job
was intentionally skipped; this fast run does not qualify Linux proof generation
or the Docker image. GitHub reports non-blocking Node20 action-runtime deprecation
annotations; all current steps passed under the runner's Node24 compatibility.
