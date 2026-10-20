# Publication

## ADDED Requirements

### Requirement: Actual upload archive admission
The publisher SHALL use official pinned SDK 5.0.5 archive/version/upload behavior and measure that exact archive before reservation/upload. Unknown/mutated SDK code or denied admission SHALL cause zero create/reserve/upload calls.

#### Scenario: Oversized archive
Actual archive bytes plus complete current retained bytes exceed decimal 10 GB; refuse before any reservation/upload.

### Requirement: Trusted bounded publication window
Publication SHALL default off and require fixed trusted manual ref, verified official prepare-save receipt/key/partition/ID, matching fixed path, explicit approved operator-window context and no other active/queued cachewriter runs. Complete paginated inventory and one seed generation per ref/partition SHALL be enforced. No deletion or hard guarantee over uncontrolled future writers is implied.

#### Scenario: Unknown API/writer state
Missing pages, unknown running workflows or failed API access SHALL refuse before reservation. A window flag alone SHALL not prove exclusive control.
