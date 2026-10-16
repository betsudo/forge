# Proof Relay design proposal

Use a separate optional command/store and one pinned upstream. Preserve binary `/prove` API for a separately qualified official protocol profile; forward `/check` and supported service routes live. No JSON witness schema or claim of all-server compatibility.

Hash exact request bytes plus namespace, method/path, pinned server/adapter/features, parameters and fully resolved builtin/key inventory. Do not strip binding/randomness/domain fields. If resolver provenance or independent response verification is unavailable, forward without cache admission. Use local HMAC-SHA256 keyed request digests and owner-only storage; do not persist witness bodies or upload proof stores into CI artifact caches.

Admit only successful independently verified proofs; verify hashes and proofs on every hit. Preserve original binary bytes. Atomic response+manifest publication, bounded disk/body/deadline/concurrency, TTL/purge and process-death lock release are required. Do not retry uncertain expensive POST failures automatically. Cache corruption is explicit failure.

Proof randomness means replay is observable; require caller opt-in and a bypass mode. Tests must still execute contract logic, assertions and proof verification. A separate uncached lane runs genuine proof generation and negative controls. See research for exact upstream tuple/endpoint sources and unresolved protocol-verifier gates. No server or witness cache is delivered by this change document.
