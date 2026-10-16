#!/usr/bin/env python3
"""Audit and preserve Cargo and Rust standard-library notices for a native portable bundle."""
import argparse
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.request

# Audited immutable upstream license files omitted by these published crate archives.
# Every request verifies both the crate VCS revision and the SHA256 below.
SUPPLEMENTS = {'blake2b_simd@1.0.4': [['https://raw.githubusercontent.com/oconnor663/blake2_simd/6a94ae2e18985c7c35bada8a4d438bfe9ab0d0c0/LICENSE',
                         '27e0387973d6b8507cb15f825f6f26e0278d4d5857082c1f56b49a7b39a90183']],
 'blake2b_simd@1.0.5': [['https://raw.githubusercontent.com/oconnor663/blake2_simd/47714dc3c424e82213d7f2eb4a833e3843017be5/LICENSE',
                         '27e0387973d6b8507cb15f825f6f26e0278d4d5857082c1f56b49a7b39a90183']],
 'blst@0.3.17': [['https://raw.githubusercontent.com/supranational/blst/54e6e55674722fc2797ebb4bbb71b26d881eb4b8/LICENSE',
                  'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4']],
 'dispatch2@0.3.1': [['https://raw.githubusercontent.com/madsmtm/objc2/8852b424193ca41602281b3d7540d7c8ed51e49a/LICENSE.md',
                      '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']],
 'halo2derive@0.2.0': [['https://raw.githubusercontent.com/privacy-scaling-explorations/halo2curves/4b7a69e6a3f1878b150c212d73ec82a3210c29f9/LICENSE-MIT',
                        '23f18e03dc49df91622fe2a76176497404e46ced8a715d9d2b67a7446571cca3'],
                       ['https://raw.githubusercontent.com/privacy-scaling-explorations/halo2curves/4b7a69e6a3f1878b150c212d73ec82a3210c29f9/LICENSE-APACHE',
                        '769f80b5bcb42ed0af4e4d2fd74e1ac9bf843cb80c5a29219d1ef3544428a6bb']],
 'objc2-core-foundation@0.3.2': [['https://raw.githubusercontent.com/madsmtm/objc2/7b1abfd750a2cacaea71d6a56ecfb83cb7de560b/LICENSE.md',
                                  '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']],
 'objc2-encode@4.1.0': [['https://raw.githubusercontent.com/madsmtm/objc2/8d214f5477365ffcbcbb7de058c86ed9a518efb7/LICENSE.md',
                         '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']],
 'objc2-io-kit@0.3.2': [['https://raw.githubusercontent.com/madsmtm/objc2/7b1abfd750a2cacaea71d6a56ecfb83cb7de560b/LICENSE.md',
                         '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']],
 'objc2-open-directory@0.3.2': [['https://raw.githubusercontent.com/madsmtm/objc2/7b1abfd750a2cacaea71d6a56ecfb83cb7de560b/LICENSE.md',
                                 '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']],
 'objc2@0.6.4': [['https://raw.githubusercontent.com/madsmtm/objc2/8852b424193ca41602281b3d7540d7c8ed51e49a/LICENSE.md',
                  '7f976f7e9cb2d87df7230606feb932c3f21ac0e664045a775b600046ff850c54']]}

GRAPHS = {'root': 'Cargo.toml', 'v3': 'workers/zkir3/Cargo.toml', 'v31': 'workers/zkir31/Cargo.toml'}

def run(*args, cwd=None):
    return subprocess.run(list(map(str, args)), cwd=cwd, check=True, capture_output=True).stdout

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def is_notice(name):
    return pathlib.PurePosixPath(name).name.lower().startswith(
        ('license', 'licence', 'copying', 'notice', 'copyright', 'unlicense'))

def is_license(name):
    return pathlib.PurePosixPath(name).name.lower().startswith(
        ('license', 'licence', 'copying', 'unlicense'))

def selected(metadata):
    nodes = {node['id']: node for node in metadata['resolve']['nodes']}
    pending = list(metadata['workspace_members'])
    result = set()
    while pending:
        key = pending.pop()
        if key in result:
            continue
        result.add(key)
        pending.extend(dependency['pkg'] for dependency in nodes[key]['deps'])
    return [package for package in metadata['packages'] if package['id'] in result]

def supplement(package, vcs):
    key = package['name'] + '@' + package['version']
    values = SUPPLEMENTS.get(key, [])
    require(values, f'no audited license supplement for {key}')
    result = []
    for url, expected in values:
        require(vcs and vcs['git']['sha1'] in url, f'upstream license revision mismatch: {key}')
        require(url.startswith(package['repository'].replace('https://github.com/',
                  'https://raw.githubusercontent.com/').removesuffix('.git') + '/'),
                f'upstream license repository mismatch: {key}')
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        require(digest(data) == expected, f'upstream license SHA256 mismatch: {url}')
        result.append((url.rsplit('/', 1)[1], data, url))
    return result

