# Design

The shell entry point resolves its own directory and execs the existing Python
3.11+ release installer with arguments unchanged. It requires no Nix, Cargo or
repository build. Existing gh authentication, exact tag, checksum/source manifest,
archive/runtime checks, matched workers/helper and atomic managed activation stay
authoritative. There is no latest lookup or source-build fallback.

`--github-path` is opt-in. Validate the Actions command-file location and the
single-line absolute installation bin path before installation; append only after
verified installation succeeds. Invalid/missing configuration refuses before
activation. Other installer errors leave the PATH command file unchanged. A PATH
append I/O failure is reported; an already completed installation is not rolled
back or misrepresented as unchanged. Existing launcher collisions still refuse.

Local users choose a prefix and set PATH themselves. CI uses a job-private prefix
under RUNNER_TEMP. Neither entry point edits shell profiles, credentials, Forge
cache data, public parameters or Nix GC roots. Installing a different executable
does not authorize Compact's exact-build allowlist or qualify its keys.
