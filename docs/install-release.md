# Private release installation and pinned Nix use

The installer and candidate builder are local implementation work. **No downloadable
Forge binary release is published by this increment.** A supported target is not
qualified merely because the script recognizes its name. macOS/Linux ARM64/x86_64
are the target matrix; clean-runtime qualification is tracked separately per target.

## Nix users: use the existing package directly

Authorized users can pin this private repository without cloning a working tree.
The default package includes CLI, exact v3 worker and CI helper:

```sh
nix profile install 'git+ssh://git@github.com/input-output-hk/midnight-zkir-forge?rev=5d9c4c62b8c59b4a2939943b762032ff9f390be8'
# Or use a temporary shell:
nix shell 'git+ssh://git@github.com/input-output-hk/midnight-zkir-forge?rev=5d9c4c62b8c59b4a2939943b762032ff9f390be8'
```

That is an existing published source commit, not the unpushed installer increment.
Its Nixpkgs input no longer evaluates for Intel macOS; use the corrected pin below
after its publication, or a local Git input on this machine.
Replace it with a reviewed full commit when adopting later changes. Native systems:
`aarch64-darwin`, `x86_64-darwin`, `aarch64-linux`, `x86_64-linux`. Native validation
and actual runtime support are reported in progress/evidence, not inferred from
flake evaluation alone. Authentication requires GitHub SSH read access; `gh auth
login` by itself does not configure SSH. Do not put tokens in flake URLs or files.

[examples/nix/flake.nix](../examples/nix/flake.nix) pins reviewed local commit
`6c6490d25ff83366ee09ba5056f4c4638bc1ad85`, including the Intel macOS correction and isolated JSON3.1 worker. It
is not published yet: remote readers cannot fetch it until publication is separately
authorized. On this machine use a `git+file://` input for this checkout with the
same full revision. Keep its generated `flake.lock` in the consumer repository;
Nix itself is required. No consumer/Compact checkout is modified here.

## Binary users: intended flow once qualified assets exist

Install `gh` and Python 3.11+, authenticate with `gh auth login`, and obtain read
access to this private repository. Read permission also exposes source code;
release download is not a separate download-only permission.

Download `install-release.py` and `SHA256SUMS` from one explicit release into a
fresh scratch directory with `gh release download TAG --repo
input-output-hk/midnight-zkir-forge --pattern install-release.py --pattern
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
  --directory .local/release-candidate-2026.10.0 \
  --runtime-python /opt/homebrew/bin/python3 --deny-nix
```

The macOS restricted-runtime experiment copies the candidate/installer to private
scratch, uses fake gh only for the local download boundary, denies `/nix` and the
checkout to the installer and installed commands, and runs both genuine backend
qualifications. Choose an installed Python 3.11+ outside Nix. This does not replace
an actual clean no-Nix host, Linux execution, or authenticated GitHub download test.
Omit `--deny-nix` only when deliberately recording an ordinary native candidate
experiment; its receipt reports whether Python itself comes from Nix.

Intel macOS selects separately locked official `nixpkgs-26.05-darwin`; ARM macOS
and Linux retain the original package set. The example follows both inputs and
selects by system. All four derivations evaluate; Intel runtime is unqualified.
Upstream identifies 26.05 as the final Intel macOS Nixpkgs release, so continued
future support needs an explicit reviewed strategy rather than a floating pin.
