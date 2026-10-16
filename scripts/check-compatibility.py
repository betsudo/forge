#!/usr/bin/env python3
"""Real CLI/export/HTTP descriptor parity and parameter refusal controls; private stores."""
import argparse,json,os,pathlib,subprocess,tempfile,time,socket,urllib.request,urllib.error,hashlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=pathlib.Path,required=True);p.add_argument('--params-dir',type=pathlib.Path,default=pathlib.Path(os.environ.get('MIDNIGHT_PP',str(pathlib.Path.home()/'.cache/midnight/zk-params'))));a=p.parse_args();binary=a.binary.resolve()
def cli(root,*args,ok=True):
 start=time.monotonic();r=subprocess.run(list(map(str,[binary,'--cache-dir',root,*args])),capture_output=True,text=True,timeout=120)
 assert (r.returncode==0)==ok,(r.stdout,r.stderr)
 return json.loads(r.stdout),(time.monotonic()-start)*1000
with tempfile.TemporaryDirectory(prefix='forge-compatibility-') as d:
 temp=pathlib.Path(d).resolve();results=[]
 for profile,fixture in [('ledger8-v2','assert.zkir'),('zkir3','assert-v3.zkir')]:
  store=temp/profile;source=ROOT/'fixtures'/fixture;args=['--profile',profile,'--params-dir',a.params_dir,'prepare',source,'--name','proof']
  cold,cold_ms=cli(store,*args);before,_=cli(store,'stats');warm,warm_ms=cli(store,*args);after,_=cli(store,'stats');descriptor=warm['descriptor']
  assert cold['artifact_set_id']==warm['artifact_set_id'] and warm['cache']['hit']
  assert cold['descriptor']==descriptor==warm['export']['descriptor']
  base=pathlib.Path(warm['export']['base']);sidecar=base/'descriptor.json';manifest=(base/'manifest.json').read_bytes()
  assert json.loads(sidecar.read_text())==descriptor
  assert (cli(store,'inspect',warm['bundle_id'])[0]['descriptor'])==descriptor
  # Legacy immutable export gains only the additive sidecar after full verification.
  sidecar.unlink();again,_=cli(store,*args);assert again['cache']['hit'] and (base/'manifest.json').read_bytes()==manifest
  assert json.loads(sidecar.read_text())==descriptor
  if profile=='zkir3':assert descriptor['record']['worker'] and descriptor['serialization']['binary_ir']=='ir-source[v3-generic]'
  with socket.socket() as port:port.bind(('127.0.0.1',0));number=port.getsockname()[1]
  process=subprocess.Popen(list(map(str,[binary,'--cache-dir',store,'--params-dir',a.params_dir,'serve','--listen',f'127.0.0.1:{number}'])),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  def request(path,body=None):
   try:
    r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{number}'+path,data=body,headers={'Content-Type':'application/json'}),timeout=20)
   except urllib.error.HTTPError as r:return r.code,json.load(r)
   return r.status,json.load(r)
  try:
   deadline=time.monotonic()+15
   while True:
    try:
     if request('/health/live')[0]==200:break
    except (OSError,urllib.error.URLError):pass
    assert process.poll() is None and time.monotonic()<deadline;time.sleep(.05)
   status,value=request('/v1/bundles/'+warm['bundle_id']);assert status==200 and value['descriptor']==descriptor
   status,value=request(f"/v1/bundles/{warm['bundle_id']}/materializations?profile={profile}",b'');assert status==200 and value['descriptor']==descriptor
  finally:process.terminate();process.wait(timeout=15)
  for mode in ['absent','invalid']:
   params=temp/(profile+'-'+mode);params.mkdir()
   if mode=='invalid':(params/'bls_midnight_2p4').write_bytes(b'bad parameters')
   result,_=cli(temp/(profile+'-'+mode+'-store'),'--params-dir',params,'prepare',source,ok=False)
   expected='parameters_unavailable' if mode=='absent' else 'invalid_parameters'
   assert result['error']['code']==expected,result
   assert result['error']['availability_fallback']==(mode=='absent')
   assert str(temp) not in result['error']['message']
   with socket.socket() as port:port.bind(('127.0.0.1',0));number=port.getsockname()[1]
   process=subprocess.Popen(list(map(str,[binary,'--cache-dir',store,'--params-dir',params,'serve','--listen',f'127.0.0.1:{number}'])),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   try:
    deadline=time.monotonic()+15
    while True:
     try:
      if request('/health/live')[0]==200:break
     except (OSError,urllib.error.URLError):pass
     assert process.poll() is None and time.monotonic()<deadline;time.sleep(.05)
    status,error=request(f"/v1/bundles/{warm['bundle_id']}/materializations?profile={profile}",b'')
    assert status==(503 if mode=='absent' else 422) and error['error']['code']==expected,(status,error)
    assert error['error']['availability_fallback']==(mode=='absent') and str(temp) not in json.dumps(error)
   finally:process.terminate();process.wait(timeout=15)
  results.append({'profile':profile,'descriptor_parity':True,'legacy_manifest_preserved':True,'parameter_errors_distinct':True,'source_pin':descriptor['record']['ledger_revision'],'serialization':descriptor['serialization'],'cold_process_ms':cold_ms,'warm_process_ms':warm_ms,'job_delta':{k:after['totals'][k]-before['totals'][k] for k in ['requests','hits','misses','errors']}})
 print(json.dumps({'schema':1,'profiles':results,'scope':'local native descriptor/error tests; proof controls executed separately; Compact unchanged'}))