def package_notices(package, checksums):
    source = package['source']
    directory = pathlib.Path(package['manifest_path']).parent
    if source and source.startswith('registry+'):
        # Use the original authenticated crate archive, not mutable extracted cache files.
        archive = directory.parent.parent.parent / 'cache' / directory.parent.name / (
            package['name'] + '-' + package['version'] + '.crate')
        data = archive.read_bytes()
        expected = checksums[(package['name'], package['version'], source)]
        require(digest(data) == expected, f'Cargo.lock archive checksum mismatch: {archive.name}')
        notices = []
        vcs = None
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as crate:
            prefix = package['name'] + '-' + package['version'] + '/'
            for member in crate.getmembers():
                require(member.name.startswith(prefix) or member.name == prefix[:-1], 'unexpected crate archive root')
                relative = member.name[len(prefix):]
                if member.isfile() and (is_notice(relative) or relative == package.get('license_file')):
                    notices.append((relative, crate.extractfile(member).read(), 'crate:' + relative))
                if member.isfile() and relative == '.cargo_vcs_info.json':
                    vcs = json.load(crate.extractfile(member))
        # Copyright/NOTICE attribution is supplemental; it cannot replace license terms.
        if not any(is_license(name) or name == package.get('license_file') for name, _, _ in notices):
            notices.extend(supplement(package, vcs))
        return notices, {'crate_sha256': expected, 'vcs': vcs}
    if source and source.startswith('git+'):
        revision = source.rsplit('#', 1)[1]
        top = pathlib.Path(run('git', '-C', directory, 'rev-parse', '--show-toplevel').decode().strip())
        require(run('git', '-C', top, 'rev-parse', 'HEAD').decode().strip() == revision,
                f'Git dependency revision mismatch: {package["name"]}')
        prefix = directory.relative_to(top).as_posix()
        files = run('git', '-C', top, 'ls-tree', '-r', '--name-only', revision).decode().splitlines()
        notices = []
        for name in files:
            path = pathlib.PurePosixPath(name)
            # Include ancestor notices plus every nested notice for bundled C/assembly sources.
            ancestor = path.parent == pathlib.PurePosixPath('.') or str(path.parent) == prefix or (
                prefix.startswith(str(path.parent) + '/'))
            descendant = prefix == '.' or name.startswith(prefix + '/')
            if is_notice(name) and (ancestor or descendant):
                notices.append((name, run('git', '-C', top, 'show', revision + ':' + name), source + ':' + name))
        return notices, {'git_revision': revision}
    notices = []
    for path in sorted(directory.rglob('*')):
        if path.is_file() and is_notice(path.name) and 'target' not in path.relative_to(directory).parts:
            notices.append((path.relative_to(directory).as_posix(), path.read_bytes(), 'source:' + path.relative_to(directory).as_posix()))
    # Workers inherit the Forge root license from their workspace distribution.
    for parent in directory.parents:
        license_path = parent / 'LICENSE'
        if license_path.is_file():
            notices.append(('workspace-LICENSE', license_path.read_bytes(), 'source:LICENSE'))
            break
        if (parent / '.git').exists():
            break
    return notices, {'local_source': True}

