# Bounded pilot payload

### Requirement: Portable measured payload

#### Scenario: Prepare a snapshot for transport
**WHEN** an operator explicitly prepares a private snapshot payload
**THEN** Forge SHALL verify it by restoring through the existing CLI, encode only
regular snapshot files and required directories in a deterministic gzip/tar envelope, retain the exact
compressed SHA256/byte count and snapshot identity, and refuse existing outputs.
Payload preparation grants no publication authority and claims no key generation,
application proof, network transfer or native Linux qualification.

#### Scenario: Restore untrusted transport bytes
**WHEN** downloaded bytes are offered for restore
**THEN** verify independently pinned compressed digest/size before extraction;
bound file count, compressed and expanded bytes; refuse traversal, duplicate,
link, device, extension-header and unexpected members; restore only via the existing Forge
snapshot verifier into an absent target. On failure no target may be published.
Temporary directories belong solely to this operation and are cleaned.

Restore SHALL validate directly into the final absent store without a second
verification store. Packing SHALL remove its verification store before compression
and hash streamed bytes against the exact raw manifest consumed by the verifier
(as recorded in its restore receipt), retaining file/directory types and bounded
inventory enumeration. Failures SHALL include
OS errno/strerror or bounded Forge exit/stderr diagnostics where available.
