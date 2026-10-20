#!/usr/bin/env bash
set -euo pipefail
node scripts/factory-audit.mjs
node scripts/check-spec.mjs
node scripts/check-profile.mjs
node scripts/test-commit-policy.mjs
node scripts/test-pr-integrity.mjs
actionlint
cargo fmt --check
cargo fmt --manifest-path workers/zkir3/Cargo.toml --check
cargo fmt --manifest-path workers/zkir31/Cargo.toml --check
cargo build --locked --manifest-path workers/zkir3/Cargo.toml --target-dir target
export MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER="$PWD/target/debug/midnight-zkir-forge-zkir3-worker"
cargo build --locked --manifest-path workers/zkir31/Cargo.toml --target-dir target/zkir31
export MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER="$PWD/target/zkir31/debug/midnight-zkir-forge-zkir31-worker"
cargo test --locked
cargo build --locked --example qualify-http-fixture
cargo clippy --locked --all-targets -- -D warnings
cargo clippy --locked --manifest-path workers/zkir3/Cargo.toml --target-dir target --all-targets -- -D warnings
cargo clippy --locked --manifest-path workers/zkir31/Cargo.toml --target-dir target/zkir31 --all-targets -- -D warnings
python3 scripts/check-cargo-notices.py
python3 scripts/check-github-action.py
python3 scripts/check-compiler-local.py
python3 -m py_compile scripts/qualify-passport-local.py scripts/measure-provider-ranges.py scripts/passport-range-fixture.py
node --check integration/providers/passport.mjs
python3 scripts/check-ci-trial.py
python3 scripts/check-ci-collection.py
python3 scripts/check-ci-payload.py
python3 scripts/check-passport-linux.py
python3 -m py_compile scripts/stage-passport-linux.py
python3 -m py_compile scripts/qualify-passport-provider.py
python3 scripts/check-linux-qualification.py
python3 scripts/check-build-release.py
python3 scripts/check-installer.py --standalone
python3 scripts/check-local-install.py
python3 scripts/check-recovery.py --binary target/debug/zkir-forge
python3 scripts/check-snapshot.py --binary target/debug/zkir-forge
python3 scripts/check-http.py --binary target/debug/zkir-forge
python3 scripts/build-docs.py
python3 scripts/check-docs.py
