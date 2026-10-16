#!/usr/bin/env python3
"""Clean-container checks; invoked only by qualify-linux.py, never a host build."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase', choices=['offline', 'https'])
args = parser.parse_args()
kit = Path('/consumer')
assert os.getuid() == 1000
assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
assert not Path('/nix').exists() and not Path('/checkout').exists() and not (kit/'.git').exists()
assert all(shutil.which(tool) is None for tool in ['nix', 'cargo', 'rustc'])
assert 'MIDNIGHT_PP' not in os.environ
for line in (kit/'KIT_SHA256SUMS').read_text().splitlines():
    digest, relative = line.split('  ', 1)
    assert hashlib.sha256((kit/relative).read_bytes()).hexdigest() == digest, relative
facts = {'uid': os.getuid(), 'architecture': platform.machine(), 'kernel': platform.release(),
         'python': platform.python_version(), 'os_release': Path('/etc/os-release').read_text(),
         'nix_present': False, 'rust_present': False, 'MIDNIGHT_PP': None,
         'mountinfo': Path('/proc/self/mountinfo').read_text(), 'phase': args.phase}
(kit/(args.phase+'-environment.json')).write_text(json.dumps(facts, indent=2)+'\n')
if args.phase == 'offline':
    result = subprocess.run(['python3', str(kit/'scripts/check-release-candidate.py'),
                             '--directory', str(kit/'assets'), '--params-dir', str(kit/'params'),
                             '--require-nix-free', '--recovery'], capture_output=True, text=True)
    (kit/'offline.stderr').write_text(result.stderr)
    (kit/'offline.json').write_text(result.stdout)
    result.check_returncode()
else:
    spec = importlib.util.spec_from_file_location('installer', kit/'assets/install-release.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    archives = [p for p in (kit/'assets').glob('*.tar.gz') if not p.name.endswith('-runtime-sources.tar.gz')]
    assert len(archives) == 1
    archive = archives[0]
    rows = []
    with tempfile.TemporaryDirectory(prefix='forge-https-') as directory:
        root = installer.extract(archive, Path(directory), archive.name.removesuffix('.tar.gz'))
        manifest = json.loads((root/'manifest.json').read_text())
        installer.inventory(root, manifest)
        installer.runtime(manifest['minimum'])
        installer.smoke(root, manifest)
        for profile in ['ledger8-v2', 'zkir3', 'zkir31']:
            params = Path(directory)/profile
            assert not params.exists()
            result = subprocess.run([str(root/'bin/midnight-zkir-forge'), '--profile', profile,
                                     '--params-dir', str(params), '--fetch-params', 'qualify'],
                                    capture_output=True, text=True, timeout=600)
            (kit/('https-'+profile+'.stderr')).write_text(result.stderr)
            result.check_returncode()
            qualification = json.loads(result.stdout)
            assert all(qualification[key] for key in ['reproducible', 'valid_proof_verified',
                                                     'invalid_statement_rejected', 'corrupt_proof_rejected'])
            digest = hashlib.sha256((params/'bls_midnight_2p4').read_bytes()).hexdigest()
            assert digest == qualification['parameter_sha256'] == '232f401fad10c7ddf8828d2aa4c85c6506c5da09795998cecaeb9f75fc8f6ada'
            rows.append({'profile': profile, 'fresh_params_directory': True, 'qualification': qualification})
    (kit/'https.json').write_text(json.dumps({'source_commit': manifest['source_commit'],
        'candidate_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'rows': rows}, indent=2)+'\n')
