#!/usr/bin/env python3
"""Real compiler-wrapper and production provider-view qualification; owned scratch only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'integration/providers'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, *, env=None, timeout=300):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True,
                            timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError(f'{Path(str(command[0])).name} failed ({result.returncode}): '
                           f'{result.stderr[-6000:]}\n{result.stdout[-3000:]}')
    return result.stdout


def inventory(bundle):
    return {str(path.relative_to(bundle)): sha(path)
            for path in sorted(bundle.rglob('*')) if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['binary', 'compiler-dir', 'params-dir', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.absolute()  # retain matched sibling worker link cohort
    compiler = args.compiler_dir.resolve(strict=True)
    params = args.params_dir.resolve(strict=True)
    worker = binary.parent / 'midnight-zkir-forge-zkir31-worker'
    assert binary.is_file() and worker.is_file(), 'matched CLI/worker required'
    assert not args.output.exists(), 'new receipt path required'
    environment = dict(os.environ, MIDNIGHT_PP=str(params))
    for name in ['FORGE_PROVIDER_VIEW_URL', 'FORGE_PROVIDER_VIEW_TOKEN',
                 'MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER', 'MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER']:
        environment.pop(name, None)
    scratch = PROJECT / '.local'
    scratch.mkdir(exist_ok=True)
    process = None
    with tempfile.TemporaryDirectory(prefix='adapter-api-', dir=scratch) as directory:
        work = Path(directory).resolve()
        qualification = work / 'qualification.json'
        run([sys.executable, ROOT / 'scripts/check-providers.py', '--binary', binary,
             '--compiler-dir', compiler, '--params-dir', params, '--output', qualification],
            env=environment, timeout=600)
        qualified = json.loads(qualification.read_text())
        assert qualified['status'] == 'passed'
        qualification_hash = sha(qualification)
        cache = work / 'adapter-cache'
        provider_root = work / 'views'
        provider_root.mkdir()
        token_file = work / 'token'
        token = secrets.token_hex(32)
        token_file.write_text(token)
        token_file.chmod(0o600)
        with socket.socket() as available:
            available.bind(('127.0.0.1', 0))
            port = available.getsockname()[1]
        base = f'http://127.0.0.1:{port}'

        def request(path, method='GET', headers=None, auth=True):
            supplied = {'Authorization': 'Bearer ' + token} if auth else {}
            supplied.update(headers or {})
            req = urllib.request.Request(base + path, headers=supplied, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return response.status, response.headers, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.headers, error.read()

        with (work / 'server.log').open('w+') as log:
            process = subprocess.Popen(list(map(str, [binary, '--cache-dir', work / 'http-cache',
                'serve', '--listen', f'127.0.0.1:{port}', '--token-file', token_file,
                '--provider-root', provider_root])), stdout=log, stderr=log, env=environment)
            try:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        if request('/health/live', auth=False)[0] == 200:
                            break
                    except OSError:
                        pass
                    if process.poll() is not None or time.monotonic() >= deadline:
                        log.seek(0)
                        raise RuntimeError('provider server did not become live: ' + log.read())
                    time.sleep(.05)
                lanes = []
                reference = None
                cold_stats = None
                for label, mode in [('off', 'off'), ('local-cold', 'local'), ('local-warm', 'local')]:
                    bundle = work / label
                    command = [sys.executable, ROOT / 'scripts/compiler-local.py', '--mode', mode,
                               '--compiler-dir', compiler, '--params-dir', params]
                    if mode == 'local':
                        command += ['--binary', binary, '--cache-dir', cache, '--qualification',
                                    qualification, '--qualification-sha256', qualification_hash]
                    command += [PROJECT / 'fixtures/provider.compact', bundle]
                    run(command, env=environment)
                    current = inventory(bundle)
                    assert current['compiler/contract-manifest.json']
                    assert current['compiler/contract-info.json']
                    if reference is None:
                        reference = current
                        assert not cache.exists(), 'off mode created a Forge cache'
                    else:
                        assert current == reference, 'wrapper changed original compiler output bytes'
                    manifest_hash = current['compiler/contract-manifest.json']
                    stats = None
                    if mode == 'local':
                        stats = json.loads(run([binary, '--cache-dir', cache, 'stats'], env=environment))
                        totals = stats['totals']
                        assert totals['errors'] == 0
                        if label == 'local-cold':
                            assert totals['misses'] == 1 and totals['hits'] == 0
                            cold_stats = stats
                        else:
                            assert totals['misses'] == cold_stats['totals']['misses']
                            assert totals['hits'] == cold_stats['totals']['hits'] + 1
                    published = json.loads(run([binary, 'publish-view', bundle, '--manifest-sha256',
                                               manifest_hash, '--provider-root', provider_root], env=environment))
                    assert published['view_id'] == manifest_hash
                    assert published['reused'] is (label != 'off')
                    assert inventory(provider_root / manifest_hash) == current
                    prepared = json.loads(run([binary, '--profile', 'zkir31', '--cache-dir',
                        work / ('bare-cache-' + label), '--params-dir', params, 'prepare',
                        bundle / 'zkir/increment.zkir', '--name', 'increment'], env=environment))
                    proof_work = work / ('proofs-' + label)
                    proof_work.mkdir()
                    sdk_environment = dict(environment, FORGE_PROVIDER_VIEW_URL=base + '/views/' + manifest_hash,
                                           FORGE_PROVIDER_VIEW_TOKEN=token)
                    checks = json.loads(run(['node', PROJECT / 'check.mjs', bundle,
                        prepared['export']['base'], worker, params, proof_work], env=sdk_environment, timeout=600))
                    assert {item['lane'] for item in checks['lanes']} == {
                        'local', 'http', 'http-gzip', 'http-private', 'forge-api'}
                    for item in checks['lanes']:
                        assert all(item['proof_controls'][key] is True for key in [
                            'valid_proof_verified', 'invalid_statement_rejected', 'corrupt_proof_rejected'])
                    assert inventory(bundle) == current, 'qualification mutated compiler output'
                    lanes.append({'lane': label, 'compiler_output_sha256': current,
                                  'cache_stats': stats, 'publication': {'view_id': manifest_hash,
                                  'reused': published['reused']}, 'provider_checks': checks})
                # These are owned private exports, never installed/shared cache data.
                def adapter_command(source, output, pinned=qualification_hash):
                    return [sys.executable, ROOT / 'scripts/compiler-local.py', '--mode', 'local',
                            '--compiler-dir', compiler, '--params-dir', params, '--binary', binary,
                            '--cache-dir', cache, '--qualification', qualification,
                            '--qualification-sha256', pinned, source, output]

                def refuses_adapter(command, output):
                    refused = subprocess.run(list(map(str, command)), capture_output=True, text=True,
                                             timeout=300, env=environment)
                    assert refused.returncode != 0, 'unsafe compiler invocation unexpectedly succeeded'
                    assert not (output / 'compiler/contract-manifest.json').exists(), 'failed compiler emitted a final manifest'

                prepared = json.loads(run([binary, '--profile', 'zkir31', '--cache-dir', cache,
                    '--params-dir', params, 'prepare', work / 'local-warm/zkir/increment.zkir',
                    '--name', 'increment'], env=environment))
                private_export = Path(next(entry['path'] for entry in prepared['export']['files']
                                           if entry['kind'] == 'prover'))
                assert private_export.resolve().is_relative_to(cache.resolve()), 'refuse mutation outside private cache'
                saved_export = private_export.read_bytes()
                failed_output = work / 'refused-corrupt-export'
                try:
                    changed_export = bytearray(saved_export)
                    changed_export[-1] ^= 1
                    private_export.write_bytes(changed_export)
                    refuses_adapter(adapter_command(PROJECT / 'fixtures/provider.compact', failed_output), failed_output)
                finally:
                    private_export.write_bytes(saved_export)
                recovered_output = work / 'recovered-after-export-restore'
                run(adapter_command(PROJECT / 'fixtures/provider.compact', recovered_output), env=environment)
                assert inventory(recovered_output) == reference, 'recovery changed original compiler bundle'
                preserved_output = work / 'wrong-receipt-preflight'
                preserved_output.mkdir()
                (preserved_output / 'sentinel').write_bytes(b'owner output must survive preflight')
                before_preflight = inventory(preserved_output)
                refuses_adapter(adapter_command(PROJECT / 'fixtures/provider.compact', preserved_output,
                                                '0' * 64), preserved_output)
                assert inventory(preserved_output) == before_preflight, 'failed preflight changed existing output'
                modified_source = work / 'modified.compact'
                original_source = (PROJECT / 'fixtures/provider.compact').read_text()
                changed_source = original_source.replace('counter.increment(1)', 'counter.increment(2)')
                assert changed_source != original_source, 'fixture mutation was ineffective'
                modified_source.write_text(changed_source)
                unqualified_output = work / 'unqualified-current-zkir'
                refuses_adapter(adapter_command(modified_source, unqualified_output), unqualified_output)
                assert (unqualified_output / 'zkir/increment.zkir').is_file(), 'negative test did not reach current ZKIR generation'
                assert sha(unqualified_output / 'zkir/increment.zkir') != qualified['materialization'][0]['official_artifact_sha256']['source']
                adapter_controls = ['corrupt-private-export-refused-no-final-manifest',
                    'restored-private-export-retry-preserves-original-bundle',
                    'wrong-receipt-preflight-preserves-existing-output',
                    'modified-source-unqualified-zkir-refused-no-final-manifest']
                route = '/views/' + manifest_hash + '/keys/increment.prover'
                status, headers, body = request(route)
                original = (provider_root / manifest_hash / 'keys/increment.prover').read_bytes()
                assert status == 200 and body == original
                assert request(route, 'HEAD')[0] == 200
                assert request(route, headers={'If-None-Match': headers['ETag']})[0] == 304
                ranged = request(route, headers={'Range': 'bytes=0-7'})
                assert ranged[0] == 206 and ranged[2] == original[:8]
                assert request('/views/' + '0' * 64 + '/missing', auth=False)[0] == 401
                assert request('/views/' + manifest_hash + '/missing')[0] == 404
                assert request(route, 'POST')[0] == 405
                corrupt_file = provider_root / manifest_hash / 'keys/increment.prover'
                damaged = bytearray(original)
                damaged[-1] ^= 1
                try:
                    corrupt_file.write_bytes(damaged)
                    for method, conditional in [('HEAD', {}), ('GET', {'If-None-Match': headers['ETag']}),
                                                ('GET', {'Range': 'bytes=0-7'})]:
                        assert request(route, method, conditional)[0] == 409, 'corruption bypassed verification'
                    assert request('/views/' + manifest_hash + '/compiler/contract-manifest.json')[0] == 409
                finally:
                    corrupt_file.write_bytes(original)
                assert request(route)[0] == 200
                receipt = {'schema': 1, 'status': 'passed', 'qualification_sha256': qualification_hash,
                    'qualification': qualified, 'lanes': lanes, 'adapter_controls': adapter_controls,
                    'api_controls': ['authenticated-read', 'head', 'conditional', 'range',
                        'authentication-before-missing-lookup', 'undeclared-file', 'read-only-route',
                        'corrupt-head', 'corrupt-conditional', 'corrupt-range',
                        'corrupt-sibling-refuses-manifest', 'restored-bytes-recover'],
                    'harness_sha256': {str(path.relative_to(ROOT)): sha(path) for path in [
                        Path(__file__).resolve(), ROOT / 'scripts/compiler-local.py', PROJECT / 'check.mjs']},
                    'scope': 'native macOS ARM64 minimal Compact0.35 JSON3.1 fixture; real CLI, local compiler wrapper, '
                             'official SDK Node/Fetch and authenticated Forge HTTP provider views; '
                             'not arbitrary circuits, full Passport, Linux, browser/TLS/CDN or hosted savings',
                    'owned_scratch_cleanup': 'private compiler outputs, caches, keys, token, preimages and proof inputs removed on exit'}
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
    with args.output.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'adapter_lanes': len(lanes),
                      'genuine_proofs': sum(len(lane['provider_checks']['lanes']) for lane in lanes),
                      'api_controls': len(receipt['api_controls'])}))


if __name__ == '__main__':
    main()
