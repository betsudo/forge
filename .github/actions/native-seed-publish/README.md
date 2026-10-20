# One bounded native seed (pilot; default off)

Proper Node 24 Action; install exact locked dependencies with `npm ci --ignore-scripts`
in this directory before source planning. Runtime cache token is supplied by the
Action runner, never extracted into a shell. `github-token` is used only for
read-only complete inventory. No Rust payload/library/worker/profile change.

Inputs: enabled(false), official prepare-save receipt, verified plan key,
window JSON `{repository,run_id,trusted_ref,approval}`, fresh absolute output,
and the original binary/cache-dir/baseline plus compact-guard/compact-plan.
The keyed Compact guard and official Forge report revalidate source, tools,
parameters and store at admission, immediately before upload and after completion.
A completed upload without an acknowledged finalization reports publication as
unknown; a failed postguard preserves an acknowledged finalized side effect.
The fixed pilot is betsudo/compact branch codex/issue-679-trusted-native-seed,
sole active job `Forge / Linux candidate qualification`, one seed per ref/partition.
Snapshot path must be exactly `$RUNNER_TEMP/forge-linux-supplied-snapshot`, matching
restore path/version. No alternate archive, prefix search, delete or refresh.

Before SDK work, the official Forge restore command verifies the original snapshot ID,
partition, parameters and bytes in a disposable private store, which is removed.
The prepare-save logical delta must equal the current original report and retain
positive generation misses with zero errors; elapsed time is not a logical delta.

The stock SDK creates the upload archive; exact-source guarded hooks admit its
actual bytes before reservation and verify the same bytes before stock upload.
Complete current API inventory plus the archive must fit decimal 10 GB. Other
active/queued runs/jobs, incomplete APIs, generation exhaustion and unknown size
refuse. An explicit human-approved exclusive publication window is still required;
API observation is not a mutex against future independent writers.

Run `./bootstrap.sh -- npm test --prefix .github/actions/native-seed-publish`.
Tests use real SDK compression with fake service endpoints; no live upload occurs.
Independent trust review and actual owner-authorized same-source hosted transport
and proof consumption are required before readiness. Review the draft decision.
