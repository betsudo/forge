# Design

Extend the existing Linux installer workflow with explicit material-only dispatch/call. PR portable qualification remains unchanged. The fixed public d64 payload and independent Rust1.98.1 root are built through Nix; export all runtime, source and tool roots needed by Compact's existing independent derivation checks. Record source/platform/run identity, root derivation, NAR hashes and actual executable hashes. Upload bounded-retention same-run material; caller verifies service artifact digest before import and rechecks inventory. No relocation or qualification bypass. No keys, SRS or cached verdicts included.

Reusable calls require an explicit immutable producer-source SHA matching the reviewed workflow implementation. Artifact run identity belongs to the caller, so no cross-repository token is needed. Material completion is not proof or Compact qualification. Existing Nix/source checks remain mandatory after import.

## Observed source-set failure and repair

Run39288493823 at6098556 failed the retained source/derivation equality guard after the payload build. Pinned d64 `.src` is a cleanSource attrset, not a direct store-path string. A tiny actual private-store reproduction demonstrates `nix build --expr <source-set>` exits0 with empty stdout while `toString <source-set>` materializes the filtered outPath. Explicit coercion plus immediate single absolute store-path validation precedes the long build; the actual derivation equality guard remains unchanged. Native Mac evaluation independently matches coerced d64 src to captured Linux env.src; this is not a successful full export claim.
