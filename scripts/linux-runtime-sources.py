"""Prepare exact macOS/Linux runtime notices and a same-release source companion.

Source access is a release obligation, not a URL-only assertion of compliance.
The binary bundle points to a checksummed companion asset containing full upstream
sources, locked Nixpkgs recipes/patches, and the exact Forge Git source bundle.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile


def run(*args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True,
                          text=True).stdout


def digest(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(root, output, stem, nix, flake_ref, system, repository, commit):
    """Write binary notices; return a separately prepared source asset path.

    Call before inventory/manifest creation. No upload or Git mutation occurs.
    flake_ref is the producer's immutable git+file reference to this clean commit.
    """
    root, output, repository = map(pathlib.Path, (root, output, repository))
    runtime_platform = 'darwin' if system.endswith('-darwin') else 'linux'
    nixpkgs_input = 'nixpkgs-intel' if system == 'x86_64-darwin' else 'nixpkgs'
    package_expression = f'(builtins.getAttr {json.dumps(nixpkgs_input)} (builtins.getFlake {json.dumps(flake_ref)}).inputs)'
    packages = f'({package_expression}).legacyPackages.{system}'
    package_names = ('libiconv',) if runtime_platform == 'darwin' else ('glibc', 'gcc', 'openssl')
    package_values = {'libiconv': 'p.libiconv', 'glibc': 'p.glibc', 'gcc': 'p.gcc.cc', 'openssl': 'p.openssl'}
    descriptions = ' '.join(name + '=describe ' + package_values[name] + ';' for name in package_names)
    metadata_expression = f'''let p={packages}; describe=x: {{
      name=x.name; source=toString x.src; patches=map toString (x.patches or []);
      license=x.meta.license; outputs=map (name: toString (builtins.getAttr name x)) x.outputs; }};
      in {{ {descriptions} }}'''
    metadata = json.loads(run(nix, 'eval', '--json', '--impure', '--expr', metadata_expression))
    origins_path = root / 'LICENSES' / (runtime_platform + '-runtime-origin.json')
    if origins_path.exists():
        origins = json.loads(origins_path.read_text())
        for library, origin in origins.items():
            source_path = pathlib.Path(origin['source_path']).resolve(strict=True)
            if digest(source_path) != origin['source_sha256']:
                raise RuntimeError('runtime source changed after relocation: ' + library)
            matches = [name for name, package in metadata.items()
                       if any(source_path.is_relative_to(pathlib.Path(output_path).resolve())
                              for output_path in package['outputs'])]
            if len(matches) != 1:
                raise RuntimeError('unmapped runtime library source: ' + library)
            metadata[matches[0]].setdefault('runtime_libraries', []).append(library)
    source_values = ' '.join(package_values[name] + '.src' for name in package_names)
    run(nix, 'build', '--no-link', '--json', '--impure', '--expr',
        f'let p={packages}; in [{source_values}]')
    nixpkgs = pathlib.Path(run(nix, 'eval', '--raw', '--impure', '--expr',
                               f'({package_expression}).outPath').strip())
    destination = output / (stem + '-runtime-sources.tar.gz')
    if destination.exists():
        raise RuntimeError('runtime source companion already exists')
    notices = root / 'LICENSES' / (runtime_platform + '-runtime')
    notices.mkdir(parents=True)
    license_members = {'glibc': ('COPYING', 'COPYING.LIB', 'LICENSES'),
                       'gcc': ('COPYING3', 'COPYING.RUNTIME'),
                       'openssl': ('LICENSE.txt',),
                       'libiconv': ('libiconv.txt',)}
    with tempfile.TemporaryDirectory(prefix='.runtime-sources-', dir=output) as directory:
        source_root = pathlib.Path(directory) / (stem + '-runtime-sources')
        (source_root / 'upstream').mkdir(parents=True)
        for name, package in metadata.items():
            archive = pathlib.Path(package['source'])
            if archive.is_dir():
                target = source_root / 'upstream' / (package['name'] + '-source.tar.gz')
                with tarfile.open(target, 'w:gz') as source:
                    source.add(archive, arcname=package['name'])
                package['source_tree_nar_hash'] = run(nix, 'hash', 'path', '--type', 'sha256', archive).strip()
            else:
                target = source_root / 'upstream' / archive.name.split('-', 1)[1]
                shutil.copyfile(archive, target)
            package['source_asset_path'] = target.relative_to(source_root).as_posix()
            package['source_sha256'] = digest(target)
            package['license_files'] = []
            with tarfile.open(target, 'r:*') as source:
                archive_root = source.next().name.rstrip('/')
                for member in license_members[name]:
                    entry = source.getmember(archive_root + '/' + member)
                    if not entry.isfile() or entry.size > 1024 * 1024:
                        raise RuntimeError('unexpected runtime license source')
                    path = notices / (name + '-' + member.replace('/', '-'))
                    path.write_bytes(source.extractfile(entry).read())
                    package['license_files'].append(path.relative_to(root).as_posix())
            if name == 'libiconv':
                # Apple's libiconv has BSD notices throughout its source and an
                # APSL1.0 libcharset implementation, rather than GNU LGPL files.
                blocks = {}
                for path in sorted(archive.rglob('*')):
                    if path.is_file() and path.suffix in ('.c', '.h', '.m', '.mm', '.y', '.l', '.sh'):
                        with path.open('rb') as source:
                            text = source.read(65536).decode('utf-8', errors='replace')
                        for block in re.findall(r'/\*.*?\*/', text, flags=re.S):
                            if re.search(r'copyright|license|redistribution', block, flags=re.I):
                                blocks.setdefault(block, []).append(path.relative_to(archive).as_posix())
                copyright_file = notices / 'libiconv-copyright-notices.txt'
                copyright_file.write_text('\n\n'.join('\n'.join(paths) + '\n' + block for block, paths in blocks.items()) + '\n')
                license_root = pathlib.Path(__file__).resolve().parent.parent / 'licenses/runtime'
                for filename in ('APSL-1.0.txt', 'SOURCES.json'):
                    destination_file = notices / filename
                    shutil.copyfile(license_root / filename, destination_file)
                    package['license_files'].append(destination_file.relative_to(root).as_posix())
                package['license_files'].append(copyright_file.relative_to(root).as_posix())
            for patch in package['patches']:
                pathlib.Path(patch).relative_to(nixpkgs)
        # Include the full exact Nixpkgs source, not only leaf recipes whose
        # imported build functions/patches could otherwise be omitted.
        with tarfile.open(source_root / 'nixpkgs-source.tar.gz', 'w:gz') as archive:
            archive.add(nixpkgs, arcname='nixpkgs')
        if run('git', '-C', repository, 'rev-parse', 'HEAD').strip() != commit:
            raise RuntimeError('source HEAD changed while preparing runtime sources')
        bundle = source_root / 'forge-source.bundle'
        run('git', '-C', repository, 'bundle', 'create', bundle, 'HEAD')
        if run('git', '-C', repository, 'bundle', 'list-heads', bundle).strip() != commit + ' HEAD':
            raise RuntimeError('source bundle does not identify the producer commit')
        source_manifest = {'schema': 1, 'source_commit': commit,
                           'nixpkgs_store_source': str(nixpkgs),
                           'runtime_packages': metadata,
                           'source_access': 'publish this companion beside the binary asset; never omit it'}
        (source_root / 'runtime-sources.json').write_text(json.dumps(source_manifest, indent=2) + '\n')
        instructions = '''macOS/Linux runtime sources and replacement

This source companion must accompany the binary asset at the same exact release.
The upstream source contents are unmodified; fixed directory sources are archived
as-is. runtime-sources.json records archive SHA-256 and directory NAR identities.
The full locked Nixpkgs source contains the actual package recipes and all selected
patches (paths recorded in runtime-sources.json). forge-source.bundle contains the
exact producer commit and history, including flake.lock and packaging scripts.

Rebuild (Nix required only for development):
  git clone forge-source.bundle forge
  cd forge
  git checkout SOURCE_COMMIT
  ./bootstrap.sh -- python3 scripts/build-release.py --tag RELEASE_TAG --output /fresh/output
Replace SOURCE_COMMIT/RELEASE_TAG with runtime-sources.json and binary manifest values.
Nix fetches locked public dependencies; the included nixpkgs-source.tar.gz and
upstream sources are available independently if the original download disappears.

The shared libraries use dynamic linking. You may modify/rebuild them and use a
modified Forge launcher with updated embedded runtime hashes to run those changes.
The hashes implement cache identity/integrity, not an installation signature or
restriction on modifying the program. A changed runtime/worker must use a new
compatibility identity; never reuse old pinned artifacts under a different runtime.

glibc: see COPYING, COPYING.LIB and LICENSES for per-file notices and LGPL terms.
GCC: libgcc runtime is covered by COPYING3 and COPYING.RUNTIME. The runtime
exception has conditions, including Eligible Compilation Process; merely naming
GPL does not establish those conditions. The producer uses the pinned unmodified
Rust/GCC compilation toolchain, with no proprietary GCC plugin or transformation.
OpenSSL: see Apache2.0 LICENSE.txt and retained source copyright notices.
Apple libiconv/libcharset: see BSD terms in libiconv.txt, retained per-file
copyright/license notices, APSL-1.0.txt and its immutable source citation.
The complete sources are supplied rather than a time-limited written source offer.
'''
        (source_root / 'README.txt').write_text(instructions)
        shutil.copytree(notices, source_root / 'runtime-license-notices')
        shutil.copyfile(source_root / 'README.txt', notices / 'SOURCE-ACCESS.txt')
        with tarfile.open(destination, 'w:gz') as archive:
            archive.add(source_root, arcname=source_root.name)
    notice = {'schema': 1, 'companion_asset': destination.name,
              'companion_sha256': digest(destination), 'packages': metadata,
              'requirement': 'publish the source companion and SHA256SUMS beside every corresponding binary'}
    (notices / 'manifest.json').write_text(json.dumps(notice, indent=2) + '\n')
    return destination
