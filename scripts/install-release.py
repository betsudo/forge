#!/usr/bin/env python3
"""Install an explicit private Forge release; requires gh and Python 3.11+."""
import argparse
import contextlib
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

REPOSITORY = 'betsudo/forge'
COMMANDS = ('midnight-zkir-forge', 'midnight-zkir-forge-zkir3-worker', 'midnight-zkir-forge-ci')
WORKER31 = 'midnight-zkir-forge-zkir31-worker'
PRIMARY = 'zkir-forge'
MAX_DOWNLOAD = 1024 ** 3
MAX_UNPACKED = 2 * 1024 ** 3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def strict_json(data):
    def fields(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=fields)


def target():
    system = {'Darwin': 'apple-darwin', 'Linux': 'unknown-linux-gnu'}.get(platform.system())
    arch = {'arm64': 'aarch64', 'aarch64': 'aarch64', 'x86_64': 'x86_64', 'AMD64': 'x86_64'}.get(platform.machine())
    require(system and arch, 'supported platforms: macOS/Linux ARM64 and x86_64')
    if platform.system() == 'Darwin':
        probe = subprocess.run(['/usr/sbin/sysctl', '-n', 'hw.optional.arm64'], capture_output=True, text=True)
        require(not (probe.stdout.strip() == '1' and arch != 'aarch64'), 'use native ARM64 Python; Rosetta selection is refused')
    if platform.system() == 'Linux':
        require(platform.libc_ver()[0] == 'glibc', 'only qualified glibc Linux targets are supported')
    return arch + '-' + system


def version_tuple(value):
    require(re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', value), 'invalid runtime version')
    return tuple(map(int, value.split('.')))


def runtime(minimum):
    require(set(minimum) == {'os_version', 'libc_family', 'libc_version'}, 'invalid runtime manifest')
    if platform.system() == 'Darwin':
        require(minimum['libc_family'] is None and minimum['libc_version'] is None, 'unexpected libc requirement')
        require(version_tuple(platform.mac_ver()[0]) >= version_tuple(minimum['os_version']), 'macOS is below the qualified minimum')
    else:
        family, value = platform.libc_ver()
        require(minimum['os_version'] is None and family == minimum['libc_family'] == 'glibc', 'unsupported libc')
        require(version_tuple(value) >= version_tuple(minimum['libc_version']), 'glibc is below the qualified minimum')


def gh(*arguments, output_dir=None):
    try:
        if output_dir is None:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostics:
                process = subprocess.Popen(['gh', *map(str, arguments)], stdout=output, stderr=diagnostics)
                try:
                    deadline = time.monotonic() + 300
                    while process.poll() is None:
                        require(os.fstat(output.fileno()).st_size <= 16 * 1024 ** 2, 'GitHub metadata exceeds limit')
                        require(time.monotonic() < deadline, 'GitHub metadata deadline exceeded')
                        time.sleep(.05)
                    require(process.returncode == 0, 'GitHub request failed; check gh authentication and repository read access')
                    require(os.fstat(output.fileno()).st_size <= 16 * 1024 ** 2, 'GitHub metadata exceeds limit')
                    output.seek(0)
                    return strict_json(output.read(16 * 1024 ** 2 + 1))
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
        with tempfile.TemporaryFile() as diagnostics:
            process = subprocess.Popen(['gh', *map(str, arguments)], stdout=diagnostics, stderr=diagnostics)
            try:
                deadline = time.monotonic() + 300
                while process.poll() is None:
                    size = sum(p.stat().st_size for p in output_dir.rglob('*') if p.is_file())
                    require(size <= MAX_DOWNLOAD + 1024 ** 2, 'download byte budget exceeded')
                    require(time.monotonic() < deadline, 'GitHub download deadline exceeded')
                    time.sleep(.05)
                require(process.returncode == 0, 'GitHub download failed; check gh authentication and read access')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise ValueError('gh is unavailable or timed out; install/authenticate gh and retry') from error


def checksum(data, name):
    entries = {}
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.+-]+)', line)
        require(match is not None, 'invalid SHA256SUMS entry')
        value, filename = match.groups()
        require(filename not in entries, 'duplicate checksum asset')
        entries[filename] = value
    require(name in entries, 'target checksum missing')
    return entries[name]


