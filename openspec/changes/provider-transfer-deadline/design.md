# A deadline independent of body polling

Set serve --download-timeout-seconds to integer 1..3600 (base, default 300) and
--download-min-bytes-per-second to a positive integer (default 1048576). Total
lifetime is min(3600, base + ceil(response_length / minimum_rate)) seconds, with
saturating arithmetic. A full 1GiB response gets 1324 seconds by default; a range
uses its selected response length. This is a configured rate allowance, not a
measured-progress idle timeout. It bounds transfer lifetime after verification/range
selection, not disk hashing
or the client's complete operation. Apply to both verified provider files and
ordinary artifact downloads through their common response adapter. A trickling
client cannot reset this deadline.

A producer owns the file and admission permit, serially reads 256KiB chunks in
spawn_blocking and sends through a one-slot channel. Its complete future runs
under a total timeout and selects receiver closure for disconnect cancellation.
After queuing the final chunk, the producer waits for a one-shot acknowledgment
that the body consumed its declared length. This keeps the deadline active for
small unpolled bodies and queued tails. The body owns only bounded memory and
the acknowledgment sender, not a file or permit. Deadline/cancellation
drops the producer even if the body is never polled. Already-running blocking
reads keep the file and permit until they finish; never release a spool permit
while a blocking task still owns its disk allocation. Do not promise cancellation
of stuck kernel I/O. No unchecked reopen, trusted-marker cache or second spool.

Expiry marks the body failed and closes the producer; queued bytes are verified
but an unfinished response errors/truncates, never reports successful delivery.
GET/range must restart explicitly. HEAD/304/416 have no retained producer. Keep
finite waiter rules, auth, error classification and generation admission intact.

Unexpected channel closure with remaining bytes is UnexpectedEof; complete bodies
keep clean EOF even after their lifetime. Expiry logs size and effective seconds
without identity/path/token information. Both CAS and provider files use this
policy intentionally. Library callers receive validation before storage startup.
