# Pinned Linux Nix material (issue #43)

The existing Linux installer workflow has an explicit material-only manual/reusable mode. It builds **public d64f52db7239b0ca4891fb0316dca6adb54a5db5**, exports original Forge/Rust/source Nix paths and attaches a three-day same-run artifact. It does not relocate binaries, supply SRS/keys or qualify Compact consumers. Default PR portable proofs/negative controls remain unchanged.

A reusable caller pins `.github/workflows/qualify-linux.yml` to an exact reviewed Forge toolkit commit and supplies that same immutable `producer-source` input. `material-only` defaults true for reusable calls. The exporter checks the actual Forge checkout SHA; it never interprets caller Compact `github.sha` as Forge source. Payload d64 and exporter toolkit source are distinct commitments. Calls return artifact ID/name/service digest, actual producer-attempt, payload source and system. Retain that producer attempt during partial consumer reruns; do not substitute the later caller attempt. Artifact run/repository belong to the caller, avoiding a cross-repository download credential.

## Consumer contract

1. Authenticate original GitHub run/head/attempt, expected caller repository/workflow and returned artifact ID/name/service SHA256; download from that same caller run. Check ZIP bytes against service digest before extraction. Colocated material.json is not its own authentication.
2. Safely extract, check every file size/hash in material.json, expected payload/exporter source, system and producer tuple. Require a complete NAR inventory. Refuse unknown, expired, mismatched or incomplete material without silent source-build/stale fallback.
3. Import `closure.nar` with Nix, recheck all imported NAR hashes against store-paths.json, exact root/derivation/source/Rust toolchain identities, and actual CLI/helper/worker hashes. Existing Compact independent fingerprint and derivation checks remain mandatory; profile output alone is insufficient.
4. Run actual current consumer proofs/assertions/negative controls with those imported paths. Material build success and original Forge installer qualification do not replace consumer acceptance.

The exporter caps both declared NAR size and actual export at **2GiB**; it refuses rather than omits Rust/source/runtime dependencies. This is a bounded per-artifact guard, not a global GitHub10GB quota. No actual current Linux closure size, transfer speed or benefit is claimed until the authorized producer runs. The export includes compiler/source roots required for independent qualification; it may exceed the cap and require an explicit measured budget decision.

Run focused pure tests via `./bootstrap.sh -- python3 scripts/test-build-nix-material.py`. No native payload is built by these tests. Manual dispatch builds the reviewed current exporter checkout; reusable callers must pass an immutable producer SHA. No release, registry, CDN, cache publication, macOS artifact or shared installation is introduced.

## Export lifetime

Pinned full flake source is explicitly materialized with `nix flake archive` and checked against original metadata before the long package build. Full source is officially registered with `nix-store --realise --add-root --indirect`; derivation build source, runtime output and independent Rust use Nix `--out-link` roots. Temporary roots stay outside the six-file artifact directory and survive through export/final guards, then are cleaned. No source root is omitted or fabricated.

`FORGE_TEST_PRIVATE_STORE=1 ./bootstrap.sh -- python3 scripts/test-build-nix-material.py` additionally exercises actual Nix GC only in an isolated test-owned local store: a registered source survives GC and is collected after its root is removed. This is a local root-lifetime regression, not proof the full Linux export now passes. The original failure established invalid full-source store path after build, but did not establish GC as cause (its log says automatic GC disabled); explicit materialization also addresses lazy fetcher metadata.
