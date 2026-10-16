# Design

Use one standard-library Python script over a predeclared plan and raw run rows.
Hash the exact plan bytes; every row references that hash and the same exact
consumer/workload/tool/profile/parameter/runner identity. Require three or more
complete repetitions of uncached, cold, warm, partial and unavailable lanes.
One row represents one complete successful hosted job, with a unique job URL,
raw evidence digest, explicit correctness counts and sequential measured stages.

Reject missing/duplicate lanes, mismatched identity or correctness counts,
non-finite/negative numbers, request errors and contradictory cache counters.
Warm/partial lanes must record actual downloaded bytes; cold/warm are distinct
from transport unavailability. The producer remains responsible for honest
instrumentation and genuine proof execution: JSON validation cannot establish
proof correctness or publisher trust. Retain raw artifacts for independent audit.

Report full-job median and nearest-rank p95 per lane, all paired warm deltas and
whether the predeclared median-saving threshold was reached. Preserve negative
results. Do not extrapolate billed minutes, money or consumer adoption. The
reporter never runs tests, contacts GitHub, reads cache objects or changes a store.
Local fixtures test refusal behavior only and are never performance evidence.
