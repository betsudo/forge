# Snapshot and CI design

`snapshot --output NEW_DIR --max-bytes N --wait-seconds N [--partition SHA]`
opens an existing store without schema mutations, takes BEGIN IMMEDIATE and
holds it through SQLite backup from a second read-only connection plus external
CAS/export copy. Writers wait; already open HTTP downloads may finish. A backed-up
committed SQLite database needs no copied journal. Staging is transient and omitted.
Sources, retained history, exports and metrics are preserved; this is not GC.
The snapshot manifest includes schema/producer fingerprint, optional CI partition
and sorted file digest/size inventory. Its identity is content-derived, not a
publisher signature. Bound files, manifest size, depth and total bytes; reject
links, traversal, unknown payloads, bad SQLite schema/records or corrupt objects.

`--cache-dir NEW_DIR restore SNAPSHOT [--expected-id SHA] [--partition SHA]`
requires an explicit absent destination, verifies manifest, producer, expected
partition/identity and every copied file in a private sibling staging directory.
It validates SQLite/record/artifact relationships and retained exports before
atomic no-replace rename on declared Linux/Darwin targets. Existing destinations
are never merged/replaced. Parent directories are operator-owned; no hostile
same-user concurrent mutation guarantee is claimed. Failed/raced publication
leaves no partially ready destination. Restore needs no proving parameters;
prepare still validates actual parameters and returns current absolute paths.

Snapshot source and destination must not contain one another. Regular copied
files and directories are fsynced before publication. Strict current producer
fingerprint compatibility prevents cross-tool reuse; old record recipes remain
preserved and can correctly miss under a new implementation. Database content
and hashes are not provenance for an untrusted publisher.

A dependency-free Python helper delegates snapshot/restore to CLI and provides
key, baseline, report and prepare-save commands. Keys include exact tool/profile/
platform provenance, actual declared parameter hashes, nonempty sorted workload
inputs/selectors and safe generation suffix. Baseline/report record totals only
and verify the job-local store was not replaced. Publication planning admits
only successful trusted default-branch push/manual context, positive generation
miss delta and an explicit byte budget. It creates no snapshot on PR/no-growth/
over-budget paths and never contacts GitHub. Cache action save stays a separate
reviewed workflow operation; helper guards are not an authorization boundary.

Local e2e covers metadata-only fast cases, lock contention/timeouts, competing
restores, corrupt/partial/path-hostile payloads and helper policy. Explicit real
e2e restores both official profiles and proves with warm restored artifacts,
including invalid controls. No Compact invocation or remote run is necessary.
