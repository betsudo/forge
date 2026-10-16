# Scoped local I/O evidence

A small Rust example invokes the actual provider reader on an existing pinned
compiler view. Compare one full transfer with eight sequential ranges and eight
ranges in batches of two. Observe each returned snapshot's actual descriptor
length and allocated blocks, measure wall time, return exactly the selected range
to a sink and record total/peak live logical snapshot bytes. This measures logical
I/O and allocation, not physical disk-device counters. Keep at most two live
snapshots, with metadata checking and requested-file full hashing unchanged.
A Python harness repeats the three modes through an isolated authenticated Forge
HTTP process and counts actual response body bytes, timing and response codes.
No network throughput, cold-page-cache, browser/CDN or CI saving is inferred from
loopback. Corruption/mutation/range semantics retain existing recovery controls.
Retain the implementation unless an independently reviewed optimization preserves
all verification/TOCTOU/resource guarantees and demonstrates value.
