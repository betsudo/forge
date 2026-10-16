# Two active reads, eight waiters, ten seconds

Preserve the fast path for an available active permit. Otherwise admit at most
eight waiting requests with a separate try-acquired semaphore. Await an active
permit for at most ten seconds; overflow/timeout returns the existing429
provider_reads_busy plus Retry-After:1. Drop the waiting permit before verification.
Waiting cancellation owns no blocking task and drops its queue permit. Active
cancellation still retains its permit in blocking verification, then the response
reader holds it through streaming. No cache DB or cache-work permit is involved.
Use deterministic held-permit/barrier controls for three-request success, overflow,
queue cancellation, timeout and recovery. Real provider reads use Promise.all and
retain manifest integrity and fresh proofs. Range semantics are unchanged.
