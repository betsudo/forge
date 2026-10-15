# Verified snapshots and CI cache helpers

Issue #6 implements the issue #5 research in Forge only. Add consistent directory
snapshots, verified atomic restore and local CI key/baseline/save-planning helpers.
Retain exact artifact identity, actual proofs and explicit uncached controls.
Compact, remote workflows, cache deletion and publishing stay unchanged.

Snapshot directories let Actions cache/artifacts own compression and transport;
there is no tar extraction surface or database merge. Helpers never upload or
grant cache privileges. A signed commit and local e2e receipt own this increment.
