#!/usr/bin/env python3
"""Measure exact Passport account codegen separately from the artifact-cache lanes."""
import argparse, atexit, datetime, hashlib, json, pathlib, shutil, statistics, subprocess, time
ROOT=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=pathlib.Path,required=True)
p.add_argument('--compiler-dir',type=pathlib.Path,required=True)
p.add_argument('--work',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
p.add_argument('--repetitions',type=int,default=3)
a=p.parse_args()
for name in ['source','compiler_dir','work','output']:setattr(a,name,getattr(a,name).resolve())
assert a.repetitions>=3 and not a.work.exists()
a.work.relative_to(ROOT/'.local/qualification/passport')
assert not a.output.is_relative_to(a.work) and not a.output.is_relative_to(a.source)
manifest=json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for name,digest in manifest['files'].items():assert sha(a.source/name)==digest
qualified=json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())
assert sha(a.compiler_dir/'compactc.bin')==qualified['tool_sha256']['tools/compiler/compactc.bin']
a.work.mkdir(parents=True);atexit.register(lambda:shutil.rmtree(a.work,ignore_errors=True));rows=[]
for repeat in range(a.repetitions):
 out=a.work/str(repeat);started=time.monotonic()
 subprocess.run([str(a.compiler_dir/'compactc'),'--feature-zkir-v3','--skip-zk',str(a.source/'contract/contracts/account.compact'),str(out)],check=True,timeout=1200)
 elapsed=time.monotonic()-started
 actual={f.name:sha(f) for f in sorted((out/'zkir').glob('*.zkir'))}
 assert actual==manifest['emitted_zkir_sha256'],'codegen roster or exact bytes changed'
 rows.append({'repeat':repeat+1,'seconds':elapsed,'circuits':len(actual),'all_emitted_zkir_match_qualified_hashes':True});shutil.rmtree(out)
 print(json.dumps(rows[-1]),flush=True)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({'schema':1,'status':'in-progress','rows':rows},indent=2)+'\n')
result={'schema':1,'status':'passed','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'consumer_commit':manifest['commit'],'compiler':'0.35.0 (debb05f94 2026-09-29)','compiler_sha256':sha(a.compiler_dir/'compactc.bin'),'flags':['--feature-zkir-v3','--skip-zk'],'full_circuit_roster':sorted(manifest['emitted_zkir_sha256']),'rows':rows,'median_seconds':statistics.median(r['seconds'] for r in rows),'scope':'Full52-circuit account codegen only. Keygen/proof/cache transport excluded. Shared developer host; not hostedCI.'}
a.output.write_text(json.dumps(result,indent=2)+'\n')
