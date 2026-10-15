#!/usr/bin/env python3
"""Research probe: stopped private-store relocation for two minimal Forge fixtures.

Requires existing verified parameters. Does not run Compact tests, mutate its
checkout, implement a live snapshot API or measure GitHub cache performance.
"""
import argparse,ast,hashlib,json,pathlib,shutil,sqlite3,subprocess,tempfile,time
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compact-root',type=pathlib.Path,required=True)
parser.add_argument('--binary',type=pathlib.Path,default=pathlib.Path.home()/'.local/bin/midnight-zkir-forge')
parser.add_argument('--output',type=pathlib.Path,required=True)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
compact=args.compact_root.resolve();binary=args.binary.resolve()
def call(*args):
 p=subprocess.run([str(binary),*map(str,args)],check=True,text=True,capture_output=True,timeout=60)
 return json.loads(p.stdout)
module=ast.parse((compact/'tools/compact-rust-backend/forge_circuits.py').read_text())
expected=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='BUILD' for x in n.targets))
profile=call('profile')
receipts=[]
with tempfile.TemporaryDirectory(prefix='forge-research-snapshot-') as directory:
 temporary=pathlib.Path(directory).resolve()
 for selector,fixture in [('ledger8-v2','assert.zkir'),('zkir3','assert-v3.zkir')]:
  store=temporary/selector/'producer';relocated=temporary/selector/'consumer'
  cold=call('--cache-dir',store,'--profile',selector,'prepare',root/'fixtures'/fixture)
  assert not cold['cache']['hit']
  # Every invocation is complete and this unique private store has no other writers.
  clock=time.monotonic();shutil.copytree(store,relocated);copy_ms=(time.monotonic()-clock)*1000
  with sqlite3.connect(f'file:{relocated}/index.sqlite3?mode=ro',uri=True) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  before=call('--cache-dir',relocated,'stats')['totals']
  warm=call('--cache-dir',relocated,'--profile',selector,'prepare',root/'fixtures'/fixture)
  after=call('--cache-dir',relocated,'stats')['totals']
  assert warm['cache']['hit'] and warm['artifact_set_id']==cold['artifact_set_id']
  assert pathlib.Path(warm['export']['base']).is_relative_to(relocated)
  assert pathlib.Path(warm['export']['base'])!=pathlib.Path(cold['export']['base'])
  for entry in warm['export']['files']:
   p=pathlib.Path(entry['path']);assert p.is_relative_to(relocated)
   assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
  receipts.append({'selector':selector,'sqlite_integrity_check':'ok','relocated_warm_hit':True,'same_artifact_identity':True,'paths_recomputed_under_new_root':True,'all_export_digests_verified':True,'stats_hit_delta':after['hits']-before['hits'],'snapshot_file_bytes':sum(p.stat().st_size for p in relocated.rglob('*') if p.is_file()),'local_copy_ms':copy_ms})
record={'schema':1,'date':'2026-10-15','scope':'ARM macOS installed Forge minimal fixture private stopped-store relocation only; no Compact tests, Linux/CI benchmark, live snapshot or snapshot merge qualification','compact_commit':subprocess.check_output(['git','-C',str(compact),'rev-parse','HEAD'],text=True).strip(),'forge_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'consumer_expected_build_fingerprint':expected,'installed_build_fingerprint':profile['build_fingerprint'],'consumer_build_allowlist_matches_installed_forge':expected==profile['build_fingerprint'],'profile_matches_existing_v2_adapter':profile['ledger_revision']=='b5d3e965a18e4cac17fac4f38446fc55c524439a','snapshot_probes':receipts}
args.output.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
