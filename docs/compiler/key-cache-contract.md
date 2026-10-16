# Compact compiler key-cache contract

Tracking: betsudo/forge #3. **The flags below are proposed upstream Compact
syntax, not implemented Compact or Forge CLI options.** Current interfaces are
listed separately. Compact and other checkouts are unchanged.

## Observed boundary

Read-only snapshot: Compact source 05a7885f6518e1ca358896aec03cc028a66f8c13.
File digests and scope: [audit receipt](../evidence/compact-compiler-boundary.json).
The compiler emits fresh JSON ZKIR, invokes the native tool, then writes TypeScript
and `compiler/contract-manifest.json` hashing the actual outputs:

```text
current source -> compiler -> OUT/zkir/CIRCUIT.zkir
                         -> zkir[-v3] compile-many OUT/zkir OUT/keys
                         -> OUT/zkir/CIRCUIT.bzkir
                         -> OUT/keys/CIRCUIT.prover and CIRCUIT.verifier
                         -> normal compiler integrity manifest
```

Reuse belongs inside the compile-many boundary. Do not use `--skip-zk` followed
by arbitrary key injection after a finished compilation: its manifest does not
then describe those key bytes. Preserve compiler-produced contract-info/runtime
metadata. A Forge descriptor is additional generation evidence, not a substitute.

The inspected compiler has no Forge flag. Its scoped test adapter supports v2
only, requires an older exact Forge build, invokes actual mock-compile freshly,
and leaves real proofs/assertions independent. Tool name `zkir-v3` does not prove
JSON3.0 versus JSON3.1 compatibility. Do not loosen its build guard or copy this
checkout into that shim without exact qualification.

## Proposed opt-in

```text
compactc --zk-key-cache=off INPUT.compact OUT
compactc --zk-key-cache=local --zk-key-cache-config=qualified-policy.json INPUT.compact OUT
compactc --zk-key-cache=fetch --zk-key-cache-config=qualified-policy.json INPUT.compact OUT
```

These illustrate the desired integration only. No executable example in this
repository claims those flags are accepted today.

| Selection | Contract |
| --- | --- |
| Absent / `off` | Original generator, original errors and outputs; no Forge initialization or network request. |
| `local` | Current source enters existing Forge prepare/export semantics. A genuine miss generates with verified parameters; a hit verifies bytes. |
| `fetch` | Look up an exact derivation and retrieve a complete immutable qualified provider view; no generation on GET. Remote transport remains a proposed path. |

Default is off. An explicit flag wins over any documented same-purpose default.
Existing test-only shim environment variables do not silently opt a released
compiler into reuse. Explicit local/fetch plus `--skip-zk` is a contradictory
configuration and fails before materialization. `--skip-ts` keeps its normal
meaning; it does not change artifact identity or waive integrity metadata.

The config is consumer-owned, independently qualified policy, not whatever a
producer reports. Its versioned contract must pin:

- Compiler source/version and actual official tool identity; input version,
  complete backend profile/revision, serialization and recipe/options.
- Actual Forge build and matched worker executable/source identities, platform
  and verified parameter content digests. Each supported cohort is explicit.
- Absolute native executables, explicit store/parameter directories, and, for
  fetch, allowed origin, immutable view selection and application trust anchor.
- Provider package versions and integrity-manifest hash supplied independently
  by the application where available. A manifest fetched from the same untrusted
  source as its keys establishes consistency, not publisher trust.

No mutable producer declaration can add itself to the allowlist. The actual
private cache path is transport configuration, not cryptographic identity.
Explicit cache directory wins over `MIDNIGHT_ZKIR_FORGE_DIR`, then
`~/.midnight-zkir-forge`; parameters retain existing separate rules and offline
behavior. Do not fetch parameters merely because remote artifact fetching is on.

## Errors and fallback

The proposed optional `--zk-key-cache-fallback=generate` is deliberately separate
from enabling fetch. Default is error. Only documented availability conditions
(absent artifact, busy service or narrowly classified transport failure) may
invoke the original independently qualified generator when explicitly requested.
Local prepare's ordinary cache miss already generates and needs no network fallback.

Corrupt present objects, invalid parameters, profile/version/worker mismatch,
changed source, unknown schema, authentication refusal and output-target errors
are hard failures even when generate fallback was requested. Do not branch on
stderr wording, use a catch-all retry or relabel a failed proof as a cache miss.
The existing [typed error contract](../../openspec/changes/compiler-compatibility/design.md)
provides the basis; transport-specific classification must be tested separately.

## Batch and output rules

One compile operation consumes current JSON bytes for a validated circuit name;
compile-many enumerates deterministic unique current source names, preserves
empty-batch behavior and refuses binary-only stale input. Source reads must be
consistent across lookup, verification and publication. Changed bytes mean a
new derivation or an explicit refusal, never a stale hit.

Validate every returned artifact and policy premise before copying. Requested
outputs must not alias source, cache or persistent exports, traverse paths or
follow symlinks. Use private copies so compiler/test writes cannot corrupt Forge.
Actual prover/verifier/binary IR bytes and verifier identities survive eviction.

Individual file replacement can be atomic; a three-file/batch transaction is not
assumed. If any copy fails, fail compilation, do not write a new success manifest,
and clean or require retry of the owned incomplete output. A stale manifest from
an older successful invocation cannot stand in for this failed build. Avoid
inventing a multi-directory commit protocol when ordinary compiler fail/cleanup
semantics suffice. Current upstream shell quoting (including apostrophe paths)
is not qualified by this Forge-only contract.

## Working local CLI today

These existing commands are real; choose the exact qualified profile and current
circuit bytes. They do not patch Compact's compiler pipeline:

```sh
midnight-zkir-forge --profile zkir31 --params-dir /verified/parameters \
  prepare /absolute/current/circuit.zkir --name circuit
midnight-zkir-forge stats
```

Read the returned `export.base`, `export.files`, descriptor and digests; use an
argument array and check nonzero status. Bare Forge exports do not yet claim all
compiler integrity/runtime metadata needed by current SDK providers. Provider
qualification is #4; exact native Linux consumer qualification is #5; easy local
integration and failure controls are #6/#7.

Keep emitting current compiler ZKIR and executing all ordinary proofs,
verification, assertions and invalid/corrupt-proof controls on cold and warm
runs. Metrics distinguish key-generation reuse from complete test time. No speed,
compiler-flag, universal-profile, Fetch-provider or release-readiness claim follows
from this contract alone. Cloudflare and hosted work remain deferred.
