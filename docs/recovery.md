# Local failure recovery and implementation review

Forge remains a synchronous CLI with a private filesystem store. HTTP and CI
helpers use the same storage rules. This review added no dependencies, service
processes, retry scheduler or automatic corruption repair.

## What was simplified

- Exports and snapshots share one atomic no-replace directory publication helper.
  An export publication race cannot replace another owner's empty directory.
- Ensure, resolve and HTTP download accounting use their existing SQLite writer
  transaction. Ensure commits new readiness and successful accounting together,
  rather than releasing and reacquiring the writer lease for metrics.
- Eviction relies on `save`'s existing derivation-readiness update. It still commits
  unavailability before unlink and rechecks references under the cleanup lock.
- Snapshot validation parses each export manifest once and records declared paths,
  instead of reparsing it for every exported file. All identity/inventory checks remain.

CAS reads check expected length before allocation and bound the subsequent read.
Existing CAS objects use streaming verification before reuse. A sparse oversized
object is refused rather than loaded into memory first. Relative export destinations
are resolved from the caller's working directory before staging/publication.

## Failure policy

Missing parameters, corrupt CAS, changed output identities and damaged exports are
explicit failures. Forge does not silently re-key under an existing identity.
Failed operation accounting is best effort: its own failure is attached to the
original error, preserving the actionable cause. Successful accounting is required
for an operation to commit; if it fails, newly written metadata rolls back.

Files already published before a failed transaction can remain as unreferenced CAS
or complete immutable exports. Retry verifies them before reuse; their presence
alone does not make a bundle ready. A previously ready bundle stays ready if a later
request fails without changing its metadata, but reads still verify bytes.

`cache.elapsed_ms` and the request metrics include parameter verification, writer
lock wait, integrity checks and export work, but exclude the final transaction
commit and process startup/shutdown. Capture process wall time separately for
end-to-end latency, especially when other readers can delay commit.

## Operator actions

| Failure | Local action |
| --- | --- |
| Missing/unavailable parameters | Select the correct verified parameter directory, or explicitly permit official retrieval with `--fetch-params`, then retry. |
| Interrupted writer | Let the next normal Forge open perform SQLite recovery, then retry the same request. Do not delete SQLite journals or change the pinned identity. |
| Missing export directory, intact CAS | Retry `prepare`/`ensure`; Forge reconstructs the copied export and returns a verified hit. |
| Damaged copied export, intact CAS | Stop consumers of that export, identify the exact owner-controlled directory from the previous `export.base`, and remove or move aside that directory. Retry reconstructs it from verified CAS without key generation. Eviction alone retains exports and cannot repair the damaged copy. |
| Missing/corrupt derived CAS | Investigate first. For an intentional rebuild, explicitly evict the affected bundle and retry generation. Shared references can retain a corrupt object; do not delete shared blobs blindly. Regeneration must preserve the pinned output identity. |
| Corrupt source CAS or SQLite | Preserve evidence and restore a known trusted snapshot into a new absent store, or register the original exact source in a separate store. No automatic database repair is provided. |
| Export destination obstacle | Choose a new destination or have its owner correct the obstacle. Forge does not overwrite unrelated files or incomplete exports. |

Use a private temporary store for fault injection. Do not run these probes against
`~/.midnight-zkir-forge` or a shared HTTP service. Orphaned staging/CAS/exports have
no automatic GC yet. This slice does not add multi-host coordination or a shorter
CLI lock timeout. Linux publication runtime remains unqualified on this macOS host;
process-kill tests do not establish power-loss or failing-disk durability.

## Local validation

```sh
./bootstrap.sh --check
# Verified k4 parameters required; no network retrieval by default:
./bootstrap.sh -- cargo build --locked --example qualify-http-fixture
./bootstrap.sh -- python3 scripts/check-recovery.py \
  --binary target/debug/zkir-forge --real
```

Fast checks exercise primary-error preservation when accounting also fails,
transaction rollback, oversized-object refusal and no-replace publication. The
real recovery suite covers both exact profiles: missing parameters, metrics-write
faults, partial accounting rollback, export obstacles, killing a writer after
export publication while COMMIT is reader-blocked, SQLite reopen/retry, damaged
export removal and warm reconstruction. Recovered keys must retain their output
identity and pass actual proof verification plus invalid-statement/corrupt-proof
controls. Snapshot and HTTP proof suites remain separate regression checks.

See the issue #9 evidence in `docs/evidence/local-recovery-*.json` and the
[OpenSpec contract](../openspec/changes/local-recovery/design.md).
