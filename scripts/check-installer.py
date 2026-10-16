#!/usr/bin/env python3
"""Offline private-release installer e2e with fake gh and isolated prefixes; no publication."""
import fcntl,gzip,hashlib,importlib.util,io,json,os,pathlib,platform,shutil,subprocess,sys,tarfile,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/install-release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='forge-installer-test-') as d:
 temp=pathlib.Path(d).resolve();releases=temp/'remote';releases.mkdir();bin_dir=temp/'tools';bin_dir.mkdir();prefix=temp/'prefix';native=module.target();source='a'*40
 def fixture(tag,hostile=False):
  folder=releases/tag;folder.mkdir();stem=f'midnight-zkir-forge-{tag}-{native}';payload=temp/(tag+'-payload');(payload/'bin').mkdir(parents=True);(payload/'share/midnight-zkir-forge').mkdir(parents=True);(payload/'LICENSES').mkdir()
  profiles={'root':{'fixture':'root'},'v3':{'fixture':'worker'}}
  modern=tag in ('v1.2.0','v1.4.0')
  if modern:profiles['root']['formats']=['midnight-zkir-v3.1-json'];profiles['v31']={'fixture':'worker31'}
  for name in module.COMMANDS+((module.WORKER31,) if modern else ()):
   path=payload/'bin'/name
   path.write_text('#!/bin/sh\ncase "$*" in\n *--version*) echo "'+('zkir-forge' if modern else 'midnight-zkir-forge')+' '+tag[1:]+'";;\n *zkir31*) echo \'{"fixture":"worker31"}\';;\n *zkir3*) echo \'{"fixture":"worker"}\';;\n *profile*) echo \''+json.dumps(profiles['root'])+'\';;\n *) echo help;;\nesac\n');path.chmod(0o755)
  if modern:
   shutil.copyfile(payload/'bin/midnight-zkir-forge',payload/'bin'/module.PRIMARY)
   (payload/'bin'/module.PRIMARY).chmod(0o755)
   if tag=='v1.4.0':
    with (payload/'bin'/module.PRIMARY).open('a') as changed:changed.write('# different alias bytes\n')
  (payload/'share/midnight-zkir-forge/forge-ci.py').write_text('# fixture only\n');(payload/'LICENSES/LICENSE').write_text('fixture license\n')
  files=[{'path':p.relative_to(payload).as_posix(),'bytes':p.stat().st_size,'sha256':module.digest(p),'executable':bool(p.stat().st_mode&0o111)} for p in sorted(payload.rglob('*')) if p.is_file()]
  minimum={'os_version':platform.mac_ver()[0] if platform.system()=='Darwin' else None,'libc_family':'glibc' if platform.system()=='Linux' else None,'libc_version':platform.libc_ver()[1] if platform.system()=='Linux' else None}
  manifest={'schema':1,'tag':tag,'version':tag[1:],'source_commit':source,'target':native,'minimum':minimum,'profiles':profiles,'files':files};(payload/'manifest.json').write_text(json.dumps(manifest))
  archive=folder/(stem+'.tar.gz')
  with tarfile.open(archive,'w:gz') as tar:
   tar.add(payload,arcname=stem)
   if hostile:
    entry=tarfile.TarInfo('../escape');entry.size=1;tar.addfile(entry,io.BytesIO(b'x'))
  (folder/'SHA256SUMS').write_text(module.digest(archive)+'  '+archive.name+'\n')
  return folder,archive
 for tag in ['v1.0.0','v1.1.0','v1.2.0','v1.3.0','v1.4.0']:fixture(tag,tag=='v1.3.0')
 gh=bin_dir/'gh';gh.write_text('#!'+sys.executable+'\n'+'''import json,os,pathlib,shutil,sys,time
args=sys.argv[1:];remote=pathlib.Path(os.environ['FIXTURE_REMOTE'])
if args[:2]==['release','view']:
 if os.environ.get('LARGE_METADATA'):
  sys.stdout.write('x'*(17*1024**2));sys.exit(0)
 tag=args[2];folder=remote/tag
 print(json.dumps({'tagName':tag,'isDraft':False,'isPrerelease':False,'assets':[{'name':p.name,'size':p.stat().st_size} for p in folder.iterdir()]}))
elif args[0]=='api':print(json.dumps({'sha':'a'*40}))
elif args[:2]==['release','download']:
 if os.environ.get('FAIL_DOWNLOAD'):sys.exit(1)
 if os.environ.get('PAUSE_DOWNLOAD'):
  pathlib.Path(os.environ['PAUSE_DOWNLOAD']).write_text('started')
  time.sleep(60)
 directory=pathlib.Path(args[args.index('--dir')+1]);tag=args[2]
 for p in (remote/tag).iterdir():shutil.copyfile(p,directory/p.name)
 if os.environ.get('LARGE_CHECKSUM'):(directory/'SHA256SUMS').write_bytes(b'x'*(2*1024**2))
else:sys.exit(2)
''');gh.chmod(0o755)
 env=dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],FIXTURE_REMOTE=str(releases))
 def command(tag='v1.0.0',extra=(),environment=None,ok=True,dest=None):
  r=subprocess.run([sys.executable,str(ROOT/'scripts/install-release.py'),'--version',tag,'--prefix',str(dest or prefix),*extra],env=environment or env,capture_output=True,text=True,timeout=30)
  assert (r.returncode==0)==ok,(r.stdout,r.stderr)
  return json.loads(r.stdout) if ok else r.stderr
 first=command();active=prefix/'share/midnight-zkir-forge/binary/current';old=active.resolve();assert command()['directory']==first['directory']
 assert (prefix/'bin'/module.PRIMARY).readlink()==active/'bin/midnight-zkir-forge'
 assert subprocess.check_output([str(prefix/'bin'/module.PRIMARY),'--version'],text=True).strip()=='midnight-zkir-forge 1.0.0'
 assert 'CLI alias bytes differ' in command('v1.4.0',ok=False) and active.resolve()==old
 assert 'checksum' in command(extra=('--sha256','0'*64),ok=False) and active.resolve()==old
 assert 'GitHub download failed' in command(environment=dict(env,FAIL_DOWNLOAD='1'),ok=False) and active.resolve()==old
 command('v1.3.0',ok=False);assert active.resolve()==old and not (prefix/'escape').exists()
 assert 'metadata exceeds limit' in command(environment=dict(env,LARGE_METADATA='1'),ok=False) and active.resolve()==old
 assert 'checksum metadata exceeds limit' in command(environment=dict(env,LARGE_CHECKSUM='1'),ok=False) and active.resolve()==old
 # Reject gzip expansion before tarfile can parse oversized extension headers.
 bomb=temp/'expanded.gz'
 with gzip.open(bomb,'wb') as compressed:
  for _ in range(18):compressed.write(b'0'*(1024**2))
 limit=module.MAX_UNPACKED;module.MAX_UNPACKED=1024**2
 try:
  try:module.extract(bomb,temp,'fixture')
  except ValueError as error:assert 'expanded archive budget exceeded' in str(error)
  else:raise AssertionError('unbounded expansion accepted')
 finally:module.MAX_UNPACKED=limit
 # Installer lock is released by the OS when a killed owner exits.

 lock_path=active.parent/'.install.lock'
 with lock_path.open('r+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert 'another installer' in command('v1.1.0',ok=False)
 marker=temp/'download-started'
 process=subprocess.Popen([sys.executable,str(ROOT/'scripts/install-release.py'),'--version','v1.1.0','--prefix',str(prefix)],env=dict(env,PAUSE_DOWNLOAD=str(marker)),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  deadline=time.monotonic()+10
  while not marker.exists():assert time.monotonic()<deadline and process.poll() is None;time.sleep(.01)
  import signal
  os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
 finally:
  if process.poll() is None:process.kill();process.wait()
 assert active.resolve()==old
 second=command('v1.1.0');assert active.resolve()!=old
 assert command()['directory']==first['directory'] and active.resolve()==old
 # New optional worker installs through the same pointer and rolls back to a legacy release.
 modern=command('v1.2.0');assert active.resolve()!=old
 assert (active/'bin'/module.WORKER31).is_file()
 assert subprocess.check_output([str(prefix/'bin'/module.PRIMARY),'--version'],text=True).strip()=='zkir-forge 1.2.0'
 assert module.digest(active/'bin'/module.PRIMARY)==module.digest(active/'bin/midnight-zkir-forge')
 assert not os.path.lexists(prefix/'bin'/module.WORKER31)
 modern_manifest=json.loads((active/'manifest.json').read_text())
 missing=json.loads(json.dumps(modern_manifest));missing['profiles'].pop('v31')
 try:module.inventory(active,missing)
 except ValueError as error:assert 'advertised worker missing' in str(error)
 else:raise AssertionError('advertised missing worker accepted')
 missing=json.loads(json.dumps(modern_manifest));missing['files']=[e for e in missing['files'] if e['path']!='bin/'+module.WORKER31]
 try:module.inventory(active,missing)
 except ValueError as error:assert 'incomplete' in str(error)
 else:raise AssertionError('declared missing worker accepted')
 command();assert active.resolve()==old
 assert subprocess.check_output([str(prefix/'bin'/module.PRIMARY),'--version'],text=True).strip()=='midnight-zkir-forge 1.0.0'
 for name in module.COMMANDS:assert (prefix/'bin'/name).resolve().is_file()
 # Kill at publication boundaries without adding production fault hooks.
 driver = r"""
import importlib.util,os,pathlib,sys,time
spec=importlib.util.spec_from_file_location('installer',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
point,marker,prefix=sys.argv[2:]
def pause():
 pathlib.Path(marker).write_text('ready')
 while True:time.sleep(1)
replace=m.os.replace
link=pathlib.Path.symlink_to
def replace_at(source,dest):
 if pathlib.Path(dest).name=='current' and point=='before-pointer':pause()
 result=replace(source,dest)
 if pathlib.Path(dest).name=='current' and point=='after-pointer':pause()
 return result
def link_at(self,target,*args,**kwargs):
 result=link(self,target,*args,**kwargs)
 if self.name=='midnight-zkir-forge' and self.parent.name=='bin' and point=='first-link':pause()
 return result
m.os.replace=replace_at;pathlib.Path.symlink_to=link_at
m.install('v1.1.0',pathlib.Path(prefix))
"""
 for point in ('before-pointer','after-pointer','first-link'):
  destination=prefix if point!='first-link' else temp/'interrupted-first'
  marker=temp/point
  process=subprocess.Popen([sys.executable,'-c',driver,str(ROOT/'scripts/install-release.py'),point,str(marker),str(destination)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
  try:
   deadline=time.monotonic()+15
   while not marker.exists():assert time.monotonic()<deadline and process.poll() is None;time.sleep(.01)
   os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
  finally:
   if process.poll() is None:process.kill();process.wait()
  pointer=destination/'share/midnight-zkir-forge/binary/current'
  if point=='before-pointer':assert pointer.resolve()==old
  else:assert pointer.resolve().is_dir() and json.loads((pointer/'manifest.json').read_text())['tag']=='v1.1.0'
  command('v1.1.0',dest=destination)
  for name in module.COMMANDS:assert (destination/'bin'/name).resolve().is_file()
  command()  # Restore the original active release for subsequent refusal checks.
 # An unrelated launcher (including a Nix link) must not be replaced.
 for name in ('midnight-zkir-forge',module.PRIMARY):
  conflict=temp/('conflict-'+name);(conflict/'bin').mkdir(parents=True);existing=conflict/'bin'/name;existing.symlink_to('/nix/store/fixture/bin/'+name)
  command(dest=conflict,ok=False);assert existing.readlink()==pathlib.Path('/nix/store/fixture/bin/'+name)
  assert not (conflict/'share/midnight-zkir-forge/binary/current').exists()
 # Same tag changed content cannot silently replace the pinned installation.
 folder=releases/'v1.0.0';archive=next(folder.glob('*.tar.gz'));data=archive.read_bytes();archive.write_bytes(data+b'changed');(folder/'SHA256SUMS').write_text(module.digest(archive)+'  '+archive.name+'\n')
 assert 'tag content changed' in command(ok=False) and active.resolve()==old
 print(json.dumps({'schema':1,'platform':native,'offline_fake_gh':True,'install_reinstall_upgrade_rollback':True,'primary_alias_upgrade_legacy_rollback':True,'alias_corruption_refused':True,'both_launcher_collisions_refused_before_activation':True,'optional_worker_upgrade_legacy_rollback':True,'advertised_missing_worker_refused':True,'checksum_download_archive_conflict_refusals':True,'concurrent_installer_refused':True,'killed_installer_lock_recovery':True,'activation_and_first_link_interruption_recovery':True,'metadata_checksum_and_expansion_budgets':True,'same_tag_replacement_refused':True,'scope':'private temporary fixtures; no GitHub credentials/releases or Nix-free portability claim'}))
