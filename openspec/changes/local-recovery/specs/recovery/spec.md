# Local failure recovery

## Requirement: transactional success accounting

Successful ensure and resolve SHALL commit their metadata and success metrics in
one transaction. Accounting failure SHALL not leave newly ready metadata committed.

### Scenario: accounting fails after export publication

Given a private store with an injected metrics write failure, ensure fails without
committing readiness. After removing the fault, retry verifies any retained export
and commits a complete result and successful metric.

## Requirement: preserve actionable failures

Failure accounting SHALL not mask the original operation failure.

### Scenario: parameters and error accounting fail

The caller receives the missing-parameter diagnostic with the accounting diagnostic
attached. The bundle remains unavailable and can be retried after correction.

## Requirement: no replacement and interrupted publication recovery

Export and snapshot directory publication SHALL share atomic no-replace behavior.

### Scenario: competing destination

Publication against an existing empty directory fails and leaves that directory intact.

### Scenario: writer killed after export but before metadata commit

The retained export does not advertise ready metadata. After reopening, retry
returns the same output identity and real proof/verification controls still run.
