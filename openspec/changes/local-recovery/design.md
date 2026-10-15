# Design

Reuse the existing Linux/Darwin atomic no-replace directory rename for exports and
snapshots. Keep durability sync explicit at publication sites. Export races must
not overwrite even an empty destination created by another owner.

One application transaction owns ensure/resolve metadata and success accounting;
avoid commit followed by a second writer lease for metrics. An unsuccessful ensure
rolls back before error accounting. If that accounting fails, preserve the original
operation error and attach the accounting diagnostic. Do not hide corruption or
silently regenerate changed identities. Store::save already recomputes recipe
readiness: eviction should not repeat that SQL.

Recovery tests use private stores and genuine fixture backends. Deterministically
hold a SQLite reader to stop final commit after export publication, kill the writer,
release the reader, reopen and retry. Orphaned durable exports/CAS can remain but
must not imply readiness; retries verify and reuse immutable bytes. Failure probes
cover unavailable parameters, export obstacles, accounting failures and missing
exports. No production failpoint flags or background cleanup process are added.
