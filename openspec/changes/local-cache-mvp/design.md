# Design

The product direction is SPEC.md, with owner amendments taking precedence.
The initial profile follows the latest stable official ledger8 tag 8.1.3 at
b5d3e965a18e4cac17fac4f38446fc55c524439a. Official library APIs own parsing,
parameters, key generation and serialization. The midnight-zk versions follow
that release's lockfile. The complete service does not require the ledger crate.

One circuit forms one logical bundle in this MVP. SHA-256 exact input identity,
versioned generation recipe (backend build fingerprint, options, tagged format,
actual verified parameter digest), and actual output set identity are distinct.
A SQLite immediate transaction with the default rollback journal serializes local mutating operations, including
keygen. The OS releases it on process death, avoiding a stale background lease.
WAL mode is unnecessary for this single-writer CLI and introduced a concurrent first-open journal-mode race in the real process test. This deliberately trades throughput for an easily reviewable local MVP; there
is no background job queue or durable asynchronous promise.

Immutable blobs publish before SQLite readiness. Small output records survive
eviction; regeneration must match those records. Shared objects are removed only
when no other ready record needs them. Exports are copied to persistent owned
paths and survive eviction; removing those paths is the owner's explicit action.

Metrics distinguish request latency from generation, count each requested file,
and estimate avoided generation only against the last observed cold generation
for the same recipe. Estimates are labelled, never a claimed benchmark result.

ADRs are optional for decisions already captured here. Add one only for a
cross-cutting decision, disputed tradeoff, upstream patch or incompatible change.
No accepted ADR or production claim is implied by this design.
