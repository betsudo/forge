# Next-stage Forge research — 2026-10-16

These are researched proposals, not implemented service promises. Keep the core
component simple: qualify artifact-key reuse before adding proof response reuse
or a hosted registry. All current delivery stays local, with Compact unchanged.

| Study | Decision / remaining evidence |
| --- | --- |
| [DID and Passport CI](ci-consumers.md) | Exact recipes locally, bounded verified partition/workload snapshots for GitHub transport; thin Action later. Local genuine-proof benchmarks completed: DID improved, Passport regressed; hosted transfer and full CI savings remain unmeasured. |
| [Forge Proof Relay](proof-relay.md) | Optional exact binary request reuse with independent proof verification; no fuzzy matching, witness uploads or skipped real-prover lane. Not implemented. |
| [Official backend matrix](backend-matrix.md) | Keep current independently qualified pins/workers; published v2 availability does not justify automatic v3 or ledger9 support. |
| [Hosted delivery and cost](hosting-costs.md) | Publish qualified immutable views through object storage/CDN; native keygen outside admission functions. Costs are explicit projections; consumer compression ratios remain unmeasured, while the tiny fixture probe shows prover bytes can grow. |

Tracked in issues #13–#16 under [2026.10.0](../milestones/2026.10.0.md).
Independent reviews checked cache partition/trust, timing attribution, proof
protocol/privacy and cost arithmetic. Corrections make HMAC request identity
normative, exclude relay stores from GitHub caches and pin inspected provider
source. Full local contracts live in openspec/changes/ci-consumer-cache,
proof-relay, backend-profiles and hosted-artifact-delivery.

[Product feedback and focused CI pilot](ci-pilot-review.md) records the next
x86_64 Linux/JSON3.1 validation scope, adoption gaps and parked service work.
