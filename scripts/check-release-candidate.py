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
args = parser.parse_args()
archives = list(args.directory.glob('midnight-zkir-forge-*.tar.gz'))
assert len(archives) == 1, 'one native candidate required'
archive = archives[0].resolve()
with tarfile.open(archive, 'r:gz') as tar:
    manifests = [entry for entry in tar if entry.name.endswith('/manifest.json')]
    assert len(manifests) == 1 and manifests[0].size < 1024**2
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
    env.pop('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER', None)
    sandbox = []
    if args.deny_nix:
        policy = temp/'runtime.sb'
        policy.write_text('(version 1)\n(allow default)\n(deny file-read* (subpath "/nix"))\n'
                          '(deny file-read* (subpath '+json.dumps(str(ROOT))+'))\n')
        sandbox = ['/usr/bin/sandbox-exec','-f',str(policy)]
    def run(*command):
        result = subprocess.run([*sandbox,*map(str,command)],cwd=temp,env=env,
                                capture_output=True,text=True,timeout=180)
        assert result.returncode == 0, (result.stdout,result.stderr)
        return result.stdout
    prefix = temp/'prefix'
    installed = json.loads(run(runtime,remote/'install-release.py','--version',manifest['tag'],'--prefix',prefix))
    cli = prefix/'bin/midnight-zkir-forge'
    assert run(cli,'--version').strip() == 'midnight-zkir-forge '+manifest['version']
    profiles = []
    for profile in ['ledger8-v2','zkir3']:
        result = json.loads(run(cli,'--cache-dir',temp/('cache-'+profile),'--params-dir',args.params_dir,'--profile',profile,'qualify'))
        profiles.append({'profile':profile,'qualification':result})
    run(prefix/'bin/midnight-zkir-forge-ci','--help')
    print(json.dumps({'schema':1,'candidate_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),
                      'source_commit':manifest['source_commit'],'version':manifest['version'],
                      'target':manifest['target'],'fake_gh_install':True,'runtime_python_uses_nix':str(runtime).startswith('/nix/'),'runtime_denies_nix_and_checkout':args.deny_nix,
                      'profiles':profiles,'scope':'real relocated native bundle and isolated prefix; Python origin reported separately; not a clean-host, Linux or real GitHub download qualification'}))
