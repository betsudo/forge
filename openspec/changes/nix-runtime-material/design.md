# Design

Extend the existing Linux installer workflow with explicit material-only dispatch/call. PR portable qualification remains unchanged. The fixed public d64 payload and independent Rust1.98.1 root are built through Nix; export all runtime, source and tool roots needed by Compact's existing independent derivation checks. Record source/platform/run identity, root derivation, NAR hashes and actual executable hashes. Upload bounded-retention same-run material; caller verifies service artifact digest before import and rechecks inventory. No relocation or qualification bypass. No keys, SRS or cached verdicts included.

Reusable calls require an explicit immutable producer-source SHA matching the reviewed workflow implementation. Artifact run identity belongs to the caller, so no cross-repository token is needed. Material completion is not proof or Compact qualification. Existing Nix/source checks remain mandatory after import.
