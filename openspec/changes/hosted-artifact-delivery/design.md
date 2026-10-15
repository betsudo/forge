# Hosted delivery design

## Small boundary

Keep admission/catalog, generation and immutable delivery separate. Start with
trusted complete-set publication from qualified CI/local workers; permit raw
ZKIR admission with explicit asynchronous generation later. Native keygen uses
exact official backend/parameter profiles and resource budgets, never an
unbounded function request. Use direct size-limited object uploads/downloads.

Store binaries in object storage and manifests/ACLs/state in a database. Expose
only a complete committed set after verifying every object. Use conditional
publication and fenced leases for retry/crash safety. Missing or corrupt output
cannot become a hit. Preserve historical verifier/output identity across eviction;
regenerated different bytes form a different set or an explicit identity error.

## Immutable consumer views

Publish `/views/<view-id>/keys/<circuit>.prover`, `.verifier` and
`zkir/<circuit>.bzkir`, plus exact compiler integrity/runtime metadata required by
the pinned FetchZkConfigProvider version. Forge's descriptor complements that
metadata; it cannot replace or fabricate compiler provenance. A provider-view
claim requires real SDK retrieval and proof verification, not path resemblance.

Authenticate before CDN lookup for private content; namespace identity and access
policy remain enforced even when bytes deduplicate. Immutable set URLs never
follow mutable aliases to different keys. No HTML fallback. Configure explicit
browser CORS and avoid credentials in logs/cache keys exposed to other tenants.

## Compression

Canonical identity hashes original tagged serialized bytes. Encoded variants
have separate size/hash metadata and are verified by bounded decompression.
Negotiate gzip/Brotli only when beneficial, with Content-Encoding,
Vary: Accept-Encoding, encoding-specific strong ETags and coherent HEAD lengths.
Pin/test actual browser and Node fetch decoding. Initial Range handling selects
the identity representation with its offsets/ETag; encoded responses do not
advertise range support. Do not change filenames to `.gz`, alter key encoding,
apply offsets to decoded bytes inside compressed bodies, or disable integrity.

## Cost decision

R2/Workers/D1 is the first read-heavy low-transfer-cost candidate, Rust Lambda is
a conventional AWS alternative, and Cloud Run offers native Rust containers on
Google. Azure Rust custom handlers and a single native VM remain alternatives.
This is a shortlist, not a vendor commitment. No cryptographic Worker/Wasm port
is implied. Record date, region, storage/transfer/request/CPU/metadata assumptions,
free-tier eligibility and excluded costs; use measured compression/resource data.
A local cost projection is never a cloud benchmark or complete bill.

See the linked research for current official prices and platform limits. A
provider choice and hosted pilot require measured consumer results and separate
owner authorization. No deployment automation is introduced by this contract.
