# API conventions and Midnight terminology

Reviewed against official Midnight documentation on 2026-10-15. This describes
implemented behavior; it does not add a new transport or change the pinned backend.

## Domain vocabulary

ZKIR is the zero-knowledge intermediate representation of a circuit. Forge accepts
JSON `.zkir`; the pinned backend produces binary `.bzkir`, a **prover key**
(`.prover`) and a **verifier key** (`.verifier`). Prefer these terms over vague
“prover/verifier artifacts” when describing the actual keys.

Midnight.js `ZKConfigProvider` retrieves those artifacts by circuit name.
`NodeZkConfigProvider` reads the filesystem; `FetchZkConfigProvider` fetches artifacts
over HTTP/HTTPS. `ProofProvider` generates proofs and is a separate responsibility.
Forge generates, caches and distributes circuit artifacts; consumer proof generation,
verification and assertions continue on every run.

Official references: [provider guide](https://docs.midnight.network/guides/deploy-and-operate),
[Midnight.js API](https://docs.midnight.network/api-reference/midnight-js),
[ZKIR source](https://github.com/midnightntwrk/midnight-zkir).

The exported directory includes `keys/<circuit>.prover`,
`keys/<circuit>.verifier`, `zkir/<circuit>.bzkir`, source `.zkir` and a manifest.
Current official SDK providers also require the original compiler integrity
manifest and runtime metadata; a bare Forge export is insufficient. Publish a
complete compiler bundle with `publish-view` and explicitly enable
`serve --provider-root` for `/views/{manifest_sha256}/{file}`. The existing object
API remains a management/download surface. Pin the independent manifest hash in
SDK options and retain default integrity checking. See the
[compiler adapter guide](providers/local-adapter.md). Browser CORS and TLS/CDN
remain unqualified. Match the exact compiler, backend and serialization profile.

## CLI: arguments in, JSON out

- `import FILE` and `prepare FILE` read filesystem paths. There is no stdin circuit
  upload, special `-` path, JSON-RPC, JSON-lines session or persistent stdio server.
- Each completed data command prints one JSON object followed by a newline to
  stdout, with `schema: 1`. JSON formatting/order is not an interface guarantee.
- Successful data commands exit zero. Application errors exit nonzero, print
  `{ "schema": 1, "error": { "code": "…", "message": "…" } }` to stdout and
  diagnostics to stderr. Argument parsing errors may have no JSON and use stderr.
- `--help` and `--version` print human-readable text. `serve` runs an HTTP server;
  it is not a request/response stdio command.
- Use subprocess argument arrays, check exit status and parse stdout separately
  from stderr. Artifact paths are absolute paths on the CLI host. Do not parse
  diagnostic prose, assume a hit means success, or use internal CAS paths as a
  durable provider directory.

```python
import json, subprocess

result = subprocess.run(
    ["zkir-forge", "prepare", "/absolute/path/circuit.zkir"],
    capture_output=True, text=True,
)
if result.returncode:
    raise RuntimeError(result.stderr or result.stdout)
artifacts = json.loads(result.stdout)
provider_directory = artifacts["export"]["base"]
# Supply the compatible ZK config provider with this directory.
# Run actual proofs, verification, assertions and negative controls.
```

The isolated v3 worker has an internal subprocess protocol. It is not the public
Forge stdin/stdout API; consumers invoke the main CLI.

## HTTP: metadata JSON, artifact bytes

[OpenAPI](http/openapi.json) defines routes, status codes and response schemas;
[HTTP setup](http/README.md) covers authentication and admission limits.

1. `POST /v1/bundles?name=NAME&profile=SELECTOR`: raw exact single-circuit JSON,
   maximum 16 MiB, `Content-Type: application/json`. Registration is lazy; no keys
   are generated. Upload is not a path, archive or JSON wrapper containing a path.
2. `POST /v1/bundles/{id}/materializations?profile=SELECTOR`: explicit synchronous
   generation or verified reuse, returning 200. Send `Content-Type: application/json`
   even for an empty body. Busy admission is 429 with `Retry-After: 1`.
3. Read returned origin-relative artifact URLs and SHA-256 digests. GET/HEAD
   objects returns binary bytes/headers with strong ETags and supported single
   byte ranges. Metadata responses are JSON. No base64 or local-path convention.

GET never generates keys. There is no asynchronous 202/polling/job protocol.
HTTP errors are JSON with stable codes and appropriate status; filesystem
implementation diagnostics are withheld. When a bearer token is configured,
every route except liveness requires it. Non-loopback binding requires a token.
No CORS is enabled; remote TLS belongs at a trusted proxy boundary.

## Compatibility increment

The local compiler-compatibility increment adds a transport-neutral `descriptor`
and typed error classification. See [consumer contract](compatibility.md) for the
field inventory, legacy-sidecar rules and independent acceptance/fallback policy.
CLI error messages now use safe public code text; full diagnostics remain on stderr.
