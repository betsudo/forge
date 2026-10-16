# Complete immutable views

Expose `publish-view INPUT --manifest-sha256 HASH --provider-root ROOT` locally.
The expected raw compiler-manifest SHA is an explicit independent trust input.
View ID equals that hash; stage copied complete manifest-covered output and
publish ROOT/HASH atomically without replacement. Existing matching views are
idempotent only after full verification. Corrupt existing data is never repaired
or replaced silently. Provider roots are separate from CAS/store/snapshots.

Strictly validate duplicate-free bounded manifest-version1, safe tree components,
regular nonsymlink declared files, sizes/digests, no undeclared siblings except
compiler/contract-manifest.json, compiler contract-info runtime/compiler/language
metadata and matching circuit source/binary/prover/verifier coverage. Preserve
raw manifest, contract-info and generated contract files, including formatting.
Unsupported tree/schema fails; do not adopt the pinned SDK's permissive parsing.
A caller hash establishes consistency with trusted compiler output, not proof of
publisher authenticity. Bare Forge exports and skip-zk bundles are insufficient.

`serve --provider-root ROOT` adds GET/HEAD `/views/{id}/{*file}`. Existing auth
runs before lookup. Resolve only the verified manifest inventory, never arbitrary
filesystem paths. Verify before conditional/range responses; spool a bounded
verified anonymous file and stream that same private descriptor to prevent
verify/reopen races. Admission, errors, private cache policy, HEAD/ETag/Range and
nosniff reuse existing HTTP conventions. Initial representation is identity only;
no untested compression, browser CORS wildcard or TLS/CDN qualification claim.

Real SDK Node/Fetch default integrity with expectedManifestHash must consume the
published view. A closed-loop genuine proof/verification/assertion/negative test
uses retrieved bytes. Tests cover malformed trees, metadata/runtime conflict,
corruption even on HEAD/304/range, missing files, unauthorized reads, staged
publication, same-ID collision and mutation after publication. Full provider
behavior need not imply any particular circuit compiler/backend compatibility.

PR12 read/recovery amendment: see `provider-read-recovery`. Ordinary reads verify
pinned metadata/inventory and requested-file bytes, while full audits and all
publication/reuse paths verify every file. A corrupt unrequested file can leave
unrelated reads valid; dedicated read permits isolate cache admission.
