# Identity and transport contract design

## Audit of existing identity

Bundle ID binds circuit name, input format and exact source digest. Derivation ID
binds actual source digest, official profile/revision, build fingerprint, k, digest
of verified parameter bytes and `library-keygen/default-options/no-rng`. V3 wraps
that recipe with full WorkerProvenance, including executable SHA-256. Artifact-set
ID binds the ordered actual generated artifact kind/digest/size inventory. Renamed
circuits can share a derivation; distinct contexts can legitimately generate the
same output bytes. Neither equal source bytes nor equal output IDs imply equal
compatibility premises. Build fingerprints remain conservative partitions.

A versioned typed `ArtifactDescriptor` v1 exposes schema, registration/materialized
state, circuit name and bundle ID, exact source kind/digest/size and input format/
JSON version, optional materialization context (official backend profile, revision,
actual binary serialization tag, build fingerprint, required v3 worker, k,
parameter digest and fixed keygen recipe/options), derivation ID, artifact-set ID
and full derived inventory. Lazy registration explicitly lacks generation facts;
consumers cannot treat it as a materialized hit. No local paths or requested paths
belong in this type. Transport-specific URLs/paths stay outside it.

Use actual source bytes for the input version. Record generation facts only after
upstream parameter verification and generation/verified reuse. V2 tagged-v1 and
v3 `ir-source[v3-generic]` are distinct. Serialization fields must reflect actual
upstream tags inspected from pinned code, rather than fabricated tag names.

Expose the same descriptor under `descriptor` in CLI import/inspect/prepare/ensure/
resolve/export and HTTP registration/inspection/materialization. New provider
exports contain immutable `descriptor.json` alongside unchanged `manifest.json`.
Existing exports keep their immutable manifest bytes; a verified missing sidecar
may be added atomically, never replaced with different content. Existing CAS/SQLite
Record schema and identity recipes do not gain descriptor fields. Snapshot readers
accept legacy exports without sidecars and validate sidecars when present; no silent
rewrite of legacy snapshot payloads or producer compatibility bypass is allowed.
This explicit additive decision avoids a Record/identity migration; any later
change to identity domains or legacy manifest serialization needs a separate ADR.

Descriptor v1 deserialization rejects unknown/missing/duplicate/conflicting fields,
invalid IDs/inventory, materialized fields on a lazy record, absent v3 provenance,
and inconsistent recomputed identities. Consumers accept only explicitly supported
versions and must independently qualify expected backend revision/profile, format/
serialization, build and worker allowlists, parameters/k and options. Verify input
and every downloaded artifact's bytes and compare recomputed identity fields;
compare descriptor premises to that independent policy, not to another declaration
from the same untrusted producer. Descriptor equality is not publisher trust.

Semantic compatibility is a qualified consumer/backend agreement. Exact derivation
reproducibility additionally requires equal recipe premises. Actual output identity
is the digest of the produced set. Do not weaken build partitions based on a new
descriptor or claim independently qualified Compact integration in this repository.

## Shared typed errors

Use one transport-neutral error kind/code with safe public text, HTTP status,
retryable and availability-fallback classification. CLI application failures keep
nonzero exit and schema/error/code/message JSON; add retryability/fallback facts.
HTTP emits the same code/classification with sanitized public text. Argument errors
retain Clap's stderr behavior. Internal worker failures carry a structured protocol
error code instead of parsing stderr for policy. Unknown/invalid worker replies
fail closed. Diagnostic text is never a policy input.

| Kind/code | HTTP | Retryable | Availability fallback |
| --- | --- | --- | --- |
| parameters_unavailable | 503 | yes | yes |
| invalid_parameters | 422 | no | no |
| profile_format_mismatch / worker_profile_mismatch | 409 | no | no |
| unsupported_zkir_version / invalid_input | 400 | no | no |
| integrity_error / artifact_identity_changed | 409 | no | no |
| not_found / artifacts_unavailable | 404 | no | yes |
| unauthorized | 401 | no | no |
| busy (including bounded HTTP admission subcodes) | 429 | yes | yes |
| internal_error | 500 | no | no |

Keep existing specific snapshot error codes with typed classification. A caller
may choose its original fresh key generation only for a known availability outcome
or transport connectivity failure under its own policy; it still runs proofs and
assertions. Integrity, compatibility, unknown schema and authentication refusals
must not be hidden by fallback. No HTTP diagnostic exposes filesystem paths,
tokens, raw upstream exception strings or private source material.

Detect missing parameter files distinctly from present invalid/unverifiable bytes;
upstream verification remains authoritative. Retrieval/network failures cannot
convert a known corrupt local parameter file into an availability event. Parameter
identity mismatch during v3 plan/generate is an invalid-parameter/identity refusal.
Hash the actual verified bytes; paths, timestamps, size labels and k alone are not
parameter identity. Read errors without enough evidence are internal/refusal, not
optimistic cache misses.

## Local acceptance and integration with release work

Use genuine v2/v3 fixtures for warm exported and HTTP-downloaded proof controls.
Use isolated identity-unit controls for each changed premise (including unsupported
revision/options/tag controls), not invented production backend profiles. Preserve
legacy export bytes and pinned regeneration identities, snapshot behavior and
uncached qualification. Compare complete descriptors across transports and test
strict decoding and sanitized errors, missing versus corrupt parameters, busy and
auth failures. Record per-run statistics deltas and process wall times separately.
Independent review covers identity, migration and error/fallback correctness before
acceptance. Report native platform/pins/tags; no universal Compact or Linux proof
qualification without corresponding evidence. Local implementation and signed
commits only; no push, release, workflow, deployment or dependency upgrades.
