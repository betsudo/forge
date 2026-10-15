#!/usr/bin/env python3
"""Local CI cache mechanics. Never uploads, invokes tests, or grants GitHub privileges."""
import argparse, hashlib, json, os, pathlib, platform, re, subprocess, sys, time
Path=pathlib.Path

def require(condition,message):
    if not condition: raise ValueError(message)
def hash_file(path):
    require(path.is_file() and not path.is_symlink(),'regular file required: '+str(path))
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(path):
    require(path.stat().st_size<=16*1024*1024,'metadata exceeds 16 MiB')
    def fields(pairs):
        out={}
        for key,value in pairs:require(key not in out,'duplicate JSON field');out[key]=value
        return out
    return json.loads(path.read_text(),object_pairs_hook=fields)
def write(path,value):
    # Metadata is job-owned and never silently replaced.
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def invoke(binary,*args,check=True):
    p=subprocess.run([str(binary),*map(str,args)],capture_output=True,text=True)
    try:value=json.loads(p.stdout)
    except ValueError:raise ValueError('Forge did not return JSON') from None
    if p.returncode and check:raise ValueError('Forge failed: '+value.get('error',{}).get('code','request_failed'))
    return p.returncode,value

def tool(binary,selector):
    binary=binary.resolve(strict=True)
    _,root=invoke(binary,'profile')
    _,selected=invoke(binary,'--profile',selector,'profile')
    return {'binary_sha256':hash_file(binary),'platform':{'os':platform.system(),'arch':platform.machine()},'root':root,'selected':selected}
def input_file(workspace,name):
    path=Path(name)
    require(not path.is_absolute() and path.parts and all(p not in ('.','..') for p in path.parts),'relative workload file required')
    full=workspace/path
    require(full.resolve().is_relative_to(workspace),'input escapes workspace')
    for parent in [full,*full.parents]:
        if parent==workspace:break
        require(not parent.is_symlink(),'workload symlink refused')
    return {'path':path.as_posix(),'bytes':full.stat().st_size,'sha256':hash_file(full)}
def params(directory,names):
    require(names and len(set(names))==len(names),'nonempty unique parameter files required')
    out=[]
    for name in sorted(names):
        require(re.fullmatch(r'bls_midnight_2p(?:0|[1-9][0-9]{0,2})',name) is not None and int(name.split('2p')[1])<=255,'invalid parameter filename')
        path=directory/name
        out.append({'name':name,'bytes':path.stat().st_size,'sha256':hash_file(path)})
    return out

def key(args):
    workspace=args.workspace.resolve(strict=True);directory=args.params_dir.resolve(strict=True)
    require(args.workload.strip(),'workload selector/flags must be nonempty')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.generation) is not None,'unsafe generation suffix')
    require(args.input and len(set(args.input))==len(args.input),'nonempty unique workload inputs required')
    inputs=sorted([input_file(workspace,n) for n in args.input],key=lambda row:row['path'])
    provenance=tool(args.binary,args.profile);parameters=params(directory,args.parameter)
    partition=identity({'schema':1,'tool':provenance,'parameters':parameters,'selector':args.profile})
    workload=identity({'workload':args.workload,'inputs':inputs})
    prefix='forge-v1-'+partition+'-';workload_prefix=prefix+workload+'-'
    value={'schema':1,'kind':'forge-ci-key/v1','selector':args.profile,'tool':provenance,'parameters':parameters,'params_dir':str(directory),'workspace':str(workspace),'workload':args.workload,'inputs':inputs,'partition':partition,'workload_hash':workload,'generation':args.generation,'primary':workload_prefix+args.generation,'restore_keys':[workload_prefix,prefix]}
    value['key_id']=identity(value);write(args.output,value)
    if args.github_output:
        with args.github_output.open('a') as stream:
            for name in ('primary','partition','workload_hash','key_id'):stream.write(name+'='+value[name]+'\n')
            stream.write('restore_keys_json='+json.dumps(value['restore_keys'],separators=(',',':'))+'\n')
    return value

