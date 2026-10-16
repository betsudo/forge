# Midnight ZKIR Forge

Repository home: [betsudo/forge](https://github.com/betsudo/forge). Historical
issues, PRs and qualification links remain in the original repository.

Next validation: [Passport hosted CI trial reporting](docs/ci-trial.md).
The owner selected Passport; hosted savings and the two-week trial remain unmeasured.

Local CLI and initial HTTP cache for Midnight ZKIR and generated prover/verifier keys, with a
Nix-owned toolchain. Default store: `~/.midnight-zkir-forge`.

[Documentation site](https://curly-adventure-gken1jg.pages.github.io/) (GitHub sign-in and repository access required).

## Supported profiles

| Selector | JSON format | Official backend |
| --- | --- | --- |
| `ledger8-v2` | 2.0 | Ledger8 8.1.3, ZKIR 2.1.1, commit `b5d3e965…` |
| `zkir3` | 3.0 | Consumer-pinned ZKIR 3.0.0-rc.1, commit `3a7ae036…`, `ir-source[v3-generic]` |
| `zkir31` | 3.1 | Compact 0.35.0 ZKIR 3.1.0-rc.1, ZKIR commit `e82d81d2…`, ledger commit `9a8777c4…` |

Input format is detected from exact bytes; `--profile` asserts the expected
backend and rejects mismatches. Use `profile` for the default v2 descriptor and
`--profile zkir3 profile` for the exact v3 worker provenance. The v3 worker has
its own Cargo workspace/lock and source dependencies; it does not replace or
unify the v2 proof stack.

The v3 source is pinned to
[3a7ae0361d03e6eed4fc91e31f6600f334f605d5](https://github.com/midnightntwrk/midnight-ledger/tree/3a7ae0361d03e6eed4fc91e31f6600f334f605d5),
matching the inspected local Compact v3 tool configuration. It is **not** the
same binary format as the v3 RC bundled with ledger8 8.1.3, despite the same
crate version label. JSON 3.1 uses the separately pinned `zkir31` worker with
`verifier-key[v7]`; the older profiles retain `verifier-key[v6]`. The new profile
is qualified against two exact Passport account circuits; full benchmark results
and installation qualification are tracked separately in `docs/research/passport-benchmark.md`.
The shared installed CLI may predate this source: inspect its `profile` before use.
Check a consumer's exact pin and serialization;
no ledger9 transaction/network qualification is implied.

```sh
midnight-zkir-forge --profile zkir3 prepare /absolute/path/to/circuit.zkir
midnight-zkir-forge --profile zkir3 qualify
```


## Install for all local agents

From this checkout, with Nix flakes enabled:

```sh
./bootstrap.sh --check
./scripts/install-local.sh
export PATH="$HOME/.local/bin:$PATH"
midnight-zkir-forge --version
```

Add the PATH line to your shell profile and configure the same PATH in agent
launchers that do not load shell profiles. The installed executable can be
invoked from any checkout. No server or supervisor is required. Re-run the
installer after adopting a new local commit. The installer retains a Nix GC root at
`~/.local/share/midnight-zkir-forge/current`, so runtime dependencies survive
normal Nix garbage collection. No shell profile or credential file is changed.

## Use in test setup

```sh
midnight-zkir-forge prepare /absolute/path/to/circuit.zkir > artifacts.json
midnight-zkir-forge stats
```

`prepare` imports exact input bytes, generates on a miss, verifies a warm hit,
and returns JSON containing `bundle_id`, `derivation_id`, `artifact_set_id`,
`cache.hit`, timings and `export.files` (kind, SHA-256, bytes, absolute path).
The provider layout is `zkir/<name>.zkir`, `zkir/<name>.bzkir`,
`keys/<name>.prover`, `keys/<name>.verifier` and `manifest.json`.

Parameters are **offline by default**, using the official provider's verified
cache (`MIDNIGHT_PP`, else the upstream XDG/HOME default). Missing parameters
fail explicitly. To allow acquisition from the official provider:

```sh
midnight-zkir-forge --fetch-params prepare ./fixtures/assert.zkir
```

`--params-dir /absolute/parameter/cache` overrides the parameter directory.
Upstream SHA-256 validation is retained. Parameters are not copied into each
bundle and are not counted as Forge CAS bytes.

For separate registration and materialization:

```sh
midnight-zkir-forge import ./fixtures/assert.zkir
midnight-zkir-forge ensure BUNDLE_ID
midnight-zkir-forge inspect BUNDLE_ID
midnight-zkir-forge resolve BUNDLE_ID --artifact prover
midnight-zkir-forge export BUNDLE_ID --output /new/provider-layout
midnight-zkir-forge evict BUNDLE_ID --dry-run
midnight-zkir-forge evict BUNDLE_ID
midnight-zkir-forge ensure BUNDLE_ID
```

`resolve` and `export` never trigger generation. JSON goes to stdout; diagnostics
go to stderr and failures exit nonzero with a structured JSON error. Paths are
JSON values: use a JSON parser, never `eval` the output.

## Agent integration

Use Forge only where a test normally generates keys for the exact circuit.
Read the current circuit every time; `prepare` derives identity from its bytes.
Continue executing proofs, verifiers and assertions on every test run.

Python example, without a shell or string interpolation:

```python
import json, subprocess
from pathlib import Path

result = subprocess.run(
    [str(Path.home() / ".local/bin/midnight-zkir-forge"),
     "prepare", str(Path("generated/zkir/circuit.zkir").resolve())],
    check=True, text=True, capture_output=True,
)
artifacts = json.loads(result.stdout)
paths = {entry["kind"]: Path(entry["path"])
         for entry in artifacts["export"]["files"]}
# Use paths["binary_ir"], paths["prover"], paths["verifier"] in the test.
# Run the original test assertions and proof verification here.
```

Set `MIDNIGHT_ZKIR_FORGE_DIR=/absolute/cache` or `--cache-dir` for another store.
Use private temporary stores for corruption/lifecycle tests. Keep one uncached
qualification job to exercise key generation:

```sh
midnight-zkir-forge qualify
./bootstrap.sh -- cargo test --locked --test real_backend -- --ignored --test-threads=1
./bootstrap.sh -- cargo test --locked --test zkir3 -- --ignored --test-threads=1
./bootstrap.sh -- python3 scripts/check-cli.py --binary target/debug/midnight-zkir-forge
```

The bundled assert circuits are for qualification. V3 qualification uses its
separate worker and verifies the exact source profile. `qualify` generates twice and
compares bytes, then proves and checks valid/invalid statements. It caches no
proof or test result. See [the local capability contract](openspec/changes/local-cache-mvp/specs/local-artifact-cache/spec.md).

## Metrics and storage lifetime

`stats` reports request hits/misses/errors, hit rate, per-request timings,
generation milliseconds, each requested file's counts/digest/size, hit bytes,
and CAS/export size. `estimated_generation_avoided_ms` uses the last measured
generation for that recipe; it is an estimate, not a benchmark or test verdict.
`cache.elapsed_ms` measures ensure/resolve work; `prepare` import and process
startup are outside that field. Use the benchmark script for end-to-end timing.
Per-file counts describe logical artifact-set requests, not raw disk read calls.
Recent request details are capped at 100 in output; aggregate history remains
in local SQLite. Paths and metrics stay on this machine.

All writers share a SQLite immediate transaction (rollback journal, full sync): duplicate local requests join
through serialization and then verify the hit. One generation runs at a time;
callers wait up to one hour for a busy store. Process death rolls back metadata
and releases the lock. V3 workers poll parent liveness every 50ms and stop
when orphaned; this is cancellation polling, not a strict zero-overlap guarantee
with a replacement owner during crash recovery. Only the parent can publish
cache readiness. Orphan unpublished blobs/staging files may remain.

Exports are independent **copies**, persistent until their owner removes them.
Derived eviction keeps source, small identity manifests and exports. It reclaims
only unshared derived CAS objects. Existing export paths remain usable; eviction
is not a promise to reclaim every byte of disk space. Regeneration must preserve
the previous actual artifact identity for the same recipe or fail explicitly.

## Current boundary

One circuit per bundle, synchronous CLI/HTTP materialization and a trusted
single-owner store. Hosted registry policy, durable jobs, multi-host operation,
purge/GC budget, stdio, full archive/metadata import and ledger9 transaction
integration remain future scope. V3 support is
limited to the exact 3.0 profile above. No universal JS/Rust application
compatibility or production readiness is claimed. The official Rust Resolver
is exercised by the real proof qualification. See [SPEC.md](SPEC.md),
[CONTRIBUTING.md](CONTRIBUTING.md), [progress](docs/PROGRESS.md) and
[local factory](docs/factory/README.md).

## Upgrading from the first v2-only MVP

Old v2 records and immutable exports remain readable; optional v3 metadata is
omitted for old records so their integrity manifest stays unchanged. A new
Forge build fingerprint can cause a new v2 derivation once even though the
v2 backend profile string stays the same. Old exported paths remain usable;
pinned verifier identities are not silently replaced.

## Documentation, HTTP and container preview

Build the Midnight styled documentation site with
`./bootstrap.sh -- python3 scripts/build-docs.py`; serve `.local/site` using
`python3 -m http.server 8080 --bind 127.0.0.1 --directory .local/site`.
The manual Pages workflow is prepared, without publishing anything.

The initial single-owner HTTP transport adds `serve`, with loopback defaults,
explicit synchronous materialization, exact-profile cache reuse, verified
streaming downloads and optional bearer authentication (required for remote
binding). See [HTTP setup and limits](docs/http/README.md),
[OpenAPI](docs/http/openapi.json), [Linux image packaging](container/README.md)
and [basic CI/e2e workflows](container/CI.md). The full hosted registry remains
proposed. Consumer tests continue running proofs, verification and assertions.

## Compact and GitHub CI research

[Integration proposal](docs/research/compact-ci-integration.md) covers the existing
Compact adapter, current build-qualification blockers, separate build/parameter/
Forge caches, trusted snapshots, same-run fanout and measurement gates. It includes
a research-only workflow fragment and a bounded snapshot-relocation probe.
This research does not modify Compact or enable any additional workflow.

## Snapshot/restore and CI cache reuse

See [verified snapshots and CI helpers](docs/ci-cache.md) for local relocation,
partitioned GitHub cache planning and per-job hit deltas. The Nix installer also
installs `midnight-zkir-forge-ci`. Every warm-cache consumer still executes actual
proofs, verification and assertions. Compact integration remains unchanged.

See [API conventions and Midnight provider terminology](docs/api-conventions.md) for the
CLI stdin/stdout boundary, HTTP payload conventions and local/fetch provider roles.

## Agent skill for local development

Read [SKILL.md](SKILL.md) to set up Forge and integrate its artifact cache into
local circuit tests. To hand off to another agent, use:

> Read `/absolute/path/to/midnight-zkir-forge/SKILL.md` and integrate Forge into
> this checkout's local development tests. Keep actual proof generation,
> verification, assertions and negative controls running on cold and warm runs.

The skill lives with this checkout; it can be read directly without changing an
agent's global skill installation.

See [local recovery](docs/recovery.md) for failure policy, safe owner actions,
transactional metrics and local crash/retry tests. Request timing excludes final
transaction commit and process overhead; use process wall time for end-to-end measurements.

See [private installer and pinned Nix setup](docs/install-release.md) for the
local release-installer increment and immutable flake consumption. Binary release
assets remain unpublished pending per-target qualification.

Compiler consumers should read the [descriptor and error contract](docs/compatibility.md)
before accepting local or HTTP hits; a matching version string is insufficient.

Product versions use `YYYY.M.PATCH` calendar versioning. The current local candidate
is `2026.10.0`; see [milestone scope and acceptance](docs/milestones/2026.10.0.md).
A candidate version does not imply a published binary release.
