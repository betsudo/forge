#!/usr/bin/env python3
"""Native Linux Passport qualification, not a cross-emulated performance test."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('passport', ROOT/'scripts/qualify-passport-local.py')
passport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(passport)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def native_host():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64',
            'native x86_64 Linux required; macOS/ARM/emulation does not qualify')
    require(os.environ.get('RUNNER_ARCH', 'X64') == 'X64', 'native X64 runner required')
    # This runner must execute directly on the native host, not a Docker platform
    # override. Cross-emulation is deliberately not an available invocation mode.
    require(not Path('/.dockerenv').exists(), 'run on the native host, outside Docker')
    return {'system':platform.system(), 'machine':platform.machine(), 'kernel':platform.release(),
            'runner_image':os.environ.get('ImageOS'), 'runner_image_version':os.environ.get('ImageVersion')}


def executable(path):
    require(path.is_file(),
            'executable missing: '+str(path))
    require(os.access(path, os.X_OK), 'executable permission required: '+str(path))
    # A native cohort must contain x86_64 ELF tools (not shell launchers or ARM).
    with path.open('rb') as stream:
        header = stream.read(20)
    require(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00',
            'native x86_64 ELF required: '+str(path))


def preflight(args):
    host = native_host()  # before input reads, scratch creation and subprocesses
    raw = args.cohort.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == args.cohort_sha256, 'independent cohort digest mismatch')
    cohort = json.loads(raw)
    require(cohort['schema'] == 1 and cohort['platform'] == 'x86_64-linux', 'Linux cohort required')
    require(cohort['sdk_lock_sha256'] == passport.sha(ROOT/'integration/providers/package-lock.json'),
            'SDK dependency lock changed')
    tools = {'compactc.bin':args.compiler_dir/'compactc.bin', 'zkir-v3':args.compiler_dir/'zkir-v3',
             'zkir':args.compiler_dir/'zkir', 'forge':args.binary,
             'worker':args.binary.parent/'midnight-zkir-forge-zkir31-worker',
             'helper':args.binary.parent/'midnight-zkir-forge-ci',
             'helper_payload':args.binary.parent.parent/'share/midnight-zkir-forge/forge-ci.py'}
    for name, path in tools.items():
        # The official presence probe and Nix CLI may be shell launchers; record
        # their bytes too, but the actual compiler and worker must be native ELF.
        if name in ('compactc.bin', 'zkir-v3', 'worker'):
            executable(path)
        require(name == 'helper_payload' or os.access(path, os.X_OK), 'executable permission required: '+name)
        require(passport.sha(path) == cohort['tool_sha256'][name], 'changed executable: '+name)
    reference = json.loads((ROOT/'docs/evidence/passport-full-models-local.json').read_text())['source_closure']
    for name, entry in reference['files'].items():
        data = (args.source/name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'changed source closure: '+name)
        require(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == entry['git_blob'],
                'source Git blob mismatch: '+name)
    expected = json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
    for name, digest in expected['files'].items():
        require(passport.sha(args.source/name) == digest, 'changed consumer input: '+name)
    # Parameter identities are portable bytes; obtain them from the independently
    # qualified artifact descriptors, never from caller-selected filename hashes.
    policy = json.loads((ROOT/'docs/evidence/passport-adapter-qualification-local.json').read_text())
    parameters = {f"bls_midnight_2p{r['descriptor']['record']['k']}":r['descriptor']['record']['parameter_digest']
                  for r in policy['materialization']}
    require(cohort['parameters'] == parameters, 'parameter inventory mismatch')
    for name, digest in parameters.items():
        path = args.params_dir/name
        require(not path.is_symlink() and passport.sha(path) == digest, 'changed parameter: '+name)
    work = args.work.resolve()
    work.relative_to(ROOT/'.local')
    require(work != ROOT/'.local' and not work.exists(), 'fresh owned scratch required')
    policy = args.output.with_name('passport-adapter-qualification-linux.json')
    require(args.output != policy and not args.output.exists() and not policy.exists(),
            'distinct fresh result and qualification policy paths required')
    for protected in [args.source, args.compiler_dir, args.params_dir, args.binary.resolve(), args.cohort, args.output]:
        require(not protected.resolve().is_relative_to(work), 'scratch overlaps input/receipt')
    require(shutil.disk_usage(ROOT).free >= 50*1024**3, 'at least 50 GiB scratch headroom required')
    return host, cohort, reference


def command(argv, log, timeout=7200):
    started = time.monotonic()
    with log.open('x') as stream, subprocess.Popen(list(map(str, argv)), stdout=stream,
            stderr=subprocess.STDOUT, start_new_session=True) as process:
        try:
            status = process.wait(timeout=timeout)
        except BaseException:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
            raise
    require(status == 0, 'command failed; retained log: '+str(log))
    return {'returncode':status, 'wall_ms':(time.monotonic()-started)*1000, 'command':list(map(str, argv))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','compiler-dir','params-dir','source','work','output','cohort'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--cohort-sha256', required=True)
    args = parser.parse_args()
    for name in ('binary','compiler_dir','params_dir','source','work','output','cohort'):
        setattr(args, name, getattr(args, name).absolute())
    host, cohort, closure = preflight(args)
    args.work.mkdir(parents=True)
    # Failed runs intentionally retain their bounded owned scratch/logs for
    # diagnosis. Only the existing successful qualifier removes its own lanes.
    (args.work/'source-inventory.json').write_text(json.dumps(closure, indent=2)+'\n')
    command(['npm','ci','--ignore-scripts','--prefix',ROOT/'integration/providers'], args.work/'npm-ci.log', 600)
    args.baseline = args.work/'native-off'
    start = {'measurement':'monotonic wall time around official/off process including descendants'}
    (args.work/'native-off-start.json').write_text(json.dumps(start)+'\n')
    result = command([sys.executable,ROOT/'scripts/compiler-local.py','--mode','off',
        '--compiler-dir',args.compiler_dir,'--params-dir',args.params_dir,
        args.source/'contract/contracts/account.compact',args.baseline],args.work/'native-off.log')
    (args.work/'native-off-result.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.work/'native-host.json').write_text(json.dumps(host,indent=2)+'\n')
    args.qualification_host = host
    args.cohort = cohort
    args.platform_scope = 'Native Linux x86_64'
    args.qualification_name = 'passport-adapter-qualification-linux.json'
    # The existing independent comparison creates the new per-platform policy
    # only after official artifact parity and actual SDK proof controls.
    passport.qualify(args)
    return 0


def interrupted(_signal, _frame):
    raise RuntimeError('Linux qualification interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM,interrupted)
    try: sys.exit(main())
    except (ValueError, AssertionError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('Linux Passport qualification refused: '+str(error), file=sys.stderr)
        sys.exit(1)
