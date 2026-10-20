# Local Forge RC delivery

### Requirement: exact versioned portable installation

The RC SHALL publish only source-authenticated, checksummed native assets for
qualified targets. `zkir-forge-installer.sh` SHALL install the selected native
binary and matched workers without requiring a repository checkout or source
build, preserving existing installations and refusing unsafe or incompatible data.

#### Scenario: clean isolated prefix

- **WHEN** an explicit qualified RC is installed into an absent user-owned prefix
- **THEN** installation validates archive/profile identities, stages complete files
  and publishes usable CLI/worker paths. Failure must not silently replace the
  active installation.

### Requirement: tiny circuits bypass automatic caching

The automatic compiler integration SHALL generate tiny circuit artifacts directly
without a Forge cache request or retention. The initial configurable cutoff is
`k <= 8`, unless a separately measured profile policy justifies another value.

#### Scenario: cutoff boundary

- **WHEN** the compiler processes circuits at and above the configured cutoff
- **THEN** the circuit at the cutoff follows direct generation and the eligible
  circuit above it may use Forge. Both produce valid complete compiler output
  and execute the same proof/test controls. Bypasses do not count as cache hits.

### Requirement: representative complete local comparison

The benchmark SHALL live in Forge and use a pinned Passport or midnight-did
consumer with an explicitly compatible compiler/profile. Warm results SHALL
include fresh compilation of current source, material acquisition and genuine
proof/test controls. The ordinary baseline SHALL perform real uncached keygen.

#### Scenario: claimed target achieved

- **WHEN** repeated complete warm wall time is less than half the corresponding
  ordinary wall time with unchanged artifacts and proof obligations
- **THEN** the result may be described as more than 50% wall-time reduction for
  that measured workload. Preserve cold population, setup, bytes, tiny bypasses
  and unsuccessful performance results.
