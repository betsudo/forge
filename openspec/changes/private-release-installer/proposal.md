# Private release installer

Status: proposed; specification only. Tracking: [issue #11](https://github.com/input-output-hk/midnight-zkir-forge/issues/11).

## Problem and outcome

A small group with read access to the private repository should install Forge
without cloning the source, compiling Rust or installing Nix. Distribute matched
CLI/worker/helper bundles through versioned GitHub Releases. Retain the existing
Nix installer for source development and reproducible build orchestration.

Use one explicit-version installer, GitHub CLI authentication and a verified
platform tarball. Install under a user-owned prefix; prepare and smoke-test before
switching the active release. Preserve the old release on failure, unrelated
commands, circuit caches, parameters and existing Nix GC roots.

## Scope

Target macOS and Linux on ARM64 and x86_64. Qualify and publish each target
individually on a Nix-free consumer environment; unqualified assets are unavailable,
not silently substituted. No Windows support is proposed. No promise that
an architecture in the development flake already has a portable release asset.

Include the main CLI, exact isolated v3 worker, CI helper, manifest, licensing and
checksums. Consumers need `gh` and Python 3.11+; Python supports the installer and
existing CI helper, avoiding a separate extraction/runtime dependency. There is
no anonymous private download or separate download-only repository permission.

## Non-goals and delivery boundary

No public repository/mirror, access grants, package-manager integration, automatic
updates, latest-version resolution, service installation, registry, new crypto
profile or Compact amendment. macOS signing/notarization is a later release
engineering decision; do not bypass OS security controls. No installer code,
release tag/upload, workflow dispatch, publication or current-install mutation
is authorized merely by this proposed spec. A release version remains undecided;
`vX.Y.Z` in examples is a placeholder, not an existing release.

Also document the existing flake as a directly referenceable, immutable pinned
installation/development option for authorized users who already use Nix.
