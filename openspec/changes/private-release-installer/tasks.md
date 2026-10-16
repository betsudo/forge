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
- [x] Produce final three-profile candidates from clean signed sources (Linux9359068, macOSa65d3f0; exact per-platform provenance retained).
- [x] Run actual installed CLI proof and recovery controls on clean Nix-free Linux ARM64 (Debian12 userland, recorded kernel); Intel remains unqualified.
- [ ] DEFERRED by owner on 2026-10-16: actual installed CLI proof and recovery controls on a clean Nix-free macOS host/VM; no guest tests ran.
- [x] Record final independent review and qualification evidence, explicitly retaining the unmet clean-Mac gate; no publication.

A macOS sandbox denying Nix/checkout reads is useful evidence, but does not
complete the real Nix-free macOS environment requirement.

Final Linux9359068 evidence: `docs/evidence/private-installer-linux-three-profile.json`
and `private-installer-linux-runtime-audit.json`. Independent review verified
782 payload files,415 native Cargo package notices, exact runtime source companion,
all3 installed proof/recovery profiles as UID1000 without Nix/checkout/mounts/network
or MIDNIGHT_PP, and separate fresh HTTPS retrieval per profile. The external
recovery harness fix is signed in4006a29 and its actual digest is recorded.
This completes Linux ARM64 local qualification, not macOS or Intel qualification.

Latest macOSa65d3f0 restricted-host receipt/audit: docs/evidence/
private-installer-darwin-a65d3f0-*.json. All3 installed proof/recovery profiles
pass;777payload files and422Cargo notice identities independently reviewed.
The refreshed11-file clean-Mac kit uses the corrected explicit-parameter harness;
private-installer-macos-consumer-kit.json records its checksums. Actual Nix-free
macOS remains the single unmet required qualification gate.

Owner scope update (2026-10-16): skip the VM qualification for now. The unchecked
clean-Mac task is a future publication gate, not unfinished work in the current
local increment. Download/continuation stopped and owned temporary VM/cache files
removed; see docs/evidence/private-installer-macos-deferred.json.
