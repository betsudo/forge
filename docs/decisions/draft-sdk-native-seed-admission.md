# Draft: measured SDK archive admission (#43 / Compact #679)

Status: proposed; source qualification only. Activation requires owner operational-window approval and exact-source real transport review.

## Problem

The official snapshot cap bounds snapshot payload, while GitHub uploads a separately constructed compressed tar. Public SDK saveCache has no pre-reservation size policy. Guessing archive overhead or measuring a different tar cannot enforce aggregate 10 GB admission.

## Decision

Use locked @actions/cache 5.0.5 in a proper Node 24 Action so the platform supplies its runtime service token. Guard all 21 installed SDK JavaScript/package files by committed byte hashes. A process-local size-function hook observes the exact SDK-created archive before CreateCacheEntry; a second upload wrapper verifies the SDK uploads the same admitted path/size/hash before delegating stock upload. No archive/service protocol is replaced. Preserve SDK cache version/path behavior. Unknown/mutated SDK or source/proof/window/API/budget state refuses; swallowed SDK errors never become publication success.

At admission, inspect complete current cache/run/job API pages. One pilot seed per trusted ref/partition, actual archive<=256 MiB and retained+actual<=decimal 10 GB. No deletes. The operator window is an explicit human-approved assumption plus observed writer audit, not a global atomic mutex; future independent writers remain outside this tool's control. Source-only success grants no publication authority.

## Consequences

This intentionally internal seam requires exact source pins and call-order/fake-service tests for every SDK update. Npm lock/SRI and ignore-scripts install precede native source planning; a proper Node Action consumes installed immutable auxiliary source afterward. Real SDK local tests create actual tar/zstd archives and fake only service/upload endpoints. Denied archives reserve/upload nothing. Actual hosted archive size/transport/seed restore and genuine proof consumption remain separate qualification.
