# Design and compatibility investigation

V2 remains official ledger8 8.1.3 at b5d3e965a18e4cac17fac4f38446fc55c524439a.
That source contains midnight-zkir-v3 3.0.0-rc.1 sharing the proof stack, but
its `ir-source[v3]` output is not interchangeable with the newer split v3
`ir-source[v3-generic]` implementation. JSON major version 3 does not establish
backend or binary serialization compatibility.

The known consumer's v3 tool input pins official midnight-ledger revision
3a7ae0361d03e6eed4fc91e31f6600f334f605d5. Resolve its actual crate/API/dependency
identity before choosing the first supported v3 profile. A compatible same-graph
backend can share the process behind typed dispatch. Conflicting dependencies
require an independently built worker with its own lockfile. No generic trait
abstraction or distributed worker system is required.

Input format, backend/serialization and actual parameter bytes belong in recipe
identity. V2 inventory identity remains stable. Old record JSON must stay
readable and existing immutable exports usable. New fields in old export
manifests must not invalidate their bytes merely because a record was read by
an upgraded CLI. An application-pinned verifier must never be silently replaced.

Tests must use actual official APIs and real proofs, distinguish artifact hits
from test outcomes, cover profile refusals and exercise eviction/concurrency.
No cross-profile cache reuse based on filename, JSON version or shared crate name.
