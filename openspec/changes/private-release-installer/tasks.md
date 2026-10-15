# Tasks

- [x] Define private exact-version distribution, portability and safe install contract.
- [x] Include macOS/Linux target scope and an immutable private-flake consumer path.
- [x] Implement the small gh/Python installer and archive/manifest validation.
- [x] Implement native bundle preparation and dependency/loader portability checks.
- [x] Add isolated fake-gh failure, conflict, concurrency, interruption and rollback tests.
- [ ] Validate native target locally; identify unavailable OS/architecture qualification explicitly.
- [x] Document pinned-flake use and evaluate native/package outputs locally.
- [x] Independent review and signed implementation/evidence commits.

No release upload, tag, hosted job, access mutation or push is authorized by these
local implementation tasks. Publishing and real private-release download qualification
require a separately authorized release; local mocked-download tests must be labeled.

Local fake-gh receipt: docs/evidence/private-installer-local.json. Native package
production/clean-runtime qualification is separate: macOS candidate pending, Linux
Nix ELF dependency refusal is intentional until a portable production strategy exists.
