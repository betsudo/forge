#!/usr/bin/env python3
"""Prepare a local native release candidate, never upload or tag. Requires a clean source tree."""
import argparse,hashlib,importlib.util,json,os,pathlib,platform,re,shutil,subprocess,tarfile,tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install-release.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
def run(*args):return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True).stdout

def prepare(tag,output):
 installer.require(re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',tag),'semantic release tag required')
 installer.require(not run('git','-C',ROOT,'status','--porcelain'),'commit source changes before preparing a candidate')
 commit=run('git','-C',ROOT,'rev-parse','HEAD').strip()
 # Build the exact clean commit, never attribute caller-supplied/stale binaries to HEAD.
 nix=shutil.which('nix') or '/nix/var/nix/profiles/default/bin/nix'
 built=json.loads(run(nix,'build','--no-link','--json',f'git+file://{ROOT}?rev={commit}#default'))
 package=pathlib.Path(built[0]['outputs']['out'])
 binary=package/'bin/midnight-zkir-forge';worker=package/'bin/midnight-zkir-forge-zkir3-worker'
 target=installer.target();output=output.resolve();output.mkdir(parents=True,exist_ok=True)
 stem=f'midnight-zkir-forge-{tag}-{target}';archive=output/(stem+'.tar.gz')
 installer.require(not archive.exists(),'candidate already exists; choose a fresh output directory')
 with tempfile.TemporaryDirectory(prefix='.bundle-',dir=output) as d:
  root=pathlib.Path(d)/stem;(root/'bin').mkdir(parents=True);(root/'share/midnight-zkir-forge').mkdir(parents=True);(root/'LICENSES').mkdir()
  for source,name in [(binary,'midnight-zkir-forge'),(worker,'midnight-zkir-forge-zkir3-worker')]:
   destination=root/'bin'/name;shutil.copyfile(source.resolve(),destination);destination.chmod(0o755)
  (root/'share/midnight-zkir-forge/forge-ci.py').write_text(run('git','-C',ROOT,'show',commit+':scripts/forge-ci.py'))
  launcher=root/'bin/midnight-zkir-forge-ci';launcher.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
os.execv(sys.executable,[sys.executable,str(root/'share/midnight-zkir-forge/forge-ci.py'),'--binary',str(root/'bin/midnight-zkir-forge'),*sys.argv[1:]])
''');launcher.chmod(0o755)
  (root/'LICENSES/Forge-LICENSE').write_text(run('git','-C',ROOT,'show',commit+':LICENSE'))
  (root/'LICENSES/NOTICE').write_text('Forge uses the pinned official Midnight libraries and Cargo dependencies. This candidate requires review of dependency license notices before release publication.\n')
  if platform.system()=='Darwin':
   # Native macOS SDK dependencies are external; Nix dylibs must be bundled/relocated.
   pending=[root/'bin'/name for name in installer.COMMANDS[:2]];seen=set();library_sources={}
   while pending:
    path=pending.pop()
    if path in seen:continue
    seen.add(path)
    for line in run('/usr/bin/otool','-L',path).splitlines()[1:]:
     dependency=line.strip().split(' (',1)[0]
     if dependency.startswith('/nix/store/'):
      source=pathlib.Path(dependency);library=root/'lib'/source.name;library.parent.mkdir(exist_ok=True)
      if library.exists():installer.require(library_sources[library.name]==installer.digest(source),'runtime library basename collision')
      else:shutil.copyfile(source,library);library.chmod(0o755);pending.append(library);library_sources[library.name]=installer.digest(source)
      relative='@loader_path/'+('../lib/' if path.parent.name=='bin' else '')+library.name
      run('/usr/bin/install_name_tool','-change',dependency,relative,path)
   for path in sorted(seen):
    if path.parent.name=='lib':run('/usr/bin/install_name_tool','-id','@rpath/'+path.name,path)
    run('/usr/bin/codesign','--force','--sign','-',path)
    installer.require('/nix/store/' not in run('/usr/bin/otool','-L',path),'Nix loader dependency remains')
   minimum={'os_version':platform.mac_ver()[0],'libc_family':None,'libc_version':None}
  else:
   for name in installer.COMMANDS[:2]:
    report=run('ldd',root/'bin'/name)
    installer.require('/nix/store/' not in report,'Linux candidate still requires Nix libraries; portable Linux production strategy is not yet implemented')
    installer.require('/nix/store/' not in run('readelf','-l',root/'bin'/name),'Linux candidate still requires a Nix ELF loader')
   family,version=platform.libc_ver();minimum={'os_version':None,'libc_family':family,'libc_version':version}
  environment=dict(os.environ);environment.pop('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER',None)
  def profile(*args):return json.loads(subprocess.run([str(root/'bin/midnight-zkir-forge'),*args],env=environment,check=True,capture_output=True,text=True).stdout)
  files=[]
  for path in sorted(root.rglob('*')):
   if path.is_file():files.append({'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':installer.digest(path),'executable':bool(path.stat().st_mode&0o111)})
  manifest={'schema':1,'tag':tag,'version':tag[1:],'source_commit':commit,'target':target,'minimum':minimum,'profiles':{'root':profile('profile'),'v3':profile('--profile','zkir3','profile')},'files':files}
  (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');installer.runtime(minimum);installer.inventory(root,manifest);installer.smoke(root,manifest)
  with tarfile.open(archive,'w:gz') as tar:tar.add(root,arcname=stem)
 (output/'install-release.py').write_text(run('git','-C',ROOT,'show',commit+':scripts/install-release.py'))
 sums=''.join(f'{installer.digest(path)}  {path.name}\n' for path in [archive,output/'install-release.py'])
 (output/'SHA256SUMS').write_text(sums)
 return {'candidate':str(archive),'target':target,'source_commit':manifest['source_commit'],'qualification':'local candidate only; clean Nix-free target host and dependency-license audit still required; no publication'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 print(json.dumps(prepare(a.tag,a.output)))
