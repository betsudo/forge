#!/usr/bin/env python3
"""Real-process HTTP contract checks. --real explicitly generates/proves circuits."""
import argparse, concurrent.futures, http.client, hashlib, json, os, pathlib, secrets, signal, socket, sqlite3, subprocess, tempfile, time, urllib.error, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=pathlib.Path, default=ROOT/'target/debug/midnight-zkir-forge')
parser.add_argument('--url', help='Test an existing isolated server (do not use a shared production store)')
parser.add_argument('--token-file', type=pathlib.Path)
parser.add_argument('--real', action='store_true')
parser.add_argument('--include-zkir31', action='store_true')
parser.add_argument('--v2-proof-helper', type=pathlib.Path)
args = parser.parse_args()
binary = args.binary.resolve()
def free_port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def run(*command):
    return subprocess.run(list(map(str,command)), check=True,capture_output=True,text=True,timeout=120)
with tempfile.TemporaryDirectory(prefix='forge-http-e2e-') as directory:
    temporary = pathlib.Path(directory); process = None; cache = temporary/'cache'
    token_file = args.token_file or temporary/'token'
    if not args.token_file: token_file.write_text(secrets.token_hex(32)); token_file.chmod(0o600)
    token = token_file.read_text().strip()
    url = args.url or f'http://127.0.0.1:{free_port()}'
    def request(path, method='GET', data=None, headers=None, auth=True):
        h = {'Authorization': 'Bearer '+token} if auth else {}
        if data is not None: h['Content-Type']='application/json'
        h.update(headers or {})
        req=urllib.request.Request(url+path,data=data,headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=45) as response: return response.status,response.headers,response.read()
        except urllib.error.HTTPError as error: return error.code,error.headers,error.read()
    def value(path, method='GET', data=None):
        status,_,body=request(path,method,data)
        assert status in (200,201), (status,body)
        result=json.loads(body)
        assert str(cache).encode() not in body and b'"export"' not in body, body
        return result
    try:
        if not args.url:
            refused=subprocess.run([str(binary),'serve','--listen','0.0.0.0:0'],capture_output=True,text=True,timeout=10)
            assert refused.returncode != 0 and 'token' in refused.stderr
            log=(temporary/'server.log').open('w+')
            process=subprocess.Popen([str(binary),'--cache-dir',str(cache),'serve','--listen',url.removeprefix('http://'),'--token-file',str(token_file)],stdout=log,stderr=log)
        deadline=time.monotonic()+20
        while True:
            try:
                if request('/health/live',auth=False)[0]==200: break
            except OSError: pass
            if time.monotonic()>deadline:
                if process: log.seek(0); raise RuntimeError(log.read())
                raise RuntimeError('server did not become live')
            time.sleep(.05)
        assert request('/health/ready',auth=False)[0]==401
        assert request('/v1/profiles',auth=False)[0]==401
        assert request('/v1/profiles',headers={'Authorization':'Bearer incorrect'})[0]==401
        assert value('/health/ready')['status']=='ready'
        assert {p['selector'] for p in value('/v1/profiles')['profiles']}=={'ledger8-v2','zkir3','zkir31'}
        assert '/v1/bundles' in value('/openapi.json')['paths']
        source=(ROOT/'fixtures/assert.zkir').read_bytes()
        path='/v1/bundles?name=http-assert&profile=ledger8-v2'
        assert request(path,'POST',source,headers={'Content-Type':'text/plain'})[0]==415
        assert request('/v1/bundles?name=../bad','POST',source)[0]==400
        assert request('/v1/bundles?name=a&input=/etc/passwd','POST',source)[0]==400
        assert request('/v1/bundles?name=a&profile=unknown','POST',source)[0]==400
        assert request(path,'POST',b'{"input":"/etc/passwd"}')[0]>=400
        assert request('/v1/objects/'+'z'*64)[0]==400
        assert request('/v1/objects/'+'0'*64)[0]==404
        # Declared oversize is rejected without buffering its body.
        endpoint=urllib.parse.urlsplit(url)
        connection=http.client.HTTPConnection(endpoint.hostname,endpoint.port,timeout=5)
        connection.putrequest('POST',path);connection.putheader('Authorization','Bearer '+token)
        connection.putheader('Content-Type','application/json');connection.putheader('Content-Length',16*1024*1024+1);connection.endheaders()
        oversized=connection.getresponse();assert oversized.status==413;oversized.read();connection.close()
        # Incomplete upload bodies consume the two bounded slots before buffering.
        slow=[]
        try:
            for _ in range(2):
                s=socket.create_connection((endpoint.hostname,endpoint.port),timeout=5)
                s.sendall((f'POST {path} HTTP/1.1\r\nHost: {endpoint.netloc}\r\nAuthorization: Bearer {token}\r\nContent-Type: application/json\r\nContent-Length: {len(source)}\r\n\r\n').encode()+source[:1]);slow.append(s)
                time.sleep(.05)
            assert request(path,'POST',source)[0]==429
        finally:
            for s in slow: s.close()
        time.sleep(.1)
        uploaded=value(path,'POST',source); bundle=uploaded['bundle_id']
        assert not uploaded['ready']
        assert value('/v1/bundles/'+bundle)['bundle_id']==bundle
        link=uploaded['source']['url']
        status,headers,body=request(link)
        assert status==200 and body==source
        assert headers['ETag']=='"'+hashlib.sha256(source).hexdigest()+'"'
        assert headers['Content-Type']=='application/json'
        etag=headers['ETag']
        assert request(link,'HEAD')[2]==b''
        assert int(request(link,'HEAD')[1]['Content-Length'])==len(source)
        assert request(link,headers={'If-None-Match':etag})[0]==304
        assert request(link,headers={'If-None-Match':'W/'+etag})[0]==304
        status,h,body=request(link,headers={'Range':'bytes=1-7'})
        assert status==206 and body==source[1:8] and h['Content-Range']==f'bytes 1-7/{len(source)}'
        assert request(link,headers={'Range':'bytes=-7'})[2]==source[-7:]
        assert request(link,headers={'Range':'bytes=1-','If-Range':'"wrong"'})[0]==200
        assert request(link,headers={'Range':'bytes=999999-'})[0]==416
        assert request(link,headers={'Range':'bytes=1-2,4-5'})[0]==416
        assert request(f'/v1/bundles/{bundle}/circuits/http-assert/source')[2]==source
        assert request(f'/v1/bundles/{bundle}/circuits/wrong/source')[0]==404
        if not args.url:
            # Real CLI writer contention holds the store lease; no parameters/keygen required.
            lock=sqlite3.connect(cache/'index.sqlite3',timeout=10);lock.execute('BEGIN IMMEDIATE')
            missing='/v1/bundles/'+'0'*64+'/materializations'
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pending=pool.submit(request,missing,'POST',b'')
                time.sleep(.15)
                deadline=time.monotonic()+5; saturated=False
                while time.monotonic()<deadline:
                    status,_,_=request(missing,'POST',b'')
                    if status==429: saturated=True;break
                    time.sleep(.01)
                assert saturated, 'generation admission must reject while one owner waits on SQLite'
                assert request('/health/live',auth=False)[0]==200, 'blocking SQLite must not block the HTTP executor'
                lock.rollback();lock.close()
                assert pending.result()[0]==404
            # Verify corruption before conditional 304, then restore private test bytes.
            cas=cache/'objects'/hashlib.sha256(source).hexdigest();cas.write_bytes(b'corrupt')
            assert request(link,headers={'If-None-Match':etag})[0]==409
            cas.write_bytes(source)
            assert request(link)[2]==source
        proof_receipts=[]
        if args.real:
            selected=[('ledger8-v2','assert.zkir'),('zkir3','assert-v3.zkir')]
            if args.include_zkir31:selected.append(('zkir31','assert-v31.zkir'))
            for selector,fixture in selected:
                raw=(ROOT/'fixtures'/fixture).read_bytes()
                record=value('/v1/bundles?name=proof&profile='+selector,'POST',raw)
                materialize='/v1/bundles/'+record['bundle_id']+'/materializations?profile='+selector
                cold=value(materialize,'POST',b'');warm=value(materialize,'POST',b'')
                assert not cold['cache']['hit'] and warm['cache']['hit']
                assert cold['artifact_set_id']==warm['artifact_set_id']
                exported=temporary/selector;(exported/'zkir').mkdir(parents=True);(exported/'keys').mkdir()
                inventory=[]
                for artifact in warm['artifacts']:
                    status,_,raw=request(artifact['url']);assert status==200
                    assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and len(raw)==artifact['bytes']
                    kind=artifact['kind'];ext={'binary_ir':'bzkir','prover':'prover','verifier':'verifier'}[kind]
                    folder='zkir' if kind=='binary_ir' else 'keys';(exported/folder/('proof.'+ext)).write_bytes(raw)
                    inventory.append({'kind':kind,'digest':artifact['sha256'],'size':len(raw)})
                (exported/'manifest.json').write_text(json.dumps(warm['descriptor']['record']))
                if selector in ('zkir3','zkir31'):
                    variable='MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER' if selector=='zkir31' else 'MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER'
                    name='midnight-zkir-forge-zkir31-worker' if selector=='zkir31' else 'midnight-zkir-forge-zkir3-worker'
                    worker=pathlib.Path(os.environ.get(variable,binary.parent/name))
                    proof=json.loads(run(worker,'qualify-export','--output',exported,'--circuit-name','proof').stdout)
                    assert all(proof[k] for k in ('valid_proof_verified','invalid_statement_rejected','corrupt_proof_rejected','used_exported_artifacts'))
                    proof_receipts.append({'profile':selector,'downloaded_warm_artifacts_prove_and_reject_invalid_controls':True})
                else:
                    proof=json.loads((run(args.v2_proof_helper.resolve(),exported) if args.v2_proof_helper else run(binary,'qualify-export',exported)).stdout)
                    assert all(proof[k] for k in ('valid_proof_verified','invalid_statement_rejected','corrupt_proof_rejected'))
                    proof_receipts.append({'profile':selector,'downloaded_warm_artifacts_prove_and_reject_invalid_controls':True})
        stats=value('/v1/stats');assert 'requested_path' not in json.dumps(stats)
        assert stats['totals']['hits']>0
        print(json.dumps({'schema':1,'http_source_roundtrip':True,'auth_and_remote_binding':True,'head_etag_range':True,'path_inputs_refused':True,'sqlite_contention_admission_and_responsive_liveness':not bool(args.url),'corruption_refused_before_conditional_response':not bool(args.url),'real_proofs':proof_receipts,'scope':'isolated real HTTP process; local private store' if not args.url else 'externally supplied isolated server'}))
    finally:
        if process:
            process.send_signal(signal.SIGTERM)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill();process.wait();raise RuntimeError('server did not stop gracefully')
            log.close()
