#!/usr/bin/env python3
"""Isolated real-process snapshot/restore and local CI helper e2e. --real proves fixtures."""
import argparse,concurrent.futures,hashlib,json,os,pathlib,shutil,signal,sqlite3,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=pathlib.Path,default=ROOT/'target/debug/midnight-zkir-forge');p.add_argument('--real',action='store_true');p.add_argument('--include-zkir31',action='store_true');p.add_argument('--params-dir',type=pathlib.Path,default=pathlib.Path(os.environ.get('MIDNIGHT_PP',str(pathlib.Path.home()/'.cache/midnight/zk-params'))));a=p.parse_args();binary=a.binary.resolve()
def cmd(*args,ok=True,env=None):
 r=subprocess.run(list(map(str,args)),text=True,capture_output=True,env=env,timeout=120)
 value=json.loads(r.stdout)
 assert (r.returncode==0)==ok,(r.returncode,r.stdout,r.stderr)
 return value
def cli(store,*args,ok=True):return cmd(binary,'--cache-dir',store,*args,ok=ok)
def helper(*args,ok=True,env=None):return cmd(sys.executable,ROOT/'scripts/forge-ci.py','--binary',binary,*args,ok=ok,env=env)
def resign(directory):
 manifest=json.loads((directory/'snapshot.json').read_text())
 for entry in manifest['files']:
  path=directory/entry['path']
  if path.is_file() and not path.is_symlink():entry['bytes']=path.stat().st_size;entry['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
 value=[manifest[k] for k in ('schema','format','producer','partition','files')]
 manifest['snapshot_id']=hashlib.sha256(b'midnight-zkir-forge/snapshot/v1\0'+json.dumps(value,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 (directory/'snapshot.json').write_text(json.dumps(manifest,indent=2))
 return manifest
with tempfile.TemporaryDirectory(prefix='forge-snapshot-e2e-') as d:
 temp=pathlib.Path(d).resolve();source=temp/'source';snap=temp/'snapshot'
 registered=cli(source,'import',ROOT/'fixtures/assert.zkir','--name','proof');bundle=registered['bundle_id']
 initial=cli(source,'snapshot','--output',snap,'--partition','a'*64)
 restored=temp/'relocated';r=cli(restored,'restore',snap,'--expected-id',initial['snapshot_id'],'--partition','a'*64)
 assert r['snapshot_id']==initial['snapshot_id']
 assert r['manifest_sha256']==hashlib.sha256((snap/'snapshot.json').read_bytes()).hexdigest()
 assert cli(restored,'inspect',bundle)['ready'] is False
 cli(restored,'restore',snap,ok=False)
 assert cli(restored,'inspect',bundle)['record']['source']==registered['source']
 existing=temp/'empty';existing.mkdir();cli(existing,'restore',snap,ok=False)
 dest=temp/'absent';cli(dest,'restore',snap,'--partition','b'*64,ok=False);assert not dest.exists()
 cli(dest,'restore',snap,'--expected-id','b'*64,ok=False);assert not dest.exists()
 cli(dest,'restore',snap,'--max-bytes','1',ok=False);assert not dest.exists()
 cli(dest,'--profile','zkir3','restore',snap,ok=False);assert not dest.exists()
 cli(source,'snapshot','--output',temp/'tiny','--max-bytes','1',ok=False);assert not (temp/'tiny').exists()
 cli(source,'snapshot','--output',source/'nested',ok=False)
 # A real SQLite writer excludes snapshot: failure is bounded and no output exists.
 with sqlite3.connect(source/'index.sqlite3') as lock:
  lock.execute('BEGIN IMMEDIATE');out=temp/'busy'
  start=time.monotonic();cli(source,'snapshot','--output',out,'--wait-seconds','0',ok=False)
  assert time.monotonic()-start<5 and not out.exists();lock.rollback()
 # A snapshot succeeds after the writer exits; readers may coexist.
 with sqlite3.connect(source/'index.sqlite3') as reader:
  reader.execute('BEGIN');reader.execute('SELECT count(*) FROM bundles').fetchone()
  cli(source,'snapshot','--output',temp/'with-reader','--wait-seconds','0');reader.rollback()
 # WAL source is captured as one standalone DELETE database; source config is untouched.
 wal=temp/'wal';cli(wal,'import',ROOT/'fixtures/assert.zkir','--name','proof')
 with sqlite3.connect(wal/'index.sqlite3') as writer:
  assert writer.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
  writer.execute("INSERT INTO requests(bundle,requested_path,operation,outcome,elapsed_ms,estimated_saved_ms) VALUES(?,?,?,?,?,?)",(bundle,'/old/location','sample','hit',1,0));writer.commit()
  cli(wal,'snapshot','--output',temp/'wal-snapshot')
 cli(temp/'wal-copy','restore',temp/'wal-snapshot')
 assert cli(temp/'wal-copy','stats')['totals']['hits']==1
 # Concurrent restoration cannot overwrite even an empty raced destination.
 race=temp/'race'
 with concurrent.futures.ThreadPoolExecutor() as executor:
  futures=[executor.submit(subprocess.run,[str(binary),'--cache-dir',str(race),'restore',str(snap)],capture_output=True,text=True,timeout=30) for _ in range(2)]
  results=[f.result() for f in futures];assert sorted(r.returncode for r in results)==[0,1]
 assert cli(race,'inspect',bundle)['record']['source']==registered['source']
 mutations=['missing','extra','symlink','traversal','duplicate','producer','schema','ready','partial','empty-directory']
 for kind in mutations:
  bad=temp/('bad-'+kind);shutil.copytree(snap,bad);manifest=json.loads((bad/'snapshot.json').read_text());cas=bad/'objects'/registered['source']['digest']
  if kind=='missing':cas.unlink()
  elif kind=='extra':(bad/'unknown').write_text('extra')
  elif kind=='symlink':cas.unlink();cas.symlink_to(ROOT/'fixtures/assert.zkir')
  elif kind=='traversal':manifest['files'][0]['path']='../escape';(bad/'snapshot.json').write_text(json.dumps(manifest))
  elif kind=='duplicate':manifest['files'].append(manifest['files'][0]);(bad/'snapshot.json').write_text(json.dumps(manifest))
  elif kind=='producer':manifest['producer']['build_fingerprint']='0'*64;(bad/'snapshot.json').write_text(json.dumps(manifest));resign(bad)
  elif kind=='empty-directory':(bad/'objects'/'unexpected').mkdir()
  else:
   with sqlite3.connect(bad/'index.sqlite3') as db:
    if kind=='schema':db.execute('ALTER TABLE bundles ADD COLUMN unexpected INTEGER')
    elif kind=='ready':db.execute('UPDATE bundles SET ready=2')
    else:
     record=json.loads(db.execute('SELECT record FROM bundles').fetchone()[0]);record['k']=4;db.execute('UPDATE bundles SET record=?',(json.dumps(record),))
    db.commit()
   resign(bad)
  target=temp/('refused-'+kind);cli(target,'restore',bad,ok=False);assert not target.exists(),kind
 # Data corruption gets tested independently from manifest identity mismatch.
 bad=temp/'bad-bytes';shutil.copytree(snap,bad);(bad/'objects'/registered['source']['digest']).write_bytes(b'corrupt')
 cli(temp/'bad-target','restore',bad,ok=False);assert not (temp/'bad-target').exists()
 # Kill after staging starts; no partially ready destination is ever visible.
 orphan=b'0'*(32*1024*1024);orphan_path=source/'objects'/hashlib.sha256(orphan).hexdigest();orphan_path.write_bytes(orphan)
 killed=temp/'killed';process=subprocess.Popen([str(binary),'--cache-dir',str(source),'snapshot','--output',str(killed)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 deadline=time.monotonic()+10
 while not list(temp.glob('.tmp*')) and process.poll() is None and time.monotonic()<deadline:time.sleep(.001)
 assert process.poll() is None,'snapshot finished before interruption probe'
 process.kill();process.wait();assert not killed.exists();orphan_path.unlink()
 cli(source,'snapshot','--output',temp/'after-kill')
 # CI policy/key mechanics are local; no GitHub API or upload is involved.
 workspace=temp/'workload';workspace.mkdir();(workspace/'circuit.zkir').write_bytes((ROOT/'fixtures/assert.zkir').read_bytes())
 fake=temp/'parameters';fake.mkdir();(fake/'bls_midnight_2p4').write_bytes(b'parameter-plan-only; no fast keygen')
 key=temp/'key.json'
 k=helper('key','--workspace',workspace,'--params-dir',fake,'--parameter','bls_midnight_2p4','--input','circuit.zkir','--profile','ledger8-v2','--workload','assert proof','--generation','1-1','--output',key)
 key2=temp/'key2.json';k2=helper('key','--workspace',workspace,'--params-dir',fake,'--parameter','bls_midnight_2p4','--input','circuit.zkir','--profile','ledger8-v2','--workload','assert proof','--generation','2-1','--output',key2)
 assert k['partition']==k2['partition'] and k['restore_keys']==k2['restore_keys'] and k['primary']!=k2['primary']
 ci_store=temp/'ci-store';baseline=temp/'baseline.json';helper('baseline','--key',key,'--cache-dir',ci_store,'--output',baseline)
 report=helper('report','--key',key,'--cache-dir',ci_store,'--baseline',baseline);assert report['delta']['requests']==0
 common=['--key',key,'--cache-dir',ci_store,'--baseline',baseline,'--snapshot',temp/'not-published','--max-bytes','1048576','--trusted-ref','refs/heads/main']
 trusted=dict(os.environ,GITHUB_EVENT_NAME='push',GITHUB_REF='refs/heads/main')
 assert helper('prepare-save',*common,env=trusted)['reason']=='tests_not_confirmed'
 assert helper('prepare-save',*common,'--tests-passed',env=dict(trusted,GITHUB_EVENT_NAME='pull_request'))['reason']=='untrusted_event_or_ref'
 assert helper('prepare-save',*common,'--tests-passed',env=dict(trusted,GITHUB_REF='refs/heads/feature'))['publish'] is False
 assert helper('prepare-save',*common,'--tests-passed',env=trusted)['reason']=='no_generation_misses'
 assert not (temp/'not-published').exists()
 missing=helper('restore','--key',key,'--cache-dir',temp/'cache-miss','--snapshot',temp/'does-not-exist','--max-bytes','1048576');assert not missing['restored'] and not (temp/'cache-miss').exists()
 (workspace/'circuit.zkir').write_text('changed');helper('report','--key',key,'--cache-dir',ci_store,'--baseline',baseline,ok=False)
 (workspace/'circuit.zkir').write_bytes((ROOT/'fixtures/assert.zkir').read_bytes());(fake/'bls_midnight_2p4').write_text('changed');helper('report','--key',key,'--cache-dir',ci_store,'--baseline',baseline,ok=False)
 proofs=[]
 if a.real:
  selected=[('ledger8-v2','assert.zkir'),('zkir3','assert-v3.zkir')]
  if a.include_zkir31:selected.append(('zkir31','assert-v31.zkir'))
  for selector,fixture in selected:
   key=temp/(selector+'-key.json');store=temp/(selector+'-store');base=temp/(selector+'-baseline.json')
   (workspace/'circuit.zkir').write_bytes((ROOT/'fixtures'/fixture).read_bytes())
   planned=helper('key','--workspace',workspace,'--params-dir',a.params_dir,'--parameter','bls_midnight_2p4','--input','circuit.zkir','--profile',selector,'--workload','actual assert proof controls','--generation','3-1','--output',key)
   helper('baseline','--key',key,'--cache-dir',store,'--output',base)
   cold=cli(store,'--profile',selector,'--params-dir',a.params_dir,'prepare',workspace/'circuit.zkir','--name','proof');assert not cold['cache']['hit']
   args=['--key',key,'--cache-dir',store,'--baseline',base,'--trusted-ref','refs/heads/main','--tests-passed']
   over=helper('prepare-save',*args,'--snapshot',temp/(selector+'-over'),'--max-bytes','1',env=trusted);assert over['reason']=='over_budget' and not (temp/(selector+'-over')).exists()
   snapshot=temp/(selector+'-seed');saved=helper('prepare-save',*args,'--snapshot',snapshot,'--max-bytes','10485760',env=trusted);assert saved['publish']
   target=temp/(selector+'-restored');helper('restore','--key',key,'--cache-dir',target,'--snapshot',snapshot,'--max-bytes','10485760','--expected-id',saved['snapshot']['snapshot_id'])
   if selector=='zkir31':
    changed_worker=temp/'changed-worker31';shutil.copytree(snapshot,changed_worker)
    manifest=json.loads((changed_worker/'snapshot.json').read_text());manifest['producer']['worker31']['executable_sha256']='0'*64
    (changed_worker/'snapshot.json').write_text(json.dumps(manifest))
    rejected=temp/'changed-worker31-target'
    helper('restore','--key',key,'--cache-dir',rejected,'--snapshot',changed_worker,'--max-bytes','10485760',ok=False)
    assert not rejected.exists()
   # Cross-table records must pin one output set for every derivation recipe.
   contradictory=temp/(selector+'-contradictory');shutil.copytree(snapshot,contradictory)
   with sqlite3.connect(contradictory/'index.sqlite3') as db:
    record=json.loads(db.execute('SELECT record FROM derivations').fetchone()[0]);record['artifacts'].reverse()
    set_id=hashlib.sha256(b'midnight-zkir-forge/artifacts/v1\0'+json.dumps(record['artifacts'],separators=(',',':')).encode()).hexdigest()
    record['artifact_set_id']=set_id
    db.execute('UPDATE derivations SET record=?',(json.dumps(record),))
    db.execute('INSERT INTO artifact_sets(id,record) VALUES(?,?)',(set_id,json.dumps(record)));db.commit()
   resign(contradictory)
   refused=temp/(selector+'-contradictory-target');cli(refused,'restore',contradictory,ok=False);assert not refused.exists()
   wrong_scope=temp/(selector+'-wrong-scope');cli(wrong_scope,'restore',snapshot,'--parameter-digest','0'*64,ok=False);assert not wrong_scope.exists()
   # Even a coherently rehashed envelope cannot change immutable export manifests.
   malformed=temp/(selector+'-noncanonical');shutil.copytree(snapshot,malformed)
   export_manifest=next((malformed/'exports').glob('*/*/*/manifest.json'))
   export_manifest.write_text(export_manifest.read_text()+'\n');resign(malformed)
   refused=temp/(selector+'-noncanonical-target');cli(refused,'restore',malformed,ok=False);assert not refused.exists()
   inherited=temp/(selector+'-restored-baseline.json');helper('baseline','--key',key,'--cache-dir',target,'--output',inherited)
   warm=cli(target,'--profile',selector,'--params-dir',a.params_dir,'prepare',workspace/'circuit.zkir','--name','proof')
   assert warm['cache']['hit'] and warm['artifact_set_id']==cold['artifact_set_id']
   assert pathlib.Path(warm['export']['base']).is_relative_to(target)
   if selector=='ledger8-v2':proof=cmd(binary,'--params-dir',a.params_dir,'qualify-export',warm['export']['base'])
   else:
    variable='MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER' if selector=='zkir31' else 'MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER'
    name='midnight-zkir-forge-zkir31-worker' if selector=='zkir31' else 'midnight-zkir-forge-zkir3-worker'
    worker=pathlib.Path(os.environ.get(variable,str(binary.parent/name)))
    proof=cmd(worker,'qualify-export','--output',warm['export']['base'],'--circuit-name','proof')
   assert all(proof[n] for n in ('valid_proof_verified','invalid_statement_rejected','corrupt_proof_rejected'))
   delta=helper('report','--key',key,'--cache-dir',target,'--baseline',inherited)['delta'];assert delta['hits']==1 and delta['misses']==0
   # Preserve pinned identity and historical exports even when derived CAS was evicted.
   cli(store,'evict',cold['bundle_id']);evicted=temp/(selector+'-evicted');cli(store,'snapshot','--output',evicted)
   regen_root=temp/(selector+'-regen');cli(regen_root,'restore',evicted);regen=cli(regen_root,'--params-dir',a.params_dir,'ensure',cold['bundle_id']);assert regen['artifact_set_id']==cold['artifact_set_id']
   proofs.append({'profile':selector,'warm_restored_artifacts_prove':True,'invalid_controls_rejected':True,'evicted_identity_and_exports_preserved':True,'ci_budget_growth_and_stat_deltas':True})
 print(json.dumps({'schema':1,'relocation':True,'writer_contention_timeout_and_reader_coexistence':True,'wal_backup_standalone':True,'concurrent_no_replace':True,'hostile_and_corrupt_payloads_refused':mutations+['corrupt-bytes'],'killed_snapshot_not_published':True,'ci_key_and_policy_guards':True,'real_proofs':proofs,'scope':'isolated local process e2e; no Compact or remote cache operations'}))
