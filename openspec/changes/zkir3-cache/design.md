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

## Selected implementation

Exact consumer pin 3a7ae0361d03e6eed4fc91e31f6600f334f605d5 is verified from
its read-only flake input. Its own lock uses transient2.1.0, base1.0.0,
serialize1.1.0 and the same registry proof/circuit pins as v2. It is also named
3.0.0-rc.1 but uses ir-source[v3-generic]; crate version labels alone are not
sufficient. Use a separate workers/zkir3 Cargo workspace/lock and one-shot
private worker. No source patching or dependency unification is performed.

The worker supports parse inspection, verified parameter planning, generation
into a unique private staging directory and uncached real qualification. The
parent checks exact worker profile/revision, actual executable SHA-256, worker
build fingerprint, plan parameter digest and returned artifact digests. Only
the parent publishes cache readiness under SQLite ownership. The worker stops
on parent death on Unix, preventing abandoned expensive generation from running
indefinitely. No async job/supervisor service is introduced.

The CLI detects supported v2/v3 format and allows --profile ledger8-v2 or
--profile zkir3 to assert the expected backend. This is not automatic selection
among arbitrary v3 implementations: zkir3 always means the exact pinned source
above. Consumers must compare their actual tool pin before integration. The
new split 3.1.0-rc.1/default proof graph is not supported by this profile.

V2 retains inventory identity and profile string. Adding new Forge implementation
changes its conservative build fingerprint and can cause one new derivation;
old records/manifests remain readable, and old immutable exports remain usable.
Optional v3 metadata fields are omitted for old v2 records to preserve exact
manifest bytes on explicit resolve.

Runtime discovery: the exact consumer parser accepts only minor0; minor1 is
refused. Qualification is therefore JSON3.0 only. Parent liveness uses50ms
polling, not a real-time bound or zero-overlap crash-recovery guarantee. Warm
and regenerated exported artifacts are used in actual fixture proofs by the
private qualify-export test operation; fresh backend and cached-path evidence
are both exercised.
