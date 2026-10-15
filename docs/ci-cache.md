# Verified snapshots and CI cache helpers

Forge snapshots move cache artifacts between isolated jobs. They never cache test
results: keep proofs, verification, assertions and negative controls running after
both cold generation and warm restore. Compact is unchanged by this implementation.

## Local snapshot and restore

Install both commands with `./scripts/install-local.sh`. The Nix package includes
`midnight-zkir-forge` and `midnight-zkir-forge-ci` (Python is supplied by Nix).

```sh
midnight-zkir-forge --cache-dir "$HOME/.midnight-zkir-forge" snapshot \
  --output /absolute/existing-parent/forge-snapshot --max-bytes 1073741824
midnight-zkir-forge --cache-dir /absolute/existing-parent/new-job-cache restore \
  /absolute/existing-parent/forge-snapshot --max-bytes 1073741824
```

Both destinations must be absent, even if an existing directory is empty. Restore
requires an explicit `--cache-dir` or `MIDNIGHT_ZKIR_FORGE_DIR`. Parent directories
must exist. Source and destination must be disjoint. Keep the shared default store
out of CI: each job restores to its own private directory.

A snapshot is a directory containing `snapshot.json`, a standalone SQLite backup,
CAS objects and persistent export copies. Let GitHub cache/artifacts provide
compression; do not archive a live cache directory yourself. Forge acquires its
SQLite writer lease, backs up committed metadata, checks referenced bytes and
copies under that lease. Readers can coexist; other writers wait. `--wait-seconds`
defaults to 30. A busy/failed operation publishes no partial destination. Restore
validates in a private sibling directory and atomically publishes without replacing
any competing destination. Staging from an abruptly killed process may remain as
an unreferenced temporary sibling; it is never a ready cache.

Inventory paths, file sizes, SHA-256, bundle/recipe/output identities, exact SQLite
schema, ready references, immutable export manifests, profile and worker provenance
are checked. Unsafe paths, symlinks, extra/missing files and incompatible producers
are rejected. Defaults are 10 GiB of payload, 100,000 tree entries and 16 MiB of
manifest metadata. `--expected-id SHA256` pins a receipt obtained separately;
`--partition SHA256`, `--profile` and repeated `--parameter-digest SHA256` restrict
scope before publication. A snapshot preserves historical recipes, evicted states
and inherited statistics; it relocates provider exports when used in the new store.

Checksums detect corruption, not a malicious publisher who can rewrite all bytes
and digests. Consume snapshots only from trusted producer/workflow scopes. Current
producer matching is deliberately conservative; snapshot format v1 has no migration
or merge support. Snapshots can contain circuit sources, keys, export metadata and
historical request paths. Use private cache/artifact access appropriate to the input.

## Plan a partition and run a job

From a source checkout the equivalent helper is
`python3 scripts/forge-ci.py --binary /absolute/path/to/midnight-zkir-forge`.
The installed wrapper supplies its matching Forge binary automatically.

```sh
midnight-zkir-forge-ci key --workspace "$PWD" \
  --params-dir "$MIDNIGHT_PP" --parameter bls_midnight_2p4 \
  --input fixtures/assert.zkir --profile ledger8-v2 \
  --workload 'assert fixture; proof controls enabled' \
  --generation local-1 --output /tmp/forge-key.json

# First let actions/cache/restore or download-artifact populate this snapshot path.
# Missing snapshot is a cold cache; a malformed present snapshot is an error.
midnight-zkir-forge-ci restore --key /tmp/forge-key.json \
  --snapshot /tmp/downloaded-forge-snapshot --cache-dir /tmp/new-forge-job \
  --max-bytes 1073741824
midnight-zkir-forge-ci baseline --key /tmp/forge-key.json \
  --cache-dir /tmp/new-forge-job --output /tmp/forge-baseline.json

# Run the ordinary test suite with its already-qualified Forge adapter here.
# Example cache request only (this command does not itself test proofs):
midnight-zkir-forge --cache-dir /tmp/new-forge-job --params-dir "$MIDNIGHT_PP" \
  prepare fixtures/assert.zkir --name proof

midnight-zkir-forge-ci report --key /tmp/forge-key.json \
  --cache-dir /tmp/new-forge-job --baseline /tmp/forge-baseline.json
```

