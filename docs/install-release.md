# Private release installation and pinned Nix use

## Short binary-install command

In a reviewed checkout, run `./install.sh --version "$FORGE_VERSION" --prefix
"$HOME/.local/forge"`. Add `--sha256 "$FORGE_ARCHIVE_SHA256"` for an independently
obtained archive digest. The five-line shell entry point forwards to the existing
Python 3.11+/gh installer; it does not invoke Nix, Cargo or a source build. It works
from an unrelated current directory as well. Version selection remains mandatory.

For GitHub Actions, `--prefix "$RUNNER_TEMP/forge" --github-path` uses a job-private
installation and appends its absolute `bin` directory to the existing `GITHUB_PATH`
command file only after verified installation succeeds. Subsequent steps discover
the CLI, matched workers and helper; in the same step use their absolute paths.
Missing/invalid command-file context or newline-containing bin paths refuse before
installation. An install failure emits no PATH record. A later PATH-write failure
is an error but cannot undo an already completed installation. PATH registration
is never implicit, and shell profiles/credentials/cache data remain untouched.

The standalone `install-release.py` asset remains usable directly; the shell entry
point requires its adjacent `scripts/install-release.py` from the reviewed checkout.
Neither path is a release publisher or a consumer compatibility qualification.

The installer and candidate builder are local implementation work. **No downloadable
Forge binary release is published by this increment.** A supported target is not
qualified merely because the script recognizes its name. macOS/Linux ARM64/x86_64
are the target matrix; clean-runtime qualification is tracked separately per target.

## Nix users: use the existing package directly

