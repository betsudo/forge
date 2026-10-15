# Hosted artifact delivery

Status: proposed research contract, 2026-10-16; not implemented or deployed.

## Problem and outcome

Distribute exact qualified circuit binary IR, prover keys and verifier keys over
HTTPS without placing large transfer or expensive native generation inside a
small Rust HTTP function. Compare serverless control planes and a simpler VM
option against measured total cost, including storage/CDN/egress and compression.

## Scope

A bounded authenticated Rust upload/catalog layer, database metadata, immutable
object sets/provider views, optional separately leased native generation, CDN
content negotiation, and local failure/consumer qualification. Research AWS,
Google, Azure, R2/Workers and middle-tier VM/CDN alternatives. Preserve exact
Forge identities, official backend pins and consumer integrity/runtime metadata.

## Non-goals

No deployment, credentials, cloud account changes, published private sources,
Compact changes, ledger transaction support or proof-response cache. No generic
multi-cloud implementation or queue framework before one measured pilot design
is selected. Current local HTTP/SQLite behavior does not become a distributed
service merely through this proposal.

Research and dated price assumptions: [hosting-costs](../../../docs/research/hosting-costs.md).
