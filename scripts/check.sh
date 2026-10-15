#!/usr/bin/env bash
set -euo pipefail
node scripts/factory-audit.mjs
node scripts/check-spec.mjs
node scripts/check-profile.mjs
node scripts/test-commit-policy.mjs
cargo fmt --check
cargo fmt --manifest-path workers/zkir3/Cargo.toml --check
cargo build --locked --manifest-path workers/zkir3/Cargo.toml --target-dir target
export MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER="$PWD/target/debug/midnight-zkir-forge-zkir3-worker"
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo clippy --locked --manifest-path workers/zkir3/Cargo.toml --target-dir target --all-targets -- -D warnings
