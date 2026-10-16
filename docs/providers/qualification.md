# Local and Fetch provider qualification

Tracking: betsudo/forge #4. This delivers an isolated qualification harness, not
a new production HTTP provider endpoint. Cloudflare remains deferred.

## What is qualified

Pinned official packages:

- `@midnight-ntwrk/midnight-js-node-zk-config-provider` 5.0.0-rc.2.
- `@midnight-ntwrk/midnight-js-fetch-zk-config-provider` 5.0.0-rc.2.
- `@midnight-ntwrk/compact-runtime` 0.20.0, plus exact transitive package lock.

The native macOS ARM64 fixture uses the already recorded official Compact0.35.0
compiler/backend executable hashes. It compiles a real counter-increment circuit
normally, compares original compiler binary IR/prover/verifier bytes to Forge's
cold/warm JSON3.1 artifacts, and copies only byte-identical private artifacts into
the owned compiler output. Original compiler manifest and contract-info bytes
are retained. No compiler provenance is fabricated or integrity disabled.

Actual SDK providers retrieve the artifacts in four independent lanes: local,
HTTP, gzip HTTP and authenticated HTTP. Every lane performs fresh contract
execution, checks counter0->1 and one call-proof trace, then makes a genuine
native proof using **the bytes returned by that provider**. Each proof is
verified, and invalid-statement/corrupt-proof controls run. No proof result or
preimage is cached. Four proofs/four verifications/eight proof negative controls
and twelve state/trace assertions execute per complete qualification run.

Thirteen additional provider/HTTP controls cover bare export metadata/runtime
refusal, wrong local/fetch manifest anchors, corrupt local/fetch prover keys,
missing fetched manifest, HTML fallback, missing authentication, unsafe local/
fetch circuit names, HEAD length and conditional ETag. The fixture authenticates
private reads before byte lookup and never logs headers/tokens.

Exact local receipt: [provider-sdk-local.json](../evidence/provider-sdk-local.json).
Package lock and harness hashes identify the exact tested producer/consumer code;
this receipt is not a Linux, full Passport, browser, TLS/CDN or production claim.

## Preserve compiler integrity

The SDK providers default to requiring compiler integrity metadata. A bare
Forge `export.base` contains source/key material and Forge metadata, but it is
**not sufficient** for this SDK version's default provider contract.
Serve the full qualified compiler bundle, for example:

```text
BUNDLE/
  compiler/contract-manifest.json   # original compiler bytes
  compiler/contract-info.json      # original compiler runtime/provenance
  contract/...                    # normal compiled contract output
  zkir/increment.zkir
  zkir/increment.bzkir
  keys/increment.prover
  keys/increment.verifier
```

Use the official compiler's ordinary manifest step after generating/reusing keys,
not a blanket post-compile insertion. See [the compiler boundary contract](../compiler/key-cache-contract.md).
The qualification may substitute an already listed key only after proving exact
byte equality. It cannot add a missing manifest entry or change the manifest.

For an already qualified bundle, SDK usage is:

```js
new NodeZkConfigProvider(bundleDirectory, { expectedManifestHash });
new FetchZkConfigProvider(immutableBaseUrl, { expectedManifestHash });
```

Supply the manifest digest independently from the application/build pipeline;
fetching a manifest and its keys from one untrusted server only establishes
internal consistency. Exact backend/worker/parameter/compiler compatibility
requires its own qualification policy. Do not use `verify: 'off'` to make a
bare export work or replace compiler metadata with Forge's descriptor.

## Reproduce locally

Run inside this checkout. Supply a trusted official native compiler directory
and an already verified parameter directory; the harness intentionally refuses
an unqualified platform/compiler. It does not download compilers or parameters,
modify the shared installed CLI, or mutate another checkout.

```sh
./bootstrap.sh -- npm ci --prefix integration/providers --ignore-scripts --no-audit --no-fund
./bootstrap.sh -- nix build .#default --no-link --print-out-paths
# Use the printed package's absolute CLI path:
./bootstrap.sh -- python3 scripts/check-providers.py \
  --binary /nix/store/PRINTED-PACKAGE/bin/zkir-forge \
  --compiler-dir /absolute/qualified/compact-0.35.0 \
  --params-dir /absolute/verified/parameters \
  --output /absolute/new-receipt.json
```

The test fixture is in `integration/providers/fixtures/provider.compact`. The
HTTP server in `integration/providers/check.mjs` is an allowlisted loopback test
fixture and exits with the harness. It does not expose the default cache. Temporary
stores, private key copies, preimages and proof inputs are removed; only explicit
receipts and pinned test dependencies remain. Real proof tests are opt-in and are
not silently added as a network/dependency-heavy default CI requirement.

## Remaining issue #4 gates

- A production Forge provider-view endpoint with immutable publication semantics,
  independent policy and bounded authenticated serving; current management/CAS
  routes are not that API.
- Real browser/CORS and HTTPS/CDN retrieval and gzip/Brotli/range qualification;
  Node loopback HTTP fixture headers alone do not establish them.
- Exact native Linux Compact/Passport consumer qualification (#5), followed by
  a simple compiler-facing local adapter (#6) and consumer-path recovery (#7).

The proposed compiler flag is not implemented by this harness. Existing Compact
and consumer checkouts, official Rust/backend pins and default cache behavior
remain unchanged. No hosted service, transaction support or speedup is claimed.
