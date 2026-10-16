#!/usr/bin/env python3
"""Exact DID v0.7.0 selected-circuit key cache benchmark; all lanes make real proofs.
Run inside ./bootstrap.sh -- python3 scripts/bench-did.py --help. Never edits consumer.
"""
import argparse, hashlib, json, os, pathlib, shutil, statistics, subprocess, tarfile, threading, time, platform, re, atexit, sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--source',type=pathlib.Path,required=True)
P.add_argument('--compiler-dir',type=pathlib.Path,required=True)
P.add_argument('--binary',type=pathlib.Path,required=True)
P.add_argument('--forge-build-mode',choices=['release','debug'],required=True)
P.add_argument('--prover',type=pathlib.Path,required=True)
P.add_argument('--prover-build-mode',choices=['release','debug'],required=True)
P.add_argument('--params-dir',type=pathlib.Path,required=True)
P.add_argument('--work',type=pathlib.Path,required=True)
P.add_argument('--output',type=pathlib.Path,required=True)
P.add_argument('--repetitions',type=int,default=3)
a=P.parse_args()
for key in ['source','compiler_dir','binary','prover','params_dir','work','output']:setattr(a,key,getattr(a,key).resolve())
assert a.repetitions>=3,'at least three repetitions required'
assert not a.output.is_relative_to(a.work),'receipt must be outside ephemeral work'
assert not a.output.is_relative_to(a.source),'consumer is read only'
assert not a.work.exists(),'use an absent private work directory'
a.work.relative_to(ROOT/'.local/qualification/did')
manifest=json.loads((ROOT/'benchmarks/did/consumer-files.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for path,digest in manifest['files'].items():assert sha(a.source/path)==digest,('consumer source changed',path)
# Preserve the consumer lock's exact cryptographic/runtime dependency resolution.
fixture_lock=json.loads((ROOT/'benchmarks/did/package-lock.json').read_text())
consumer_lock=(a.source/'pnpm-lock.yaml').read_text()
for location,package in fixture_lock['packages'].items():
 if not location:continue
 name=location.rsplit('node_modules/',1)[1]
 marker=re.escape(name+'@'+package['version'])
 match=re.search(r"^  '?"+marker+r"'?:\n    resolution: \{integrity: ([^}]+)\}",consumer_lock,re.MULTILINE)
 assert match and match[1]==package['integrity'],('fixture diverges from exact consumer lock',name,package['version'])

expected_parameters=json.loads((ROOT/'benchmarks/did/expected-parameters.json').read_text())
for name,digest in expected_parameters.items():
 path=a.params_dir/name
 assert path.is_file() and not path.is_symlink() and sha(path)==digest,('required verified parameter premise',name)
a.work.mkdir(parents=True)
atexit.register(shutil.rmtree,a.work,ignore_errors=True)
def run(args,cwd=None):
 start=time.monotonic();r=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=600,env={**os.environ,'MIDNIGHT_PP':str(a.params_dir)})
 if r.returncode:raise RuntimeError((list(map(str,args)),r.stdout[-2000:],r.stderr[-4000:]))
 return r.stdout,(time.monotonic()-start)*1000

compiler_version=run([a.compiler_dir/'compactc','--version'])[0].strip()
zkir_version=run([a.compiler_dir/'zkir','--version'])[0].strip()
assert compiler_version=='0.31.1' and zkir_version=='midnight-zkir 2.1.0',('unqualified compiler',compiler_version,zkir_version)

def cli(cache,*args):
 raw,ms=run([a.binary,'--cache-dir',cache,'--params-dir',a.params_dir,*args]);return json.loads(raw),ms

def compile_to(path):return run([a.compiler_dir/'compactc','--skip-zk',a.source/'packages/contract/src/did.compact',path])[1]
def archive(snapshot,dest):
 start=time.monotonic()
 with tarfile.open(dest,'w:gz',compresslevel=6) as t:t.add(snapshot,arcname='snapshot')
 return (time.monotonic()-start)*1000

def plan_key(work,out,names):
 key_path=work/'ci-key.json'
 command=[sys.executable,ROOT/'scripts/forge-ci.py','--binary',a.binary,'key','--workspace',out,'--params-dir',a.params_dir,'--profile','ledger8-v2','--workload','did-v0.7.0/all12/deactivate-realproof','--generation',f'benchmark-{work.name}','--output',key_path]
 for name in expected_parameters:command+=['--parameter',name]
 for name in names:command+=['--input',f'zkir/{name}.zkir']
 raw,ms=run(command)
 return json.loads(raw),key_path,ms

def helper_restore(cache,snapshot,key_path,planned):
 assert not cache.exists(),'restore target must be absent'
 raw,ms=run([sys.executable,ROOT/'scripts/forge-ci.py','--binary',a.binary,'restore','--key',key_path,'--cache-dir',cache,'--snapshot',snapshot,'--max-bytes','1073741824'])
 result=json.loads(raw)
 assert result['schema']==1 and 'error' not in result
 if snapshot.exists():
  assert result['restored'] is True and result['result']['partition']==planned['partition']
 else:
  assert result['restored'] is False and result['reason']=='cache_miss' and result['partition']==planned['partition']
  assert not cache.exists(),'availability miss must not publish a store'
 return result,ms

def restore(arc,dest,cache,key_path,planned):
 start=time.monotonic();dest.mkdir()
 # Only this runner's freshly created immutable archive is accepted, not network tar input.
 with tarfile.open(arc,'r:gz') as t:t.extractall(dest,filter='data')
 result,process_ms=helper_restore(cache,dest/'snapshot',key_path,planned)
 return result,(time.monotonic()-start)*1000,process_ms

def save_snapshot(cache,destination,planned):
 args=['snapshot','--output',destination,'--partition',planned['partition']]
 for digest in expected_parameters.values():args+=['--parameter-digest',digest]
 value,ms=cli(cache,*args)
 assert value['partition']==planned['partition']
 return value,ms

runtime=a.work/'runtime';runtime.mkdir();shutil.copy(ROOT/'benchmarks/did/package.json',runtime);shutil.copy(ROOT/'benchmarks/did/package-lock.json',runtime)
_,dependency_ms=run(['npm','ci','--ignore-scripts','--no-audit','--no-fund'],runtime)
run([a.compiler_dir/'compactc','--skip-zk',a.source/'packages/jubjub-schnorr/src/jubjub-schnorr.compact',runtime/'managed/jubjub-schnorr'])
shutil.copy(ROOT/'benchmarks/did/make-preimage.mjs',runtime)
# Transpile the pinned consumer's own signing implementation without changing its imports/logic.
run(['node','--input-type=module','-e','import {stripTypeScriptTypes} from "node:module";import fs from "node:fs";fs.writeFileSync(process.argv[2],stripTypeScriptTypes(fs.readFileSync(process.argv[1],"utf8")));',a.source/'packages/jubjub-schnorr/src/signing.ts',runtime/'signing.mjs'])
def refuse(cache,*args):
 result=subprocess.run(list(map(str,[a.binary,'--cache-dir',cache,'--params-dir',a.params_dir,*args])),capture_output=True,text=True,timeout=120)
 assert result.returncode!=0,(args,result.stdout)
 value=json.loads(result.stdout);assert not value['error']['availability_fallback'];return value['error']['code']
names=[];rows=[];identities={};roster=None;controls={};descriptors={}
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
  if roster is None:roster=actual;names=actual
  assert actual==roster
  expected_sources=json.loads((ROOT/'benchmarks/did/expected-zkir.json').read_text())
  assert {name:sha(out/'zkir'/f'{name}.zkir') for name in actual}==expected_sources,'unexpected compiler-emitted circuit bytes'
  shutil.rmtree(runtime/'contract',ignore_errors=True);shutil.copytree(out/'contract',runtime/'contract')
  result,execution_ms=run(['node','make-preimage.mjs'],runtime);execution=json.loads(result)
  restore_ms=0.;prepare_ms=0.;save_ms=0.;compression_ms=0.;archive_bytes=0;snapshot_bytes=0;restore_archive_bytes=0;seed_ms=0.;hits=[];paths={};restore_result=None;planning_ms=0.;helper_restore_ms=0.;planned=None
  if lane!='uncached':planned,key_path,planning_ms=plan_key(work,out,names)
  if lane in ['warm-restored','partial-restored']:
   seed=a.work/f'{repetition}-partial-seed'
   seed_archive=a.work/f'{repetition}-warm-seed.tar.gz' if lane=='warm-restored' else seed/'snapshot.tar.gz'
   if lane=='partial-restored':
    seed_start=time.monotonic()
    seed.mkdir();cli(seed/'cache','prepare',out/'zkir/deactivate.zkir','--name','deactivate');save_snapshot(seed/'cache',seed/'snapshot',planned);archive(seed/'snapshot',seed/'snapshot.tar.gz')
    seed_ms=(time.monotonic()-seed_start)*1000
   restore_archive_bytes=seed_archive.stat().st_size
   restore_result,restore_ms,helper_restore_ms=restore(seed_archive,work/'transport',cache,key_path,planned)
   if lane=='warm-restored':seed_archive.unlink()
   else:shutil.rmtree(seed)
  if lane=='unavailable':
   # This is an absent local transport, not a simulated network/auth outage.
   missing=work/'missing-snapshot';assert not missing.exists()
   restore_result,helper_restore_ms=helper_restore(cache,missing,key_path,planned)
   restore_ms=helper_restore_ms
  if lane!='uncached':before_stats=cli(cache,'stats')[0]['totals']
  else:
   _,prepare_ms=run([a.compiler_dir/'zkir','compile-many',out/'zkir',work/'official-keys'])
  for name in names:
   source=out/'zkir'/f'{name}.zkir'
   if lane=='uncached':
    prover=work/'official-keys'/f'{name}.prover';verifier=work/'official-keys'/f'{name}.verifier'
    paths[name]={'prover':prover,'verifier':verifier,'binary_ir':source.with_suffix('.bzkir')}
    fresh_identity={kind:sha(path) for kind,path in paths[name].items()}
    if name in identities:assert fresh_identity==identities[name],('nonreproducible original compiler keys',name)
    identities[name]=fresh_identity
   else:
    value,ms=cli(cache,'prepare',source,'--name',name);prepare_ms+=ms;hits.append(value['cache']['hit'])
    if name in descriptors:assert value['descriptor']==descriptors[name],('descriptor changed across lanes',name)
    descriptors[name]=value['descriptor']
    paths[name]={f['kind']:pathlib.Path(f['path']) for f in value['export']['files']}
    assert {k:sha(paths[name][k]) for k in ['prover','verifier','binary_ir']}==identities[name],('compiler/Forge mismatch',name,lane)
  expected={'cold':[False]*len(names),'warm-restored':[True]*len(names),'partial-restored':[name=='deactivate' for name in names],'unavailable':[False]*len(names)}
  if lane!='uncached':assert hits==expected[lane],(lane,hits)
  result,proof_process_ms=run([a.prover,out/'zkir/deactivate.zkir',paths['deactivate']['prover'],paths['deactivate']['verifier'],runtime/'preimage.bin',a.params_dir]);proof=json.loads(result)
  assert (execution['assertions'],proof['proofs'],proof['verifications'],proof['negative_controls'])==(5,1,1,2)
  if lane in ['cold','partial-restored','unavailable']:
   _,save_ms=save_snapshot(cache,work/'snapshot',planned);compression_ms=archive(work/'snapshot',work/'snapshot.tar.gz');archive_bytes=(work/'snapshot.tar.gz').stat().st_size;snapshot_bytes=sum(p.stat().st_size for p in (work/'snapshot').rglob('*') if p.is_file())
  wall_ms=(time.monotonic()-start)*1000
  # Partial seed represents a prior job. Its manufacture is excluded, but restore/generation/new save are timed.
  row={'repetition':repetition,'lane':lane,'ci_planning_process_ms':planning_ms,'ci_restore_process_ms':helper_restore_ms,'restore_result':restore_result,'ci_partition':planned['partition'] if planned else None,'ci_key_id':planned['key_id'] if planned else None,'codegen_ms':codegen_ms,'execution_ms':execution_ms,'restore_ms':restore_ms,'key_prepare_ms':prepare_ms,'proof_process_ms':proof_process_ms,'snapshot_ms':save_ms,'compression_ms':compression_ms,'archive_bytes':archive_bytes,'restored_archive_bytes':restore_archive_bytes,'snapshot_bytes':snapshot_bytes,'hits':hits,'execution':execution,'proof':proof,'total_ms':wall_ms-seed_ms,'prior_job_seed_ms_excluded':seed_ms,'observed_wall_ms':wall_ms,'sampled_peak_job_disk_bytes':disk_peak[0]}
  if lane!='uncached':
   row['stats']=cli(cache,'stats')[0]
   row['job_stats_delta']={key:row['stats']['totals'][key]-before_stats[key] for key in ['requests','hits','misses','errors','generation_ms']}
   assert row['job_stats_delta']['requests']==len(names) and row['job_stats_delta']['hits']==sum(hits) and row['job_stats_delta']['misses']==len(names)-sum(hits) and row['job_stats_delta']['errors']==0
  row['observed_wall_ms']=(time.monotonic()-start)*1000
  row['total_ms']=row['observed_wall_ms']-seed_ms
  stop.set();monitor.join();row['sampled_peak_job_disk_bytes']=disk_peak[0]
  if repetition==0 and lane=='cold':
   # Consumer-specific refusal controls outside measured lanes, cleaned immediately.
   control=a.work/'controls';control.mkdir();source=out/'zkir/deactivate.zkir'
   corrupt=control/'corrupt-cache';shutil.copytree(cache,corrupt)
   object_path=corrupt/'objects'/identities['deactivate']['prover']
   payload=bytearray(object_path.read_bytes());payload[-1]^=1;object_path.write_bytes(payload)
   assert refuse(corrupt,'prepare',source,'--name','deactivate')=='integrity_error'
   assert refuse(control/'wrong-profile','--profile','zkir3','prepare',source,'--name','deactivate')=='profile_format_mismatch'
   changed=control/'changed.zkir';changed.write_bytes(source.read_bytes()+b'\n')
   changed_result,_=cli(control/'changed-cache','prepare',changed,'--name','deactivate')
   assert not changed_result['cache']['hit']
   assert changed_result['descriptor']['record']['source']['digest']!=sha(source)
   controls={'corrupt_consumer_prover':'integrity_error; fallback refused','wrong_profile':'profile_format_mismatch; fallback refused','changed_exact_source':'miss; same math is not exact source identity'}
   shutil.rmtree(control)
  if lane=='cold':shutil.move(work/'snapshot.tar.gz',a.work/f'{repetition}-warm-seed.tar.gz')
  rows.append(row)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'schema':1,'status':'in-progress','rows':rows},indent=2)+'\n')
  shutil.rmtree(work)
