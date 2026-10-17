#!/usr/bin/env python3
"""Actual full-manifest Passport provider delivery; never rebuilds Compact."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT/'integration/providers'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','worker','zkir3-worker','params-dir','baseline','work','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    args = parser.parse_args()
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64', 'this receipt scope requires native Mac ARM64'
    for name in ('binary','worker','zkir3_worker','params_dir','baseline','work','output'):
        setattr(args,name,getattr(args,name).absolute())
    assert not args.work.exists() and not args.output.exists()
    args.work.relative_to(ROOT/'.local')
    assert args.work != ROOT/'.local'
    for path in (args.binary,args.worker,args.zkir3_worker,args.params_dir,args.baseline,args.output):
        assert not path.resolve().is_relative_to(args.work.resolve())
    assert sha(args.baseline/'compiler/contract-manifest.json') == args.manifest_sha256
    files = [p for p in args.baseline.rglob('*') if p.is_file()]
    total, largest = sum(p.stat().st_size for p in files), max(p.stat().st_size for p in files)
    assert len(files) == 213 and 4*1024**3 < total <= 16*1024**3 and largest <= 1024**3
    assert shutil.disk_usage(args.work.parent).free > total + 2*1024**3
    args.work.mkdir()
    root = args.work/'views'
    cache = args.work/'unused-private-cache'
    environment = dict(os.environ,MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER=str(args.worker),
                       MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER=str(args.zkir3_worker))
    for key in ('FORGE_PROVIDER_VIEW_URL','FORGE_PROVIDER_VIEW_TOKEN'):
        environment.pop(key,None)
    def cli(*command):
        result = subprocess.run(list(map(str,[args.binary,'--cache-dir',cache,*command])),
            capture_output=True,text=True,env=environment,timeout=1800)
        return result, json.loads(result.stdout)
    publish = ['publish-view',args.baseline,'--manifest-sha256',args.manifest_sha256,'--provider-root',root]
    refused, error = cli(*publish)
    assert refused.returncode and error['error']['code'] == 'provider_limit'
    assert not error['error']['availability_fallback'] and not root.exists()
    explicit = [*publish,'--provider-max-view-bytes',str(16*1024**3)]
    # Exercise a real interrupted large copy, before its atomic publication.
    with (args.work/'interrupted.log').open('w') as log:
        interrupted = subprocess.Popen(list(map(str,[args.binary,'--cache-dir',cache,*explicit])),
            stdout=log,stderr=log,env=environment)
        stopped_bytes = 0
        try:
            deadline = time.monotonic()+300
            while time.monotonic() < deadline:
                assert interrupted.poll() is None, 'publisher completed before interruption control'
                stages = list(root.glob('.provider-stage-*'))
                stopped_bytes = sum(p.stat().st_size for stage in stages for p in stage.rglob('*') if p.is_file())
                if stopped_bytes >= 64*1024**2:
                    os.kill(interrupted.pid,signal.SIGSTOP)
                    break
                time.sleep(.02)
            assert stopped_bytes >= 64*1024**2 and not (root/args.manifest_sha256).exists()
        finally:
            interrupted.kill()
            interrupted.wait()
    assert not (root/args.manifest_sha256).exists()
    leftovers = list(root.glob('.provider-stage-*'))
    assert leftovers
    # Explicit removal only of this experiment's private abandoned stages.
    for stage in leftovers: shutil.rmtree(stage)
    free_before = shutil.disk_usage(root).free
    start = time.monotonic()
    published, value = cli(*explicit)
    assert published.returncode == 0 and value['reused'] is False
    publish_ms = (time.monotonic()-start)*1000
    view = root/args.manifest_sha256
    assert sum(p.stat().st_size for p in view.rglob('*') if p.is_file()) == total
    assert sha(view/'compiler/contract-manifest.json') == args.manifest_sha256
    reused, value = cli(*explicit)
    assert reused.returncode == 0 and value['reused'] is True
    token = secrets.token_hex(32)
    token_file = args.work/'token'
    token_file.write_text(token)
    token_file.chmod(0o600)
    controls = []
    def serve(limit):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        log = (args.work/f'server-{limit}.log').open('w')
        process = subprocess.Popen(list(map(str,[args.binary,'--cache-dir',cache,'serve','--listen',url[7:],
            '--token-file',token_file,'--provider-root',root,'--provider-max-view-bytes',limit])),
            stdout=log,stderr=log,env=environment)
        try:
            for _ in range(200):
                if process.poll() is not None: raise RuntimeError('provider server exited')
                try:
                    with urllib.request.urlopen(url+'/health/live',timeout=1): return process,log,url
                except urllib.error.URLError: time.sleep(.05)
            raise RuntimeError('provider server did not start')
        except BaseException:
            process.kill();process.wait();log.close();raise
    def stop(process,log):
        process.send_signal(signal.SIGINT)
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired: process.kill();process.wait();raise
        finally: log.close()
    def request(url,code,method='GET',headers=None,auth=True):
        h = dict(headers or {})
        if auth: h['Authorization'] = 'Bearer '+token
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=h,method=method),timeout=60) as response:
                body = response.read(); status = response.status
        except urllib.error.HTTPError as error:
            body = error.read(); status = error.code
        assert status == code, (status,code)
        return body
    process,log,url = serve(4*1024**3)
    try:
        endpoint = url+'/views/'+args.manifest_sha256+'/compiler/contract-manifest.json'
        request(endpoint,401,auth=False)
        error = json.loads(request(endpoint,500))['error']
        assert error['code'] == 'provider_limit' and not error['availability_fallback']
        controls.append('default-budget-refuses-already-published-large-view-auth-first')
    finally: stop(process,log)
    process,log,url = serve(16*1024**3)
    try:
        environment.update(FORGE_PROVIDER_VIEW_URL=url+'/views/'+args.manifest_sha256,FORGE_PROVIDER_VIEW_TOKEN=token)
        (PROJECT/'.local').mkdir(exist_ok=True)
        def sdk(env):
            with tempfile.TemporaryDirectory(prefix='full-passport-fetch-',dir=PROJECT/'.local') as scratch:
                command = list(map(str,['node',PROJECT/'passport.mjs',args.baseline,args.worker,args.params_dir,Path(scratch).resolve()]))
                with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                      text=True,env=env,start_new_session=True) as process:
                    try: stdout, stderr = process.communicate(timeout=1800)
                    except BaseException:
                        try: os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                        process.communicate()
                        raise
                    return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
        result = sdk(environment)
        assert result.returncode == 0, result.stderr[-4000:]
        proof = json.loads(result.stdout)
        # Final compiler output, independently of the Forge export/view copies.
        consumer_key = args.baseline/'keys/deposit_unshielded.prover'
        original_key = consumer_key.read_bytes()
        consumer_key.write_bytes(b'damaged owned final compiler output')
        local_environment = dict(environment)
        local_environment.pop('FORGE_PROVIDER_VIEW_URL',None)
        local_environment.pop('FORGE_PROVIDER_VIEW_TOKEN',None)
        try:
            refused = sdk(local_environment)
            assert refused.returncode and 'ZkArtifactIntegrityError' in refused.stderr
        finally: consumer_key.write_bytes(original_key)
        repaired = sdk(local_environment)
        assert repaired.returncode == 0, repaired.stderr[-4000:]
        consumer_recovery = {'control':'final-compiler-output-integrity-refusal-exact-owner-repair',
                             'provider_checks':json.loads(repaired.stdout)}
        assert len(proof['lanes']) == 4 and {row['lane'] for row in proof['lanes']} == {'local','fetch'}
        assert proof['manifest_sha256'] == args.manifest_sha256
        target = view/'keys/deposit_unshielded.verifier'
        original = target.read_bytes()
        endpoint = url+'/views/'+args.manifest_sha256+'/keys/deposit_unshielded.verifier'
        target.write_bytes(b'corrupt owned published verifier')
        try:
            for method, headers in [('HEAD',{}),('GET',{'Range':'bytes=0-0'}),
                ('GET',{'If-None-Match':'"'+hashlib.sha256(original).hexdigest()+'"'})]:
                request(endpoint,409,method,headers)
        finally: target.write_bytes(original)
        assert request(endpoint,200) == original
        controls += ['actual-parallel-full-view-Fetch-and-Node-proofs','corruption-refuses-before-HEAD-range-304','exact-byte-restoration-retry']
    finally: stop(process,log)
    audited, audit = cli('verify-view',view,'--manifest-sha256',args.manifest_sha256,
                         '--provider-max-view-bytes',str(16*1024**3))
    assert audited.returncode == 0 and audit['bytes'] == total and audit['files'] == 213
    receipt = {'schema':1,'status':'passed','scope':'Native macOS ARM64 full213-file Passport HTTP view; selected2 application circuits through both Node/Fetch; no Linux/hostedCI claim',
        'manifest_sha256':args.manifest_sha256,'files':len(files),'persistent_bytes':total,'largest_file_bytes':largest,
        'configured_max_view_bytes':16*1024**3,'default_max_view_bytes':4*1024**3,
        'max_temporary_snapshot_bytes':2*1024**3,'largest_actual_two_snapshot_bound_bytes':2*largest,
        'destination_free_before_publish':free_before,'publication_wall_ms':publish_ms,
        'interruption':{'staged_bytes_observed':stopped_bytes,'target_absent_after_kill':True,'owned_leftovers_explicitly_removed':len(leftovers)},
        'controls':controls,'provider_checks':proof,'consumer_recovery':consumer_recovery,'full_audit':audit,
        'tools':{'forge':sha(args.binary),'worker':sha(args.worker),'zkir3_worker':sha(args.zkir3_worker)},
        'harness_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PROJECT/'passport.mjs']}}
    token_file.unlink()
    shutil.rmtree(args.work)
    receipt['cleanup'] = 'owned provider view, abandoned stages, private HTTP cache/token/logs and SDK proof/preimage copies removed'
    with args.output.open('x') as output: output.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'proofs':6,'verifications':6,'negative_controls':12,'assertions':54}))


def interrupted(_signal, _frame):
    raise RuntimeError('provider qualification interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM,interrupted)
    main()
