# Optional Forge Proof Relay

Status: proposed research scope; no implementation authorization is inferred.

## Why

Repeated expensive proof requests may benefit from exact verified response reuse. Similar contracts or witnesses are insufficient. First measure repeated request rates; randomized transaction context may prevent useful hits.

## What changes

Propose an opt-in loopback proof-server relay with exact pinned protocol/context identity, unchanged miss forwarding, verified response admission/hits and bounded private storage. Preserve the existing artifact cache and mandatory uncached proof-generation tests. This explicitly proposes an exception for proof bytes to the current artifacts-only scope; it does not amend existing runtime behavior or permit caching test outcomes.

## Non-goals

Fuzzy matching, cached assertions/check outcomes, replacing proof coverage, arbitrary upstream URLs, public/multi-tenant witness storage, hosted deployment or Compact changes.

See [research](../../../docs/research/proof-relay.md).
