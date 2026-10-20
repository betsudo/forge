#!/usr/bin/env python3
"""Stage a minimal installed-consumer kit and qualify native Linux x86_64 offline/HTTPS.

Requires an exact clean-commit build-release.py candidate. Never mounts a checkout,
uses emulation, publishes a release, or prunes shared Docker/Nix resources.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent.parent
IMAGE = 'python:3.11-slim-bookworm@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590'


def run(*command, **kwargs):
    return subprocess.run(list(map(str, command)), check=True, capture_output=True, text=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64', 'native x86_64 Linux host required'
    assert os.environ.get('RUNNER_ARCH', 'X64') == 'X64'
    assert not run('git', '-C', ROOT, 'status', '--porcelain'), 'clean committed source required'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    candidate = args.candidate.resolve()
    revision = run('git', '-C', ROOT, 'rev-parse', 'HEAD').strip()
    (output/'producer-environment.json').write_text(json.dumps({'source_commit': revision,
        'architecture': platform.machine(), 'kernel': platform.release(), 'image': IMAGE,
        'runner_arch': os.environ.get('RUNNER_ARCH'), 'disk': run('df', '-h', '/')}, indent=2)+'\n')
    run('docker', 'pull', '--platform', 'linux/amd64', IMAGE)
    (output/'image.json').write_text(run('docker', 'image', 'inspect', IMAGE))
    nix = shutil.which('nix') or '/nix/var/nix/profiles/default/bin/nix'
    package = json.loads(run(nix, 'build', '--no-link', '--json', f'git+file://{ROOT}?rev={revision}#default'))[0]['outputs']['out']
    with tempfile.TemporaryDirectory(prefix='forge-consumer-kit-') as directory:
        kit = Path(directory)
        kit.chmod(0o755)
        (kit/'assets').mkdir()
        for path in candidate.iterdir():
            if path.name in ['install-release.py', 'zkir-forge-installer.sh', 'SHA256SUMS'] or (path.name.endswith('.tar.gz') and not path.name.endswith('-runtime-sources.tar.gz')):
                shutil.copyfile(path, kit/'assets'/path.name)
        (kit/'scripts').mkdir()
        for name in ['check-release-candidate.py', 'check-recovery.py', 'qualify-linux-consumer.py']:
            shutil.copyfile(ROOT/'scripts'/name, kit/'scripts'/name)
        shutil.copytree(ROOT/'fixtures', kit/'fixtures')
        params = kit/'params'
        # The official CLI verifies downloaded parameters; copy only its public k4 bytes.
        environment = dict(os.environ)
        environment.pop('LD_FOR_BUILD', None)
        fetched = json.loads(run(Path(package)/'bin/midnight-zkir-forge', '--params-dir', params,
                                 '--cache-dir', kit/'producer-cache', '--fetch-params', 'qualify', env=environment))
        assert fetched['parameter_sha256'] == hashlib.sha256((params/'bls_midnight_2p4').read_bytes()).hexdigest()
        (output/'producer-parameters.json').write_text(json.dumps(fetched, indent=2)+'\n')
        sums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(kit).as_posix()+'\n'
                       for p in sorted(kit.rglob('*')) if p.is_file())
        (kit/'KIT_SHA256SUMS').write_text(sums)
        (output/'KIT_SHA256SUMS').write_text(sums)
        for phase in ['offline', 'https']:
            name = 'forge-qualify-'+uuid.uuid4().hex
            created = False
            try:
                run('docker', 'create', '--name', name, '--platform', 'linux/amd64',
                    '--network', 'none' if phase == 'offline' else 'bridge', '--cap-drop', 'ALL',
                    '--cap-add', 'CHOWN', '--security-opt', 'no-new-privileges', IMAGE, 'sleep', 'infinity')
                created = True
                run('docker', 'start', name)
                run('docker', 'cp', str(kit)+'/.', name+':/consumer')
                run('docker', 'exec', name, 'chown', '-R', '1000:1000', '/consumer')
                inspected = json.loads(run('docker', 'inspect', name))
                assert not inspected[0]['Mounts'] and not inspected[0]['HostConfig']['Binds']
                (output/(phase+'-container.json')).write_text(json.dumps(inspected, indent=2)+'\n')
                result = subprocess.run(['docker', 'exec', '--user', '1000:1000', '-e', 'HOME=/tmp',
                    name, 'python3', '/consumer/scripts/qualify-linux-consumer.py', phase], capture_output=True, text=True)
                (output/(phase+'-process.stdout')).write_text(result.stdout)
                (output/(phase+'-process.stderr')).write_text(result.stderr)
                # Retrieve diagnostics even if a genuine test failed.
                for filename in [phase+'.json', phase+'-environment.json', 'offline.stderr',
                                 *['https-'+p+'.stderr' for p in ['ledger8-v2', 'zkir3', 'zkir31']]]:
                    subprocess.run(['docker', 'cp', name+':/consumer/'+filename, str(output/filename)], capture_output=True)
                result.check_returncode()
            finally:
                if created:
                    run('docker', 'rm', '-f', name)
        receipt = json.loads((output/'offline.json').read_text())
        assert len(receipt['profiles']) == 3 and receipt['recovery'] is not None
        assert all(all(row['qualification'][key] for key in ['reproducible', 'valid_proof_verified',
            'invalid_statement_rejected', 'corrupt_proof_rejected']) for row in receipt['profiles'])
        assert receipt['source_commit'] == revision and receipt['target'] == 'x86_64-unknown-linux-gnu'
        assert json.loads((output/'https.json').read_text())['source_commit'] == revision
        (output/'SUCCESS.json').write_text(json.dumps({'source_commit': revision, 'offline': True,
            'fresh_https': True, 'owned_containers_removed': True,
            'scope': 'native installed portable payload; fake GitHub release transport, not authenticated release downloading'}, indent=2)+'\n')


if __name__ == '__main__':
    main()
