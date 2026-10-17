# Complete compiler views with an explicit storage budget

Tracking: [#31](https://github.com/betsudo/forge/issues/31). Keep the original
compiler manifest and every declared file. A source-only or selected-circuit
directory is not the full compiler bundle.

The default aggregate limit is **4 GiB**, including the original manifest,
runtime metadata, source ZKIR, binary ZKIR and all prover/verifier keys. Operators
can explicitly set `--provider-max-view-bytes` on `publish-view`, `verify-view`
and `serve`. Accepted values are integer bytes from 1 through **64 GiB**. This
does not increase the fixed 1 GiB per-file, 4 MiB metadata or 4096-file limits.

For the unchanged Passport account, use a 16 GiB budget at each entrypoint:

```sh
zkir-forge publish-view /absolute/compiler-output \
  --manifest-sha256 INDEPENDENT_ORIGINAL_MANIFEST_SHA256 \
  --provider-root /absolute/owned-provider-views \
  --provider-max-view-bytes 17179869184

zkir-forge verify-view /absolute/owned-provider-views/MANIFEST_SHA256 \
  --manifest-sha256 INDEPENDENT_ORIGINAL_MANIFEST_SHA256 \
  --provider-max-view-bytes 17179869184

zkir-forge --cache-dir /absolute/separate-private-cache serve \
  --provider-root /absolute/owned-provider-views \
  --provider-max-view-bytes 17179869184 --token-file /absolute/private-token
```

Do not copy the placeholder digest literally. Pin the exact compiler manifest
independently and pass it to the official SDK's `expectedManifestHash` option.
The CLI emits `provider_limit` on a configured/per-file budget refusal; stderr
identifies required/configured bytes and the option. HTTP returns the same code
with status 500 on reads: the serving budget is a server configuration failure.
Invalid request paths/IDs remain 400. Neither path authorizes availability fallback. Serving an
already published large view also requires the explicit serving budget.

Before a new copy, Forge checks destination filesystem space for the full
declared size plus 64 MiB reserve. Insufficient headroom produces
`provider_storage_unavailable` (HTTP mapping 507), without availability fallback
or automatic retry. Use one publisher per provider root. This check cannot
reserve space against another process.
Later copy/disk failures still cannot publish partial content. Reuse performs a
complete audit of the existing view and does not allocate another full copy.

Publication syncs private staging and uses atomic no-replace rename. A killed
publisher may leave `.provider-stage-*` directories, which are not addressable
view identities. Inspect and remove only stages belonging to your interrupted
operation after all publishers have stopped; Forge does not delete them on behalf
of another writer. Retry publishes a fresh complete copy. Existing damaged views
refuse reuse; identity does not silently change.

HTTP retains two active verification/stream snapshots, eight finite waiters and
a ten-second admission timeout. The fixed file cap bounds active temporary
snapshot content to 2 GiB, in addition to persistent views and the caller's
original compiler output. Every requested file is fully verified before HEAD,
ETag and range handling. Increasing aggregate storage does not alter this rule.

Local qualification uses `scripts/qualify-passport-provider.py` against a complete
213-file official output, an independently pinned original manifest and exact
official workers. It tests real interruption/retry, default refusal, authenticated
parallel Fetch retrieval, real selected application proofs and corruption before
conditional/range handling. Response payload bytes exclude HTTP headers/TLS;
measurement clones responses and is not a latency benchmark. Native Linux and
hosted CI require their own receipts. See [Passport local setup](passport-local.md)
and the latest progress entry for actual execution status.

The [native macOS ARM64 receipt](../evidence/passport-full-provider-local.json)
records a complete 213-file, 12,184,494,074-byte view under an explicit 16 GiB
budget. All files passed the final audit. Two selected application circuits ran
through both Node and Fetch providers, then Node again after exact-byte repair:
6 fresh proofs, 6 verifications, 12 negative proof controls and 54 assertions.
Interruption left no published partial view; retry succeeded. Damaged HTTP
artifacts refused HEAD/range/conditional requests, and damaged compiler output
failed the SDK integrity check before owner repair.

Publication took 91.72 seconds on the shared developer host; selected Fetch
requests transferred 25,140,103 identity payload bytes. Neither number is a
hosted transport benchmark. The largest file was 495,024,744 bytes, bounding two
simultaneous snapshots for this bundle at 990,049,488 bytes. The unchanged global
bound remains 2 GiB. The [reference provenance](../evidence/passport-full-provider-reference.json)
pins the fresh original manifest independently. Its source map differs from the
historical run because the compiler records the output path; artifact entries
match. Historical manifests and receipts were not rewritten.
