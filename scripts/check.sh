#!/usr/bin/env bash
set -euo pipefail
node scripts/factory-audit.mjs
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
