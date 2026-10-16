# Official backend profiles and published crates

Status: researched 2026-10-16; profile expansion remains proposed. Ledger9 transaction support is deferred. Supporting a circuit IR/key serialization does not establish support for a ledger transaction, network or Midnight.js release.

## Observed compatibility matrix

| Profile/family | Official source | Actual scope | Forge status |
| --- | --- | --- | --- |
| Ledger8 8.1.3 / ZKIR2.1.1 | `midnight-ledger` revision `b5d3e965a18e4cac17fac4f38446fc55c524439a` | Existing v2 profile; `ir-source[v2]`; locked proof graph | Retain existing pin and qualification |
| Consumer ZKIR3.0 | `midnight-ledger` revision `3a7ae0361d03e6eed4fc91e31f6600f334f605d5` | Existing separate worker; JSON3.0, `ir-source[v3-generic]` | Existing exact worker only; no generic ledger9 claim |
| Ledger8 bundled v3 RC | 8.1.3 source, `midnight-zkir-v3` 3.0.0-rc.1 | Different `ir-source[v3]` family; proof-server experimental feature matters | Not interchangeable with current worker |
| Split newer ZKIR | `midnight-zkir` revision `33fda96d423496166a891043449ecde1c22f513c` | 3.1.0-rc.1 with different dependency graph | Research candidate; not supported by current profile |
| Ledger9 consumer/server | Exact passport lock and server image to be recorded by consumer study | Requires separate IR, serialization, params and actual proof qualification | Deferred pending exact consumer evidence |

Evidence for existing qualified profiles is the repository's [v3 design](../../openspec/changes/zkir3-cache/design.md), manifests and local receipts; this research does not repeat or broaden qualification. Upstream sources: [ledger8 manifest](https://github.com/midnightntwrk/midnight-ledger/blob/b5d3e965a18e4cac17fac4f38446fc55c524439a/zkir/Cargo.toml), [consumer v3 source](https://github.com/midnightntwrk/midnight-ledger/tree/3a7ae0361d03e6eed4fc91e31f6600f334f605d5), [split manifest](https://github.com/midnightntwrk/midnight-zkir/blob/33fda96d423496166a891043449ecde1c22f513c/zkir/Cargo.toml), [proof-server feature dispatch](https://github.com/midnightntwrk/midnight-ledger/blob/b5d3e965a18e4cac17fac4f38446fc55c524439a/proof-server/src/versioned_ir.rs).

## Registry availability

Direct crates.io API queries on 2026-10-16 returned non-yanked `midnight-zkir` 2.1.1 / 2.1.0 / 0.0.0, `midnight-ledger` 8.1.3 as newest listed ledger version, `midnight-transient-crypto` 2.1.1 as newest listed version, and `midnight-proofs` versions including 0.8.3 and 0.7.3. `midnight-zkir-v3` returned HTTP404. Thus a published official v2 crate exists, while this inspection did not find a published crate replacing the exact current v3 worker pin. Newer proof crate numbers alone are not a compatible graph. Sources: [ZKIR registry API](https://crates.io/api/v1/crates/midnight-zkir), [ledger registry API](https://crates.io/api/v1/crates/midnight-ledger), [transient registry API](https://crates.io/api/v1/crates/midnight-transient-crypto), [proofs registry API](https://crates.io/api/v1/crates/midnight-proofs), [v3 lookup](https://crates.io/api/v1/crates/midnight-zkir-v3). These are time-stamped observations, not guarantees of future registry state.

Do not replace current Git pins as part of research. A later registry migration must compare package provenance/content, lock the complete transitive graph/checksums, and run actual generation, imported/warm-key proofs and negative controls. Switching source/lock changes conservative build identity even when published source is equivalent. Never rewrite old recipe/output IDs to obtain a hit. Use the ZKIR crate and required crypto libraries directly for key generation; the full ledger crate is needed only for a demonstrated transaction/API dependency.

## Proposed scalable model

Retain a small explicit registry of compiled, reviewed profiles. Each profile declares exact input major/minor, dialect, parser/tagged serialization, official revision or registry package checksum/lock digest, proof-system and parameter identities, options, worker protocol and executable hash. Runtime dispatch may identify candidates from JSON version, but selection must compare all consumer-required premises. Multiple same-major profiles require an explicit profile/descriptor; ambiguous input must refuse. No auto-download of executable workers, semver-based guessing, format conversion or silent fallback.

Keep incompatible graphs in independently built worker workspaces/lockfiles. Reuse existing one-shot process protocol and parent-controlled publication; add no plugin loader, shared cryptographic trait-object layer or distributed scheduler. Parent checks exact worker descriptor and outputs before publishing readiness. Bound one generation at a time initially. Install packages may include only their declared, separately qualified worker set.

Each added profile needs macOS/Linux qualification for the platforms it advertises: genuine fixture from the target consumer, cold generation, exact descriptor parity, warm exported/downloaded keys used in real proofs, invalid statement/corrupt proof rejection, concurrency/crash recovery and eviction/regeneration identity preservation. Pin actual verifier bytes, not crate labels. A matching source version alone does not authorize reuse across workers, feature flags or architectures. The profile matrix must distinguish buildable, artifact-qualified and consumer-proof-qualified status.

No dependency or pin was changed and no new profile was compiled in this research. Ledger9 transaction/network support and the newer split graph remain deferred until a separate reviewed implementation increment.
