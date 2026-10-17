# Measure the Passport CI trial

Tracking: [betsudo/forge issue #2](https://github.com/betsudo/forge/issues/2).
The owner selected Passport on 2026-10-16. No hosted performance trial has started.
The reporter prepares comparisons; it does not install Forge, enroll users, run
tests, contact GitHub, upload caches or verify a cryptographic proof.

## Freeze a plan before collecting runs

Start with the previously qualified Passport account source
`0d7bb0bc834f2d45d9fe2d84c4d022a30d648423` and selected circuits
`deposit_unshielded` and `activate_initial_device_with_jubjub`.
The exact consumer inventory is [consumer-files.json](../benchmarks/passport/consumer-files.json).
Compiler 0.35.0 and the separate JSON3.1 profile were qualified in
[passport-exact-profile.json](evidence/passport-exact-profile.json).
This is a two-circuit benchmark, not all 52 circuits or a full Passport application
test suite. Preserve the official uncached key-generation control and every
execution, proof, verification, assertion and negative control in each lane.

The local warm result was slower (4.338s versus 3.934s uncached); see
[the raw local benchmark](evidence/passport-benchmark.json). It excludes actual
GitHub network transfer. Do not import its macOS executable hashes or stage times
as x86_64 Linux measurements. Qualify the exact Linux compiler/runtime/worker
combination and compare its artifact bytes before using it in the trial.

Prepare a JSON plan with these fields:

| Field | Meaning |
| --- | --- |
| `schema` | Integer `1`. |
| `scope` | `whole-job`; one row measures one complete hosted job, even when that job runs only the selected workload. |
| `repetitions` | 3–1000 complete five-lane repetitions, chosen before collection. Three is a smoke comparison, not a two-week study. |
| `minimum_saving_ms` | Positive minimum **median paired** full-job saving needed to meet the agreed threshold. Freeze this before results. |
| `cache_requests` | Expected job-local Forge requests per cached lane; at least two for a partial-hit lane. |
| `correctness` | Positive integer `proofs`, `verifications`, `assertions`, `negative_controls` expected in every job. Verification count must cover proofs; require invalid-statement and corrupt-proof controls. |
| `identity` | Exact fields in the following table, identical across every row. |

| Identity field | Meaning |
| --- | --- |
| `repository` | Consumer repository, initially `midnightntwrk/passport`. |
| `workflow_repository` | Repository actually running the measured jobs; may be `betsudo/forge` for a read-only consumer benchmark. |
| `consumer_commit` | Full 40-character source revision. |
| `workload_sha256` | Digest of a retained canonical inventory of selected sources, ZKIR, flags and workload selection. |
| `toolchain_sha256` | Digest of a retained compiler/runtime/dependency-lock and uncached-tool inventory, using actual Linux bytes. |
| `forge_sha256`, `worker_sha256` | Exact installed CLI and JSON3.1 worker executable SHA256. Include the helper and Action revisions in the retained toolchain inventory. |
| `profile` | Complete qualified profile/recipe identity from the installed tool. |
| `parameters_sha256` | Digest of the retained filename/content-digest parameter inventory, not just a parameter-directory name. |
| `runner_image` | Actual hosted runner image **version**, plus relevant CPU/kernel details in raw evidence; `ubuntu-latest` alone is insufficient. |
| `runner_arch` | `X64`, native Linux for this initial pilot. |

Keep the plan bytes unchanged, calculate their SHA256, and record that digest in
every run row. Retain the inventories themselves so another reviewer can check
the digests. The reporter cannot establish that a plan was declared in advance;
use a reviewed committed plan before the collection starts. Do not fill missing
measurements with estimates or select favorable runs after viewing results.

## Collect the five lanes

Use an isolated store for each job, never the shared home cache:

- `uncached`: official matched tool generates keys; no Forge or artifact transport.
- `cold`: no restored keys; generate, run genuine tests, then measure trusted save.
- `warm`: actually download and verify the seeded snapshot; all requests hit,
  and all ordinary proofs and assertions run freshly.
- `partial`: actually download a snapshot seeded with one of the selected
  circuits; record both hits and misses, plus eligible save work.
- `unavailable`: artifact transport is unavailable; use the original generation
  path and run the same genuine tests. Corruption is a failure, not availability.

Keep seed production as its own disclosed job; include actual setup, installation,
codegen, key preparation, proof/verification, cache download/restore and upload in
the measured lane jobs. Schedule equivalent jobs under comparable runner conditions
and predeclare lane order. Pin the Action, Forge payload, compiler, backend and
parameters. Inspect the pinned upstream tools for existing reuse before adding a
redundant layer. Avoid publishing private witnesses, proof requests or secrets.

Produce a JSON **array** of raw rows. Each row contains:

```text
plan_sha256: SHA256 of the exact plan file bytes
identity: the exact plan identity object
scope: "whole-job"
conclusion: "success"
repetition: zero-based integer
lane: "uncached" | "cold" | "warm" | "partial" | "unavailable"
job_url: https://github.com/OWNER/REPO/actions/runs/RUN_ID/job/JOB_ID
evidence_sha256: digest of a retained raw evidence/log bundle
correctness: the exact observed counts, matching the plan
timing: {
  job_ms, setup_ms, codegen_ms, key_prepare_ms, proof_verify_ms,
  download_ms, upload_ms
}
download_bytes: actual transferred bytes, integer
upload_bytes: actual transferred bytes, integer
transport_unavailable: boolean, true only for the unavailable lane
cache: null for uncached/unavailable (official generation), otherwise {requests, hits, misses, errors}
```

Use actual GitHub job start/end data for `job_ms`, including upload steps; a
wrapper timing only the test process is not a full-job measurement. Stage durations
must be non-overlapping and nonnegative. The reporter checks their **sum** against
job time, but cannot discover interval overlap or dishonest instrumentation.
`download_ms` includes lookup/download/decompression/verification/restore;
`upload_ms` includes snapshot/compression/upload. Measure actual compressed
transport bytes from retained transport logs, rather than substituting unpacked
snapshot size. The current Action alone does not provide all these measurements. Local stage
capture and strict collection prepare orchestration; actual transport instrumentation
and the frozen, native-qualified hosted pilot remain pending.

Use cache statistics **since the post-restore baseline**, not inherited totals.
The correctness counters come from real test instrumentation, including failed
statement/corrupt-proof controls. JSON counts are declarations, not proof
verification. Raw receipts must show the genuine execution and be independently
audited. Retain transport keys, cache creation age, matching source provenance,
runner details and failure diagnostics in the evidence bundle. Each row must have
a unique complete hosted job identity; rerunning a report does not add samples.

## Local capture and terminal collection

Tracking: [#9](https://github.com/betsudo/forge/issues/9). The native Passport
qualification gate must pass before freezing actual Linux tool inventories.
This increment supplies instrumentation and strict offline collection, not a
completed pilot producer, transport integration or a claim of minutes saved.

`scripts/capture-ci-stage.py` wraps one argument-array command with monotonic
start/end intervals, exit status and bounded raw stdout/stderr (16 MiB each).
Use one job/boot clock identity, sequential stages and fresh receipt names:

```sh
./bootstrap.sh -- python3 scripts/capture-ci-stage.py \
  --stage setup_ms --clock RUN-ATTEMPT-JOB-BOOT \
  --timeout 600 --output /absolute/evidence/setup.json \
  --plan-sha256 REVIEWED_PLAN_SHA256 --run-id RUN_ID --run-attempt 1 --job-id JOB_ID \
  -- npm ci --ignore-scripts --prefix integration/providers
```

Actual hosted capture requires the native Linux x86_64 GitHub runner context;
local capture is labelled local and cannot become a hosted comparison.
Timeout/overflow stops the owned process group and retains a failed receipt;
wrappers that start additional sessions must own their descendant cleanup.
Capture each lane's setup, actual codegen, key preparation and fresh proof test.
Capture actual transport stages too. This tool does not turn a command duration
into terminal whole-job time, nor snapshot size into measured network bytes.
Keep secrets, witnesses and proof requests out of commands/logs.

The frozen plan additionally needs a `collection` object with:

- `head_sha`, `run_attempt: 1`, `max_job_ms` and the exact ordered `schedule`
  of `{job_name,repetition,lane}` entries for every lane/repetition.
- `auxiliary_jobs`: a map from explicit job names to `collector` or `seed`. Seeds
  must finish successfully. A current collector may still run; a terminal failed
  collector prevents comparison. Auxiliary jobs remain outside measured lanes.
- `qualification` and `qualification_sha256`: retained actual native Linux
  Passport qualification, binding consumer commit and CLI/worker bytes.
- `inventories`: evidence-relative filenames keyed by `workload_sha256`,
  `toolchain_sha256`, `parameters_sha256`, hashed against the plan identity.
- `seeds`: frozen warm/partial `{key,seed_job_url,snapshot_sha256,
  payload_sha256,actual_bytes}` provenance.
  Review seed terminal success and complete/partial coverage before freezing.

Retain a receipt named `JOB_ID.json` per measured job. The schema is enforced by
`scripts/collect-ci-trial.py`: exact run/attempt/job/plan/identity, lane/repetition,
one clock domain, original captured stage files/hashes (including producer
run/attempt/job/plan context), raw SDK proof receipt/hash matching the captured
proof-stage stdout,
observed correctness/cache deltas, classified transport attempts and
`reusable_cache_published: false`. SDK counts must agree with raw successful
proof/verification/invalid-statement/corrupt-proof controls and assertions.
These receipts still require independent audit; JSON declarations alone are
not cryptographic verification.

Transport attempts must retain exact **compressed payload bytes**, excluding
headers/TLS, direction, outcome, every ordered attempt and raw receipt/hash.
Successful receipts also bind payload digest, cache key and seed/snapshot
provenance. The raw attempt envelope must be the captured transport-stage stdout,
bound to the same job/attempt/plan. Downloads must match the frozen compressed
payload hash/bytes and retain the successful Forge restore receipt for that exact
snapshot. No rounded Action log estimate is accepted. The initial collector
refuses partially transferred failures until a measured partial-byte policy is
defined. Integrity, authorization and identity failures cannot become misses.
The unavailable lane runs official generation with `cache: null`, no upload and
a classified transport refusal; it does not invent Forge misses.

Candidate upload is quarantined to the current run/attempt. Reusable promotion
requires a separate trusted terminal-success decision. The existing Action's
prior-step success gate is weaker than terminal job success; do not describe it
as a finished promotion implementation. PRs must never publish reusable entries.

Save raw GitHub run metadata and the **complete paginated** jobs response after
all measured jobs finish, including skipped, cancelled and failed jobs. Retain
all attempts separately; this initial pilot refuses rerun selection. Collection
can run offline if cancellation prevents an in-workflow collector from running:

```sh
./bootstrap.sh -- python3 scripts/collect-ci-trial.py \
  --plan /absolute/frozen-plan.json --plan-sha256 REVIEWED_PLAN_SHA256 \
  --run /absolute/raw-run.json --jobs /absolute/raw-complete-jobs.json \
  --evidence-dir /absolute/raw-receipts \
  --output /absolute/collection.json
```

The output retains the complete roster and raw-input hashes. Failed/missing jobs,
unplanned jobs, retry selection, stage overlap, wrong seed/byte counts or missing
native qualification prevent a comparison. A refused collection exits nonzero
and preserves diagnostics; it does not filter failures into a favorable sample.
Outputs are exclusive and outside the raw evidence directory, avoiding
self-referential hashes. The bounded raw metadata tree is at most 64 MiB/4096
entries; keep key archives and private proof data outside it.

Local tests use deliberately synthetic subprocess/API/transport fixtures. They
provide neither application-proof nor hosted-performance receipts. Actual
GitHub transport instrumentation, reviewed frozen Linux pilot and separately
authorized hosted execution remain open.

## Report without changing the raw inputs

### Prepare an exact payload locally

`scripts/ci-payload.py` provides the bounded compressed envelope for future
transport instrumentation. It accepts an existing Forge snapshot, not arbitrary
key directories. Pin the snapshot identity and partition independently:

```sh
./bootstrap.sh -- python3 scripts/ci-payload.py pack \
  --binary /absolute/zkir-forge --profile zkir31 \
  --snapshot /absolute/owned-snapshot --snapshot-id SNAPSHOT_SHA256 \
  --partition PARTITION_SHA256 --max-compressed-bytes 268435456 \
  --max-expanded-bytes 1073741824 --output /absolute/new-payload.tgz
```

The JSON result records exact compressed `actual_bytes`/`payload_sha256`, expanded
bytes and snapshot identity. The deterministic gzip/tar envelope retains regular
files and required directories, normalizes archive timestamps/modes/owners, and
refuses links, special files and extension headers. Both byte budgets are explicit
and at most64GiB. The independent100001-entry envelope cap includes directories;
a snapshot at the CLI file-count ceiling may therefore exceed this stricter cap.
These are local archive sizes, not network transfer measurements.

For downloaded payload bytes, use `restore` with the independently frozen
`--payload-sha256`, `--payload-bytes`, `--snapshot-id`, `--partition`, both budgets,
`--payload /absolute/download.tgz` and `--output /absolute/absent-private-store`.
The compressed size/hash are checked before extraction. Existing Forge snapshot
validation governs identity, producer/profile, database consistency and file
digests. Output publication never replaces an existing path. Private staging is
cleaned on handled failure; an abrupt process kill can leave its owned
`.forge-payload-*` directory for explicit inspection/removal after it stops.

Packing validates the original snapshot through a private restore, removes that
verification store, then hashes the exact bytes streamed into the archive against
the exact manifest consumed by verification (`restore.result.manifest_sha256`).
This requires the current Forge verifier. It does not extract another full snapshot. Restore
extracts once and validates directly into the final absent store; it does not
create an intermediate verification store. Peak expanded data is two snapshot
copies in either mode (including the caller-owned original while packing), plus
compressed payload copies and filesystem overhead. Allow corresponding headroom;
this is not a guarantee that a full Passport payload fits a standard runner.
The original snapshot is read-only and must remain stopped/owned during packing.
No automatic deletion, network upload, reusable cache promotion or GitHub
credential use occurs. Capturing the tool's stdout does not create the transport
attempt envelope expected by the collector. Seed generation, actual transfer
instrumentation and the reviewed native Linux pilot remain separate open work.

Fast tests exercise real CLI snapshots and hostile archives without keygen.
`scripts/check-ci-payload.py --real` additionally generates JSON3.1 fixture keys,
packs/restores them, requires a warm identity-preserving hit, and generates a
fresh proof with valid verification and invalid-statement/corrupt-proof controls.
It requires verified parameters and the pinned JSON3.1 worker environment.

```sh
./bootstrap.sh -- python3 scripts/report-ci-trial.py \
  --plan /path/to/frozen-plan.json \
  --runs /path/to/raw-run-rows.json \
  --output /path/to/new-report.json
```

The reporter refuses incomplete comparisons, incorrect counts and incompatible
identities. Keep failed jobs and refusal diagnostics as raw evidence; do not
silently discard them to improve a result. A successful report preserves all
paired warm-versus-uncached deltas, full-job medians and nearest-rank p95, including
negative savings. Its threshold decision uses the **median of paired savings**,
not the difference of independent medians. The output is created exclusively;
existing reports are not overwritten. Input hashes bind the report to the exact
plan and run files. No billed-minute or monetary saving is inferred.

This is evidence preparation, not an adoption decision. Before the two-week
trial, agree the workflow, start date, full correctness counts and practical
threshold with the consumer maintainer. No consumer checkout change, remote
dispatch, release, service expansion or Compact change is authorized by this guide.
Local synthetic reporter tests are not hosted measurements or proof executions.
