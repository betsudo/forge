# Tasks

- [x] Define private exact-version distribution, portability and safe install contract.
- [x] Include macOS/Linux target scope and an immutable private-flake consumer path.
- [x] Implement the small gh/Python installer and archive/manifest validation.
- [x] Implement native bundle preparation and dependency/loader portability checks.
- [x] Add isolated fake-gh failure, conflict, concurrency, interruption and rollback tests.
- [x] Validate native target locally; identify unavailable OS/architecture qualification explicitly.
- [x] Document pinned-flake use and evaluate native/package outputs locally.
- [x] Independent review and signed implementation/evidence commits.

No release upload, tag, hosted job, access mutation or push is authorized by these
local implementation tasks. Publishing and real private-release download qualification
require a separately authorized release; local mocked-download tests must be labeled.

Local fake-gh receipt: docs/evidence/private-installer-local.json. Native package
production/clean-runtime qualification is separate: the earlier macOS ARM64 candidate passed restricted-runtime proof/ordinary recovery checks.
A portable Linux producer is now implemented; final clean installed-candidate receipts remain pending.

Final local candidate receipt: docs/evidence/milestone-2026.10.0-local.json.

## Owner-authorized #11/#13 qualification follow-up

- [x] Add verified Linux loader/library closure with runtime source companion.
- [x] Preserve original Cargo/Rust notices from exact locked sources, with missing-license refusal controls.
- [x] Collect exact Apple libiconv source, patches and BSD/APSL notices separately from Linux.
- [x] Extend installer/profile inventory to the independently pinned JSON3.1 worker.
- [x] Exercise optional-worker upgrades and legacy rollback without dangling stable links.
- [ ] Produce final three-profile candidates from a clean signed source commit.
- [ ] Run actual installed CLI proof and recovery controls on clean Nix-free Linux.
- [ ] Run actual installed CLI proof and recovery controls on a clean Nix-free macOS host/VM.
- [ ] Record final independent review and qualification evidence; no publication.

A macOS sandbox denying Nix/checkout reads is useful evidence, but does not
complete the real Nix-free macOS environment requirement.
