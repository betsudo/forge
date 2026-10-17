# Limits and storage

Publish, verify and serve accept `--provider-max-view-bytes` (1..64 GiB;
default 4 GiB). The aggregate includes the original manifest and every declared
file. A typed `provider_limit` is nonretryable and cannot authorize availability
fallback. Diagnostics identify the required/configured bytes and explicit option.
Malformed compiler metadata remains an integrity error, without shadowing limits.

Before copying a new view, inspect available destination filesystem space using
the existing libc dependency. Require declared bytes plus 64 MiB reserve; refuse
with nonfallback `provider_storage_unavailable` before creating staging. This is
a preflight, not a reservation: a later I/O failure still cannot publish partial
content. Existing views are fully audited before reuse and need no new copy.
Retain synced private staging and atomic no-replace publication. Crash leftovers
are never addressable by a view ID and are not automatically deleted.

HTTP retains two active verified anonymous snapshots, eight waiters and ten-second
admission. Each requested file is still fully verified before HEAD, conditionals
and ranges. At the fixed 1 GiB per-file cap, temporary snapshot content is at most
2 GiB, separately from persistent provider storage. No trust markers are added.
