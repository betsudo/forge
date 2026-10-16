# Linux portable runtime

The Linux release producer builds the exact clean source commit through the
existing pinned Nix flake. It relocates the resulting CLI and official isolated
workers; it does not rebuild cryptography with a different distribution toolchain.

Linux cannot use a relative ELF interpreter path. The public commands are small
Python launchers that execute a bundled ELF loader with an explicit relative
library directory and the loader cache disabled. Python 3.11+ is already an
installer prerequisite. The real executables and their transitive dynamic
libraries are regular files under `lib/`. Build RPATHs are removed, absolute
`DT_NEEDED` entries are refused, and the bundled loader's dependency listing must
contain no `/nix/store` resolution. The Nix store is a build dependency only.

Both launchers embed the SHA-256 of every bundled runtime file. Every invocation
verifies those files before executing the loader. The existing worker executable
digest therefore commits to its worker ELF, loader and shared libraries, rather
than hashing a constant wrapper that could conceal a changed runtime. Explicit
worker overrides remain explicit; otherwise the CLI launcher selects its paired
worker beside it. Modifying a library requires updating the launcher commitment
and treating it as a different compatibility identity. These checks do not replace
the installer's full archive/manifest verification or prohibit rebuilding Forge.

Once consumer Python starts, launchers refuse inherited `LD_*` and
`GLIBC_TUNABLES` variables before executing bundled Forge binaries. Consumer Python
and its own operating-system loader are trusted prerequisites: they start before
the Python launcher checks. For example, `LD_TRACE_LOADED_OBJECTS=1` can make the
host loader print Python's dependencies and exit without running the launcher.
This is not a mechanism for isolating an adversarial process environment; use a
clean trusted environment when invoking the installer or commands.

`scripts/check-linux-runtime.py runtime --root /path/to/relocated/bundle` checks
ordinary startup, empty/nonempty override refusal and this pre-Python boundary.
Its `sources` mode evaluates the pinned Nix outputs, checks original library
digests and refuses a same-name library from another store output. Both modes
emit JSON and leave the supplied bundle unchanged.

The initial Linux consumer baseline is Debian12 with glibc2.36, Python3.11 and the
measured Linux kernel from its qualification receipt. glibc itself is bundled;
the producer Python's glibc version is not used to invent a consumer requirement.
Older systems, other architectures and additional kernel baselines need separate
runtime qualification. Containers test actual Linux execution with no Nix store,
build checkout or Rust toolchain; host architecture/emulation must be recorded.
The supported target list must follow the receipts rather than output evaluation.

Parameter fetching uses the consumer's CA certificates. If `SSL_CERT_FILE` is not
already configured, launchers select an existing standard Debian/Fedora CA bundle.
They do not download certificates, change trust policy or bypass TLS verification.
Offline real-proof checks alone do not qualify DNS/TLS parameter fetching.

## Runtime notices and corresponding sources

`scripts/linux-runtime-sources.py` obtains the exact glibc, GCC and OpenSSL sources
from the locked Nixpkgs graph. The binary carries their license texts, selected
patch/source identities, source-access instructions and a companion asset digest.
Every bundled library's original Nix output is mapped to one of those exact
packages; an unknown runtime dependency refuses packaging until its sources and
notices are included.
The producer also prepares `*-runtime-sources.tar.gz` containing:

- Full unmodified upstream archives and their SHA-256 identities.
- The complete locked Nixpkgs source, including recipes, imports and patches.
- A Git bundle of the exact Forge source commit and history.
- Rebuild instructions and instructions for using modified dynamic libraries.

The source companion and checksum must be published beside the corresponding
binary asset when release publication is authorized. Preparing it locally does
not publish it. It is a separate download so each binary installation need not
download compiler sources. No time-limited written source offer is substituted.

glibc has LGPL terms and per-file notices; GCC runtime libraries include the GCC
Runtime Library Exception, whose Eligible Compilation Process conditions must be
reviewed against the actual toolchain. OpenSSL carries Apache2.0 terms. Retain
the full license texts and sources rather than claiming compliance from package
metadata alone. Common Cargo dependencies and other platforms' runtime libraries
are audited separately.
