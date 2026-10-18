# Prepare native Linux Passport qualification

Tracking: [#5](https://github.com/betsudo/forge/issues/5),
[#6](https://github.com/betsudo/forge/issues/6),
[#7](https://github.com/betsudo/forge/issues/7).
Status: harness prepared and locally tested; **native Linux consumer execution
is pending**. Mac and ARM Docker execution cannot satisfy this gate.

The exact source is Passport `0d7bb0bc834f2d45d9fe2d84c4d022a30d648423`,
Compact 0.35.0 and the separately pinned JSON3.1 worker. The harness compares all
52 official circuit artifact sets and all 213 original compiler files; application
proofs execute two selected circuits through the official Node provider.
No other checkout or compiler implementation is modified.

On a native x86_64 Linux host with Nix flakes, build the checked-out candidate:

```sh
./bootstrap.sh -- nix build .#default --out-link .local/passport-linux-candidate
```

Obtain the official **Linux x86_64** Compact 0.35.0 archive and independently
verify its SHA-256 against trusted release provenance. Do not reuse the historical
macOS compiler hashes. Stage the archive, public pinned source closure and public
parameters; the stager verifies every downloaded file and never executes it:

```sh
./bootstrap.sh -- python3 scripts/stage-passport-linux.py \
  --compiler-archive /absolute/compact-linux-x86_64.tar.gz \
  --compiler-sha256 INDEPENDENT_ARCHIVE_SHA256 \
  --compiler-subdir . --params-base-url https://srs.midnight.network \
  --binary "$PWD/.local/passport-linux-candidate/bin/zkir-forge" \
  --output .local/passport-linux-staged
```

Set `--compiler-subdir` to the actual archive directory containing `compactc.bin`,
`zkir-v3` and the `zkir` presence probe. The fresh staged `cohort.json` records
the actual native tool/worker bytes and portable parameter identities. Its digest
freezes this run's inputs; it is **not** a previously approved compatibility
policy. Independent artifact comparison and genuine proofs create that new
policy later, for review. The stager's source and parameter hashes come from
committed evidence, not download sidecars.

Reserve at least 50 GiB free after staging/building, then use the printed cohort
digest and compiler directory:

```sh
./bootstrap.sh -- python3 scripts/qualify-passport-linux.py \
  --binary "$PWD/.local/passport-linux-candidate/bin/zkir-forge" \
  --compiler-dir /absolute/staged/compiler-archive/DIRECTORY \
  --params-dir "$PWD/.local/passport-linux-staged/params" \
  --source "$PWD/.local/passport-linux-staged/source" \
  --cohort "$PWD/.local/passport-linux-staged/cohort.json" \
  --cohort-sha256 PRINTED_COHORT_SHA256 \
  --work "$PWD/.local/passport-linux-work" \
  --output "$PWD/.local/passport-linux-result.json"
```

The runner refuses Mac/ARM/Docker before input reads or scratch creation, checks
actual native ELF/compiler/worker bytes and dependencies, installs the pinned SDK
with `npm ci --ignore-scripts`, and measures its own official/off baseline using
a monotonic clock. It reuses independent artifact comparison, cold/warm compiler
lanes and cache recovery with fresh proofs, verification, state/trace assertions
and negative controls. Final compiler-output corruption must produce the SDK's
integrity exception before exact owner repair and another fresh proof execution.
Wrong profiles/policies remain hard refusals; the default store and shared install
are untouched. Cleanup removes only owned successful lane/cache copies. Failed
runs retain their owned logs/scratch for diagnosis and cannot produce a passed
result. Do not retry into an existing scratch directory.

After independent review, pin the new qualification policy's raw digest and use
the single `compiler-local.py --mode local` invocation in the
[local adapter guide](local-adapter.md). `--mode off` retains the original official
path. The current shared Mac installation and old Mac receipt do not authorize
new Linux tool bytes. This workflow does not qualify a Nix-free portable consumer
installation or claim CI savings; generic portable installer qualification is
separate.

The manual-only `.github/workflows/passport-linux.yml` prepares the same run on
GitHub's `ubuntu-24.04` x86_64 runner. It requires explicit archive URL/digest and
public parameter URL, has a 180-minute limit, retains only receipt JSON/logs for
14 days and does not publish caches/releases. It is prepared locally; no dispatch
or hosted consumer run has occurred in this increment. This qualification is a
single correctness run, separate from the measured CI pilot.