The repository home is [betsudo/forge](https://github.com/betsudo/forge).
Pin a full reviewed commit without cloning a working tree. The default package
includes the CLI, matched workers and CI helper:

```sh
nix profile install 'github:betsudo/forge/9b1d7bbd6f55d05adb8d0543c16b659ac24e6e80'
nix shell 'github:betsudo/forge/9b1d7bbd6f55d05adb8d0543c16b659ac24e6e80'
```

The example pins the migrated baseline. Replace it with a reviewed full commit
when adopting changes. [examples/nix/flake.nix](../examples/nix/flake.nix) shows
how to include Forge in a consumer development shell. Commit the generated
consumer `flake.lock`. Native outputs cover `aarch64-darwin`, `x86_64-darwin`,
`aarch64-linux` and `x86_64-linux`; evaluation alone does not qualify runtime
support. Consult the source-specific qualification evidence and current progress.
Nix is required; Compact and consumer checkouts are unchanged.

## Binary users: intended flow once qualified assets exist

Install `gh` and Python 3.11+, authenticate with `gh auth login`, and obtain read
access to the release repository (authentication is required for private repositories). Read permission also exposes source code;
release download is not a separate download-only permission.

Download `install-release.py` and `SHA256SUMS` from one explicit release into a
fresh scratch directory with `gh release download TAG --repo
betsudo/forge --pattern install-release.py --pattern
SHA256SUMS --dir DIRECTORY`. Inspect/check the script, then run:

```sh
python3 /path/to/install-release.py --version vX.Y.Z
# Optional independently obtained bundle digest or alternate user prefix:
python3 /path/to/install-release.py --version vX.Y.Z --prefix /my/user/prefix --sha256 HEX
```

`vX.Y.Z` is a placeholder. The script downloads only the matching native tarball,
checks its unique checksum and manifest, validates archive entries and runtime
requirements, and smoke-tests the staged CLI/worker/helper. It uses an OS-managed
installer lock and one active-version pointer. Existing versions stay available;
requesting a prior explicit tag is rollback. Initial link creation can be completed
by retry after interruption. No key generation, parameter fetch or cache migration
happens during installation. Stop running Forge commands/services before upgrades.

Defaults are under `~/.local/bin` and `~/.local/share/midnight-zkir-forge/binary`.
Existing Nix launchers/GC roots are not taken over. Choose another `--prefix` or
explicitly retire old launcher links first. No sudo, shell-profile edit, access
mutation, automatic latest-version lookup or background updater is provided.
Checksums detect corruption; repository access and trusted release production
supply publisher trust. Same-release checksums do not protect against a malicious
publisher or establish independent consumer compatibility.

## Local candidate building

`scripts/build-release.py --tag v2026.10.0 --output .local/candidate` builds the
exact clean Git commit through its locked Nix flake, then prepares archive/checksums
without tagging/uploading. It accepts no arbitrary binary/worker inputs; manifest
source provenance comes from that build, not the executable version label.
It requires a clean committed source tree and explicit binary/worker/tag/output.
On macOS it relocates Nix dylib dependencies into the bundle and ad-hoc signs the
modified Mach-O files; this is not Apple Developer signing/notarization. On Linux
it refuses unresolved Nix library/ELF-loader paths; qualified portable native
binaries are required. It records the measured host minimum OS/libc conservatively.
Full dependency-license audit and clean Nix-free-host tests remain release gates.
A candidate is not a published or qualified release.

Run offline fake-gh/isolated-prefix install/failure tests with
`./bootstrap.sh -- python3 scripts/check-installer.py`. Their success does not
establish real private-release downloading, credentials or Nix-free portability.
See [the spec](../openspec/changes/private-release-installer/design.md).


For a locally built actual native candidate (no GitHub publication):

```sh
./bootstrap.sh -- python3 scripts/check-release-candidate.py \
  --directory /path/to/native-candidate \
  --runtime-python /opt/homebrew/bin/python3 --deny-nix --recovery
```

The macOS restricted-runtime experiment copies the candidate/installer to private
scratch, uses fake gh only for the local download boundary, denies `/nix` and the
checkout to the installer and installed commands, and runs every advertised profile's genuine proof and recovery
qualifications. Choose an installed Python 3.11+ outside Nix. This does not replace
an actual clean no-Nix host, Linux execution, or authenticated GitHub download test.
Omit `--deny-nix` only when deliberately recording an ordinary native candidate
experiment; its receipt reports whether Python itself comes from Nix.

Intel macOS selects separately locked official `nixpkgs-26.05-darwin`; ARM macOS
and Linux retain the original package set. The example follows both inputs and
selects by system. All four derivations evaluate; Intel runtime is unqualified.
Upstream identifies 26.05 as the final Intel macOS Nixpkgs release, so continued
future support needs an explicit reviewed strategy rather than a floating pin.

## Current local qualification

The final Linux ARM64 candidate from signed source `9359068` passed installation,
all three profiles' genuine proof/negative controls and recovery as an unprivileged
user in Nix-free Debian12/Python3.11.2 with no checkout mounts or network. Separate
fresh HTTPS parameter retrieval passed for each profile. Independent review
verified payload hashes, runtime source correspondence and original dependency
notices. See [installed receipt](evidence/private-installer-linux-three-profile.json)
and [runtime/source audit](evidence/private-installer-linux-runtime-audit.json).
The test used local fake GitHub transport; authenticated release downloading is
not qualified. Native Intel macOS and actual Nix-free macOS remain unqualified. Native x86_64 Linux qualification is recorded below.

On a real clean consumer host, use external Python and absolute verified parameter
paths with `check-release-candidate.py --require-nix-free --recovery`. That
precondition refuses a machine with a Nix store or Nix executable. A sandbox on a
Nix-equipped developer Mac is recorded separately and cannot satisfy this gate.
No binary release has been published.

The owner deferred the clean Nix-free macOS VM test on 2026-10-16. The download
was cancelled before guest boot; no guest installation, proof or recovery tests
ran. Temporary owned VM files were removed. Existing macOS ARM64 evidence is
restricted-host only; Nix-free macOS support must not be claimed from it. See
[deferral and cleanup receipt](evidence/private-installer-macos-deferred.json).

## Native x86_64 Linux follow-up

Signed source `48d9181` passed [native run38872428954](https://github.com/input-output-hk/midnight-zkir-forge/actions/runs/38872428954):
all three installed profiles' genuine proofs/reproducibility/negative controls and
recovery as UID1000 in clean Nix-free Debian12/Python with no checkout mounts and
network disabled, plus separate fresh verified HTTPS parameter controls. Existing
legacy profile pins remain unchanged. This is actual x86_64 execution, not ARM
emulation or flake evaluation. See the [exact checkpoint](evidence/private-installer-linux-x86_64-checkpoint.json)
for the successful workflow's assertions and retained artifact identity. Its local
full download timed out, so a local raw-archive audit is not inferred.

The [JSON3.1 Action](../.github/actions/zkir31-cache/README.md) wraps installed CLI
helpers with explicit restore/save phases. The final qualification workflow tests
the verified portable archive through that Action and retains small evidence and
large candidate/source artifacts separately. Consult PR22's exact run status for
that follow-up. No private release asset has been published or authenticated
release download qualified. The macOS no-Nix deferral remains unchanged.

The installer exposes primary `zkir-forge` and compatibility `midnight-zkir-forge`.
New release archives contain identical executable bytes for both; old schema1
legacy-only releases remain installable and keep both installed launchers usable
on rollback. Existing release archive names and managed installation paths stay
stable. An unrelated file at either launcher path refuses installation.


## Lightweight installer native candidate — 2026-10-19

A local macOS ARM64 archive from exact signed source
`45a72b3b6334687d22e3bfafe3fd3e64befd3dc6` passed the unchanged official
installer/checker with external Python and runtime reads of Nix/the checkout
denied. All three advertised profiles ran real reproducibility, valid-proof,
invalid-statement and corrupt-proof controls, plus the existing real recovery
checks. Independent review verified all 778 manifest file hashes, archive checksum,
worker/profile identities and retained source/parameter premises.

The initial copied Compact parameter set contained k5..17 and correctly refused
this fixture's missing k4. The exact-source Forge CLI fetched k4 through its
official verified provider in a private directory. The original archive was not
rebuilt, and the unchanged checker then passed. Original setup failure and a
metadata-only evidence-wrapper parsing error remain recorded; no assertion was
weakened. See [actual runtime receipt](evidence/binary-install-entrypoint-native-darwin.json)
and [asset/source identity](evidence/binary-install-entrypoint-native-darwin-assets.json).

This complements the shell entry point's separate offline fixture controls; the
real-payload checker invokes the packaged Python installer directly. It remains
a restricted-host experiment with fake GitHub transport, not a clean Nix-free
Mac, Linux, authenticated release download or Compact consumer acceptance. No
release asset was uploaded. A future tag must match the archive's exact source
commit; later documentation commits do not relabel its provenance.
