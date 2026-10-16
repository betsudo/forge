#!/usr/bin/env python3
"""Real compiler + Forge + pinned SDK provider qualification in owned scratch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT/'integration/providers'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True,
                            timeout=180, check=True, **kwargs)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--compiler-dir', required=True, type=Path)
    parser.add_argument('--params-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    compiler = args.compiler_dir.resolve(strict=True)
    params = args.params_dir.resolve(strict=True)
    worker = binary.parent/'midnight-zkir-forge-zkir31-worker'
    assert not args.output.exists(), 'new receipt path required'
    # The documented fixture is specifically qualified against this official tool.
    expected = json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64', 'this compiler receipt qualifies native macOS ARM64 only'
    for name in ['compactc.bin', 'zkir-v3']:
        assert sha(compiler/name) == expected['tool_sha256']['tools/compiler/'+name], 'wrong official compiler bytes'
    assert (PROJECT/'node_modules').is_dir(), 'run pinned npm ci first'
    scratch = PROJECT/'.local'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qualification-', dir=scratch) as directory:
        work = Path(directory).resolve()
        bundle = work/'managed'
        environment = dict(os.environ, MIDNIGHT_PP=str(params))
        run([compiler/'compactc', '--feature-zkir-v3', PROJECT/'fixtures/provider.compact', bundle], env=environment)
        manifest = bundle/'compiler/contract-manifest.json'
        compiler_info = bundle/'compiler/contract-info.json'
        metadata = {str(p.relative_to(bundle)): sha(p) for p in [manifest, compiler_info]}
        # This fixture deliberately has exactly one provable circuit.
        sources = sorted((bundle/'zkir').glob('*.zkir'))
        assert [p.stem for p in sources] == ['increment']
        rows = []
        for source in sources:
            def prepare():
                return json.loads(run([binary, '--profile', 'zkir31', '--cache-dir', work/'cache',
                                       '--params-dir', params, 'prepare', source, '--name', source.stem]))
            cold, warm = prepare(), prepare()
            assert cold['cache']['hit'] is False and warm['cache']['hit'] is True
            assert cold['descriptor'] == warm['descriptor']
            descriptor = cold['descriptor']
            assert descriptor['record']['worker']['executable_sha256'] == sha(worker)
            assert descriptor['input_version'] == {'major':3, 'minor':1}
            artifact_hashes = {}
            for entry in warm['export']['files']:
                kind = entry['kind']
                destination = {'source':source, 'binary_ir':source.with_suffix('.bzkir'),
                    'prover':bundle/'keys'/(source.stem+'.prover'),
                    'verifier':bundle/'keys'/(source.stem+'.verifier')}[kind]
                exported = Path(entry['path'])
                assert sha(exported) == entry['sha256'] == sha(destination), 'official/Forge artifact mismatch'
                artifact_hashes[kind] = entry['sha256']
                if kind != 'source':
                    shutil.copyfile(exported, destination)  # private byte-identical copy, not a link
            assert all(sha(bundle/name) == digest for name, digest in metadata.items()), 'compiler metadata changed'
            rows.append({'circuit':source.stem, 'cold_hit':False, 'warm_hit':True,
                         'descriptor':descriptor, 'official_artifact_sha256':artifact_hashes})
        result = json.loads(run(['node', PROJECT/'check.mjs', bundle, warm['export']['base'], worker, params, work]))
        assert all(sha(bundle/name) == digest for name, digest in metadata.items())
        receipt = {'schema':1, 'status':'passed', 'host':{'system':platform.system(), 'machine':platform.machine()},
            'tool_versions':{'node':run(['node','--version']).strip(), 'python':sys.version.split()[0]},
            'compiler_version':run([compiler/'compactc.bin', '--version']).strip(),
            'tool_sha256':{name:sha(p) for name,p in [('compactc.bin',compiler/'compactc.bin'),
                ('zkir-v3',compiler/'zkir-v3'),('forge',binary),('worker',worker)]},
            'package_lock_sha256':sha(PROJECT/'package-lock.json'),
            'fixture_sha256':sha(PROJECT/'fixtures/provider.compact'),
            'harness_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(), PROJECT/'check.mjs']},
            'compiler_metadata_sha256':metadata, 'materialization':rows, 'provider_checks':result,
            'scope':'real minimal Compact0.35.0 JSON3.1 fixture with official SDK5.0.0-rc.2; not full Passport/Compact integration, Linux, browser/TLS/CDN or production HTTP provider readiness',
            'owned_scratch_cleanup':'temporary stores, copied keys, preimages and proof inputs removed on exit'}
    with args.output.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'output':str(args.output), 'lanes':len(result['lanes']), 'provider_controls':len(result['controls'])}))


if __name__ == '__main__':
    main()
