#!/usr/bin/env python3
"""Offline packaging smoke test; only creates/removes its own temporary volume."""
import argparse
import json
import subprocess
import pathlib
import secrets
import tempfile
import time
import urllib.request
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', default='midnight-zkir-forge:2026.10.0')
args = parser.parse_args()

def docker(*arguments, check=True):
    return subprocess.run(['docker', *arguments], check=check, capture_output=True,
                          text=True, timeout=60)

image = json.loads(docker('image', 'inspect', args.image).stdout)[0]
assert image['Os'] == 'linux', 'image must contain Linux binaries'
assert image['Config']['User'] == '65532:65532', 'image must run unprivileged'
volume = 'forge-smoke-' + uuid.uuid4().hex
container = volume + '-server'
docker('volume', 'create', volume)
try:
    command = ['run', '--rm', '--pull=never', '--network=none', '--read-only',
               '--cap-drop=ALL', '--security-opt=no-new-privileges:true',
               '--tmpfs', '/tmp:mode=1777,size=256m', '--mount',
               f'type=volume,source={volume},target=/data', args.image]
    version = docker(*command, '--version').stdout.strip()
    assert version.startswith('midnight-zkir-forge 0.2.'), version
    refused = docker(*command, 'serve', '--listen', '0.0.0.0:8787', check=False)
    assert refused.returncode != 0, 'public bind without token must fail'
    error = (refused.stdout + refused.stderr).lower()
    assert 'token' in error, error
    with tempfile.TemporaryDirectory(prefix='forge-container-secret-') as directory:
        token_file = pathlib.Path(directory) / 'token'
        token_file.write_text(secrets.token_hex(32))
        token_file.chmod(0o644)  # dedicated temporary secret, readable by UID65532
        server = ['run', '--detach', '--name', container, '--pull=never',
                  '--publish', '127.0.0.1::8787', '--read-only', '--cap-drop=ALL',
                  '--security-opt=no-new-privileges:true', '--tmpfs',
                  '/tmp:mode=1777,size=256m', '--mount',
                  f'type=volume,source={volume},target=/data', '--mount',
                  f'type=bind,source={token_file},target=/run/secrets/forge-token,readonly',
                  args.image]
        docker(*server)
        binding = json.loads(docker('inspect', container).stdout)[0]['NetworkSettings']['Ports']['8787/tcp'][0]
        assert binding['HostIp'] == '127.0.0.1'
        url = 'http://127.0.0.1:' + binding['HostPort']
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(url + '/health/live', timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('container did not become live')
                time.sleep(0.1)
        subprocess.run(['python3', str(pathlib.Path(__file__).with_name('check-http.py')),
                        '--url', url, '--token-file', str(token_file)],
                       check=True, timeout=60)
    print(json.dumps({'linux_image': True, 'nonroot': True,
                      'version': version, 'public_bind_without_token_refused': True,
                      'authenticated_source_roundtrip': True, 'real_key_generation_tested': False}))
finally:
    docker('rm', '--force', container, check=False)
    docker('volume', 'rm', volume)
