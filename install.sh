#!/usr/bin/env bash
# Install a verified, explicit binary release without building Forge from source.
set -euo pipefail
script_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_root/scripts/install-release.py" "$@"
