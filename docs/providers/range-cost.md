# Verified range download cost

Status: measured locally on2026-10-17, native macOS ARM64. Serving behavior is
unchanged: every requested file is fully verified into an anonymous snapshot
before full/HEAD/conditional/range responses. The decision is to retain this
integrity boundary and document its cost. No persistent verified marker is trusted.

## Actual key and measurement boundary

The file is the24,648,297-byte prover key for Passport's
`activate_initial_device_with_jubjub` circuit. An owned reduced-export source copy
emits only that circuit and `deposit_unshielded` through the exact official
Compact0.35 compiler. All remaining circuit bodies and pure exports are preserved.
Both emitted ZKIR files and all generated artifact bytes match the original
unchanged account's independently qualified outputs. The compiler creates its
complete compiler-produced carrier manifest/runtime metadata; no bare export or hand-written
manifest is used. Fresh Node SDK proofs, verifications, negative controls and
application assertions pass for both selected circuits.

This is a benchmark carrier, not full-account compiler or HTTP qualification. The
unchanged full account emits52circuits and exceeds the current4GiB aggregate
provider-view limit; this experiment does not alter that limit. Full-account local
Node/compiler evidence is a separate gate.

## Results

| Mode | Requests | Logical snapshot bytes | Direct reader peak logical snapshot bytes | Median loopback HTTP time |
| --- | --- | --- | --- | --- |
| Full GET | 1 | 24,648,297 | 24,648,297 | 165ms |
| Eight sequential ranges | 8 | 197,186,376 | 24,648,297 | 917ms |
| Eight ranges, two concurrent | 8 | 197,186,376 | 49,296,594 | 378ms |

Each mode returns exactly24,648,297body bytes; chunk reassembly matches the pinned
SHA256. HTTP measurements have three repetitions, authenticated actual Forge
responses, validated ETag/Content-Range/status/length and an independently pinned
compiler manifest. The reader submeasurement invokes the same provider reader,
observing actual anonymous descriptor lengths and filesystem allocation.

Logical bytes/allocated blocks are not physical device I/O counters. The measured
reader peak is not an instrumentation claim about the HTTP process: HTTP retains
two active permits independently of eight bounded waiters. The filesystem is warm,
the host is shared with concurrent qualification work, and the HTTP measurement is
loopback. These values do not establish cold-cache, internet/CDN or hosted CI
throughput. Timing differences are illustrative; the full-file-per-range workload
is the durable result. Prefer whole-file fetches or a small number of resumes.

## Reproduce

Run through Nix bootstrap, using an owned complete compiler output:

```sh
./bootstrap.sh -- cargo build --locked --example measure-provider-ranges
./bootstrap.sh -- python3 scripts/measure-provider-ranges.py \
  --binary /absolute/qualified-package/bin/zkir-forge \
  --reader target/debug/examples/measure-provider-ranges \
  --bundle /absolute/complete-compiler-bundle \
  --artifact keys/activate_initial_device_with_jubjub.prover \
  --output /absolute/new-range-receipt.json
```

The harness publishes into owned scratch, starts an authenticated loopback server,
measures full/sequential/two-concurrent lanes and cleans views/tokens/processes.
The Rust reader measures snapshots separately. Rebuilding executables changes
their qualification identity; preserve actual tool/harness hashes and obtain fresh
evidence. Existing corruption/mutation/range refusal controls remain unchanged.
