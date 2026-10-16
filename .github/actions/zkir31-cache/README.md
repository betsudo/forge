# JSON3.1 artifact cache Action

A restore/save wrapper around the **installed Forge CI helper**, using pinned
`actions/cache` v5 (Node24). Initial Action target: x86_64 Linux on a current
GitHub-hosted runner. The CLI's existing profiles are unchanged. This is artifact
reuse; every ordinary proof, verification, assertion and negative control must
still run. No Action command executes tests or treats a hit as a passed test.

## Prerequisites

Install and pin the matched Forge CLI/workers/helper first, using the
[private flake or qualified binary installer](../../../docs/install-release.md).
This Action deliberately does not select a floating version or download an
unpublished release. Supply an absolute CLI path and verified public parameters
for every circuit in the selected JSON3.1 workload. Generate the current ZKIR
before using it; preserve compiler/manifests and exact backend compatibility.

For another repository, pin this Action to a reviewed full commit:
`betsudo/forge/.github/actions/zkir31-cache@FULL_REVIEWED_SHA`.
Replace that placeholder before use. The new repository is public. If using a
private copy or private CLI assets, access must already be provisioned by the
repository owner; a consumer's ordinary `GITHUB_TOKEN` does not grant access to
another private repository. The Action changes no credentials, sharing settings
or permissions.

## Two phases around the ordinary tests

The following shape assumes an earlier installation step has exposed absolute
`binary` and `params` outputs. Replace the workload files, parameter list and
command with the consumer's exact qualified JSON3.1 contract. This example is
not a delivered integration into DID, Passport or Compact.

```yaml
permissions:
  contents: read
steps:
  # Checkout, install the pinned Forge/toolchain, verify parameters, and generate
  # current ZKIR with the exact qualified compiler before this point.
  - name: Restore verified keys
    id: forge
    uses: betsudo/forge/.github/actions/zkir31-cache@FULL_REVIEWED_SHA
    with:
      phase: restore
      binary: ${{ steps.install.outputs.binary }}
      params-dir: ${{ steps.install.outputs.params }}
      parameters: '["bls_midnight_2p9", "bls_midnight_2p14"]'
      workload-files: '["package-lock.json", "contract.compact", "compiler-config.json"]'
      workload: 'exact-contract-suite; pinned compiler and generation flags'
      max-bytes: '268435456'
      slot: contract
      trusted-ref: refs/heads/main
  - name: Run ordinary proof-bearing consumer tests
    env:
      MIDNIGHT_ZKIR_FORGE_DIR: ${{ steps.forge.outputs.cache-dir }}
    run: ./run-existing-proof-bearing-tests.sh
  - name: Save eligible key growth
    if: success()
    uses: betsudo/forge/.github/actions/zkir31-cache@FULL_REVIEWED_SHA
    with:
      phase: save
      binary: ${{ steps.install.outputs.binary }}
      slot: contract
      tests-passed: 'true'
```

The test command is a consumer-owned placeholder, not a Forge-provided script.
The consumer adapter must actually use the returned store instead of its shared
home cache. Keep uncached controls. Choose a unique slot for each independent
restore in a job, and reuse that slot for its save phase. Matrix job index is
included in immutable save generation identity. Restores/save use the same
snapshot path within that slot; standard hosted runners have a stable temporary
root across runs. A runner fleet with changing roots may miss transport cache
versions, but must never bypass Forge identity checks to compensate.

## Boundaries and outputs

- `cache-dir` is a private writable store, initially absent. An absent remote
  cache starts cold. A present corrupt snapshot or changed input/tool/parameter
  identity fails explicitly. Old metrics are excluded by a post-restore baseline.
- `restored` means verified snapshot restoration. It does not mean all requested
  circuits hit, that a remote exact-key match occurred, or that any test passed.
- Restore prefixes relax workload identity only inside the exact tool, platform,
  JSON3.1 worker/profile and parameter partition. One bounded snapshot transports
  a workload's keys; the Action does not create a GitHub entry for each circuit.
- The snapshot budget defaults to256MiB and cannot exceed1GiB. Forge validates
  unpacked bytes; this is not a pre-download compressed-transport ceiling.
  Restored snapshots are kept separately from the new candidate within the job.
  Metadata and witness/proof-response material must never be transported as cache.
- Save requires explicit `tests-passed: 'true'`, successful prior steps, a push or
  manual event at the restore phase's exact trusted branch, zero request errors
  and generation growth within budget. PRs are restore-only. No-growth,
  failed-tests, failed-job and untrusted-context decisions skip remote saves.
  Choose one trusted producer job; do not run untrusted code in it.
- `report-file` contains the save decision and actual helper metrics, including
  inherited-counter-free hits/misses/errors and measured request/generation time.
  `publish` means admission to attempt an upload; the transport step's success
  is separate. `restore.json` records download/restore wall time in job metadata.
  Setup, upload, proof execution and complete workflow wall time still need
  separate measurement before claiming CI savings.
- Snapshot checksums detect corruption; they do not establish a trusted publisher.
  GitHub's repository/branch permissions remain the transport trust boundary.
  Caches can be readable by PR workflows. Do not cache secrets, private witnesses,
  proof requests or test outcomes. Parameters and compiler/build outputs remain
  separate caches.

## Qualification

Fast phase/refusal controls run in `scripts/check-github-action.py`. With a matched
installed candidate and verified parameters, `--real --binary /absolute/cli`
checks cold generation, warm restoration and fresh actual proofs/negative controls
in both lanes. On developer macOS the test harness bypasses only the Action's
platform preflight and labels the result; it is not native Linux evidence.

The PR native installer workflow qualifies the installed portable x86_64 bundle
in a clean container, then exercises this composite Action on the native runner
with real JSON3.1 preparation/proofs and restore-only PR write admission. It does
not claim a trusted remote warm-cache round trip or consumer CI minutes saved.
The owner selected Passport for the next comparison. The two-week trial and real
transfer-value measurement remain separate follow-up work; see
[the reporting contract](../../../docs/ci-trial.md) and new-repository issue #2.
