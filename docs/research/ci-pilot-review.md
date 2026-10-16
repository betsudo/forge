# Product feedback and next validation scope — 2026-10-16

Tracking: [issue #21](https://github.com/input-output-hk/midnight-zkir-forge/issues/21).

Status: next-increment plan in response to owner-supplied product review. This
is not a hosted performance result, an onboarded-team claim or release readiness.
The separate linked Claude audit requires sign-in in the available browser and
has not been read; its detailed findings remain pending owner-provided text.

## What the evidence supports

Repeated circuit key generation is the bounded problem. Existing local experiments
preserve genuine proofs, verification, assertions and negative controls. DID
v0.7.0 improved from6.857s uncached to2.492s warm; selected Passport circuits went
from3.934s to4.338s. Both ran on shared macOS ARM64 and exclude actual GitHub
network transfer. Neither establishes hosted CI minutes saved. See
[consumer evidence](ci-consumers.md#local-consumer-qualification-follow-up--2026-10-16).

The owner explicitly requested the installer and calendar versioning. Those
requests justify that completed work, but do not establish broader adoption.
No named design-partner team or agreed two-week consumer trial is recorded.
DID and Passport are benchmark candidates, not enrolled users.

Clean Linux ARM64 qualification is complete. Existing hosted x86_64 checks build
and exercise the source through Nix; they do not qualify the portable installed
binary in a Nix-free x86_64 consumer. macOS Nix-free VM qualification is explicitly
deferred. Intel runtime and authenticated release downloading remain unqualified.

## Narrow next increment

1. Qualify the portable x86_64 Linux CLI in an actual x86_64 Linux consumer
   environment without Nix, build checkout or Rust tools. Use the current
   verified installer, exact profiles/parameter identities and real installed
   proof/recovery controls; record payload/source provenance. ARM emulation on
   this developer Mac cannot establish native x86_64 performance.
2. Build a thin JSON3.1-focused GitHub Action over the existing CLI helpers and
   verified snapshot contract. Avoid a second cache implementation or a new
   service. Preserve existing independently pinned profiles for current CLI
   consumers; narrowing pilot exposure does not remove supported behavior.
3. Start with one explicitly enrolled compatible consumer and add a second only
   if useful. Passport is a candidate with a negative local result, not a promised
   speedup. DID v0.7.0 uses another profile: its positive result cannot be relabeled
   JSON3.1 evidence or used to justify an incompatible adapter.
4. Run a two-week trial after an owner/consumer maintainer agrees the exact repo,
   workflow, workload and starting date. No trial, consumer checkout modification,
   outreach, scheduled automation, publication or deployment is implied by this
   plan. Record raw comparable hosted runs and retain negative results.

## Action and experiment acceptance

- Pin the Action, Forge payload, compiler/runtime/backend and parameters. Keep
  existing exact partition boundaries, bounded snapshots, one trusted producer,
  restore-only PRs and isolated writable stores; corrupt bytes fail explicitly.
- Restore artifacts before the ordinary consumer test command and save eligible
  growth only after successful real tests. Preserve original proofs, verification,
  assertions, negative controls and an uncached control. Never cache test outcomes.
- Measure uncached, cold, warm, partial and unavailable-cache runs under comparable
  runner/tool/workload conditions. Include setup/install, actual GitHub cache
  upload/download, compression/restore, codegen, keygen, proof/verification and
  complete job wall time. Record transferred bytes, cache age/hits/misses,
  runner architecture, raw repetitions, median and tail latency.
- Distinguish job wall time, measured billed runner minutes and any projected
  monetary saving. Report the whole job as well as the key stage. Define the
  matched comparison and any practical adoption threshold with the consumer
  before collecting the trial; do not select favorable runs afterward.
- Proceed with adoption only when repeated end-to-end measurements demonstrate
  worthwhile net benefit and unchanged correctness counts. If transfer/setup
  consumes the saving, keep the original path and report no benefit. A high hit
  rate is not enough.

## Parked work and strategic check

Proof Relay, hosted artifact delivery/CDN, optional HTTPS provider service and
additional platform expansion remain proposals. Do not implement them as part
of this pilot. Keep the prior research available without presenting it as shipped.

Upstream key caching or officially distributed deterministic key artifacts could
reduce Forge's value; this is a strategic risk, not a verified current upstream
feature. At pilot start, inspect exact official compiler/SDK versions for existing
reuse and compare that simpler baseline. Prefer upstream capability if it meets
consumer needs; avoid maintaining a redundant layer without measured benefit.

Current milestone local work remains complete apart from the explicitly deferred
clean-Mac gate. PR review and future release gates remain separate. Compact is
unchanged and no merge is performed by this review follow-up.
