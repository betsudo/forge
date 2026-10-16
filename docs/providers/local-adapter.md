# Compiler adapter and immutable provider views

Use `scripts/compiler-local.py` through `./bootstrap.sh -- python3`.
It is a Forge-owned wrapper around the actual compiler, not an upstream Compact
flag. `--mode off` is the default and uses native key generation. Initial local
support is limited to independently qualified Compact0.35.0 JSON3.1 sources.

```sh
./bootstrap.sh -- python3 scripts/compiler-local.py \
  --mode local --compiler-dir /absolute/compiler \
  --binary /absolute/package/bin/zkir-forge \
  --qualification /absolute/qualification.json \
  --qualification-sha256 TRUSTED_RECEIPT_SHA256 \
  --params-dir /absolute/parameters --cache-dir /absolute/private-cache \
  /absolute/source.compact /absolute/output
```

Use canonical absolute paths without symlink ancestors or apostrophes. Keep the
output separate from source, qualification, tools, parameters and cache. The
compiler owns and may clear its output directory. Unknown circuits, changed tools,
parameters, descriptors or artifacts refuse local mode; use explicit off mode
or obtain a new reviewed qualification. Never edit an old receipt to bless a new
executable. Qualification currently covers the minimal fixture, not arbitrary
Passport contracts. Output copies are private; test proofs and assertions still run.
A failed copy can leave incomplete output, but the wrapper refuses success and
the compiler does not finish its manifest; retry compilation in owned output.

Publish a complete successful compiler output with its independently pinned hash:

```sh
zkir-forge publish-view /absolute/output \
  --manifest-sha256 TRUSTED_MANIFEST_SHA256 --provider-root /absolute/views
zkir-forge serve --provider-root /absolute/views \
  --listen 127.0.0.1:8787 --token-file /absolute/private-token
```

`FetchZkConfigProvider('http://127.0.0.1:8787/views/MANIFEST_SHA256',
{expectedManifestHash: MANIFEST_SHA256, fetchFunc: authenticatedFetch})` consumes
this view with default integrity checks. `NodeZkConfigProvider` can consume the
published local directory with the same pin. Authentication is mandatory for
non-loopback binding; use a token locally too. Paths are immutable identities,
not mutable aliases. Cache operations and snapshots do not include provider views.
The view root must not overlap the cache or compiler input. No GET triggers keygen.

See [the metadata guarantee research](../research/compiler-metadata-guarantees.md)
for trust boundaries, inventory bounds and exact source evidence. HTTP serves
identity bytes; gzip test-fixture qualification does not establish compressed
Forge HTTP support. Cloudflare and browser/TLS delivery remain deferred.

Every view request currently verifies the whole bundle and copies the requested
file to a temporary descriptor. This favors simple corruption detection over read
throughput; measure large bundles before using this endpoint in CI. Authentication
and admission limits apply, but this is not a public multi-tenant service.

For maintainers, reproduce the bounded real qualification locally (requires the
exact official native macOS ARM64 compiler, verified parameters and pinned npm
project dependencies already installed):

```sh
./bootstrap.sh -- python3 scripts/check-provider-view-adapter.py \
  --binary /absolute/package/bin/zkir-forge \
  --compiler-dir /absolute/compiler --params-dir /absolute/parameters \
  --output /absolute/new-receipt.json
```

The harness creates private temporary stores, runs fresh official/Forge SDK proof
qualification, then off/cold/warm compiler and actual provider-view tests. The
receipt is written only after all controls pass and scratch cleanup completes.
Review it before pinning its hash in a consumer; generating a receipt alone does
not establish an independent trusted publisher.
