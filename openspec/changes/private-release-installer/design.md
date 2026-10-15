# Private release installation design

## Small consumer interface

Proposed script: `scripts/install-release.py`, also attached to each release as
`install-release.py`. Run it with Python 3.11+ after inspection. Prerequisites:
a supported OS/architecture and `gh` authenticated for github.com with read access
to `input-output-hk/midnight-zkir-forge` (including any required organization SSO).
The installer never logs in, requests broader scopes, prints credentials or changes
repository access. It uses `gh`'s existing interactive/CI authentication.

```sh
# One-time authentication, performed by the user:
gh auth login

# Proposed flow AFTER a release exists; substitute a real published tag.
# Use a fresh scratch directory so existing files cannot be overwritten.
gh release download vX.Y.Z --repo input-output-hk/midnight-zkir-forge \
  --pattern install-release.py --pattern SHA256SUMS --dir /path/to/fresh/scratch
# Inspect the downloaded script; verify its listed SHA-256 before running.
python3 /path/to/fresh/scratch/install-release.py --version vX.Y.Z
```

The script interface is intentionally limited:

- `--version TAG` required; exact `vMAJOR.MINOR.PATCH` with optional SemVer
  prerelease suffix. No implicit latest, branches or floating upgrade selection.
- `--prefix PATH` optional, default `~/.local`; resolve to an absolute path.
- `--sha256 HEX` optional, an independently obtained expected bundle digest in
  addition to the release checksum. It does not replace checksum verification.
- `--help`: human-readable prerequisites, destinations and failure policy.

No shell evaluation, `curl | sh`, automatic shell-profile edits, `sudo`, platform
emulation fallback, credential flags or generic download URL/repository override.
The installer runs subprocesses with argument arrays and bounded network commands;
errors explain access, unsupported platform, checksum, compatibility or conflict
without revealing tokens. A standard GH token environment in CI is supported.
Success prints installed tag/platform/path and a PATH hint. Nonzero means installation
is incomplete or refused; warnings never disguise a failed activation.

The bootstrap script is trusted code from the authorized release publisher.
Checking it against a checksum downloaded from the same release detects corruption,
not publisher compromise. Neither bootstrap nor payload is independently authenticated
by plain SHA-256. Repository permissions and trusted release production remain the
trust boundary; no GPG/attestation consumer dependency is added in this first slice.

## Assets and version pairing

Proposed asset names:

```text
install-release.py
SHA256SUMS
midnight-zkir-forge-TAG-TARGET.tar.gz
```

`TARGET` is one of `aarch64-apple-darwin`, `x86_64-apple-darwin`,
`aarch64-unknown-linux-gnu`, `x86_64-unknown-linux-gnu`. Detect the running native
platform once; do not silently choose x86 emulation for ARM. Unsupported platforms,
musl hosts and unqualified targets fail with a clear supported-target list.
Published platform metadata states the measured minimum OS/libc and Python
requirements. These baselines must be fixed by qualification before publishing;
this proposal does not invent a tested minimum OS version.

Each tarball contains exactly one expected root directory, with:

```text
midnight-zkir-forge-TAG-TARGET/
  bin/midnight-zkir-forge
  bin/midnight-zkir-forge-zkir3-worker
  bin/midnight-zkir-forge-ci
  share/midnight-zkir-forge/forge-ci.py
  manifest.json
  LICENSES/...
  lib/...  # inventoried relocated runtime libraries when needed
```

The CI helper launcher uses the consumer Python and its bundled script/main CLI;
it has no Nix shebang or build-host path. The manifest includes schema, release tag,
package version, source commit, target, minimum runtime requirements, root/backend
profiles and fingerprints, exact worker descriptor, plus per-file relative path,
size and SHA-256 (excluding the manifest itself). `SHA256SUMS` lists each tarball
and installer exactly once, with safe asset basenames and lowercase SHA-256.
Downloaded names, release metadata/tag and manifest must agree. Drafts are refused;
an explicitly named prerelease is allowed and labeled as such. No unrelated release
asset or GitHub-generated source archive is executable payload.

A release producer assembles CLI, worker and helper from one reviewed source commit
and locked dependencies. The candidate builder builds the exact clean Git commit
through Nix itself; arbitrary prebuilt executable inputs cannot be attributed to
HEAD. A Nix store executable copied into a tarball is NOT
portable by definition: remove/bundle runtime dependencies and qualify each target
on a clean environment with no `/nix/store`, build checkout or Rust toolchain.
Use platform tools to inspect loader/library references and test relocation. Shared
library dependencies and bundled-license obligations must be recorded. SHA checks
alone do not establish runtime portability. Do not publish incomplete target sets
as if they were supported or replace published version assets in place; use a new
tag for corrected content. Concrete release automation is a later implementation
step, not a mandatory multi-platform pipeline in this proposal.

## Download, validate, prepare, activate

1. Preflight Python, `gh`, native platform, exact tag, runtime baseline and writable
   user-owned prefix. Reject symlinked managed directories and unrelated command
   conflicts before activation. Missing permission/auth fails with a `gh` login/
   repository-access hint, without token capture. Resolve the exact release once;
   download only its exact target bundle and SHA256SUMS into a private temp area.
