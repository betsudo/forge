# Initial HTTP transport

The CLI, HTTP adapter and official backends share the existing application/CAS/
SQLite implementation. This is a single-owner service, not a public registry.
The exact initial API is [OpenAPI](openapi.json); the larger product `SPEC.md`
remains proposed wherever this subset does not implement it.

## Run locally

```sh
./bootstrap.sh -- cargo build --locked --manifest-path workers/zkir3/Cargo.toml --target-dir target
./bootstrap.sh -- cargo build --locked
./bootstrap.sh -- target/debug/zkir-forge serve
```

Default listener is `127.0.0.1:8787`; the default cache remains
`~/.midnight-zkir-forge`. Global `--cache-dir`, `--params-dir`, `--profile` and
`--fetch-params` apply to the service. Parameter retrieval stays offline unless
explicitly enabled. Use a private temporary cache for experiments.

For a non-loopback bind, provide `serve --listen 0.0.0.0:8787 --token-file PATH`.
The file must contain at least 32 printable ASCII characters without internal
whitespace (a final newline is allowed). Keep it private. When configured,
`Authorization: Bearer TOKEN` protects every endpoint except `/health/live`,
including readiness, docs and artifact reads. No token values are logged. This
is one shared owner credential, with no namespace ACLs, TLS or public exposure
policy. Put remote use behind a trusted TLS boundary. No CORS is enabled;
POST requires `Content-Type: application/json` even when the body is empty.

## Register, materialize, fetch

The following example assumes the default loopback server without a token.
Use the exact consumer profile. The v3 selector supports only official ledger
`3a7ae0361d03e6eed4fc91e31f6600f334f605d5`, JSON3.0 and
`ir-source[v3-generic]`. JSON3.1 uses the distinct `zkir31` selector, official
ZKIR `e82d81d25aabcc5f5092e2bd559083487f577914` with ledger
`9a8777c4d035fc7f38ae286bcf5f8656668efd9f` and verifier-key[v7].
These profiles are not interchangeable; inspect `/v1/profiles` on the actual server.
Ledger9 transaction/network support remains deferred.

```sh
curl --fail-with-body -H 'Content-Type: application/json' \
  --data-binary @fixtures/assert.zkir \
  'http://127.0.0.1:8787/v1/bundles?name=assert&profile=ledger8-v2'
# Read bundle_id from that JSON, then:
curl --fail-with-body -X POST -H 'Content-Type: application/json' \
  "http://127.0.0.1:8787/v1/bundles/$BUNDLE_ID/materializations?profile=ledger8-v2"
# Fetch each origin-relative artifacts[].url from the materialization response.
```

Upload is **raw exact single-circuit JSON**, maximum16MiB. It does not accept
archives, manifests or server-local paths. Names allow ASCII letters, digits,
underscore and hyphen. Import is lazy. Repeating a materialization returns a
verified hit and the same pinned identity. Responses contain HTTP URLs/digests,
not server paths. GET source, objects and inventory never trigger generation.

Materialization is synchronous200; no202/job polling/cancellation promise is
implemented. One HTTP materializer is admitted at a time. SQLite also serializes
CLI/HTTP writers across processes. Busy HTTP admission returns429 with
`Retry-After: 1`. Blocking storage and crypto run off HTTP executor threads.
Two uploads can buffer at most16MiB each, with a30s body deadline; eight work
operations and eight streaming downloads are admitted. These are admission
bounds, not a strict CPU/memory sandbox or a complete idle-connection policy.
A disconnected request may finish admitted generation safely. SIGINT/SIGTERM
wait for admitted work; forced termination retains existing transaction recovery.

Objects are hash-verified before streaming or returning304, using the same
opened descriptor under the store transaction. GET/HEAD provide strong digest
ETags, exact lengths, private immutable caching and `Accept-Ranges: bytes`.
Single byte ranges, suffix ranges, If-Range and If-None-Match are supported;
multiple/unsatisfiable ranges return416. HEAD describes the full representation.
A download already holding its descriptor may finish after CLI eviction; a
subsequent evicted object lookup returns404. Corruption returns409, never new
bytes under an existing identity.

`GET /v1/stats` includes logical artifact request counts, generation/hit timings
and estimated avoided generation. Download/HEAD/conditional requests count as
logical artifact hits, not disk-read or proof-success measurements. Requested
local paths are removed from HTTP stats. Metadata requests use no-store;
verified immutable object responses use private immutable caching. Errors expose
stable codes, not underlying filesystem diagnostics. `/health/ready` checks
storage/backend availability; it does not guarantee all parameter sizes exist.

## Validate

```sh
./bootstrap.sh --check
./bootstrap.sh -- python3 scripts/check-http.py --binary target/debug/zkir-forge
# Explicit real key generation/proof coverage; verified parameters must exist:
./bootstrap.sh -- cargo build --locked --example qualify-http-fixture
./bootstrap.sh -- python3 scripts/check-http.py --binary target/debug/zkir-forge --real
```

The fast suite starts a real authenticated process and checks upload/source
roundtrip, metadata, auth, path refusal, HEAD/ETag/ranges, corruption and SQLite
contention/admission while liveness remains responsive. Real mode adds cold/warm
materializations and downloaded artifact digests for both profiles, real proof/negative controls for both profiles using **downloaded
warm artifacts**. Consumer proofs, verification and assertions still run.
The existing Rust real-backend tests remain the independent uncached controls.

`--url BASE --token-file PATH` targets an externally supplied **isolated** test
server for container smoke checks. It skips private-CAS corruption and direct
SQLite contention; do not point this mutating test at a shared service.

Archives, durable jobs, namespaces, GC, TLS, resumable upload,
public rate policy and full JS provider qualification remain future slices.
See [container setup](../../container/README.md) and [CI notes](../../container/CI.md).

See [API conventions and Midnight provider terminology](../api-conventions.md) for the
CLI stdin/stdout boundary, HTTP payload conventions and local/fetch provider roles.

## Verified compiler provider views

An explicit `--provider-root` enables GET/HEAD `/views/{manifest_sha256}/{file}`.
Publish complete compiler output locally with `publish-view`; the caller must
supply the independently trusted SHA256 of its original compiler manifest.
The service validates all inventory and metadata before conditional/range reads,
never generates keys on reads, and preserves authentication before lookup.
Views are separate from cache exports and snapshots. See the
[local adapter guide](../providers/local-adapter.md) and
[metadata guarantee research](../research/compiler-metadata-guarantees.md).
This initial route supports identity bytes and safe two-component paths.