def collect_metadata(bundle, graphs, sysroot, rust_version, checksums, commit, target):
    """Internal audit entry point; graphs must come from the exact immutable release source."""
    destination = pathlib.Path(bundle) / 'LICENSES' / 'cargo'
    require(not destination.exists(), 'Cargo notices destination already exists')
    destination.mkdir(parents=True)
    records = {}
    for graph, metadata in graphs.items():
        for package in selected(metadata):
            key = (package['name'], package['version'], package['source'])
            if key in records:
                records[key]['graphs'].append(graph)
                continue
            notices, provenance = package_notices(package, checksums)
            require(notices, f'no license/NOTICE files: {package["name"]}@{package["version"]}')
            require(package['license'] or package.get('license_file'), f'no licensing declaration: {package["name"]}')
            identity = package['name'] + '-' + package['version'] + '-' + digest((package['source'] or 'forge').encode())[:12]
            output = destination / identity
            output.mkdir()
            inventory = []
            for number, (name, data, origin) in enumerate(notices):
                require(data.strip(), f'empty notice: {package["name"]}/{name}')
                filename = f'{number:03d}-' + pathlib.PurePosixPath(name).name
                (output / filename).write_bytes(data)
                inventory.append({'path': (output / filename).relative_to(bundle).as_posix(),
                                  'original_path': name, 'origin': origin, 'sha256': digest(data), 'bytes': len(data)})
            records[key] = {'name': package['name'], 'version': package['version'], 'source': package['source'],
                            'repository': package['repository'], 'license_expression': package['license'],
                            'license_file': package.get('license_file'), 'graphs': [graph],
                            'provenance': provenance, 'notices': inventory}
    rust_docs = pathlib.Path(sysroot) / 'share/doc/rust'
    rust_output = pathlib.Path(bundle) / 'LICENSES/rust-standard-library'
    rust_output.mkdir()
    files = [rust_docs / 'COPYRIGHT-library.html', *sorted((rust_docs / 'licenses').glob('*'))]
    require(files[0].is_file() and len(files) > 1, 'Rust standard library notices unavailable')
    rust_notices = []
    for path in files:
        if path.is_file():
            data = path.read_bytes()
            (rust_output / path.name).write_bytes(data)
            rust_notices.append({'path': (rust_output / path.name).relative_to(bundle).as_posix(),
                                 'sha256': digest(data), 'bytes': len(data)})
    inventory = {'schema': 1, 'source_commit': commit, 'target': target,
                 'scope': 'Conservative native-target Cargo dependency closure, including build/dev dependencies; not a binary symbol attribution.',
                 'rust': {'version_verbose': rust_version, 'notices': rust_notices},
                 'packages': sorted(records.values(), key=lambda p: (p['name'], p['version'], p['source'] or ''))}
    path = pathlib.Path(bundle) / 'LICENSES/cargo-inventory.json'
    path.write_text(json.dumps(inventory, indent=2) + '\n')
    (pathlib.Path(bundle) / 'LICENSES/NOTICE').write_text(
        'This distribution includes the pinned Forge Cargo dependency closures and Rust standard library.\n'
        'Original license and copyright notices are preserved in cargo/ and rust-standard-library/.\n'
        'See cargo-inventory.json for exact package versions, sources, archive checksums, graphs and notice hashes.\n'
        'Native shared-library notices and corresponding source are inventoried separately.\n'
        'No dependency source modifications are made by this notice collector.\n')
    return inventory

def collect(bundle, nix, flake_ref, repository, commit):
    """Collect native-target notices from Nix-owned Cargo and an exact clean source commit."""
    repository = pathlib.Path(repository).resolve()
    require(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'full source commit required')
    require(flake_ref == f'git+file://{repository}?rev={commit}', 'flake source must match release commit')
    with tempfile.TemporaryDirectory(prefix='forge-cargo-notices-') as temporary:
        source = pathlib.Path(temporary)
        archive = run('git', '-C', repository, 'archive', '--format=tar', commit)
        # git archive contains tracked source only; reject unusual paths and links before extraction.
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                path = pathlib.PurePosixPath(member.name)
                require(not path.is_absolute() and '..' not in path.parts and not member.issym() and not member.islnk(),
                        'unsafe source archive member')
            tar.extractall(source, filter='data')
        def cargo(*args):
            return run(nix, 'develop', flake_ref, '--command', *args, cwd=source)
        rust_version = cargo('rustc', '-vV').decode()
        target = next(line.removeprefix('host: ') for line in rust_version.splitlines() if line.startswith('host: '))
        sysroot = cargo('rustc', '--print', 'sysroot').decode().strip()
        graphs = {}
        checksums = {}
        for graph, manifest in GRAPHS.items():
            graphs[graph] = json.loads(cargo('cargo', 'metadata', '--locked', '--format-version', '1',
                                               '--filter-platform', target, '--manifest-path', str(source / manifest)))
            lock = tomllib.loads((source / pathlib.Path(manifest).parent / 'Cargo.lock').read_text())
            for package in lock['package']:
                if 'checksum' in package:
                    checksums[(package['name'], package['version'], package['source'])] = package['checksum']
        return collect_metadata(pathlib.Path(bundle), graphs, sysroot, rust_version, checksums, commit, target)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=pathlib.Path, required=True)
    parser.add_argument('--nix', default='/nix/var/nix/profiles/default/bin/nix')
    parser.add_argument('--repository', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent)
    parser.add_argument('--commit', required=True)
    arguments = parser.parse_args()
    result = collect(arguments.bundle, arguments.nix,
                     f'git+file://{arguments.repository.resolve()}?rev={arguments.commit}',
                     arguments.repository, arguments.commit)
    print(json.dumps({'packages': len(result['packages']), 'target': result['target'], 'source_commit': result['source_commit']}))
