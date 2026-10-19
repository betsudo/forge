# Material requirements

## ADDED Requirements

### Requirement: Fixed original runtime payload
The producer SHALL build public Forge d64f52db7239b0ca4891fb0316dca6adb54a5db5 for native x86_64-linux and export its original Nix paths, independent Rust toolchain and bound source roots without relocation.

#### Scenario: Wrong host
A non-native Linux x86_64 producer SHALL refuse before building.

### Requirement: Authenticated same-run material
The producer SHALL record current producer Git SHA, payload source SHA, run/attempt/repository, exact root derivation and complete NAR/path inventory plus closure byte hash. Consumers SHALL verify original GitHub artifact service digest and expected tuple before import; source fields alone are not authentication.

#### Scenario: Reusable caller
A caller pins the producer workflow and producer-source SHA, obtains artifact ID/name/digest as job outputs, and downloads from the same caller run.

### Requirement: Preserve qualification
The PR installer job SHALL retain all original proofs/negative controls. Material-only completion SHALL make no consumer/proof/performance acceptance claim. No circuit artifacts, SRS or test verdict cache SHALL be exported.

### Requirement: Bounded material and live producer
The producer SHALL refuse declared or actual export size over2GiB and incomplete/duplicate/noncanonical SHA256 NAR inventory. It SHALL recheck producer HEAD, tracked clean state and exporter byte hash before emitting success.

#### Scenario: Producer source changes during build
The final live guard SHALL refuse without a success material.json. Actual producer attempt SHALL be exposed as a reusable output, independently of a later consumer rerun.

#### Scenario: Non-material dispatch or reusable call
An explicit material-only:false call SHALL fail at the first job preflight rather than succeed with empty outputs. Real PR installer qualification remains unchanged; reusable callers do not trigger the portable PR job.