def checked_key(path,binary):
    value=load(path);claimed=value.pop('key_id');require(claimed==identity(value),'key manifest identity changed');value['key_id']=claimed
    require(value['schema']==1 and value['kind']=='forge-ci-key/v1','unsupported key schema')
    require(value['tool']==tool(binary,value['selector']),'Forge/platform identity differs from planned key')
    require(value['parameters']==params(Path(value['params_dir']),[p['name'] for p in value['parameters']]),'parameter files changed')
    require(value['inputs']==sorted([input_file(Path(value['workspace']),p['path']) for p in value['inputs']],key=lambda row:row['path']),'workload inputs changed')
    expected_partition=identity({'schema':1,'tool':value['tool'],'parameters':value['parameters'],'selector':value['selector']})
    expected_workload=identity({'workload':value['workload'],'inputs':value['inputs']})
    require(value['partition']==expected_partition and value['workload_hash']==expected_workload,'key partition/workload mismatch')
    prefix='forge-v1-'+expected_partition+'-';wp=prefix+expected_workload+'-'
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',value['generation']) is not None,'unsafe generation suffix')
    require(value['primary']==wp+value['generation'] and value['restore_keys']==[wp,prefix],'unsafe restore/save key')
    return value

def store_identity(root):
    root=root.resolve(strict=True);db=root/'index.sqlite3';require(not db.is_symlink(),'database symlink refused')
    metadata=db.stat();return {'root':str(root),'device':metadata.st_dev,'inode':metadata.st_ino}
def totals(binary,root):return invoke(binary,'--cache-dir',root,'stats')[1]['totals']
def outside(path,root):require(not path.resolve().is_relative_to(root.resolve()),'CI metadata must be outside the cached store')
def baseline(args):
    planned=checked_key(args.key,args.binary);outside(args.output,args.cache_dir)
    before=totals(args.binary,args.cache_dir)
    value={'schema':1,'kind':'forge-ci-baseline/v1','key_id':planned['key_id'],'store':store_identity(args.cache_dir),'totals':before,'started_monotonic_ns':time.monotonic_ns()}
    write(args.output,value);return value

def report(args):
    planned=checked_key(args.key,args.binary);before=load(args.baseline)
    require(before['schema']==1 and before['kind']=='forge-ci-baseline/v1','unsupported baseline schema')
    require(before['key_id']==planned['key_id'],'baseline key mismatch')
    require(before['store']==store_identity(args.cache_dir),'job-local store replaced or relocated after baseline')
    after=totals(args.binary,args.cache_dir);delta={}
    for name in ('requests','hits','misses','errors','generation_ms','estimated_generation_avoided_ms','total_request_ms'):
        delta[name]=after[name]-before['totals'][name];require(delta[name]>=0,'inherited metrics moved backwards')
    count=delta['hits']+delta['misses'];delta['hit_rate']=delta['hits']/count if count else None
    return {'schema':1,'key_id':planned['key_id'],'partition':planned['partition'],'delta':delta,'job_elapsed_ms':(time.monotonic_ns()-before['started_monotonic_ns'])/1e6,'scope':'logical requests since baseline; misses are not unique derivations; timings/estimates are not test outcomes'}

def restore(args):
    planned=checked_key(args.key,args.binary)
    require(not os.path.lexists(args.cache_dir),'restore target already exists')
    if not os.path.lexists(args.snapshot):return {'schema':1,'restored':False,'reason':'cache_miss','partition':planned['partition']}
    manifest=load(args.snapshot/'snapshot.json')
    expected_profile=planned['tool']['selected']['profile']
    args.cache_dir.parent.mkdir(parents=True,exist_ok=True)
    # Validate declared scope before atomically publishing; Forge verifies all payload bytes.
    _scope(manifest,planned,expected_profile)
    command=['--profile',planned['selector'],'--cache-dir',args.cache_dir,'restore',args.snapshot,'--partition',planned['partition'],'--max-bytes',args.max_bytes]
    for p in planned['parameters']:command+=['--parameter-digest',p['sha256']]
    if args.expected_id:command+=['--expected-id',args.expected_id]
    _,value=invoke(args.binary,*command)
    return {'schema':1,'restored':True,'result':value}

