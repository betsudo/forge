#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
nix_bin="$(command -v nix || true)"
if [[ -z "$nix_bin" && -x /nix/var/nix/profiles/default/bin/nix ]]; then
  nix_bin=/nix/var/nix/profiles/default/bin/nix
fi
[[ -n "$nix_bin" ]] || { echo "Nix with flakes is required" >&2; exit 1; }
install_root="${HOME}/.local/share/midnight-zkir-forge"
# Refuse launcher collisions before Nix can switch the active GC-root pointer.
for name in zkir-forge midnight-zkir-forge midnight-zkir-forge-zkir3-worker midnight-zkir-forge-zkir31-worker midnight-zkir-forge-ci; do
  launcher="${HOME}/.local/bin/$name"
  if [[ -e "$launcher" || -L "$launcher" ]]; then
    [[ -L "$launcher" ]] || { echo "Unrelated executable exists: $launcher" >&2; exit 1; }
    target="$(readlink "$launcher")"
    expected="$install_root/current/bin/$name"
    if [[ "$name" == zkir-forge || "$name" == midnight-zkir-forge ]]; then
      [[ "$target" == "$install_root/current/bin/zkir-forge" || "$target" == "$install_root/current/bin/midnight-zkir-forge" ]] || { echo "Unrelated launcher exists: $launcher" >&2; exit 1; }
    else
      [[ "$target" == "$expected" ]] || { echo "Unrelated launcher exists: $launcher" >&2; exit 1; }
    fi
  fi
done
mkdir -p "$install_root" "${HOME}/.local/bin"
"$nix_bin" build . --cores 2 --out-link "$install_root/current" "$@"
ln -sfn "$install_root/current/bin/zkir-forge" "${HOME}/.local/bin/zkir-forge"
ln -sfn "$install_root/current/bin/zkir-forge" "${HOME}/.local/bin/midnight-zkir-forge"
# macOS current_exe may retain the launcher symlink; expose its worker sibling too.
ln -sfn "$install_root/current/bin/midnight-zkir-forge-zkir3-worker" "${HOME}/.local/bin/midnight-zkir-forge-zkir3-worker"
ln -sfn "$install_root/current/bin/midnight-zkir-forge-zkir31-worker" "${HOME}/.local/bin/midnight-zkir-forge-zkir31-worker"
ln -sfn "$install_root/current/bin/midnight-zkir-forge-ci" "${HOME}/.local/bin/midnight-zkir-forge-ci"
printf '%s\n'  'Installed ~/.local/bin/zkir-forge with midnight-zkir-forge alias (Nix GC-rooted)' 'Add ~/.local/bin to PATH for every local agent.'
