#!/usr/bin/env python3
"""Build a private reduced-export performance fixture, never full-account qualification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SELECTED = {'deposit_unshielded','activate_initial_device_with_jubjub'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source','compiler-dir','params-dir','work','output']:
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    work=args.work.resolve()
    work.relative_to(ROOT/'.local/milestone-2026.10.1/passport')
    assert not work.exists() and not args.output.exists()
    closure=json.loads((ROOT/'docs/evidence/passport-full-models-local.json').read_text())['source_closure']
    tools=json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())['tool_sha256']
    for name in ['compactc.bin','zkir-v3']:
        assert sha(args.compiler_dir/name)==tools['tools/compiler/'+name]
    sources={}
    for name,facts in closure['files'].items():
        path=args.source/name
        assert sha(path)==facts['sha256']
        target=work/name
        target.parent.mkdir(parents=True,exist_ok=True)
        original=path.read_text()
        transformed=re.sub(r'^export circuit ([A-Za-z0-9_]+)',
            lambda match:match[0] if match[1] in SELECTED else 'circuit '+match[1],original,flags=re.MULTILINE)
        target.write_text(transformed)
        sources[name]={'original_sha256':facts['sha256'],'fixture_sha256':sha(target)}
    bundle=work/'bundle'
    environment=dict(os.environ,MIDNIGHT_PP=str(args.params_dir.resolve()))
    environment['PATH']=str(args.compiler_dir.resolve())+os.pathsep+environment.get('PATH','')
    subprocess.run([args.compiler_dir/'compactc.bin','--feature-zkir-v3',
        work/'contract/contracts/account.compact',bundle],env=environment,check=True,timeout=1200)
    expected=json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
    assert {p.stem for p in (bundle/'zkir').glob('*.zkir')}==SELECTED
    for name in SELECTED:
        assert sha(bundle/'zkir'/(name+'.zkir'))==expected['emitted_zkir_sha256'][name+'.zkir']
    old=json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())
    for row in old['rows']:
        for artifact in row['generation']['artifacts']:
            kind=artifact['kind']
            target=bundle/('zkir' if kind=='binary_ir' else 'keys')/(row['circuit']+'.'+('bzkir' if kind=='binary_ir' else kind))
            assert sha(target)==artifact['sha256']
    receipt={'schema':1,'status':'passed','consumer_commit':closure['revision'],'source_transform':
        'In an owned private copy only, remove export from unselected impure circuits; preserve all bodies and pure exports. Original checkout/source closure remains unchanged.',
        'sources':sources,'selected_circuit_bytes_match_unchanged_account':True,
        'selected_official_binary_ir_and_keys_match_previous_independent_qualification':True,
        'compiler_manifest_sha256':sha(bundle/'compiler/contract-manifest.json'),
        'compiler_sha256':sha(args.compiler_dir/'compactc.bin'),'harness_sha256':sha(Path(__file__)),
        'scope':'Reduced-export compiler-generated benchmark carrier only; original complete metadata retained. This does not qualify the full-account compiler adapter or full-account HTTP serving.'}
    with args.output.open('x') as stream:
        json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps({'bundle':str(bundle),'output':str(args.output)}))


if __name__=='__main__': main()
