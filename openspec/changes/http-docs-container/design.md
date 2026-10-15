# Initial HTTP, documentation and container design

The CLI gains `serve`, default 127.0.0.1:8787. This is a single-owner local service;
non-loopback binding requires an operator-supplied bearer token file. Every API
and readiness endpoint is protected when configured; only liveness is public.
No CORS is enabled. Require application/json for uploads to reject browser simple
form requests. Do not log tokens or expose local paths/underlying error messages.

POST /v1/bundles accepts exact raw single-circuit ZKIR bytes (16 MiB limit),
with required safe name and optional exact profile selector in query. This is an
explicit narrow deviation from the future streamed archive/manifest contract.
POST /v1/bundles/{id}/materializations synchronously returns 200 ready references;
it never pretends to be a durable job or returns an unimplemented 202 job URL.
GET bundle/source/objects/profiles/stats are read-only and never generate keys.
GET and HEAD objects verify the content hash before sending a streaming file,
with strong ETag, conditional requests and a single byte range. Responses contain
HTTP artifact URLs and digests, never server-local exported paths.

Use Axum with bounded admission and blocking work off async executor threads.
Each request opens its own store connection; existing SQLite BEGIN IMMEDIATE
serializes CLI and HTTP publication, preserving verifier identity. One materializer
is admitted at a time; saturated admission returns 429 rather than an unbounded
queue. Request disconnect does not cancel admitted generation; it may safely
finish and publish. Shutdown waits for admitted work; forced termination retains
the existing transaction/crash guarantees. No strict CPU/memory sandbox is claimed.

Readiness checks configured storage and worker compatibility; it is not a promise
that all circuit parameter sizes are present. Parameter retrieval remains an
explicit operator startup option. Production TLS, rate limits, publisher trust,
namespace policy and durable jobs remain future work.

The static site follows the official Midnight brand hub, uses relative asset
links under a repository Pages prefix and clearly separates implemented and
proposed features. Nix builds the Linux container closure; image runs non-root,
mounts cache and verified parameters, and uses a mounted token file for binding
inside Docker. Default CI checks are bounded; real proof e2e is explicit opt-in
and continues actual proof/verification/negative controls. Workflow files are
prepared locally, without enabling remote publication.
