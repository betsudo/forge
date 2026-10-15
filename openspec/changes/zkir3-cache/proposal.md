# Cache ZKIR v3 alongside the existing v2 backend

## Why

A local consumer integration currently leaves ZKIR v3 uncached because Forge
only supports v2. Issue #3 adds an explicitly qualified v3 profile while retaining
actual consumer proofs, verification, assertions and an uncached qualification.

## What changes

- Pin the official v3 backend matching the consumer tool and isolate incompatible
  proof graphs when necessary. Keep the existing ledger8 v2 profile available.
- Make format/profile selection observable and reject wrong/unsupported versions
  before writes or expensive generation. Do not convert v3 to v2.
- Reuse CAS, copied exports, SQLite ownership, metrics and identity checks.
- Qualify real v3 generation, proof controls, warm reuse and regeneration.
- Save the consumer starter prompt in the Midnight vault and link it from the
  global skill; update instructions after the installed CLI is qualified.

## Capabilities

### Added capabilities

- `zkir3-cache`: exact profile-aware local generation/reuse for v3 inputs.

## Non-goals

Ledger transaction/network compatibility, automatic dependency upgrades, HTTP,
consumer checkout changes, hosted CI, code push, PR or supervision.
