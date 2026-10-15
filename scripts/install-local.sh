#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
nix_bin="$(command -v nix || true)"
if [[ -z "$nix_bin" && -x /nix/var/nix/profiles/default/bin/nix ]]; then
  nix_bin=/nix/var/nix/profiles/default/bin/nix
fi
[[ -n "$nix_bin" ]] || { echo "Nix with flakes is required" >&2; exit 1; }
install_root="${HOME}/.local/share/midnight-zkir-forge"
mkdir -p "$install_root" "${HOME}/.local/bin"
"$nix_bin" build . --cores 2 --out-link "$install_root/current" "$@"
ln -sfn "$install_root/current/bin/midnight-zkir-forge" "${HOME}/.local/bin/midnight-zkir-forge"
# macOS current_exe may retain the launcher symlink; expose its worker sibling too.
ln -sfn "$install_root/current/bin/midnight-zkir-forge-zkir3-worker" "${HOME}/.local/bin/midnight-zkir-forge-zkir3-worker"
ln -sfn "$install_root/current/bin/midnight-zkir-forge-ci" "${HOME}/.local/bin/midnight-zkir-forge-ci"
printf '%s\n'  'Installed ~/.local/bin/midnight-zkir-forge (Nix GC-rooted)' 'Add ~/.local/bin to PATH for every local agent.'