def inventory(root, manifest):
    require(set(manifest) == {'schema', 'tag', 'version', 'source_commit', 'target', 'minimum', 'profiles', 'files'}, 'invalid manifest fields')
    require(manifest['schema'] == 1 and re.fullmatch('[0-9a-f]{40}', manifest['source_commit']), 'invalid manifest provenance')
    require(set(manifest['profiles']) in ({'root', 'v3'}, {'root','v3','v31'}), 'invalid profile manifest')
    require('midnight-zkir-v3.1-json' not in manifest['profiles']['root'].get('formats', []) or 'v31' in manifest['profiles'], 'advertised worker missing')
    payload_commands = COMMANDS + ((WORKER31,) if 'v31' in manifest['profiles'] else ())
    declared = {}
    for entry in manifest['files']:
        require(set(entry) == {'path', 'bytes', 'sha256', 'executable'}, 'invalid inventory entry')
        path = PurePosixPath(entry['path'])
        require(not path.is_absolute() and path.parts and all(p not in ('.', '..') for p in path.parts) and '\\' not in str(path), 'unsafe inventory path')
        require(str(path) == entry['path'] and entry['path'] not in declared, 'duplicate/noncanonical inventory')
        allowed = str(path) in {*('bin/' + name for name in payload_commands), 'share/midnight-zkir-forge/forge-ci.py', 'bin/' + PRIMARY}
        allowed |= len(path.parts) >= 2 and path.parts[0] in ('LICENSES', 'lib')
        require(allowed and type(entry['bytes']) is int and entry['bytes'] >= 0 and type(entry['executable']) is bool, 'unexpected payload')
        require(re.fullmatch('[0-9a-f]{64}', entry['sha256']), 'invalid file hash')
        declared[str(path)] = entry
    require(all('bin/' + name in declared for name in payload_commands), 'incomplete CLI/worker/helper bundle')
    require('share/midnight-zkir-forge/forge-ci.py' in declared and any(p.startswith('LICENSES/') for p in declared), 'missing helper/licensing')
    allowed_dirs = set()
    for name in declared:
        allowed_dirs.update(p.as_posix() for p in PurePosixPath(name).parents if p.as_posix() != '.')
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'managed payload symlink refused')
        if path.is_dir():
            require(path.relative_to(root).as_posix() in allowed_dirs, 'unexpected payload directory')
            continue
        name = path.relative_to(root).as_posix()
        if name == 'manifest.json':
            continue
        require(path.is_file() and name in declared, 'unexpected installed file')
        entry = declared[name]
        require(path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'], 'payload checksum mismatch')
        require(bool(path.stat().st_mode & 0o111) == entry['executable'], 'payload mode mismatch')
        actual.add(name)
    require(actual == set(declared), 'missing installed file')
    # Legacy schema1 archives remain installable; new dual-name archives must
    # describe two regular, executable byte-identical representations.
    if 'bin/' + PRIMARY in declared:
        primary, legacy = declared['bin/' + PRIMARY], declared['bin/midnight-zkir-forge']
        require(all(primary[key] == legacy[key] for key in ('bytes', 'sha256', 'executable')) and primary['executable'], 'CLI alias bytes differ')


def extract(archive_path, destination, expected_root):
    # Bound all gzip expansion, including PAX/GNU headers, before tarfile parses it.
    with tempfile.TemporaryFile() as expanded:
        with gzip.open(archive_path, 'rb') as compressed:
            remaining = MAX_UNPACKED + 16 * 1024 ** 2
            while chunk := compressed.read(min(1024 ** 2, remaining + 1)):
                remaining -= len(chunk)
                require(remaining >= 0, 'expanded archive budget exceeded')
                expanded.write(chunk)
        expanded.seek(0)
        return extract_tar(expanded, destination, expected_root)


def extract_tar(expanded, destination, expected_root):
    with tarfile.open(fileobj=expanded, mode='r:') as archive:
        members = []
        seen = set()
        total = 0
        for member in archive:
            members.append(member)
            require(len(members) <= 10000, 'archive member budget exceeded')
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and path.parts and path.parts[0] == expected_root and '..' not in path.parts and '\\' not in member.name, 'unsafe archive path')
            require(str(path) == member.name.rstrip('/') and member.name.isascii(), 'noncanonical archive name')
            require(str(path) not in seen and (member.isfile() or member.isdir()) and not member.mode & 0o7000, 'duplicate/link/special archive entry')
            seen.add(str(path))
            total += member.size
            require(total <= MAX_UNPACKED, 'archive byte budget exceeded')
        # No extract-all or symlink traversal. All metadata validated before writing.
        for member in members:
            path = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, path.open('xb') as output:
                    shutil.copyfileobj(source, output)
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
    return destination / expected_root