2. Verify the unique expected bundle checksum and optional independent digest
   before extraction. Abort on missing/duplicate checksum names, changed assets,
   interrupted/truncated downloads or authentication failures. Defaults bound
   compressed download to 1 GiB, unpacked data to 2 GiB and archive members to
   10,000, with a 5-minute deadline per network operation. GitHub metadata is capped
   at 16 MiB and checksum/manifest metadata at 1 MiB. A bounded decompressed spool
   (2 GiB plus 16 MiB tar framing allowance) precedes archive-header parsing, so
   oversized PAX/GNU headers cannot bypass the expansion budget. Check advertised size
   before download, actual size afterward, and cumulative member/read bytes during
   controlled extraction. Those bounds are initial delivery limits, not a promise
   to support any circuit/key size in the installed cache.
3. Validate all archive entries before extracting; allow only the expected relative
   root and declared regular files/directories. Reject absolute/traversal paths,
   links, special files, duplicates, non-UTF-8 names, unexpected payloads and elevated
   mode bits. Do not call an unrestricted extract-all. Verify the strict manifest,
   all per-file sizes/hashes, version/target and runtime requirements before execution.
4. Stage on the same filesystem under the binary installation root. Run the staged
   CLI's `--version`, root and v3 `profile`, and helper `--help`, explicitly selecting
   the staged worker for profile verification. Also check default worker discovery.
   Do not generate keys, fetch parameters, start HTTP, migrate a cache or mutate the
   current install during smoke checks. A loader error or mismatched worker fails.
5. Publish a verified version directory, then atomically replace one `current`
   symlink. Version storage is content-specific; concurrent installs use one atomic
   installer lock, fail clearly if busy, and never interleave activation. Keep the
   previous release; do not add a background version GC or automatically delete it.

Default installation layout is deliberately separate from the Nix GC root:

```text
PREFIX/bin/midnight-zkir-forge                 -> binary/current/bin/...
PREFIX/bin/midnight-zkir-forge-zkir3-worker    -> binary/current/bin/...
PREFIX/bin/midnight-zkir-forge-ci              -> binary/current/bin/...
PREFIX/share/midnight-zkir-forge/binary/
  releases/TAG-TARGET-BUNDLE_SHA256/...
  current -> releases/TAG-TARGET-BUNDLE_SHA256
```

The command symlinks use correct absolute or relative targets to that binary root
(the abbreviated arrows above are conceptual). Existing Nix
`share/midnight-zkir-forge/current` and its GC root remain untouched. First-install
links are created only after the complete version is ready. A killed first install
may leave a subset of valid managed links, never dangling links to missing payloads;
an idempotent retry completes them. Upgrades leave the stable command links in place
and switch only the one binary `current` pointer. Do not promise an atomic batch
creation of three new directory entries.

A previously installed different digest under the same tag/target is refused;
release content is not silently replaced. Reinstalling the same version verifies
local payload before reusing it. Selecting a prior explicit version is the rollback
mechanism; no separate rollback command or automatic updater is needed. Faults
before the activation swap leave the old pointer intact. After the swap, an
interrupted command may already have activated the new verified version; retry
reports/converges to that version rather than claiming no changes occurred. Stale
lock recovery must distinguish a dead owner from a live installer, without stealing
a live lock; it must have deterministic interrupted-process tests.

Never overwrite unrelated files/symlinks in `PREFIX/bin`, including existing Nix
launchers. Explain how to choose a different prefix or explicitly retire the old
launcher links; do not silently take them over. Preserve the shared Forge cache,
parameters and user shell files. Ask users to stop Forge commands/services before
switching versions; uninterrupted hot upgrades are not a supported guarantee.
Stopping one of three command-link creations during first install is recoverable,
not a reason to delete already verified release files.

## Qualification and sources

Test authenticated downloading with read-only repository access and lack of access.
Most fault tests use a fake/local `gh` and isolated prefixes without credentials;
separately perform the real private-release download on an authorized clean consumer.
Build and run through Nix during development. The target must actually install,
relocate and run without Nix at consumer runtime; absence from PATH alone is not
sufficient when `/nix/store` still exists.

Official references reviewed 2026-10-16:

- [Release visibility and read access](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
- [Exact-tag asset download and --repo/--pattern/--dir](https://cli.github.com/manual/gh_release_download).

No ADR is required: this design owns the distribution decision and does not change
cryptographic identities or core cache semantics.

## Pinned Nix alternative

The existing flake exposes `packages.<system>.default`, `zkir3-worker` and
`devShells.<system>.default` for the four macOS/Linux systems. Consumers may pin
this private repository as `git+ssh://git@github.com/input-output-hk/midnight-zkir-forge?rev=FULL_COMMIT`
in their flake inputs; their flake.lock records the immutable revision. Existing
GitHub SSH read access is required; gh login alone does not configure SSH access.
Do not embed tokens in URLs, checked-in files or command history. A copied sample
must use a real full commit chosen by the consumer, not a floating main revision
masquerading as a pin. Nix installation intentionally retains its Nix closure and
is a separate supported path from Nix-free bundles. Expose the CLI and matching
worker/helper together through the default package. No consuming checkout edits
are implied; a self-contained example and local flake evaluation are sufficient.


### Intel macOS Nix input correction — issue #18

The final four-system evaluation found that the existing locked Nixpkgs26.11
revision has dropped x86_64-darwin. Retain that exact input for ARM macOS and both
Linux systems. Add a separately locked official nixpkgs-26.05-darwin input for Intel macOS
only, since upstream identifies that stable line as supported through end2026.
This is not a Midnight graph upgrade or a universal runtime claim. Apply the same
selection in the consumer example and evaluate all package/worker/shell outputs.
A future upstream Intel support change requires an explicit policy/pin amendment;
never hide evaluation failure behind an advertised unsupported output.
