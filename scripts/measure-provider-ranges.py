#!/usr/bin/env python3
"""Local range-cost receipt: actual verified snapshots and authenticated loopback HTTP."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['binary', 'reader', 'bundle', 'output']:
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--artifact', required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'fresh receipt required'
    manifest = sha(args.bundle/'compiler/contract-manifest.json')
    artifact = args.bundle/args.artifact
    assert artifact.resolve().is_relative_to(args.bundle.resolve())
    size, digest = artifact.stat().st_size, sha(artifact)
    assert size >= 8
    rows = []
    with tempfile.TemporaryDirectory(prefix='forge-range-measure-') as directory:
        work = Path(directory).resolve()
        binary = args.binary.absolute()
        views = work/'views'
        published = subprocess.run([binary, '--cache-dir', work/'cache', 'publish-view',
            args.bundle, '--manifest-sha256', manifest, '--provider-root', views],
            check=True, capture_output=True, text=True)
        assert json.loads(published.stdout)['view_id'] == manifest
        core = json.loads(subprocess.check_output([args.reader, views/manifest, manifest, args.artifact], text=True))
        for row in core['rows']:
            assert row['returned_bytes'] == size
            assert row['snapshot_logical_bytes'] == size*row['requests']
            assert row['peak_live_snapshot_logical_bytes'] == size*row['concurrency']
        token = secrets.token_hex(32)
        token_file = work/'token'
        token_file.write_text(token)
        token_file.chmod(0o600)
        with socket.socket() as available:
            available.bind(('127.0.0.1', 0))
            port = available.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        process = subprocess.Popen([binary, '--cache-dir', work/'http-cache', 'serve',
            '--listen', f'127.0.0.1:{port}', '--provider-root', views, '--token-file', token_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+30
            while True:
                try:
                    with urllib.request.urlopen(base+'/health/live', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('isolated HTTP server did not start')
                    time.sleep(.05)
            url = base+'/views/'+manifest+'/'+args.artifact

            def fetch(index, chunks):
                headers = {'Authorization':'Bearer '+token}
                begin, end = size*index//chunks, size*(index+1)//chunks
                if chunks > 1:
                    headers.update({'Range':f'bytes={begin}-{end-1}', 'If-Range':'"'+digest+'"'})
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                    body = response.read()
                    assert response.status == (200 if chunks == 1 else 206)
                    assert response.headers['ETag'] == '"'+digest+'"'
                    if chunks > 1:
                        assert response.headers['Content-Range'] == f'bytes {begin}-{end-1}/{size}'
                    assert len(body) == end-begin
                    return index, body

            for repeat in range(3):
                for label, chunks, parallel in [('full',1,1), ('sequential-ranges',8,1), ('concurrent-ranges',8,2)]:
                    start = time.monotonic()
                    if parallel == 1:
                        bodies = [fetch(index,chunks) for index in range(chunks)]
                    else:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
                            bodies = list(pool.map(lambda index:fetch(index,chunks), range(chunks)))
                    elapsed = (time.monotonic()-start)*1000
                    reconstructed = hashlib.sha256()
                    for _, data in sorted(bodies):
                        reconstructed.update(data)
                    returned = sum(len(data) for _, data in bodies)
                    assert reconstructed.hexdigest() == digest
                    rows.append({'repeat':repeat+1, 'mode':label,'requests':chunks,'concurrency':parallel,
                                 'wall_ms':elapsed,'response_body_bytes':returned,'digest_verified':True})
                    del bodies
        finally:
            process.terminate()
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
    receipt = {'schema':1,'status':'passed','host':platform.platform(),
        'manifest_sha256':manifest,'artifact':args.artifact,'artifact_sha256':digest,'artifact_bytes':size,
        'tools':{'cli_sha256':sha(args.binary),'reader_sha256':sha(args.reader),
                 'harness_sha256':sha(Path(__file__))},'provider_reader':core,'http':rows,
        'decision':'Retain full-file verification and anonymous snapshots; document measured amplification. No persistent trusted marker or unchecked range optimization.',
        'scope':'Warm local filesystem and authenticated loopback; logical snapshot lengths/allocation measured directly, not physical device counters. No hosted/CDN/CI or cold-cache throughput claim.',
        'cleanup':'owned views, snapshot descriptors, token, server and temporary stores removed'}
    with args.output.open('x') as stream:
        json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(args.output),'artifact_bytes':size,'http_lanes':len(rows)}))


if __name__ == '__main__':
    main()
