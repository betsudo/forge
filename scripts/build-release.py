#!/usr/bin/env python3
"""Prepare a local native release candidate, never upload or tag. Requires a clean source tree."""
import argparse,hashlib,importlib.util,io,json,os,pathlib,platform,re,shutil,subprocess,tarfile,tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install-release.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
def run(*args):return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True).stdout

def _prepare(tag,output,commit,frozen):
 installer.require(re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',tag),'semantic release tag required')
 # Build the exact clean commit, never attribute caller-supplied/stale binaries to HEAD.
 nix=shutil.which('nix') or '/nix/var/nix/profiles/default/bin/nix'
 built=json.loads(run(nix,'build','--no-link','--json','--cores','2',f'git+file://{ROOT}?rev={commit}#default'))
 package=pathlib.Path(built[0]['outputs']['out'])
 installer.require((package/'bin'/installer.PRIMARY).is_file(), 'primary CLI missing from package')
 installer.require(installer.digest(package/'bin'/installer.PRIMARY)==installer.digest(package/'bin/midnight-zkir-forge'), 'package CLI aliases differ')
 native_commands=['midnight-zkir-forge','midnight-zkir-forge-zkir3-worker']
 worker31=package/'bin'/installer.WORKER31
 if worker31.exists():native_commands.append(installer.WORKER31)
 target=installer.target();output=output.resolve();output.mkdir(parents=True,exist_ok=True)
 stem=f'midnight-zkir-forge-{tag}-{target}';archive=output/(stem+'.tar.gz')
 companions=[]
 installer.require(not archive.exists(),'candidate already exists; choose a fresh output directory')
 with tempfile.TemporaryDirectory(prefix='.bundle-',dir=output) as d:
  root=pathlib.Path(d)/stem;(root/'bin').mkdir(parents=True);(root/'share/midnight-zkir-forge').mkdir(parents=True);(root/'LICENSES').mkdir()
  for name in native_commands:
   source=package/'bin'/name
   destination=root/'bin'/name;shutil.copyfile(source.resolve(),destination);destination.chmod(0o755)
  (root/'share/midnight-zkir-forge/forge-ci.py').write_text(run('git','-C',ROOT,'show',commit+':scripts/forge-ci.py'))
  launcher=root/'bin/midnight-zkir-forge-ci';launcher.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
os.execv(sys.executable,[sys.executable,str(root/'share/midnight-zkir-forge/forge-ci.py'),'--binary',str(root/'bin/midnight-zkir-forge'),*sys.argv[1:]])
''');launcher.chmod(0o755)
  (root/'LICENSES/Forge-LICENSE').write_text(run('git','-C',ROOT,'show',commit+':LICENSE'))
  cargo_spec=importlib.util.spec_from_file_location('cargo_notices',frozen/'scripts/cargo-notices.py');cargo_notices=importlib.util.module_from_spec(cargo_spec);cargo_spec.loader.exec_module(cargo_notices)
  cargo_notices.collect(root,nix,f'git+file://{ROOT}?rev={commit}',ROOT,commit)
  if platform.system()=='Darwin':
   # Native macOS SDK dependencies are external; Nix dylibs must be bundled/relocated.
   pending=[root/'bin'/name for name in native_commands];seen=set();library_sources={}
   while pending:
    path=pending.pop()
    if path in seen:continue
    seen.add(path)
    for line in run('/usr/bin/otool','-L',path).splitlines()[1:]:
     dependency=line.strip().split(' (',1)[0]
     if dependency.startswith('/nix/store/'):
      source=pathlib.Path(dependency);library=root/'lib'/source.name;library.parent.mkdir(exist_ok=True)
      if library.exists():installer.require(library_sources[library.name]['source_sha256']==installer.digest(source),'runtime library basename collision')
      else:shutil.copyfile(source,library);library.chmod(0o755);pending.append(library);library_sources[library.name]={'source_path':str(source),'source_sha256':installer.digest(source)}
      relative='@loader_path/'+('../lib/' if path.parent.name=='bin' else '')+library.name
      run('/usr/bin/install_name_tool','-change',dependency,relative,path)
   for path in sorted(seen):
    if path.parent.name=='lib':run('/usr/bin/install_name_tool','-id','@rpath/'+path.name,path)
    run('/usr/bin/codesign','--force','--sign','-',path)
    installer.require('/nix/store/' not in run('/usr/bin/otool','-L',path),'Nix loader dependency remains')
   for name,origin in library_sources.items():origin['relocated_sha256']=installer.digest(root/'lib'/name)
   (root/'LICENSES/darwin-runtime-origin.json').write_text(json.dumps(library_sources,indent=2)+'\n')
   system='aarch64-darwin' if target.startswith('aarch64-') else 'x86_64-darwin'
   source_spec=importlib.util.spec_from_file_location('darwin_sources',frozen/'scripts/linux-runtime-sources.py');darwin_sources=importlib.util.module_from_spec(source_spec);source_spec.loader.exec_module(darwin_sources)
   companions.append(darwin_sources.collect(root,output,stem,nix,f'git+file://{ROOT}?rev={commit}',system,ROOT,commit))
   minimum={'os_version':platform.mac_ver()[0],'libc_family':None,'libc_version':None}
  else:
   system='aarch64-linux' if target.startswith('aarch64-') else 'x86_64-linux'
   expression=f'(builtins.getFlake "git+file://{ROOT}?rev={commit}").inputs.nixpkgs.legacyPackages.{system}.patchelf'
   tools=json.loads(run(nix,'build','--no-link','--json','--impure','--expr',expression))
   patchelf=pathlib.Path(tools[0]['outputs']['out'])/'bin/patchelf'
   linux_spec=importlib.util.spec_from_file_location('linux_runtime',frozen/'scripts/linux-runtime.py');linux_runtime=importlib.util.module_from_spec(linux_spec);linux_spec.loader.exec_module(linux_runtime)
   linux_runtime.relocate(root,patchelf,native_commands)
   source_spec=importlib.util.spec_from_file_location('linux_sources',frozen/'scripts/linux-runtime-sources.py');linux_sources=importlib.util.module_from_spec(source_spec);source_spec.loader.exec_module(linux_sources)
   companions.append(linux_sources.collect(root,output,stem,nix,f'git+file://{ROOT}?rev={commit}',system,ROOT,commit))
   # glibc is bundled, so the producer Python's glibc version is not a consumer
   # requirement. The explicit qualification target is Debian12/glibc2.36;
   # older hosts require a separate qualification rather than an inferred claim.
   minimum={'os_version':None,'libc_family':'glibc','libc_version':'2.36'}
  # Relocate/sign one executable only, then copy its final bytes. Linux launchers
  # intentionally share the legacy lib/ELF name and identical closure commitment.
  shutil.copyfile(root/'bin/midnight-zkir-forge',root/'bin'/installer.PRIMARY)
  (root/'bin'/installer.PRIMARY).chmod(0o755)
  environment=dict(os.environ)
  # Nix exports this build-tool selector; it is not a runtime loader setting.
  # Keep all actual LD_* controls intact in both consumer and producer checks.
  environment.pop('LD_FOR_BUILD',None)
  for variable in ('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER','MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER'):environment.pop(variable,None)
  def profile(*args):return json.loads(subprocess.run([str(root/'bin/midnight-zkir-forge'),*args],env=environment,check=True,capture_output=True,text=True).stdout)
  files=[]
  for path in sorted(root.rglob('*')):
   if path.is_file():files.append({'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':installer.digest(path),'executable':bool(path.stat().st_mode&0o111)})
  profiles={'root':profile('profile'),'v3':profile('--profile','zkir3','profile')}
  if installer.WORKER31 in native_commands:profiles['v31']=profile('--profile','zkir31','profile')
  manifest={'schema':1,'tag':tag,'version':tag[1:],'source_commit':commit,'target':target,'minimum':minimum,'profiles':profiles,'files':files}
  (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');installer.runtime(minimum);installer.inventory(root,manifest);installer.smoke(root,manifest,environment=environment)
  with tarfile.open(archive,'w:gz') as tar:tar.add(root,arcname=stem)
 (output/'install-release.py').write_text(run('git','-C',ROOT,'show',commit+':scripts/install-release.py'))
 renderer_spec=importlib.util.spec_from_file_location('render_installer',frozen/'scripts/render-installer.py')
 renderer=importlib.util.module_from_spec(renderer_spec);renderer_spec.loader.exec_module(renderer)
 shell=output/'zkir-forge-installer.sh';shell.write_bytes(renderer.render((output/'install-release.py').read_bytes()));shell.chmod(0o755)
 sums=''.join(f'{installer.digest(path)}  {path.name}\n' for path in [archive,output/'install-release.py',shell,*companions])
 (output/'SHA256SUMS').write_text(sums)
 return {'candidate':str(archive),'target':target,'source_commit':manifest['source_commit'],'qualification':'local candidate only; clean Nix-free target host qualification still required; dependency notices and runtime source companion inventoried; no publication'}
def prepare(tag,output):
 global installer
 installer.require(not run('git','-C',ROOT,'status','--porcelain'),'commit source changes before preparing a candidate')
 commit=run('git','-C',ROOT,'rev-parse','HEAD').strip()
 # Freeze all packaging helpers and vendored notices before the potentially long
 # Nix build. Ancillary bytes and imported behavior must identify the same commit.
 with tempfile.TemporaryDirectory(prefix='forge-release-source-') as directory:
  frozen=pathlib.Path(directory)
  archive=subprocess.run(['git','-C',str(ROOT),'archive','--format=tar',commit],check=True,capture_output=True).stdout
  with tarfile.open(fileobj=io.BytesIO(archive)) as source:
   for member in source.getmembers():
    path=pathlib.PurePosixPath(member.name)
    installer.require(not path.is_absolute() and '..' not in path.parts and (member.isfile() or member.isdir()),'unsafe source archive member')
   source.extractall(frozen,filter='data')
  module_spec=importlib.util.spec_from_file_location('frozen_installer',frozen/'scripts/install-release.py')
  installer=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(installer)
  return _prepare(tag,output,commit,frozen)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 print(json.dumps(prepare(a.tag,a.output)))