medians={lane:statistics.median(r['total_ms'] for r in rows if r['lane']==lane) for lane in ['uncached','cold','warm-restored','partial-restored','unavailable']}
result={'schema':1,'status':'passed','consumer':{'tag':manifest['tag'],'commit':manifest['commit']},'forge_build_mode':a.forge_build_mode,'prover_build_mode':a.prover_build_mode,'helper_source_sha256':sha(ROOT/'benchmarks/did/prove.rs'),'compiler_version':compiler_version,'compiler_zkir_version':zkir_version,'selected_key_circuits':names,'proof_circuit':'deactivate','complete_circuit_roster':roster,'host':{'system':platform.system(),'machine':platform.machine(),'cpu_count':os.cpu_count(),'performance_isolation':'shared developer host; concurrent qualification work; not isolated CI capacity'},'scope':'local selected-workload proof/key benchmark; not whole DID CI or localnet transaction submission','verified_parameters':expected_parameters,'dependency_setup_ms':dependency_ms,'dependency_lock_sha256':sha(ROOT/'benchmarks/did/package-lock.json'),'dependency_lock_premise':'every minimal fixture package version/integrity matches exact consumer pnpm-lock.yaml','tool_hashes':{str(p.relative_to(a.compiler_dir)) if p.is_relative_to(a.compiler_dir) else p.name:sha(p) for p in [a.compiler_dir/'compactc',a.compiler_dir/'compactc.bin',a.compiler_dir/'zkir',a.binary,a.prover]},'profile':cli(a.work/'profile-only','profile')[0],'identities':identities,'qualified_descriptors':descriptors,'negative_controls':controls,'rows':rows,'median_total_ms':medians,'warm_saving_ms':medians['uncached']-medians['warm-restored'],'transport':'local archive compression/extraction and validated Forge restore; no hosted cache upload/download latency'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(a.output),'median_total_ms':medians,'warm_saving_ms':result['warm_saving_ms']}))
