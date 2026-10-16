# Design

Expose explicit restore/save phases in a composite Action. Use installed absolute
CLI paths and the existing forge-ci helper for exact profile/worker/parameter/
workload partitioning, verification, baseline/report and bounded trusted growth.
Delegate transport to SHA-pinned actions/cache restore/save. Restore before normal
tests; save only afterward with explicit test success and a trusted push/manual
branch context. PRs remain restore-only; never invoke tests or cache outcomes.

Keep job metadata outside the transported snapshot and use absent private stores.
Use environment variables and subprocess argument arrays for all inputs. Reject
reused slots, unsafe paths, wrong profiles, changed identity and corrupt snapshots.
Report actual restore status separately from remote exact-key matches. Cache misses
start cold; transport corruption and CLI refusals fail explicitly.

Build the exact clean committed native package through Nix on a hosted x86_64
Linux runner. Copy a minimal candidate/test kit into an unprivileged clean Docker
consumer, without host checkout mounts, Nix or Rust tooling. Run installed genuine
proof/reproducibility/negative/recovery controls offline, plus separate verified
fresh HTTPS parameter controls. Retain hashes, environment and source provenance
as PR-run artifacts; no release upload or tag. This job is a correctness gate,
not a hosted cache-performance benchmark.

Unit/process tests exercise phase orchestration and trust refusals locally, plus
real installed JSON3.1 cold/warm proofs. Independently review identity/transport
and write-admission boundaries before any release-readiness claim.
