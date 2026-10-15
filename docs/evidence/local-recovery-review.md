# Local reliability review — 2026-10-15

Issue #9; independent read-only reviewer `/root/reliability_review`.

Addressed findings:

- Metrics failures could mask the primary error, or report failure after committing
  readiness. Success accounting now shares the operation transaction; failed
  accounting attaches context to the original failure.
- CAS `read` and existing-object comparisons could allocate an oversized corrupt
  file before checking its expected size. Reads are length-checked/bounded and
  existing objects are stream-verified.
- Export publication used a separate replacing rename. It now shares the atomic
  no-replace directory primitive with snapshots; relative destinations work.
- Duplicate eviction readiness SQL and repeated snapshot manifest parsing removed.
- Missing recovery coverage for damaged exports is addressed by explicit
  owner-directed removal/reconstruction tests; no automatic corruption repair.

Final independent review found no blocking identity/concurrency regressions. Real
v2/v3 recovery tests verify pinned output identities, reader-blocked-COMMIT writer
termination/reopen/retry, accounting rollback, export obstacles and real proofs
with invalid-statement/corrupt-proof controls. Existing v2 (3) and v3 (2) real
backend tests, full bootstrap checks, snapshot/HTTP real e2e, formatting and Clippy
pass. The relative-path test initially compared a canonical /private/var path to
macOS's /var alias; canonicalizing the private test root corrected the assertion.

Native execution: aarch64-darwin. Linux runtime, power-loss and actual disk-full
recovery are not qualified by this run. SQLite trigger faults model accounting
write failure. No package reinstall, Compact access, push or hosted CI occurred.
