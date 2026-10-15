#!/usr/bin/env bash
set -euo pipefail
node scripts/factory-audit.mjs
node scripts/check-spec.mjs
node scripts/check-profile.mjs
node scripts/test-commit-policy.mjs
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
