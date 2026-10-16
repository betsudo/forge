# One key-generation boundary

Ship a Forge-owned Python wrapper for qualified Compact0.35.0/JSON3.1 locally.
This is not a newly shipped upstream flag. Explicit off runs the actual official
compiler unchanged and never initializes Forge. Explicit local uses a private
process-only PATH shim for zkir-v3 compile-many, invokes the actual compiler
binary, and restores the ordinary official tool for unknown commands. No binary,
checkout or global PATH is modified. The normal compiler still emits current
ZKIR, TypeScript, contract-info and its final integrity manifest after keygen.

Require a consumer-owned exact qualification receipt plus independent digest
anchor. Pin actual compiler/native tool/Forge/matched-worker bytes, backend/
format/serialization/recipe and parameter premises; observed producer facts cannot
qualify themselves. Refuse mismatched tools/overrides/current input, unsafe output
aliases/symlinks, binary-only stale inputs and changed source. Parameter downloads
stay off. Default store and existing explicit/env overrides remain unchanged.

At compile-many, snapshot current exact sources, call existing prepare on one
source at a time, validate complete descriptors/bytes against the independent
policy and copy private staged binary IR/prover/verifier outputs. Verify source
stability and preserve normal compiler exit/manifest ordering. Fail before final
compiler manifest on errors; no fallback after integrity/profile/schema errors.
No multi-directory transaction is claimed; failed builds require ordinary cleanup.
Actual proofs/assertions remain in the caller's tests, never inferred from hits.

Qualify off/cold/warm real compiler output, identical original compiler-manifest
bytes and genuine SDK proof controls. Negative tests exercise wrong policy/tool/
parameters, missing sources/symlink outputs, corrupt cache exports and interruption.
Do not claim Linux or full Passport coverage from a native developer-host fixture.
