# Forge Proof Relay: proposed exact proof-response reuse

Status: research and proposed scope, 2026-10-16. No relay implementation or performance result is claimed. **Forge Proof Relay** names the optional component: an ordinary proof-server endpoint forwards misses and can reuse a previously verified response. The existing Forge artifact cache remains independently useful and unchanged.

## What the official protocol actually carries

The pinned ledger8 server accepts `POST /prove` as tagged binary serialization of `(ProofPreimageVersioned, Option<ProvingKeyMaterial>, Option<Fr>)`, returning a tagged `ProofVersioned`. The third field can overwrite the binding input. `POST /check` takes a different tuple and returns check results; `/prove-tx` is deprecated in this source. These are binary operations, not JSON witnesses or a filename API. See the [exact endpoint source](https://github.com/midnightntwrk/midnight-ledger/blob/b5d3e965a18e4cac17fac4f38446fc55c524439a/proof-server/src/endpoints.rs).

The same server uses `OsRng` for proving. Identical input need not produce identical proof bytes. Reusing one valid response is a different mode from independently sampling a fresh proof; callers requiring fresh randomness, unlinkability or proof-generation coverage must bypass reuse. Experimental feature flags also change accepted IR families: successful parsing of JSON3 alone says nothing about the server's proving capabilities. See [versioned proving dispatch](https://github.com/midnightntwrk/midnight-ledger/blob/b5d3e965a18e4cac17fac4f38446fc55c524439a/proof-server/src/versioned_ir.rs).

At Midnight.js revision `d1d32aaa24386fce97f653732f8a87c55eb938fe`, `httpClientProvingProvider` builds binary payloads with `createCheckPayload` / `createProvingPayload`, posts `application/octet-stream` to `/check` / `/prove`, and parses responses through the ledger runtime. `httpClientProofProvider` is the higher transaction-level `ProofProvider`; `ZKConfigProvider` supplies artifacts. Preserve these distinct names. The client also resolves protocol builtins without caller-supplied key material, so hashing only transmitted keys is insufficient. See the [pinned client](https://github.com/midnightntwrk/midnight-js/blob/d1d32aaa24386fce97f653732f8a87c55eb938fe/packages/http-client-proof-provider/src/http-client-proving-provider.ts) and [provider architecture](https://github.com/midnightntwrk/midnight-js/blob/d1d32aaa24386fce97f653732f8a87c55eb938fe/packages/http-client-proof-provider/src/index.ts).

Official guidance keeps proof servers local because they receive witness material. A relay inherits that exposure. See [Midnight deployment guidance](https://docs.midnight.network/guides/deploy-and-operate).

## Proposed identity and admission

Use exact request bytes, not “similar” contracts, inputs or witnesses. Do not normalize binary payloads or strip binding inputs, randomness, commitments, network/domain data or unknown extension bytes to improve hit rates. Conservative misses are acceptable.

Proposed domain-separated identity:

```text
H("midnight-zkir-forge/proof-response/v1",
  namespace_id, protocol_adapter_id, method, exact_endpoint,
  HMAC-SHA256(local_secret, exact_decoded_HTTP_entity_bytes),
  upstream_generation_identity, resolved_dependency_manifest_digest)
```

The configuration manifest pins the actual proof-server executable/image digest, official source revision, features, ledger/proof/serialization family, actual parameter digests and resolved builtin IR/prover/verifier inventory. Caller-supplied key material is already in the request digest; a qualified decoder additionally checks its association with the expected verifier/statement. An upstream URL or `/version` string is not a generation identity. Mutable resolver locations must be resolved to immutable bytes first. If complete premises cannot be established, transparently forward without cache admission. Network/domain settings outside the payload belong in the pinned context. Changing credentials/tenant policy must isolate namespaces; secrets never become public cache keys.

Do not implement arbitrary protocol decoding in the HTTP frontend. A small separately pinned adapter/worker must validate request framing, supported operation and the exact response's verification against its statement and verifier. A byte hash only detects disk corruption; it does not establish proof validity. If a supported server response cannot be independently verified by the chosen official APIs, initial implementation must remain pass-through for that profile. Document that gate before offering reuse.

## Forwarding and storage contract

- Disabled by default; separate command/configuration and store from artifacts. Start on loopback, one configured upstream and one bounded in-flight operation. No arbitrary per-request destination or hosted shared witness cache.
- Cache only successful `/prove` responses that pass the qualified verifier. `/check` always executes upstream; it is a check result, not reusable proof material. `/version`, readiness and other known support routes are live pass-through; report relay health separately. Do not cache `/prove-tx`, errors, timeouts or malformed/truncated responses.
- Preserve original binary request and successful response bytes. Qualified adapter specifies supported content encodings and relevant headers; first version accepts identity encoding only. Bound request/response sizes, deadlines, disk use and upstream concurrency. Do not automatically retry expensive POST requests: a timeout can occur after upstream generation.
- Store response bytes plus request digest/context and verified provenance using atomic publication; verify stored hashes and reverify the proof before every hit. Corruption fails explicitly, never masquerades as a hit or silent fallback. A miss forwards unchanged and admits only a complete verified response. Crashes leave no visible partial response; writer lock releases on death.
- No request-body persistence by default, no witness/body logs, restrictive owner-only directories and files. Digest-only metadata can still enable equality/dictionary inference; require a local HMAC-SHA256 request digest with a stable secret stored outside snapshots. Losing/rotating that key deliberately misses old entries. TTL/byte budget, explicit purge and namespace isolation are required. Do not upload relay stores into GitHub caches or CDN. Encryption and remote multi-tenant operation remain separate designs.
- Expose aggregate hits, misses, bypasses, upstream calls/time, verification time, bytes and evictions without witness/key-location labels. “Avoided proving time” is an estimate from comparable cold requests, not a measured warm proof-generation event.

## Tests and decision gates

Local fixtures must exercise exact cold → warm reuse, a real proof verifier on both paths, and a byte-identical forwarded miss. Independently vary witness, public input, binding override, circuit/key bytes, parameters, backend/features, builtin resolver revision and namespace; every change must miss or refuse. Include corrupt cached response, invalid upstream proof, truncated/error response, cancellation/crash, disk budget, writer death, unsupported payload, and upstream outage. Hits may remain available during outage only with all pinned premises and successful verification.

Keep a mandatory uncached lane executing the real prover and all positive/negative verification and assertions. Application tests using the relay still execute contract logic and assertions; cached proofs cannot count as a fresh prover test. Proof replay can conceal proving regressions and affect linkability, so no claim that it replaces proof-generation coverage. DID/passport experiments must first measure repeated **exact request** rates; fresh transaction randomness/binding/context may make hit rates negligible. Key caching is the lower-risk first optimization.

No live proof-server experiment was run for this proposal. Protocol behavior above is source inspection; cache benefit, exact-request repeat rate and verification cost remain hypotheses to measure.
