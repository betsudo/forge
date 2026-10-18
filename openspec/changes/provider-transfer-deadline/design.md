# A deadline independent of body polling

Set serve --download-timeout-seconds to integer1..3600, default300. It bounds
transfer lifetime starting after verification/range selection, not disk hashing
or the client's complete operation. Apply to both verified provider files and
ordinary artifact downloads through their common response adapter. A trickling
client cannot reset this deadline.

A producer owns the file and admission permit, serially reads64KiB chunks in
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
