#!/usr/bin/env python3
"""Install a real local candidate with fake gh, then qualify both native backends.

--deny-nix additionally denies runtime access to /nix and this checkout on macOS.
This is a restricted-host experiment, not a clean-host portability receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--runtime-python', type=Path, default=Path(sys.executable))
parser.add_argument('--params-dir', type=Path, default=Path.home()/'.cache/midnight/zk-params')
parser.add_argument('--deny-nix', action='store_true')
parser.add_argument('--recovery', action='store_true')
parser.add_argument('--require-nix-free', action='store_true', help='Refuse qualification when a Nix store or nix executable is present')
args = parser.parse_args()
if args.require_nix_free:
    assert not Path('/nix/store').exists() and shutil.which('nix') is None, 'a real Nix-free consumer environment is required'
archives = [p for p in args.directory.glob('midnight-zkir-forge-*.tar.gz') if not p.name.endswith('-runtime-sources.tar.gz')]
assert len(archives) == 1, 'one native candidate required'
archive = archives[0].resolve()
with tarfile.open(archive, 'r:gz') as tar:
    expected_manifest=archive.name.removesuffix('.tar.gz')+'/manifest.json'
    manifests = [entry for entry in tar if entry.name == expected_manifest]
    assert len(manifests) == 1 and manifests[0].isfile() and manifests[0].size < 1024**2
    manifest = json.load(tar.extractfile(manifests[0]))
with tempfile.TemporaryDirectory(prefix='forge-native-install-') as directory:
    temp = Path(directory).resolve()
    remote = temp/'remote'; remote.mkdir()
    for name in [archive.name, 'install-release.py', 'SHA256SUMS']:
        shutil.copyfile(args.directory/name, remote/name)
    runtime = args.runtime_python.resolve()
    if args.deny_nix:
        assert platform.system() == 'Darwin' and not str(runtime).startswith('/nix/')
    tools = temp/'tools'; tools.mkdir()
    metadata = {'tagName': manifest['tag'], 'isDraft': False, 'isPrerelease': False,
                'assets': [{'name': p.name, 'size': p.stat().st_size} for p in remote.iterdir()]}
    (temp/'metadata.json').write_text(json.dumps(metadata))
    gh = tools/'gh'
    gh.write_text('#!'+str(runtime)+'\n'+'''import json,pathlib,shutil,sys
root=pathlib.Path(__file__).resolve().parent.parent
args=sys.argv[1:]
if args[:2]==['release','view']:print((root/'metadata.json').read_text())
elif args[0]=='api':print(json.dumps({'sha':COMMIT}))
elif args[:2]==['release','download']:
 destination=pathlib.Path(args[args.index('--dir')+1])
 for name in ASSETS:shutil.copyfile(root/'remote'/name,destination/name)
else:sys.exit(2)
'''.replace('COMMIT', repr(manifest['source_commit'])).replace('ASSETS', repr([archive.name,'SHA256SUMS'])))
    gh.chmod(0o755)
    env = dict(os.environ, PATH=os.pathsep.join([str(tools),str(runtime.parent),'/opt/homebrew/bin','/usr/bin','/bin']))
    for variable in ('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER','MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER'):env.pop(variable,None)
    sandbox = []
    if args.deny_nix:
        policy = temp/'runtime.sb'
        policy.write_text('(version 1)\n(allow default)\n(deny file-read* (subpath "/nix"))\n'
                          '(deny file-read* (subpath '+json.dumps(str(ROOT))+'))\n')
        sandbox = ['/usr/bin/sandbox-exec','-f',str(policy)]
    def run(*command):
        result = subprocess.run([*sandbox,*map(str,command)],cwd=temp,env=env,
                                capture_output=True,text=True,timeout=600)
        assert result.returncode == 0, (result.stdout,result.stderr)
        return result.stdout
    prefix = temp/'prefix'
    installed = json.loads(run(runtime,remote/'install-release.py','--version',manifest['tag'],'--prefix',prefix))
    cli = prefix/'bin/midnight-zkir-forge'
    version = run(cli,'--version').strip()
    assert version in {name+' '+manifest['version'] for name in ('midnight-zkir-forge','zkir-forge')}
    primary = prefix/'bin/zkir-forge'
    if primary.exists():
        assert run(primary,'--version').strip() == version
        assert json.loads(run(primary,'profile')) == manifest['profiles']['root']
        cli = primary
    if any(entry['path']=='bin/zkir-forge' for entry in manifest['files']):
        assert primary.exists() and version == 'zkir-forge '+manifest['version']
    profiles = []
    selectors=['ledger8-v2','zkir3']+(['zkir31'] if 'v31' in manifest['profiles'] else [])
    for profile in selectors:
        result = json.loads(run(cli,'--cache-dir',temp/('cache-'+profile),'--params-dir',args.params_dir,'--profile',profile,'qualify'))
        profiles.append({'profile':profile,'qualification':result})
    run(prefix/'bin/midnight-zkir-forge-ci','--help')
    recovery=None
    if args.recovery:
        checks=temp/'checks';(checks/'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/check-recovery.py',checks/'scripts/check-recovery.py')
        shutil.copytree(ROOT/'fixtures',checks/'fixtures')
        command=[runtime,checks/'scripts/check-recovery.py','--binary',cli,'--params-dir',args.params_dir,'--real']
        if 'v31' in manifest['profiles']:command.append('--include-zkir31')
        recovery=json.loads(run(*command))
    print(json.dumps({'schema':1,'candidate_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),
                      'source_commit':manifest['source_commit'],'version':manifest['version'],
                      'target':manifest['target'],'fake_gh_install':True,'runtime_python_uses_nix':str(runtime).startswith('/nix/'),'runtime_denies_nix_and_checkout':args.deny_nix,'required_nix_free_environment':args.require_nix_free,
                      'profiles':profiles,'recovery':recovery,'scope':'real relocated native bundle and isolated prefix; host/environment facts recorded separately; fake GitHub transport, not a real release download'}))
