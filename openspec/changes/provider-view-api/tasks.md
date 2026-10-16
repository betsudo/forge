# Tasks

- [x] Research actual compiler/SDK metadata and trust guarantees.
- [x] Define local publication/read contracts and failure boundaries.
- [x] Implement strict immutable view publication and HTTP reads.
- [x] Add malformed/corruption/path/metadata/publication/conditional tests.
- [x] Run genuine Node/Fetch provider proof controls against the actual API.
- [x] Independent identity/concurrency review and meaningful local checks.
- [x] Document limits/research, record receipts and sign local delivery; no push.

Evidence: `docs/evidence/provider-view-adapter-local.json`, Rust provider-view12tests,
adapter12failuretests, full Rust tests/Clippy and HTTP/recovery/snapshot checks.
Independent review corrected source-swap and skipped-hook gaps; exact scope and
limits are recorded in `docs/PROGRESS.md`. Local commits only; no push.
