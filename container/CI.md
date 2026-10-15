# Prepared GitHub workflows

The workflow files are committed for review; preparing them does not run remote
CI, enable Pages, publish an image or deploy a service.

- `.github/workflows/ci.yml`: pull requests and pushes to `main` run locked
  Nix-toolchain checks, fast Rust tests, Clippy, HTTP source/auth/error e2e and
  documentation validation. The job has a 35-minute limit and cancels superseded
  runs. A lockfile/toolchain-keyed Rust cache avoids repeated dependency builds.
  Fast checks do not generate proofs or download proving parameters.
- The same workflow's manual `real_proofs` input opts into a separate 40-minute
  job. It fetches parameters through upstream verification, runs both profiles'
  genuine proof/invalid-control/cache-regeneration tests and HTTP proof e2e.
  A cold GitHub runner may exceed that budget; a timeout is not a passing result.
- `.github/workflows/pages.yml`: manual only, builds/checks `.local/site`, uploads
  the Pages artifact, then deploys to the `github-pages` environment. Configure
  Pages to use GitHub Actions and apply environment approval protection before
  intentionally dispatching it. Publication is a separate owner action.

Every external action is pinned to an official repository commit, resolved from
its release tag during local preparation. Checkout does not persist credentials.
Routine checks have read-only repository permissions; only the Pages deploy job
receives Pages write and OIDC permission. There are no scheduled workflows,
registry credentials, image pushes or release jobs.
