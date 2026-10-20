# Forge RC and local compiler reuse (#11, #43)

## Owner direction — 2026-10-20

Own the representative benchmark in Forge, using Passport or midnight-did.
Deliver a versioned RC with downloadable Linux/macOS binaries and a standalone
`zkir-forge-installer.sh`. Integrate compatible material reuse smoothly into
`compactc`, compare the same local build with and without Forge, then consider
GitHub Actions optimization. Autonomous execution and RC tag/release/assets are
explicitly authorized. Preserve existing unrelated checkouts and installations.

## Success criteria

- Target more than 50% reduction in complete warm local build/test wall time
  versus the same ordinary uncached build/test command. Record cold population
  separately; do not substitute cold-Forge timing for the uncached baseline.
- Include source compilation, artifact acquisition/materialization and the same
  genuine proof/test assertions in each measured lane. Report setup separately.
- Bypass Forge for tiny circuits before cache acquisition. Start with `k <= 8`
  in the compiler policy, retain a configurable cutoff and test its boundary.
- Keep exact input/backend/tool/recipe/serialization/parameter identities,
  artifact integrity, verifier identity and uncached execution. Cache no proofs
  or test verdicts. A numerical miss remains a reported miss, not acceptance.

## Delivery order

1. Audit and reuse the existing Forge Passport benchmark and release machinery.
2. Prepare one coherent calendar RC, initially `v2026.10.0-rc.1`, from a signed
   source commit; binary, manifest, installer and tag versions must agree.
3. Qualify native Linux x86_64 and macOS ARM64 assets and their actual release
   download/install path. Advertise additional targets only with exact evidence.
4. Deliver the small optional compiler path with tiny-circuit bypass.
5. Run the Forge-owned representative local off/cold/warm/restored comparisons.
6. Use measured benefit, size and costs to decide later Actions/cache/CDN work.

The superseded Compact cache pilot is being stopped with its receipts preserved.
Its planned follow-up restore dispatch is deferred. Release build/qualification
jobs in Forge remain in scope where a native Linux executor is required.
