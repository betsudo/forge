# Backend profile design

Maintain explicit reviewed profile definitions: input dialect/version, source or registry checksum and full lock graph, tags/options, proof/parameter identities, platform, worker protocol/build/executable identity. Same-major ambiguity requires explicit selection; no semver guessing or automatic executable downloads.

Reuse the current process-isolated worker design for incompatible graphs. Parent owns leases, generation staging, validation and publication. Retain one generation at a time initially. New profiles are buildable, artifact-qualified or consumer-proof-qualified independently; release manifests must disclose only actual qualifications.

Prefer official published crates where available and independently qualified; no registry migration in this proposal. The 2026-10-16 registry query found ZKIR2.1.1 and ledger8.1.3 but no midnight-zkir-v3 crate; exact official Git pins remain valid. A registry migration changes conservative recipe/build identity and never rewrites historical records or verifier identities.

Qualification includes target consumer fixtures, cold/warm/downloaded-export actual proofs and negative controls, descriptor parity, mismatches, recovery and regeneration identity. Ledger9 transaction support stays deferred. Source citations and matrix are in the research note.


## Accepted implementation slice for issue #13

The owner's finish-Passport instruction authorizes additional isolated JSON3.1
support. Pin official split ZKIR tag zkir-3.1.0-rc.1 at
`e82d81d25aabcc5f5092e2bd559083487f577914`, including its exact official lock graph
and ledger patch revision9a8777c4d035fc7f38ae286bcf5f8656668efd9f. Preserve existing
v2 and3.0 pins unchanged. Use selector zkir31, format midnight-zkir-v3.1-json and
separate worker executable/workspace. Dispatch only exact known JSON major/minor;
wrong explicit selectors refuse. Serialization includes actual verifier-key[v7],
not the existing profiles' v6. Bind actual worker executable/runtime, options and
verified parameters in the existing recipe scheme. Snapshots declare additional
worker provenance additively while legacy-only manifests retain their bytes.
