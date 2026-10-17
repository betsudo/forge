# Bounded provider burst admission — #28

A single SDK can fetch binary IR, prover and verifier concurrently. Immediate
refusal at two active reads makes a normal burst unreliable. Add a small finite
wait while retaining the current verification/snapshot/stream resource bound and
independent cache admission. No hosted/multi-owner scalability claim is added.
