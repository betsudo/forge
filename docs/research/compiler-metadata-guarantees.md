# Preserving compiler metadata across cached key generation

Status: locally implemented boundary; qualification is limited to the exact
Compact0.35.0 / JSON3.1 fixture and official SDK5.0.0-rc.2 cohort. Upstream flags,
other compilers, Linux consumers and hosted delivery are separate qualifications.

## What must be preserved

A Forge key export is not a complete compiler output. Official
`NodeZkConfigProvider` and `FetchZkConfigProvider` consume the compiler's original
`compiler/contract-manifest.json`, `compiler/contract-info.json`, binary ZKIR,
prover keys and verifier keys. The manifest also inventories source ZKIR and
contract runtime files. Keep that complete output, including the original raw
manifest bytes. Never create replacement compiler metadata from a Forge export.

The inspected SDK defaults to `verify: 'require'`; `expectedManifestHash` pins the
SHA256 of the raw manifest. It checks listed content, but flattens only one
level and can skip unknown nested entries. Its runtime-version lookup prefers
manifest metadata without comparing compiler-info. Forge therefore rejects
unsupported nesting, unknown inventory, duplicate JSON keys, symlinks and special
files; verifies every size/hash; cross-checks compiler-info versions and circuit
roster; and requires compiler-commit equality when supplied by either document.

## Guarantee chain

1. Independently qualify the exact compiler, Forge executable, worker, profile,
   parameter bytes, source and resulting artifacts using real proofs and negative
   controls. Pin the receipt hash independently. The initial adapter deliberately
   accepts only sources in that receipt; it is not a generic compiler integration.
2. Run the actual compiler. Substitute private byte-identical cached copies only
   at its `zkir-v3 compile-many` key-generation boundary. Require that hook to
   complete. Let the compiler itself emit runtime code, contract-info and its
   final integrity manifest after key materialization.
3. Publish the complete output with an independently supplied manifest SHA256.
   `publish-view` verifies and copies it privately, then atomically publishes a
   directory named by that raw manifest digest without replacing an existing
   view. A repeated publication revalidates the existing view.
4. Configure each SDK provider with that trusted `expectedManifestHash`, retain
   default integrity checking, and execute proofs, verification and assertions
   on cold and warm runs. Use a fresh provider for a new manifest identity.
5. On HTTP reads verify the complete view before HEAD, conditional or range
   handling; stream a verified private descriptor rather than reopening the path.
   Authentication precedes lookup when configured. GET never generates keys.

Preseeding compiler output before compilation fails because compilation removes
its output directories. Compiling with skipped key generation and copying keys
later also fails this contract: the original manifest was already finalized.

## Trust and practical limits

A hash supplied by the same untrusted server as the content is not an independent
trust anchor. Hash consistency cannot prove which compiler executed or authenticate
claimed sources. Obtain pins through reviewed source control or a separately
trusted release channel. Signing or build provenance can strengthen that channel;
Forge does not invent provenance from matching bytes.

This is a single-owner local service, not a sandbox against malicious processes
with the same filesystem privileges. Publication copies are independent of the
cache and compiler output. Same-user edits cause subsequent validation refusal;
protect the provider root and qualification receipts operationally. Concurrent
compiler output mutation is unsupported; adapter checks detect changes before
publication but do not provide a filesystem transaction over a live compiler.
Initial limits are flat two-level trees,4096 files,4MiB JSON,1GiB per file and
4GiB total. HTTP serves identity encoding; browser/CORS, TLS/CDN and Cloudflare
remain unqualified/deferred. Explicit provider roots are outside cache snapshots.

## Evidence and primary sources

- Exact official SDK packages and publisher integrity: [package lock](../../integration/providers/package-lock.json),
  `@midnight-ntwrk/midnight-js-utils`, Node/Fetch providers5.0.0-rc.2 and runtime0.20.0.
  Inspected utils `dist/index.js` lines1508–1607. Upstream
  [Midnight JS repository](https://github.com/midnightntwrk/midnight-js) and
  [official deployment guidance](https://docs.midnight.network/guides/deploy-and-operate).
- Read-only Compact source revision `05a7885f6518e1ca358896aec03cc028a66f8c13`:
  `compiler/passes.ss:145–190` (cleanup, key generation, final manifest),
  `compiler/manifest-passes.ss:27–83` (inventory),
  `compiler/save-contract-info-passes.ss:90–110` (runtime metadata).
  Source inspection is not a claim that this revision built the qualified binary;
  the qualification separately pins the actual executable bytes.
- [Original real provider qualification](../evidence/provider-sdk-local.json),
  [provider view specification](../../openspec/changes/provider-view-api/specs/provider-views/spec.md),
  [adapter specification](../../openspec/changes/compiler-local-adapter/specs/compiler-adapter/spec.md).

Final local API/adapter evidence: [native off/cold/warm receipt](../evidence/provider-view-adapter-local.json).
It records complete output identities, actual SDK proof controls, cache statistics
and corruption/refusal/recovery checks. Scope remains the exact native fixture.
