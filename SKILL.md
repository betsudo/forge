---
name: midnight-zkir-forge
description: Set up Midnight ZKIR Forge and integrate its local circuit artifact cache into development and tests while preserving proof generation, verification and assertions.
---

# Midnight ZKIR Forge for local development

Use Forge to generate, reuse and distribute ZKIR, prover keys and verifier keys.
Read the consumer checkout's instructions before editing it. This skill supplies
an integration workflow; it does not authorize unrelated checkout changes.

## Locate and install

Locate the Forge checkout or an existing `zkir-forge` on PATH. Resolve
reference paths below relative to this Forge checkout. If already installed,
inspect `--version`, `--help` and `profile` before deciding whether to rebuild.

From the Forge checkout, with Nix flakes enabled:

```sh
./bootstrap.sh --check
./scripts/install-local.sh
export PATH="$HOME/.local/bin:$PATH"
zkir-forge profile
zkir-forge --profile zkir3 profile
```

The installer supplies the CLI, isolated v3 worker and CI helper, with a Nix GC
root. Configure the PATH in the consumer's agent/test launcher if it does not
inherit the shell environment, or invoke `$HOME/.local/bin/zkir-forge`
explicitly. No service process is needed for local integration. Reinstall after
adopting a new Forge revision; do not edit shell startup files without a request.

Default artifact store: `~/.midnight-zkir-forge`. Override with `--cache-dir` or
`MIDNIGHT_ZKIR_FORGE_DIR`. Use a private temporary store for integration experiments;
leave shared caches intact.

## Establish compatibility before replacing key generation

Inspect the consumer's actual ZKIR version, backend pin, binary serialization and
any executable fingerprint allowlist. Compare against current `profile` output:

- `ledger8-v2`: official ledger8 8.1.3 / ZKIR 2.1.1; JSON 2.0.
- `zkir3`: official ledger revision
  `3a7ae0361d03e6eed4fc91e31f6600f334f605d5`; JSON 3.0,
  binary tag `ir-source[v3-generic]`.

These profiles are not interchangeable with other v3 RCs, JSON 3.1, newer split
ZKIR graphs or ledger9 transaction support. Use [README.md](README.md) for current
qualified scope. Preserve existing consumer compatibility checks; an allowlist
update needs qualification against that consumer. Retain its uncached tool when
compatibility is unsupported or unqualified. Do not modify Compact merely because
this skill is invoked.

Parameters use `--params-dir` / `MIDNIGHT_PP`, otherwise the official provider's
cache. Retrieval is offline by default; `--fetch-params` explicitly permits verified
acquisition. Keep official parameter verification enabled. Fixture qualification
can check the toolchain, but does not replace the consumer's own proof tests:

```sh
zkir-forge qualify
zkir-forge --profile zkir3 qualify
```

## Integrate at the artifact-generation boundary

Keep circuit compilation producing the current ZKIR. Replace only repeated,
compatible key generation with `prepare` on that file's exact current bytes:

```sh
zkir-forge --profile ledger8-v2 prepare /absolute/path/circuit.zkir
# For the separately qualified v3 consumer:
zkir-forge --profile zkir3 prepare /absolute/path/circuit.zkir
```

Invoke via subprocess argument arrays. Check exit status, parse stdout as JSON,
and retain stderr for diagnostics. The CLI reads file paths, not stdin; it has no
JSON-RPC/JSON-lines server. Argument errors may produce no JSON. Details:
[docs/api-conventions.md](docs/api-conventions.md).

Use `export.base` as the copied provider directory, or `export.files` for explicit
paths (`kind`, `sha256`, `bytes`, `path`). Kinds are `source`, `binary_ir`, `prover`,
`verifier`. The directory contains:

```text
zkir/<name>.zkir
zkir/<name>.bzkir
keys/<name>.prover
keys/<name>.verifier
manifest.json
```

Preserve the circuit name expected by the consumer; use `--name NAME` if needed.
`NodeZkConfigProvider` reads a compatible local directory; `ZKConfigProvider`
retrieves artifacts, whereas `ProofProvider` generates proofs. Keep the existing
proof provider and all actual proof generation, verification, assertions, fixture
checks and negative controls running on both hits and misses. Never cache test
outcomes or treat `cache.hit` as proof success. Forge's current HTTP object URLs
are not a drop-in `FetchZkConfigProvider` layout endpoint.

## Validate and measure the consumer integration

Exercise a cold prepare and a second warm prepare against the same current input
in an isolated store. Check unchanged `artifact_set_id`, a warm `cache.hit`, current
export paths and real consumer proof/verification results. Change the circuit input
and confirm the consumer no longer reuses the old bundle. Keep an uncached
qualification lane available.

Use `stats` before/after a run to inspect hit/miss/error totals, per-file requests
and timing estimates. Counters are logical requests; estimated avoided generation
is not a measured end-to-end speedup. Record workload-specific wall time separately.
Do not delete the shared cache to manufacture a cold run. For job-only deltas or
verified snapshot relocation, read [docs/ci-cache.md](docs/ci-cache.md) and use
`midnight-zkir-forge-ci --help`; CI publishing is a separate workflow decision.

Report the exact consumer/tool profiles, integration point, cold/warm observations
and real tests executed, including any unsupported path left uncached.
