# Backend profile design

Maintain explicit reviewed profile definitions: input dialect/version, source or registry checksum and full lock graph, tags/options, proof/parameter identities, platform, worker protocol/build/executable identity. Same-major ambiguity requires explicit selection; no semver guessing or automatic executable downloads.

Reuse the current process-isolated worker design for incompatible graphs. Parent owns leases, generation staging, validation and publication. Retain one generation at a time initially. New profiles are buildable, artifact-qualified or consumer-proof-qualified independently; release manifests must disclose only actual qualifications.

Prefer official published crates where available and independently qualified; no registry migration in this proposal. The 2026-10-16 registry query found ZKIR2.1.1 and ledger8.1.3 but no midnight-zkir-v3 crate; exact official Git pins remain valid. A registry migration changes conservative recipe/build identity and never rewrites historical records or verifier identities.

Qualification includes target consumer fixtures, cold/warm/downloaded-export actual proofs and negative controls, descriptor parity, mismatches, recovery and regeneration identity. Ledger9 transaction support stays deferred. Source citations and matrix are in the research note.
