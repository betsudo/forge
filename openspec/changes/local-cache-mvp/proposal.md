# Local artifact cache MVP

## Why

Repeated Midnight circuit tests regenerate identical keys. Reuse exact compatible
artifact files while every consumer continues executing its tests.

## What changes

Deliver a Nix-owned Rust CLI with a configured local store, official ledger8
8.1.3 backend, durable content identity, verified hits, preserved verifier
identity, persistent copied exports, derived eviction and per-file efficiency
metrics. GitHub issues #1 (bootstrap) and #2 (cache) own this increment.

## Capabilities

### Added capabilities

- `local-artifact-cache`: import and derive one circuit, export usable paths,
  safely reuse and evict files, report observed efficiency.

## Non-goals

HTTP, background supervision, remote CI, ledger9, ZKIR3, multi-host scheduling,
full multi-circuit bundle manifests, hosted publication and production readiness.
