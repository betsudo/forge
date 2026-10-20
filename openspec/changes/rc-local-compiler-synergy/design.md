# Design

Reuse the existing portable builder, canonical Python installer, worker profile
checks, native candidate qualification and consumer proof harnesses. Do not create
a competing cache, archive format or key-identity implementation.

The requested shell entry point must work independently of a repository clone.
Generate or bootstrap it from the canonical installer so validation and rollback
have one maintained implementation. State runtime prerequisites explicitly and
avoid Nix/Cargo/source builds on consumer hosts. Install first into isolated user
prefixes; preserve existing shared launchers, GC roots and caches.

An RC archive belongs to its exact immutable source/version. Preserve old assets
and receipts; rebuild rather than relabel an archive made for another tag or
commit. Include checksums, runtime/source companions, notices, supported profiles
and platform evidence. RC notes must distinguish native/restricted-host testing
from actual clean no-Nix host testing; do not imply signing/notarization or broad
platform support that was not qualified.

Passport already has a Forge-owned full 52-circuit compiler qualification and
selected application proofs. Its JSON3.1 profile differs from Compact's Ledger8
JSON2.1.1 lane. Audit the actual target compiler and consumer pins before choosing
the new acceptance workload; never coerce profiles or infer compatibility from
version labels. Prefer the existing Passport workload when it matches the target;
otherwise use a pinned midnight-did contract with genuine consumer assertions.

For the compiler integration, emit current ZKIR, determine circuit size using the
actual backend, bypass tiny circuits, and request complete compatible artifacts
for eligible circuits. Preserve the compiler's own manifests/runtime metadata.
Unknown identity and corruption must refuse reuse. Keep ordinary uncached mode
explicit and executable.

The cache cutoff initially remains `k <= 8` for automatic compiler reuse. The
earlier native-capacity experiment's cutoff16 is not a product default. Record
bypasses separately from hits and misses; do not retain tiny artifacts in Forge
through the automatic compiler path. Refine thresholds only from measured costs.

The primary performance comparison is warm installed-RC local build/test versus
ordinary uncached local build/test, with the same complete contract output and
proof obligations. Alternate repeated lanes, hold source/tool/parameter premises,
and report raw durations and medians. Keygen-only speedup and warm-versus-cold
Forge differences are secondary measurements. More than 50% is a target to prove.