def _scope(manifest,planned,expected_profile):
    require(manifest['producer']['build_fingerprint']==planned['tool']['root']['build_fingerprint'],'snapshot producer does not match key')
    if planned['selector']=='zkir3':require(manifest['producer']['worker']==planned['tool']['selected']['worker'],'snapshot worker does not match key')
    require(manifest['partition']==planned['partition'],'snapshot partition does not match key')
    # Scope comes from Forge's validated summary, not this unsigned declaration.
    # The snapshot command receipt is verified below at preparation time.

def prepare_save(args):
    denied=lambda reason,**extra:{'schema':1,'publish':False,'reason':reason,**extra}
    if not args.tests_passed:return denied('tests_not_confirmed')
    if os.environ.get('GITHUB_EVENT_NAME') not in ('push','workflow_dispatch') or os.environ.get('GITHUB_REF')!=args.trusted_ref:return denied('untrusted_event_or_ref')
    require(args.trusted_ref.startswith('refs/heads/') and len(args.trusted_ref)>len('refs/heads/'),'explicit trusted branch ref required')
    require(args.max_bytes>0,'byte budget must be positive')
    delta=report(args)
    if delta['delta']['errors']:return denied('request_errors',report=delta)
    if delta['delta']['misses']==0:return denied('no_generation_misses',report=delta)
    planned=checked_key(args.key,args.binary)
    outside(args.snapshot,args.cache_dir);args.snapshot.parent.mkdir(parents=True,exist_ok=True)
    scope=[item for p in planned['parameters'] for item in ['--parameter-digest',p['sha256']]]
    status,value=invoke(args.binary,'--profile',planned['selector'],'--cache-dir',args.cache_dir,'snapshot','--output',args.snapshot,'--partition',planned['partition'],'--max-bytes',args.max_bytes,*scope,check=False)
    if status:
        if value.get('error',{}).get('code')=='snapshot_limit':return denied('over_budget',report=delta)
        raise ValueError('snapshot failed: '+value.get('error',{}).get('code','request_failed'))
    summary=value['summary'];profile=planned['tool']['selected']['profile'];digests={p['sha256'] for p in planned['parameters']}
    # A mixed-profile/undeclared-parameter store must not be published under this partition.
    require(set(summary['profiles'])<=set([profile]) and set(summary['parameter_digests'])<=digests,'snapshot exceeds declared profile/parameter scope')
    _scope(load(args.snapshot/'snapshot.json'),planned,profile)
    return {'schema':1,'publish':True,'reason':'trusted_growth_within_budget','key':planned['primary'],'snapshot':value,'report':delta,'authority':'planning only; workflow/server-side cache scope supplies authorization'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=Path.home()/'.local/bin/midnight-zkir-forge')
    subs=parser.add_subparsers(dest='command',required=True)
    p=subs.add_parser('key');p.add_argument('--workspace',type=Path,required=True);p.add_argument('--params-dir',type=Path,required=True);p.add_argument('--parameter',action='append',required=True);p.add_argument('--input',action='append',required=True);p.add_argument('--profile',choices=['ledger8-v2','zkir3'],required=True);p.add_argument('--workload',required=True);p.add_argument('--generation',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--github-output',type=Path)
    for name in ('baseline','report','restore','prepare-save'):
        p=subs.add_parser(name);p.add_argument('--key',type=Path,required=True);p.add_argument('--cache-dir',type=Path,required=True)
        if name in ('report','prepare-save'):p.add_argument('--baseline',type=Path,required=True)
        if name=='baseline':p.add_argument('--output',type=Path,required=True)
        if name in ('restore','prepare-save'):p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--max-bytes',type=int,required=True)
        if name=='restore':p.add_argument('--expected-id')
        if name=='prepare-save':p.add_argument('--trusted-ref',required=True);p.add_argument('--tests-passed',action='store_true')
    args=parser.parse_args();functions={'key':key,'baseline':baseline,'report':report,'restore':restore,'prepare-save':prepare_save}
    print(json.dumps(functions[args.command](args)))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'schema':1,'error':{'code':'ci_cache_refused','message':str(error)}}));sys.exit(1)
