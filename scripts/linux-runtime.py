"""Relocate a Nix Linux runtime without requiring a consumer Nix store.

Public commands stay Python launchers (Python is already an installer requirement).
They execute the bundled ELF loader directly; a relative ELF PT_INTERP is not
supported by Linux. Every runtime byte is hashed before execution, including the
worker launcher identity, so libraries cannot silently change a cache recipe.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess


def output(*args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True,
                          text=True).stdout


def relocate(root, patchelf, names=('midnight-zkir-forge', 'midnight-zkir-forge-zkir3-worker')):
    root = pathlib.Path(root)
    runtime = root / 'lib'
    runtime.mkdir()
    names = tuple(names)
    libraries = {}
    loaders = set()
    for name in names:
        executable = root / 'bin' / name
        interpreter = output(patchelf, '--print-interpreter', executable).strip()
        loaders.add(interpreter)
        for line in output(interpreter, '--inhibit-cache', '--list', executable).splitlines():
            match = re.search(r'(?:=>\s*)?(/[^\s]+)\s+\(', line)
            if match:
                source = pathlib.Path(match[1])
                if not str(source).startswith('/nix/store/'):
                    raise RuntimeError('unexpected non-Nix producer runtime dependency')
                previous = libraries.setdefault(source.name, source)
                if previous.read_bytes() != source.read_bytes():
                    raise RuntimeError('conflicting Linux runtime library basenames')
        executable.rename(runtime / name)
    if len(loaders) != 1:
        raise RuntimeError('CLI and worker require different ELF loaders')
    loader = pathlib.Path(loaders.pop())
    libraries[loader.name] = loader
    for name, source in sorted(libraries.items()):
        shutil.copyfile(source, runtime / name)
        (runtime / name).chmod(0o755)
    for path in runtime.iterdir():
        if path.name == loader.name:
            continue
        output(patchelf, '--remove-rpath', path)
        if path.name in names:
            # Valid conventional interpreter for inspection; launchers explicitly
            # invoke our bundled loader, so the host need not provide this path.
            interpreter = ('/lib/ld-linux-aarch64.so.1' if 'aarch64' in loader.name
                           else '/lib64/ld-linux-x86-64.so.2')
            output(patchelf, '--set-interpreter', interpreter, path)
        if any('/' in name for name in output(patchelf, '--print-needed', path).splitlines()):
            raise RuntimeError('runtime contains an absolute ELF dependency')
    for name in names:
        report = output(runtime / loader.name, '--inhibit-cache', '--library-path', runtime,
                        '--list', runtime / name)
        if '/nix/store/' in report:
            raise RuntimeError('relocated runtime still resolves a Nix dependency')
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(runtime.iterdir())}
    origins = {name: {'source_path': str(path),
                      'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'relocated_sha256': hashes[name]}
               for name, path in sorted(libraries.items())}
    licenses = root / 'LICENSES'
    licenses.mkdir(exist_ok=True)
    (licenses / 'linux-runtime-origin.json').write_text(json.dumps(origins, indent=2) + '\n')
    # Embed the complete runtime commitment in both launchers. The worker
    # executable SHA-256 therefore commits to its ELF and loader/library closure.
    # No separate mutable manifest can weaken the existing worker identity.
    for name in names:
        launcher = root / 'bin' / name
        launcher.write_text('''#!/usr/bin/env python3
import hashlib,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
if any(name.startswith('LD_') or name=='GLIBC_TUNABLES' for name in os.environ):
    raise SystemExit('Forge bundled Linux runtime refuses loader override variables')
expected=''' + repr(hashes) + '''
for name,digest in expected.items():
    path=root/'lib'/name
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise SystemExit('Forge bundled Linux runtime integrity failure')
if 'SSL_CERT_FILE' not in os.environ:
    for certificate in ('/etc/ssl/certs/ca-certificates.crt','/etc/pki/tls/certs/ca-bundle.crt'):
        if Path(certificate).is_file():
            os.environ['SSL_CERT_FILE']=certificate
            break
''' + (''.join("os.environ.setdefault(" + repr(variable) + ",str(root/'bin'/" + repr(worker) + "))\n"
               for worker, variable in (
                   ('midnight-zkir-forge-zkir3-worker', 'MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER'),
                   ('midnight-zkir-forge-zkir31-worker', 'MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER'))
               if worker in names) if name == names[0] else '') + '''loader=root/'lib'/''' + repr(loader.name) + '''
os.execv(str(loader),[str(loader),'--inhibit-cache','--library-path',str(root/'lib'),str(root/'lib'/''' + repr(name) + '''),*sys.argv[1:]])
''')
        launcher.chmod(0o755)
    return {'loader': loader.name, 'libraries': sorted(libraries),
            'runtime_sha256': hashes,
            'launcher': 'Python 3.11+, bundled ELF loader, verified runtime closure'}
