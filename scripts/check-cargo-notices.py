#!/usr/bin/env python3
"""Bounded offline licensing collector regressions; no compilation or source-cache mutation."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import tarfile
import tempfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('cargo_notices', ROOT / 'scripts/cargo-notices.py')
NOTICES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOTICES)


def refuses(action, message):
    try:
        action()
    except RuntimeError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError('Expected refusal: ' + message)


def fixture(base, files, name='example', version='1.0.0', license_file=None):
    directory = base / 'registry/src/index' / f'{name}-{version}'
    directory.mkdir(parents=True, exist_ok=True)
    archive = base / 'registry/cache/index' / f'{name}-{version}.crate'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'w:gz') as tar:
        for path, data in files.items():
            entry = tarfile.TarInfo(f'{name}-{version}/' + path)
            entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))
    package = {'name': name, 'version': version, 'source': 'registry+https://github.com/rust-lang/crates.io-index',
               'manifest_path': str(directory / 'Cargo.toml'), 'license_file': license_file}
    checksums = {(name, version, package['source']): hashlib.sha256(archive.read_bytes()).hexdigest()}
    return package, checksums, archive


def check():
    results = []
    # The outer guard makes accidental requests a hard failure: tests must stay offline.
    with patch.object(NOTICES.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network request')):
        refuses(lambda: NOTICES.supplement({'name': 'unreviewed', 'version': '1'}, None), 'no audited license supplement')
        results.append('unlisted supplement rejected')
        blst = {'name': 'blst', 'version': '0.3.17', 'repository': 'https://github.com/supranational/blst'}
        refuses(lambda: NOTICES.supplement(blst, {'git': {'sha1': '0' * 40}}), 'revision mismatch')
        results.append('wrong crate VCS revision rejected')
        with patch.object(NOTICES.urllib.request, 'urlopen', return_value=contextlib.closing(io.BytesIO(b'tampered license'))):
            refuses(lambda: NOTICES.supplement(blst, {'git': {'sha1': '54e6e55674722fc2797ebb4bbb71b26d881eb4b8'}}), 'SHA256 mismatch')
        results.append('tampered upstream supplement rejected')
        with tempfile.TemporaryDirectory(prefix='forge-notices-check-') as temporary:
            base = pathlib.Path(temporary)
            package, checksums, archive = fixture(base, {'LICENSE': b'Original license'})
            archive.write_bytes(b'tampered archive')
            refuses(lambda: NOTICES.package_notices(package, checksums), 'archive checksum mismatch')
            results.append('tampered registry archive rejected')
            package, checksums, _ = fixture(base, {'NOTICE': b'Original attribution'})
            refuses(lambda: NOTICES.package_notices(package, checksums), 'no audited license supplement')
            results.append('NOTICE-only unreviewed crate rejected')
            with patch.object(NOTICES, 'supplement', return_value=[('LICENSE', b'Original terms', 'immutable-upstream')]) as supplement:
                notices, _ = NOTICES.package_notices(package, checksums)
                supplement.assert_called_once()
                assert {name: data for name, data, _ in notices} == {'NOTICE': b'Original attribution', 'LICENSE': b'Original terms'}
            results.append('NOTICE-only crate supplemented while retaining original attribution')
            package, checksums, _ = fixture(base, {'NOTICE': b'Original attribution', 'TERMS.txt': b'Explicit license terms'}, license_file='TERMS.txt')
            notices, _ = NOTICES.package_notices(package, checksums)
            assert {name for name, _, _ in notices} == {'NOTICE', 'TERMS.txt'}
            results.append('explicit custom license_file accepted and retained')
            revision = 'a' * 40
            package = {'name': 'git-root', 'version': '1', 'source': 'git+https://example.test/repo#' + revision,
                       'manifest_path': str(base / 'Cargo.toml')}
            originals = {'LICENSE': b'Original root terms', 'vendor/backend/NOTICE': b'Original vendor attribution',
                         'vendor/backend/LICENSE': b'Original vendor terms'}
            def git(*args, **kwargs):
                if args[-2:] == ('rev-parse', '--show-toplevel'):
                    return str(base).encode() + b'\n'
                if args[-2:] == ('rev-parse', 'HEAD'):
                    return revision.encode() + b'\n'
                if 'ls-tree' in args:
                    return ('\n'.join(originals) + '\n').encode()
                if 'show' in args:
                    return originals[args[-1].split(':', 1)[1]]
                raise AssertionError(args)
            with patch.object(NOTICES, 'run', side_effect=git):
                notices, _ = NOTICES.package_notices(package, {})
            assert {name: data for name, data, _ in notices} == originals
            results.append('Git repository-root package retains nested vendor notices and licenses')
    return {'schema': 1, 'network': 'disabled by test guard', 'checks': results, 'passed': len(results),
            'collector_sha256': hashlib.sha256((ROOT / 'scripts/cargo-notices.py').read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path)
    arguments = parser.parse_args()
    receipt = json.dumps(check(), indent=2) + '\n'
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(receipt)
    print(receipt, end='')
