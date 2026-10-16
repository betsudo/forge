#!/usr/bin/env python3
"""Exact Passport account selected-circuit key cache benchmark; all lanes make real proofs.
Run inside ./bootstrap.sh -- python3 scripts/bench-passport.py --help. Never edits consumer.
"""
import atexit, argparse, datetime, hashlib, json, os, pathlib, shutil, statistics, subprocess, sys, tarfile, threading, time, platform
ROOT=pathlib.Path(__file__).resolve().parent.parent
P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--source',type=pathlib.Path,required=True)
P.add_argument('--compiler-dir',type=pathlib.Path,required=True)
P.add_argument('--binary',type=pathlib.Path,required=True)
P.add_argument('--worker',type=pathlib.Path,required=True)
P.add_argument('--emitted',type=pathlib.Path,required=True)
P.add_argument('--params-dir',type=pathlib.Path,required=True)
P.add_argument('--work',type=pathlib.Path,required=True)
P.add_argument('--output',type=pathlib.Path,required=True)
P.add_argument('--repetitions',type=int,default=3)
a=P.parse_args()
for key in ['source','compiler_dir','binary','worker','emitted','params_dir','work','output']:setattr(a,key,getattr(a,key).resolve())
assert a.repetitions>=3,'at least three repetitions required'
assert not a.work.exists(),'use an absent private work directory'
assert not a.output.is_relative_to(a.work),'receipt must survive scratch cleanup'
assert not a.output.is_relative_to(a.source),'read-only consumer source cannot hold output'
a.work.relative_to(ROOT/'.local/qualification/passport')
os.environ['MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER']=str(a.worker)
manifest=json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for path,digest in manifest['files'].items():assert sha(a.source/path)==digest,('consumer source changed',path)
for filename,digest in manifest['emitted_zkir_sha256'].items():assert sha(a.emitted/'zkir'/filename)==digest,('compiler output changed',filename)
assert sorted(p.name for p in (a.emitted/'zkir').glob('*.zkir'))==sorted(manifest['emitted_zkir_sha256'])
qualified=json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())
for name in ['compactc.bin','zkir-v3']:assert sha(a.compiler_dir/name)==qualified['tool_sha256']['tools/compiler/'+name],('wrong official compiler tool',name)
a.work.mkdir(parents=True)
atexit.register(lambda:shutil.rmtree(a.work,ignore_errors=True))
def run(args,cwd=None):
 start=time.monotonic();r=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=600)
 if r.returncode:raise RuntimeError((list(map(str,args)),r.stdout[-2000:],r.stderr[-4000:]))
 return r.stdout,(time.monotonic()-start)*1000

def cli(cache,*args):
 raw,ms=run([a.binary,'--cache-dir',cache,'--params-dir',a.params_dir,*args]);return json.loads(raw),ms

def compile_to(path):
 # Codegen is measured separately: every artifact lane receives identical current emitted bytes.
 start=time.monotonic();shutil.copytree(a.emitted,path);return (time.monotonic()-start)*1000
def archive(snapshot,dest):
 start=time.monotonic()
 with tarfile.open(dest,'w:gz',compresslevel=6) as t:t.add(snapshot,arcname='snapshot')
 return (time.monotonic()-start)*1000

def restore(arc,dest,cache):
 start=time.monotonic();dest.mkdir()
 # Only this runner's freshly created immutable archive is accepted, not network tar input.
 with tarfile.open(arc,'r:gz') as t:t.extractall(dest,filter='data')
 _,ms=cli(cache,'restore',dest/'snapshot')
 return (time.monotonic()-start)*1000,ms