Use fresh job-owned paths, not reusable `/tmp` names from this example. Planning
metadata and baseline files must stay outside the store and are create-only.
Declare every parameter file and generated circuit/other workload input; repeated
`--input` and `--parameter` flags are supported. Include selection and compiler flags
in `--workload`. Parameter hashing is key identity, not official parameter
verification: actual generation still uses the upstream verifying provider.

The partition binds OS/architecture, actual Forge binary SHA, root/selected backend
provenance, worker identity and actual parameter bytes. The workload hash binds
sorted declared input bytes and workload flags. Generation is a unique bounded
suffix (for example run ID plus attempt). Restore prefixes relax workload and then
stay within the exact partition; they never cross profiles, tools or parameters.
Every later operation rechecks current tool, parameter and workload identities.
Metrics are deltas from the post-restore baseline, so historical hits are excluded.
Store replacement/relocation and counters moving backwards are errors. Misses count
logical requests, not unique derivations. Avoided generation time remains an estimate.

## Wire into GitHub Actions

Use separate caches for Rust/Nix builds, verified public parameters and Forge
snapshots. The helper does not call GitHub, upload, execute tests or grant authority.
The caller supplies the declared inputs and trusted ref. Do not save from pull
requests, forks, feature branches, failed tests or `pull_request_target` executing
untrusted code. Restrict publication with workflow conditions and GitHub's own
branch/cache scopes; environment variables and `--tests-passed` are planning inputs,
not a security boundary.

1. Build/install the pinned tool and obtain verified parameter files.
2. Run `key` with `--generation "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"` and optionally
   `--github-output "$GITHUB_OUTPUT"`. Outputs include `primary`, `partition` and
   `restore_keys_json` (an ordered JSON array).
3. `actions/cache/restore` restores only a **snapshot** directory, using `primary`
   and newline-joined prefixes from `restore_keys_json`. Pass it to helper `restore`
   into a different absent job-local cache. Restore before `baseline` creates it.
4. Take `baseline`; run all real tests with the job-local Forge root; run `report`.
5. On explicit trusted branch push/manual runs **after test success**, prepare:

```sh
midnight-zkir-forge-ci prepare-save --key "$RUNNER_TEMP/forge-key.json" \
  --cache-dir "$RUNNER_TEMP/forge-job" \
  --baseline "$RUNNER_TEMP/forge-baseline.json" \
  --snapshot "$RUNNER_TEMP/forge-save" --max-bytes 1073741824 \
  --trusted-ref refs/heads/main --tests-passed > "$RUNNER_TEMP/forge-save.json"
```

6. Only when that receipt has `publish: true`, use `actions/cache/save` with its
   exact `key` and snapshot path. `publish: false` explains no generation growth,
   errors, untrusted event/ref, missing test confirmation or excess budget. A present
   corrupt/incompatible snapshot is a hard error; do not turn it into silent success.
   A unique save key avoids GitHub cache immutability blocking later growth. An
   all-hit job does not save another copy. Existing global cache retention remains
   the workflow owner's responsibility; this helper bounds each snapshot only.

Pin Actions by reviewed full commit SHA. For a matrix, one trusted producer can
publish the stopped snapshot via an artifact; each consumer downloads independently
and restores to a private root. Avoid a shared SQLite writer across runners.
No consumer adapter or Compact workflow is changed here. Consult the
[Compact research](research/compact-ci-integration.md) for its existing exact-build
allowlist and separate future consumer qualification requirements.

## Local evidence

`./bootstrap.sh --check` includes the fast snapshot/helper e2e suite. To prove
restored v2 and v3 keys, with verified local k4 parameters available:

```sh
./bootstrap.sh -- cargo build --locked --example qualify-http-fixture
./bootstrap.sh -- python3 scripts/check-snapshot.py \
  --binary target/debug/midnight-zkir-forge --real
```

The real suite runs cold generation, budget refusal, trusted save preparation,
restore, warm hits, genuine proof verification and invalid-statement/corrupt-proof
controls for both exact profiles, plus evicted identity regeneration. It performs
no remote cache uploads and does not invoke Compact.
