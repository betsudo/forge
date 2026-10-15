#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
nix_bin="$(command -v nix || true)"
if [[ -z "$nix_bin" && -x /nix/var/nix/profiles/default/bin/nix ]]; then
  nix_bin=/nix/var/nix/profiles/default/bin/nix
fi
[[ -n "$nix_bin" ]] || { echo "Nix with flakes is required" >&2; exit 1; }
case "${1:-}" in
  --check) exec "$nix_bin" develop --command bash scripts/check.sh ;;
  --audit-pi) exec "$nix_bin" develop --command bash -c 'pi --version; node scripts/factory-audit.mjs' ;;
  --pi) shift; exec "$nix_bin" develop --command bash -c 'node scripts/factory-audit.mjs && exec pi --no-extensions --no-skills --no-prompt-templates "$@"' forge-pi "$@" ;;
  --) shift; exec "$nix_bin" develop --command "$@" ;;
  "") exec "$nix_bin" develop ;;
  *) echo "Usage: ./bootstrap.sh [--check|--audit-pi|--pi [args]|-- command...]" >&2; exit 2 ;;
esac
