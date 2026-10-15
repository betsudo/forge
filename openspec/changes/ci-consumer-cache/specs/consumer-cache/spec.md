# Consumer cache requirements

## Requirement: exact recipes with bounded transport

The implementation MUST use exact derivation identity for key reuse and retain
platform/tool/profile/parameter snapshot partition boundaries. It MUST bound
snapshot bytes, avoid stats-only saves, isolate writable stores per job and use
one trusted publisher without database merging.

### Scenario: changed source in a compatible workload

Given a trusted snapshot in the exact partition, when one circuit changes, then
unchanged recipes are verified hits and the changed recipe generates normally;
all selected tests still execute. A new bounded snapshot is eligible only after
successful tests and generation growth, under a fresh immutable GitHub key.

### Scenario: untrusted or corrupt cache

Given a PR job or a corrupt present snapshot, then PRs cannot publish trusted
seeds and corruption is an explicit failure. An absent remote cache starts cold;
corruption is not silently accepted or relabeled as a miss.

## Requirement: provider contract qualification

An optional provider view MUST be qualified with the selected actual NodeZkConfigProvider
or FetchZkConfigProvider and its manifest/runtime rules. Management endpoints MUST
remain distinct. Loopback HTTPS MUST retain normal TLS trust and hostname validation.

### Scenario: browser provider reads artifacts

When a configured origin fetches a circuit, then paths, decoded bytes, content
hashes and key identities match local exports. Unknown circuit/path traversal,
wrong profile, disallowed origin and invalid TLS are refused.

## Requirement: representative consumer evidence

DID v0.7.0 and the recorded Passport commit MUST be separately preflighted and
benchmarked before CI speedup claims. The benchmark MUST preserve actual proofs,
verification, assertions and negative controls in every measured lane. Offline
simulator tests alone MUST NOT count as proof-bearing consumer qualification.

### Scenario: unsupported compiler/profile

When Passport requires unavailable Compact0.35.0 or an unsupported exact ZKIR
profile, then qualification reports blocked with the missing pin/tool and makes
no speedup claim; it never substitutes a convenient fixture or another compiler.