def smoke(root, manifest, environment=None):
    env = dict(os.environ if environment is None else environment)
    env.pop('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER', None)
    env.pop('MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER', None)
    def run(*args, structured=True):
        result = subprocess.run(list(map(str, args)), capture_output=True, text=True, env=env, timeout=30)
        require(result.returncode == 0, 'staged executable failed; active release unchanged')
        return strict_json(result.stdout) if structured else result.stdout
    cli = root / 'bin/midnight-zkir-forge'
    version = run(cli, '--version', structured=False).strip()
    require(version in {name + ' ' + manifest['version'] for name in ('midnight-zkir-forge', PRIMARY)}, 'package version mismatch')
    primary = root / 'bin' / PRIMARY
    if primary.is_file():
        require(version == PRIMARY + ' ' + manifest['version'] and run(primary, '--version', structured=False).strip() == version, 'primary CLI version mismatch')
        require(run(primary, 'profile') == manifest['profiles']['root'], 'primary root profile mismatch')
        require(run(primary, '--profile', 'zkir3', 'profile') == manifest['profiles']['v3'], 'primary worker profile mismatch')
        if 'v31' in manifest['profiles']:
            require(run(primary, '--profile', 'zkir31', 'profile') == manifest['profiles']['v31'], 'primary3.1 worker profile mismatch')
    require(run(cli, 'profile') == manifest['profiles']['root'], 'root profile mismatch')
    require(run(cli, '--profile', 'zkir3', 'profile') == manifest['profiles']['v3'], 'default worker discovery/profile mismatch')
    env['MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER'] = str(root / 'bin/midnight-zkir-forge-zkir3-worker')
    require(run(cli, '--profile', 'zkir3', 'profile') == manifest['profiles']['v3'], 'explicit worker profile mismatch')
    if 'v31' in manifest['profiles']:
        require(run(cli, '--profile', 'zkir31', 'profile') == manifest['profiles']['v31'], 'default3.1 worker profile mismatch')
        env['MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER'] = str(root / 'bin' / WORKER31)
        require(run(cli, '--profile', 'zkir31', 'profile') == manifest['profiles']['v31'], 'explicit3.1 worker profile mismatch')
    run(root / 'bin/midnight-zkir-forge-ci', '--help', structured=False)


def managed_directory(path):
    require(not path.is_symlink(), 'managed directory symlink refused: ' + str(path))
    if path.exists():
        require(path.is_dir(), 'managed directory is not a directory')
    else:
        path.mkdir(mode=0o700, parents=True)


