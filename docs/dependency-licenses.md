# Portable bundle dependency notices

`scripts/cargo-notices.py` preserves original Cargo dependency and Rust standard
library license/copyright notices in each native release bundle. The release
producer calls:

```python
inventory = cargo_notices.collect(
    bundle_root, nix_executable, flake_ref, repository_path, full_source_commit
)
```

`flake_ref` must be exactly
`git+file://<absolute-repository-path>?rev=<full-source-commit>`. The collector
extracts that tracked Git commit into temporary storage and runs its Nix-owned
Cargo with `--locked`. It reads the root, JSON 3.0 worker and JSON 3.1 worker
manifests and their separate lockfiles. No Rust compilation is required.
Temporary source storage is removed on completion or failure.

The collector determines the native target from the selected Nix Rust toolchain,
then calls `cargo metadata --filter-platform <target>`. It traverses the resolved
dependency graph from each workspace member. This conservatively includes
build and development dependencies: it is an attribution superset, not a claim
that every listed package contributes machine code to the installed executables.
Foreign-target dependencies outside that resolved graph are not attributed.
Feature-specific additions must be covered if the release build changes its
Cargo feature selection; the current producer uses the same default features.

The distribution contains:

- `LICENSES/cargo-inventory.json`: source commit, native target, Rust version,
  package versions/sources, graph membership, declared license expressions,
  registry archive checksums, Git revisions and notice file hashes.
- `LICENSES/cargo/<package-version-source>/`: original license, COPYING,
  copyright and NOTICE files, including nested notices for bundled native code.
  The inventory retains original relative paths when files are flattened.
- `LICENSES/rust-standard-library/`: `COPYRIGHT-library.html` and the upstream
  license texts shipped with the exact Nix Rust toolchain, covering its bundled
  standard library. The compiler itself is not redistributed in the CLI bundle.
- `LICENSES/NOTICE`: a short map to those inventories and the separate native
  shared-library attribution/source materials.

Registry notice bytes come from the original `.crate` archive after SHA256
verification against the exact Cargo.lock entry, rather than mutable extracted
Cargo cache files. Git dependency notices come from `git show` at the full
resolved revision; ancestor workspace notices are included for packages that
inherit licensing from a workspace root. The Forge source comes from the exact
release commit. This collector does not modify dependency sources.

Copyright or NOTICE files alone do not satisfy the license-text requirement.
The collector retains those attribution files and requires a license/ COPYING/
UNLICENSE file, an explicit Cargo `license_file`, or a reviewed supplement.
Root-level Git packages include nested vendor license and NOTICE files.

Some published crates omit their license files. The script contains an explicit
reviewed supplement table for the currently pinned macOS/Linux graph:
`blake2b_simd`, `blst`, `halo2derive`, `objc2`/`dispatch2` and their macOS framework
crates. Supplement URLs use a full immutable upstream commit and a pinned SHA256;
that commit must match `.cargo_vcs_info.json` inside the authenticated crate
archive and the repository must match Cargo metadata. Both dual-license texts
are retained where upstream provides them. There is no branch-name lookup,
fallback license substitution or inferred copyright notice.

Packaging fails when a selected package lacks a licensing declaration, has no
notice files or audited supplement, has a mismatched source revision/archive
checksum, or has a supplement content hash mismatch. A changed dependency graph
may therefore require updating this audited table before packaging succeeds.

The notice inventory supports distribution review; its existence alone does not
prove that every license obligation has been satisfied. Preserve all original
notices and expressions when redistributing. Native runtime libraries have
separate source/relinking requirements: Linux runtime packaging documents its
corresponding-source companion in `linux-runtime-packaging.md`, and macOS bundled
dylibs require their own attribution/source inventory. Platform SDK libraries
provided by the consumer OS are not silently copied into this Cargo inventory.
Review those records alongside the exact bundle manifest before publication.

Local qualification of the collector used all three locked macOS ARM64 graphs:
422 unique package/source identities, including conservative build/dev coverage,
with authenticated archives, pinned supplements and the Rust 1.98.1 standard
library notices. This exploratory check is not a final release-commit receipt;
the producer must run the collector again for each exact candidate commit and
platform. Linux receives its own native-target graph, not a copied macOS list.

The bounded offline regression suite is reproducible with the Nix-owned Python:

```sh
./bootstrap.sh -- python3 scripts/check-cargo-notices.py \
  --output .local/qualification/licenses/cargo-notices-regression.json
```

It checks unknown supplements, mismatched VCS revisions, tampered archive and
supplement bytes, NOTICE-only refusal/supplement behavior, explicit custom
license files and nested vendor notices for repository-root Git packages.
A network guard rejects unexpected requests; no build, Git commit or cache
mutation is needed. The receipt binds its results to the collector SHA256.
