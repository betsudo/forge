#!/usr/bin/env python3
"""Stage pinned public inputs; never executes downloaded compiler binaries."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, path, digest, limit):
    if not url.startswith('https://'):
        raise ValueError('HTTPS input required')
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, path.open('xb') as stream:
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS redirect required')
        size = 0
        while chunk := response.read(128*1024):
            size += len(chunk)
            if size > limit:
                raise ValueError('download limit exceeded')
            stream.write(chunk)
    if sha(path) != digest:
        raise ValueError('download digest mismatch: '+str(path))


def extract(archive, destination):
    with tarfile.open(archive) as tar:
        size = 0
        seen = set()
        for index, member in enumerate(tar):
            path = PurePosixPath(member.name)
            if index >= 2048 or path.is_absolute() or '..' in path.parts or '\\' in member.name:
                raise ValueError('unsafe compiler archive path/count')
            if member.isdir():
                continue
            if not member.isfile() or member.name in seen:
                raise ValueError('compiler archive links/duplicates/special files refused')
            seen.add(member.name)
            size += member.size
            if size > 2*1024**3:
                raise ValueError('compiler archive size limit')
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('compiler-archive','binary','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--compiler-sha256', required=True)
    parser.add_argument('--params-base-url', required=True)
    parser.add_argument('--compiler-subdir', default='.')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.compiler_sha256) or sha(args.compiler_archive) != args.compiler_sha256:
        raise ValueError('independently verified official compiler archive digest required')
    if args.output.exists():
        raise ValueError('fresh staging directory required')
    subdir = PurePosixPath(args.compiler_subdir)
    if subdir.is_absolute() or '..' in subdir.parts:
        raise ValueError('unsafe compiler subdirectory')
    args.output.mkdir(parents=True)
    compiler_root = args.output/'compiler-archive'
    extract(args.compiler_archive, compiler_root)
    compiler = compiler_root.joinpath(*subdir.parts)
    pinned = json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
    closure = json.loads((ROOT/'docs/evidence/passport-full-models-local.json').read_text())['source_closure']
    source_files = dict(pinned['files'])
    source_files.update({name:entry['sha256'] for name, entry in closure['files'].items()})
    for name, digest in source_files.items():
        fetch('https://raw.githubusercontent.com/midnightntwrk/passport/'+pinned['commit']+'/'+name,
              args.output/'source'/name, digest, 4*1024**2)
    policy = json.loads((ROOT/'docs/evidence/passport-adapter-qualification-local.json').read_text())
    parameters = {f"bls_midnight_2p{r['descriptor']['record']['k']}":r['descriptor']['record']['parameter_digest']
                  for r in policy['materialization']}
    for name, digest in parameters.items():
        fetch(args.params_base_url.rstrip('/')+'/'+name, args.output/'params'/name, digest, 512*1024**2)
    tools = {'compactc.bin':compiler/'compactc.bin','zkir-v3':compiler/'zkir-v3','zkir':compiler/'zkir',
             'forge':args.binary,'worker':args.binary.parent/'midnight-zkir-forge-zkir31-worker',
             'helper':args.binary.parent/'midnight-zkir-forge-ci',
             'helper_payload':args.binary.parent.parent/'share/midnight-zkir-forge/forge-ci.py'}
    cohort = {'schema':1,'platform':'x86_64-linux','tool_sha256':{name:sha(path) for name,path in tools.items()},
        'parameters':parameters,'sdk_lock_sha256':sha(ROOT/'integration/providers/package-lock.json'),
        'compiler_archive_sha256':args.compiler_sha256,'consumer_commit':pinned['commit']}
    output = args.output/'cohort.json'
    output.write_text(json.dumps(cohort,indent=2)+'\n')
    print(json.dumps({'cohort':str(output.absolute()),'cohort_sha256':sha(output),'compiler_dir':str(compiler.absolute())}))


if __name__ == '__main__':
    main()