runtime=a.work/'runtime';runtime.mkdir()
shutil.copy(a.source/'contract/package.json',runtime);shutil.copy(a.source/'contract/package-lock.json',runtime)
_,dependency_ms=run(['npm','ci','--ignore-scripts','--no-audit','--no-fund'],runtime)
shutil.copy(ROOT/'benchmarks/passport/make-preimage.mjs',runtime)
names=['deposit_unshielded','activate_initial_device_with_jubjub'];rows=[];identities={};descriptors={};roster=None
for repetition in range(a.repetitions):
 for lane in ['uncached','cold','warm-restored','partial-restored','unavailable']:
  work=a.work/f'{repetition}-{lane}';work.mkdir();cache=work/'cache';start=time.monotonic();out=work/'emitted'
  stop=threading.Event();disk_peak=[0]
  def sample_disk():
   while not stop.is_set():
    total=0
    for path in work.rglob('*'):
     try:
      if path.is_file():total+=path.stat().st_size
     except FileNotFoundError:pass
    disk_peak[0]=max(disk_peak[0],total);stop.wait(.05)
  monitor=threading.Thread(target=sample_disk,daemon=True);monitor.start()
  codegen_ms=compile_to(out);actual=sorted(p.stem for p in (out/'zkir').glob('*.zkir'))
  if roster is None:roster=actual
  assert actual==roster
  shutil.rmtree(runtime/'contract',ignore_errors=True);shutil.copytree(out/'contract',runtime/'contract')
  execution=[];execution_ms=0.
  for name in names:
   raw,elapsed=run(['node','make-preimage.mjs',runtime/'contract/index.js',runtime/f'{name}.bin',name],runtime)
   execution.append(json.loads(raw));execution_ms+=elapsed
  restore_ms=0.;prepare_ms=0.;save_ms=0.;compression_ms=0.;archive_bytes=0;restored_archive_bytes=0;snapshot_bytes=0;seed_ms=0.;hits=[];paths={};availability_attempt=None;helper_key_ms=0.;helper_restore_ms=0.
  if lane in ['warm-restored','partial-restored']:
   seed=a.work/f'{repetition}-cold' if lane=='warm-restored' else a.work/f'{repetition}-partial-seed'
   if lane=='partial-restored':
    seed_start=time.monotonic()
    seed.mkdir();cli(seed/'cache','prepare',out/'zkir/deposit_unshielded.zkir','--name','deposit_unshielded');cli(seed/'cache','snapshot','--output',seed/'snapshot');archive(seed/'snapshot',seed/'snapshot.tar.gz')
    seed_ms=(time.monotonic()-seed_start)*1000
   restored_archive_bytes=(seed/'snapshot.tar.gz').stat().st_size
   restore_ms,_=restore(seed/'snapshot.tar.gz',work/'transport',cache)
  if lane=='unavailable':
   # Exercise the real CI helper's checked transport-miss policy, not a simulated boolean.
   # Planning and attempted restore are part of the measured lane total.
   key=work/'ci-key.json';helper=[sys.executable,ROOT/'scripts/forge-ci.py','--binary',a.binary]
   _,helper_key_ms=run([*helper,'key','--workspace',out,'--params-dir',a.params_dir,
      '--parameter','bls_midnight_2p9','--parameter','bls_midnight_2p14',
      '--input','zkir/deposit_unshielded.zkir','--input','zkir/activate_initial_device_with_jubjub.zkir',
      '--profile','zkir31','--workload','Passport account selected genuine proofs','--generation','benchmark',
      '--output',key])
   raw,helper_restore_ms=run([*helper,'restore','--key',key,'--cache-dir',cache,
      '--snapshot',work/'missing-snapshot','--max-bytes','1073741824'])
   availability_attempt=json.loads(raw)
   assert availability_attempt['restored'] is False and availability_attempt['reason']=='cache_miss'
   assert not cache.exists(),'missing transport must not initialize or populate the store'
   restore_ms=helper_key_ms+helper_restore_ms
  if lane!='uncached':before_stats=cli(cache,'stats')[0]['totals']
  if lane=='uncached':
   selected=work/'selected-zkir';selected.mkdir();keys=work/'official-keys';keys.mkdir()
   for name in names:shutil.copy(out/'zkir'/f'{name}.zkir',selected/f'{name}.zkir')
   _,prepare_ms=run([a.compiler_dir/'zkir-v3','compile-many',selected,keys])
  for name in names:
   source=out/'zkir'/f'{name}.zkir'
   if lane=='uncached':
    paths[name]={'prover':keys/f'{name}.prover','verifier':keys/f'{name}.verifier','binary_ir':(selected/f'{name}.bzkir')}
    actual_identity={kind:sha(path) for kind,path in paths[name].items()}
    if name in identities:assert identities[name]==actual_identity,('official regeneration identity changed',name)
    else:identities[name]=actual_identity
   else:
    value,ms=cli(cache,'prepare',source,'--name',name);prepare_ms+=ms;hits.append(value['cache']['hit'])
    assert value['descriptor']['record']['worker']['executable_sha256']==sha(a.worker),'generation and proof worker differ'
    paths[name]={f['kind']:pathlib.Path(f['path']) for f in value['export']['files']}
    if name in descriptors:assert descriptors[name]==value['descriptor'],('recipe identity changed',name)
    else:descriptors[name]=value['descriptor']
    assert {k:sha(paths[name][k]) for k in ['prover','verifier','binary_ir']}==identities[name],('compiler/Forge mismatch',name,lane)
  expected={'cold':[False,False],'warm-restored':[True,True],'partial-restored':[True,False],'unavailable':[False,False]}
  if lane!='uncached':assert hits==expected[lane],(lane,hits)
  proofs=[];proof_process_ms=0.
  for name in names:
   flat=work/f'{name}-proof';flat.mkdir()
   for kind,extension in [('binary_ir','bzkir'),('prover','prover'),('verifier','verifier')]:
    shutil.copy(paths[name][kind],flat/f'circuit.{extension}')
   started=time.monotonic()
   process=subprocess.run([str(a.worker),'prove-preimage','--params-dir',str(a.params_dir),'--preimage',str(runtime/f'{name}.bin'),'--output',str(flat)],input=(out/'zkir'/f'{name}.zkir').read_bytes(),capture_output=True,timeout=600)
   assert process.returncode==0,(process.stdout.decode(),process.stderr.decode())
   proof_process_ms+=(time.monotonic()-started)*1000
   proof=json.loads(process.stdout)['proof_controls'];proofs.append(proof)
   shutil.rmtree(flat)
   assert (proof['proof_count'],proof['verification_count'],proof['negative_controls'])==(1,1,2)
  assert [e['assertions'] for e in execution]==[9,9]
  if lane in ['cold','partial-restored','unavailable']:
   _,save_ms=cli(cache,'snapshot','--output',work/'snapshot');snapshot_bytes=sum(p.stat().st_size for p in (work/'snapshot').rglob('*') if p.is_file());compression_ms=archive(work/'snapshot',work/'snapshot.tar.gz');archive_bytes=(work/'snapshot.tar.gz').stat().st_size;shutil.rmtree(work/'snapshot')
  wall_ms=(time.monotonic()-start)*1000
  # Partial seed represents a prior job. Its manufacture is excluded, but restore/generation/new save are timed.
  row={'repetition':repetition,'lane':lane,'emitted_copy_ms':codegen_ms,'execution_ms':execution_ms,'restore_ms':restore_ms,'helper_key_ms':helper_key_ms,'helper_restore_ms':helper_restore_ms,'availability_attempt':availability_attempt,'key_prepare_ms':prepare_ms,'proof_process_ms':proof_process_ms,'snapshot_ms':save_ms,'compression_ms':compression_ms,'archive_bytes':archive_bytes,'restored_archive_bytes':restored_archive_bytes,'snapshot_bytes':snapshot_bytes,'hits':hits,'execution':execution,'proofs':proofs,'total_ms':wall_ms-seed_ms,'prior_job_seed_ms_excluded':seed_ms,'observed_wall_ms':wall_ms,'sampled_peak_job_disk_bytes':disk_peak[0]}
  if lane!='uncached':
   row['stats']=cli(cache,'stats')[0]
   row['job_stats_delta']={key:row['stats']['totals'][key]-before_stats[key] for key in ['requests','hits','misses','errors','generation_ms']}
   assert row['job_stats_delta']['requests']==2 and row['job_stats_delta']['hits']==sum(hits) and row['job_stats_delta']['misses']==2-sum(hits) and row['job_stats_delta']['errors']==0
  row["observed_wall_ms"]=(time.monotonic()-start)*1000
  row["total_ms"]=row["observed_wall_ms"]-seed_ms
  stop.set();monitor.join();row["sampled_peak_job_disk_bytes"]=disk_peak[0]
  rows.append(row)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'schema':1,'status':'in-progress','rows':rows},indent=2)+'\n')
  # Preserve receipts, not fifteen key-store copies. Only the first cold store is retained for controls.
  if lane=='warm-restored':
   prior=a.work/f'{repetition}-cold'
   if repetition==0:(prior/'snapshot.tar.gz').unlink()
   else:shutil.rmtree(prior)
  if lane=='partial-restored':shutil.rmtree(a.work/f'{repetition}-partial-seed')
  if lane!='cold':shutil.rmtree(work)