def install(version, prefix, expected_sha=None):
    require(sys.version_info >= (3, 11), 'Python 3.11+ required')
    require(re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version), 'explicit semantic release tag required')
    native = target()
    prefix = Path(os.path.abspath(prefix.expanduser()))
    root = prefix / 'share/midnight-zkir-forge/binary'
    for directory in (prefix, prefix / 'share', root.parent, root, root / 'releases', prefix / 'bin'):
        managed_directory(directory)
    links = {prefix / 'bin' / name: root / 'current/bin' / name for name in COMMANDS}
    # Keep the public new name usable across upgrades and historical rollbacks.
    links[prefix / 'bin' / PRIMARY] = root / 'current/bin/midnight-zkir-forge'
    for path, expected in links.items():
        require(not os.path.lexists(path) or (path.is_symlink() and path.readlink() == expected), 'unrelated executable exists; choose --prefix or retire old launcher explicitly: ' + str(path))
    with os.fdopen(os.open(root / '.install.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('another installer is active; retry when it exits') from error
        current = root / 'current'
        require(not os.path.lexists(current) or current.is_symlink(), 'active path is not a managed symlink')
        if current.is_symlink():
            require(current.resolve().is_relative_to(root / 'releases'), 'unrelated active pointer')
        release = gh('release', 'view', version, '--repo', REPOSITORY, '--json', 'tagName,isDraft,isPrerelease,assets')
        require(release['tagName'] == version and not release['isDraft'], 'draft or conflicting release')
        asset = f'midnight-zkir-forge-{version}-{native}.tar.gz'
        matches = [a for a in release['assets'] if a['name'] == asset]
        require(len(matches) == 1 and 0 < matches[0]['size'] <= MAX_DOWNLOAD, 'qualified target asset unavailable or exceeds budget')
        require(sum(a['name'] == 'SHA256SUMS' and a['size'] <= 1024 ** 2 for a in release['assets']) == 1, 'checksum asset unavailable')
        commit = gh('api', f'repos/{REPOSITORY}/commits/{version}')['sha']
        with tempfile.TemporaryDirectory(prefix='.install-', dir=root) as temporary:
            stage = Path(temporary)
            gh('release', 'download', version, '--repo', REPOSITORY, '--pattern', asset, '--pattern', 'SHA256SUMS', '--dir', stage, output_dir=stage)
            bundle = stage / asset
            require(bundle.stat().st_size <= MAX_DOWNLOAD, 'download byte budget exceeded')
            sums = stage / 'SHA256SUMS'
            require(sums.stat().st_size <= 1024 ** 2, 'checksum metadata exceeds limit')
            sha = checksum(sums.read_bytes(), asset)
            require(digest(bundle) == sha and (expected_sha is None or expected_sha == sha), 'bundle checksum mismatch')
            identity = f'{version}-{native}-{sha}'
            require(all(p.name == identity for p in (root / 'releases').glob(f'{version}-{native}-*')), 'published tag content changed; request a new release tag')
            unpacked = extract(bundle, stage, asset.removesuffix('.tar.gz'))
            metadata = unpacked / 'manifest.json'
            require(metadata.stat().st_size <= 1024 ** 2, 'manifest too large')
            manifest = strict_json(metadata.read_bytes())
            require(manifest['tag'] == version and manifest['version'] == version[1:] and manifest['target'] == native and manifest['source_commit'] == commit, 'release/manifest mismatch')
            runtime(manifest['minimum'])
            inventory(unpacked, manifest)
            smoke(unpacked, manifest)
            destination = root / 'releases' / identity
            if destination.exists():
                require(not destination.is_symlink(), 'release symlink refused')
                require((destination / 'manifest.json').read_bytes() == metadata.read_bytes(), 'installed manifest differs')
                inventory(destination, manifest)
            else:
                unpacked.rename(destination)
            # Version is complete before pointer publication or initial command-link creation.
            pointer = stage / 'current'
            pointer.symlink_to(destination)
            os.replace(pointer, current)
            for path, expected in links.items():
                if not os.path.lexists(path):
                    path.symlink_to(expected)
                else:
                    require(path.is_symlink() and path.readlink() == expected, 'raced executable conflict; verified release retained')
            return {'version': version, 'target': native, 'directory': str(destination), 'prefix': str(prefix), 'prerelease': release['isPrerelease']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--prefix', type=Path, default=Path.home() / '.local')
    parser.add_argument('--sha256')
    parser.add_argument('--github-path', action='store_true',
                        help='append PREFIX/bin to GITHUB_PATH after successful installation')
    args = parser.parse_args()
    if args.sha256:
        require(re.fullmatch('[0-9a-f]{64}', args.sha256), 'invalid expected SHA-256')
    with contextlib.ExitStack() as stack:
        path_stream = None
        if args.github_path:
            configured = os.environ.get('GITHUB_PATH')
            require(configured is not None and configured != '', '--github-path requires GITHUB_PATH')
            github_path = Path(configured)
            require(github_path.is_absolute() and github_path.is_file() and not github_path.is_symlink(),
                    'GITHUB_PATH must be an existing absolute regular file')
            bin_path = str(Path(os.path.abspath(args.prefix.expanduser())) / 'bin')
            require('\n' not in bin_path and '\r' not in bin_path, 'installation PATH contains a newline')
            descriptor = os.open(github_path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
            path_stream = stack.enter_context(os.fdopen(descriptor, 'a'))
            require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'GITHUB_PATH is not a regular file')
        result = install(args.version, args.prefix, args.sha256)
        if path_stream is not None:
            path_stream.write(bin_path + '\n')
    print(json.dumps(result))
    print('Add ' + str(Path(result['prefix']) / 'bin') + ' to PATH. Stop Forge operations before switching releases.', file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired, tarfile.TarError) as error:
        print('Forge installation refused: ' + str(error), file=sys.stderr)
        sys.exit(1)
