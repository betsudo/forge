#!/usr/bin/env python3
"""Issue #43: pinned original Nix material only; no consumer qualification."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile

SOURCE = 'd64f52db7239b0ca4891fb0316dca6adb54a5db5'
REF = 'github:betsudo/forge/' + SOURCE


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def derivation(value, root):
    rows = value.get('derivations', value)
    matches = [row for row in rows.values() if row.get('env', {}).get('out') == str(root)]
    require(len(matches) == 1 and matches[0]['system'] == 'x86_64-linux', 'exact Linux output derivation required')
    return matches[0]


def producer_identity(actual, expected):
    require(re.fullmatch('[0-9a-f]{40}', expected) and actual == expected,
            'exporter checkout differs from pinned producer source')


def inventory_size(inventory, paths):
    rows = inventory if isinstance(inventory, dict) else {row['path']: row for row in inventory}
    require(isinstance(inventory, dict) or len(rows) == len(inventory), 'duplicate NAR inventory path')
    require(set(rows) == set(paths), 'complete closure NAR inventory required')
    require(all(isinstance(row.get('narHash'), str) and re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=', row['narHash'])
                and len(base64.b64decode(row['narHash'][7:], validate=True)) == 32
                and base64.b64encode(base64.b64decode(row['narHash'][7:], validate=True)).decode() == row['narHash'][7:]
                and type(row.get('narSize')) is int and row['narSize'] >= 0 for row in rows.values()),
            'actual NAR hash and size required')
    size = sum(row['narSize'] for row in rows.values())
    require(size <= 2147483648, 'material closure exceeds explicit 2GiB budget')
    return size


def run_dirty(root):
    return subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()


def store_output(raw):
    """Successful Nix exit alone does not establish a single materialized path."""
    lines = raw.splitlines()
    require(len(lines) == 1 and re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/\s]+', lines[0]),
            'exactly one absolute Nix store output required')
    return Path(lines[0])


def register_root(run, path, root):
    """Official registration, never a fabricated symlink to an unregistered path."""
    actual = Path(run('nix-store', '--realise', path, '--add-root', root, '--indirect'))
    require(actual == root or actual == path, 'root registration returned unexpected path: ' + str(actual))
    require(root.is_symlink(), 'official root registration did not create a symlink')
    # Nix prints the root link when --add-root is supplied; query the logical path
    # separately so relocated private test stores use the same official checks.
    run('nix-store', '--check-validity', path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'native Linux x86_64 required')
    root = Path(__file__).resolve().parent.parent
    exporter = Path(__file__).resolve()
    exporter_sha = sha(exporter)
    producer = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    producer_identity(producer, args.producer_source)
    require(not run_dirty(root), 'clean producer checkout required')
    require(not args.output.exists(), 'fresh material directory required')
    args.output.mkdir(parents=True)
    def run(*argv):
        return subprocess.check_output(list(map(str, argv)), text=True).strip()
    def capture(name, *argv):
        text = run(*argv)
        (args.output / name).write_text(text + '\n')
        return json.loads(text)
    with tempfile.TemporaryDirectory(prefix='forge-material-roots-', dir=args.output.parent) as roots_directory:
        gcroots = Path(roots_directory)
        metadata = capture('flake.json', 'nix', 'flake', 'metadata', REF, '--json')
        require(metadata['locked']['rev'] == SOURCE, 'payload source revision mismatch')
        source = store_output(metadata['path'])
        archived = json.loads(run('nix', 'flake', 'archive', '--json', REF))
        require(store_output(archived['path']) == source, 'materialized pinned source differs from flake metadata')
        register_root(run, source, gcroots / 'source')
        realized_source = store_output(run('nix', 'build', '--impure', '--expr',
            'toString (builtins.getFlake "' + REF + '").packages.x86_64-linux.default.src',
            '--out-link', gcroots / 'build-source', '--print-out-paths', '--max-jobs', '1', '--cores', '2'))
        package = store_output(run('nix', 'build', REF, '--out-link', gcroots / 'package', '--print-out-paths', '--max-jobs', '1', '--cores', '2'))
        expression = ('let f = builtins.getFlake "' + REF + '"; '
                      'pkgs = import f.inputs.nixpkgs { system = "x86_64-linux"; overlays = [(import f.inputs.rust-overlay)]; }; '
                      'in pkgs.rust-bin.stable."1.98.1".minimal.override { extensions = ["rustfmt" "clippy"]; }')
        rust = store_output(run('nix', 'build', '--impure', '--expr', expression, '--out-link', gcroots / 'rust', '--print-out-paths', '--max-jobs', '1', '--cores', '2'))
        drv = capture('forge-derivation.json', 'nix', 'derivation', 'show', package)
        row = derivation(drv, package)
        require(str(rust) in row['env']['nativeBuildInputs'].split(), 'independent Rust root absent from actual derivation')
        build_source = store_output(row['env']['src'])
        require(realized_source == build_source, 'materialized build source differs from actual derivation')
        roots = [package, rust, source, build_source]
        paths = run('nix-store', '--query', '--requisites', *roots).splitlines()
        require(paths and len(paths) == len(set(paths)) and all(path.startswith('/nix/store/') for path in paths), 'invalid closure inventory')
        inventory = capture('store-paths.json', 'nix', 'path-info', '--json', *sorted(paths))
        nar_bytes = inventory_size(inventory, paths)
        closure = args.output / 'closure.nar'
        with closure.open('xb') as output:
            subprocess.run(['nix-store', '--export', *sorted(paths)], stdout=output, check=True)
        require(closure.stat().st_size <= 2147483648, 'export bytes exceed explicit 2GiB budget')
        (args.output / 'rustc-verbose.txt').write_text(run(rust / 'bin/rustc', '-vV') + '\n')
        binaries = {str(path): sha(path.resolve(strict=True)) for path in sorted((package / 'bin').iterdir()) if path.is_file()}
        required_binaries = {'zkir-forge', 'midnight-zkir-forge', 'midnight-zkir-forge-ci', 'midnight-zkir-forge-zkir3-worker', 'midnight-zkir-forge-zkir31-worker'}
        require(required_binaries <= {Path(name).name for name in binaries}, 'required CLI/helper/worker roster missing')
        producer_identity(run('git', '-C', root, 'rev-parse', 'HEAD'), args.producer_source)
        require(not run_dirty(root) and sha(exporter) == exporter_sha, 'producer source changed before material success')
        report = dict(schema=1, scope='original Nix runtime/source/tool material only; no consumer or proof qualification',
                      payload_source=SOURCE, producer_source=producer, exporter_sha256=exporter_sha, system='x86_64-linux', root=str(package),
                      rust_root=str(rust), source_root=str(source), build_source_root=str(build_source),
                      producer_repository='betsudo/forge', repository=os.environ['GITHUB_REPOSITORY'], run_id=os.environ['GITHUB_RUN_ID'],
                      run_attempt=os.environ['GITHUB_RUN_ATTEMPT'], store_paths=len(paths),
                      nar_bytes=nar_bytes, max_bytes=2147483648,
                      files={path.name: dict(bytes=path.stat().st_size, sha256=sha(path)) for path in args.output.iterdir() if path.is_file()},
                      binaries=binaries)
        (args.output / 'material.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