# Consumer-specific refusal controls run after measured lanes; never relabel corruption as availability.
control=a.work/'controls';control.mkdir()
def refuse(cache,*args):
 result=subprocess.run(list(map(str,[a.binary,'--cache-dir',cache,'--params-dir',a.params_dir,*args])),capture_output=True,text=True,timeout=120)
 assert result.returncode!=0,(args,result.stdout)
 value=json.loads(result.stdout);assert not value['error']['availability_fallback'];return value['error']['code']
source=a.work/'0-cold/emitted/zkir/deposit_unshielded.zkir'
corrupt=control/'corrupt-cache';shutil.copytree(a.work/'0-cold/cache',corrupt)
object_path=corrupt/'objects'/identities['deposit_unshielded']['prover']
payload=bytearray(object_path.read_bytes());payload[-1]^=1;object_path.write_bytes(payload)
assert refuse(corrupt,'prepare',source,'--name','deposit_unshielded')=='integrity_error'
assert refuse(control/'wrong-profile','--profile','zkir3','prepare',source,'--name','deposit_unshielded')=='profile_format_mismatch'
changed=control/'changed.zkir';changed.write_bytes(source.read_bytes()+b'\n')
changed_result,_=cli(control/'changed-cache','prepare',changed,'--name','deposit_unshielded')
assert not changed_result['cache']['hit']
assert changed_result['descriptor']['record']['source']['digest']!=sha(source)
controls={'corrupt_consumer_prover':'integrity_error; fallback refused','wrong_profile':'profile_format_mismatch; fallback refused','changed_exact_source':'miss; same math is not exact source identity'}
medians={lane:statistics.median(r['total_ms'] for r in rows if r['lane']==lane) for lane in ['uncached','cold','warm-restored','partial-restored','unavailable']}
result={'schema':1,'status':'passed','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'consumer':{'commit':manifest['commit']},'selected_key_circuits':names,'proof_circuits':names,'complete_circuit_roster':roster,'host':{'system':platform.system(),'machine':platform.machine(),'cpu_count':os.cpu_count(),'performance_isolation':'shared developer host; concurrent qualification work; not isolated CI capacity'},'scope':'local selected-workload proof/key benchmark; not full Passport CI or localnet transaction submission','dependency_setup_ms':dependency_ms,'dependency_lock_sha256':sha(a.source/'contract/package-lock.json'),'dependency_lock_premise':'npm ci uses exact unchanged pinned consumer package-lock.json; no minimal dependency re-resolution','tool_hashes':{str(p.relative_to(a.compiler_dir)) if p.is_relative_to(a.compiler_dir) else p.name:sha(p) for p in [a.compiler_dir/'compactc.bin',a.compiler_dir/'zkir-v3',a.binary,a.worker]},'profile':cli(a.work/'profile-only','--profile','zkir31','profile')[0],'identities':identities,'descriptors':descriptors,'negative_controls':controls,'rows':rows,'median_total_ms':medians,'warm_saving_ms':medians['uncached']-medians['warm-restored'],'uncached_keygen':'one official zkir-v3 compile-many invocation for the exact two selected circuits; full52-circuit keygen is outside scope', 'separate_codegen_receipt':{'path':'docs/evidence/passport-codegen.json','sha256':sha(ROOT/'docs/evidence/passport-codegen.json')}, 'harness_sha256':sha(pathlib.Path(__file__)), 'codegen_scope':'Full account codegen is separately measured; lane totals include copied current compiler output, actual key preparation, runtime execution, proofs, verification and local transport. No complete CI total modeled.', 'transport':'local archive compression/extraction and validated Forge restore; no hosted cache upload/download latency'}
a.output.write_text(json.dumps(result,indent=2)+'\n');shutil.rmtree(a.work/'0-cold');shutil.rmtree(control);shutil.rmtree(runtime);result['owned_work_cleanup']='All measured stores, snapshots, preimages, node_modules and proof copies removed after evidence capture';a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(a.output),'median_total_ms':medians,'warm_saving_ms':result['warm_saving_ms']}))
