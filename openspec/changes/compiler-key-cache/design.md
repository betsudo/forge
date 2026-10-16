# Compiler boundary design

At the inspected Compact source, current JSON ZKIR is emitted before compile-many
and before TypeScript/integrity-manifest generation. Forge reuse must materialize
binary IR and keys at this exact boundary. Normal manifest generation then hashes
the actual files. --skip-zk plus post-compile key injection is not equivalent.

Propose --zk-key-cache=off|local|fetch with default off. The proposed flag is not a
Forge CLI option and is not present in Compact today. An exact independently
qualified policy supplies backend/worker/parameter/compiler premises; observed
producer descriptors cannot qualify themselves. The config explicitly supplies
absolute native tools and local store, or immutable provider origin information.
No implicit profile inference from tool name zkir-v3 or a ledger family label.

Explicit flag/config values override documented same-purpose defaults; legacy
test-shim environment does not silently enable production compiler reuse. Off
uses the original tool without initializing Forge. local invokes existing
prepare/export semantics on current source; fetch resolves verified complete
provider views, with networking explicit. fetch remains a proposal until issue #4
provider qualification and implementation. Read-only fetches never generate.

Default fetch failure policy is error. Optional explicit generate fallback only
permits documented availability outcomes; auth, integrity, compatibility, schema
and changed-source failures are always hard errors. Local prepare performs normal
verified generation on a genuine miss. Parameter fetching stays separately opt-in.
One writer and one generation at a time; no new queue, registry or cache identity.

Preserve compile/compile-many arguments, normal circuit names, binary IR beside
current ZKIR and prover/verifier keys in the requested key directory. Verify and
stage every selected output before publishing; private copies, never writable
links into Forge exports/CAS. Each file may be atomically replaced, but the set
is not claimed transactional: failures stop compilation, leave no newly completed
compiler manifest, and require cleanup/retry. Prior existing manifests must not
be mistaken for success. reject symlinks, aliases and changed source; never
publish partial output as a ready set. Original compiler output limitations and
apostrophe path escaping are documented, not silently fixed in another checkout.

Actual implementation and compatibility qualifications are acceptance gates in
issues #4–#7. This contract does not weaken existing exact-build allowlists, modify
Compact or establish JSON3.1 compatibility for its old v2-only test adapter.
