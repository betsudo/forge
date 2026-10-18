#!/usr/bin/env python3
"""Opt-in local wrapper for an explicitly qualified Compact JSON3.1 tool cohort.

This is a Forge wrapper, not a new Compact flag. Qualification is source-specific;
new circuits/tools require a new independently checked and pinned receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    def fields(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'duplicate qualification field')
            out[key] = value
        return out
    with path.open('rb') as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    require(len(raw) <= 16 * 1024 * 1024, 'qualification too large')
    return json.loads(raw, object_pairs_hook=fields), hashlib.sha256(raw).hexdigest()


def safe_path(path):
    path = path.absolute()
    require(all(ord(c) >= 32 and c != "'" for c in str(path)), 'unsupported compiler path quoting')
    for item in [path, *path.parents]:
        require(not item.is_symlink(), 'symlink path refused')
    return path.resolve()


def keygen_timeout(value):
    require(type(value) is int and 1 <= value <= 86400,
            'keygen timeout must be an integer from 1 to 86400 seconds')
    return value


def timeout_argument(value):
    try:
        return keygen_timeout(int(value))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def command(args, *, timeout=180):
    environment = dict(os.environ)
    for key in ['MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER','MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER']:
        environment.pop(key, None)
    # Own a session so a timeout stops the backend worker as well as the CLI.
    with subprocess.Popen(list(map(str, args)), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, env=environment, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, args, stdout, stderr)
        return stdout


def policy(args):
    require(args.binary and args.params_dir and args.qualification and args.qualification_sha256,
            'local mode requires binary, params-dir and independently pinned qualification')
    q, digest = load(args.qualification)
    require(digest == args.qualification_sha256, 'qualification digest mismatch')
    require(q['schema'] == 1 and q['status'] == 'passed', 'successful qualification required')
    require(q['materialization'] and q['provider_checks']['lanes'], 'qualified sources and actual proofs required')
    for lane in q['provider_checks']['lanes']:
        proof = lane['proof_controls']
        require(all(proof.get(k) is True for k in ['valid_proof_verified', 'invalid_statement_rejected', 'corrupt_proof_rejected']),
                'qualification lacks genuine proof controls')
    paths = {'compactc.bin':args.compiler_dir/'compactc.bin', 'zkir-v3':args.compiler_dir/'zkir-v3',
             'forge':args.binary, 'worker':args.binary.parent/'midnight-zkir-forge-zkir31-worker'}
    for key, path in paths.items():
        require(path.is_file() and sha(path) == q['tool_sha256'][key], 'unqualified executable: '+key)
    require((args.compiler_dir/'zkir').is_file() and os.access(args.compiler_dir/'zkir', os.X_OK),
            'official compiler zkir presence probe unavailable')
    expected = q['materialization'][0]['descriptor']
    selected = json.loads(command([args.binary, '--profile', 'zkir31', 'profile']))
    require(selected['profile'] == expected['record']['profile'] and
            selected['worker'] == expected['record']['worker'], 'unqualified backend/worker')
    for row in q['materialization']:
        d = row['descriptor']
        require(d['materialized'] is True and d['input_version'] == {'major':3, 'minor':1} and
                d['input_format'] == 'midnight-zkir-v3.1-json' and
                d['record']['worker'] == expected['record']['worker'], 'unsupported qualified source/profile')
        parameter = args.params_dir/f"bls_midnight_2p{d['record']['k']}"
        require(parameter.is_file() and not parameter.is_symlink() and sha(parameter) == d['record']['parameter_digest'],
                'qualified parameter bytes required')
    return q


def materialize(config, argv):
    require(len(argv) == 3 and argv[0] == 'compile-many', 'unsupported cached keygen operation')
    timeout = keygen_timeout(config.get('keygen_timeout_seconds', 180))
    compiler = Path(config['compiler_dir'])
    args = argparse.Namespace(compiler_dir=compiler, binary=Path(config['binary']), params_dir=Path(config['params_dir']),
        qualification=Path(config['qualification']), qualification_sha256=config['qualification_sha256'])
    q = policy(args)  # recheck actual executable and parameter bytes at the hook
    source_dir, keys_dir = map(lambda v:safe_path(Path(v)), argv[1:])
    output = Path(config['output'])
    require(source_dir == output/'zkir' and keys_dir == output/'keys', 'unexpected compiler output boundary')
    require(source_dir.is_dir() and (not keys_dir.exists() or keys_dir.is_dir()), 'compiler output directories required')
    require(not (output/'compiler/contract-manifest.json').exists(), 'manifest already finalized before keygen')
    names = set()
    sources = sorted(source_dir.glob('*.zkir'))
    source_hashes = {source:sha(source) for source in sources if source.is_file()}
    for p in source_dir.glob('*.bzkir'):
        require(p.with_suffix('.zkir') in sources, 'binary-only stale input refused')
    plans = []
    for source in sources:
        safe_path(source)
        require(source.is_file(), 'regular current source required')
        name = source.stem
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name) and name not in names, 'invalid/duplicate circuit name')
        names.add(name)
        source_hash = sha(source)
        qualified = [r for r in q['materialization'] if r['descriptor']['record']['name'] == name and
                     r['official_artifact_sha256']['source'] == source_hash]
        require(len(qualified) == 1, 'current circuit bytes not independently qualified; use off or qualify first')
        row = qualified[0]
        prepared = json.loads(command([args.binary, '--profile','zkir31','--cache-dir',config['cache_dir'],
            '--params-dir',args.params_dir,'prepare',source,'--name',name], timeout=timeout))
        descriptor = prepared['descriptor']
        require(descriptor == row['descriptor'], 'generation descriptor differs from qualification')
        inventory = prepared['export']['files']
        require(len(inventory) == 4 and {f['kind'] for f in inventory} == {'source','binary_ir','prover','verifier'},
                'incomplete export inventory')
        destinations = {'source':source, 'binary_ir':source.with_suffix('.bzkir'),
            'prover':keys_dir/(name+'.prover'), 'verifier':keys_dir/(name+'.verifier')}
        for entry in inventory:
            exported = Path(entry['path'])
            require(exported.is_file() and not exported.is_symlink(), 'unsafe exported file')
            require(sha(exported) == entry['sha256'] == row['official_artifact_sha256'][entry['kind']] and
                    exported.stat().st_size == entry['bytes'], 'artifact bytes differ from qualification')
            destination = destinations[entry['kind']]
            safe_path(destination)
            require(destination.resolve() != exported.resolve(), 'output aliases export')
            if entry['kind'] != 'source':
                plans.append((exported, destination, entry['sha256']))
        require(sha(source) == source_hash, 'source changed during preparation')
    # Stage ALL private output copies before any publication. Per-file replacement
    # is atomic; compiler failure prevents a new completed manifest on errors.
    with tempfile.TemporaryDirectory(prefix='.forge-keygen-', dir=output.parent) as directory:
        staging = Path(directory)
        require(staging.stat().st_dev == output.stat().st_dev, 'staging/output filesystem mismatch')
        keys_dir.mkdir(exist_ok=True)
        staged = []
        for i, (exported, target, expected) in enumerate(plans):
            p = staging/str(i)
            shutil.copyfile(exported, p)
            require(sha(p) == expected, 'export changed during staging')
            staged.append((p, target))
        require(sorted(source_dir.glob('*.zkir')) == sources, 'source inventory changed before publication')
        for source in sources:
            safe_path(source)
            require(source.is_file() and sha(source) == source_hashes[source],
                    'source changed before publication')
        for p, target in staged:
            safe_path(target)
            os.replace(p, target)


def main():
    try:
        if len(sys.argv) > 2 and sys.argv[1] == '--keygen-hook':
            config, _ = load(Path(sys.argv[2]))
            materialize(config, sys.argv[3:])
            if config.get('completed'): Path(config['completed']).write_text('completed')
            return 0
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--mode', choices=['off','local'], default='off')
        parser.add_argument('--compiler-dir', required=True, type=Path)
        parser.add_argument('--binary', type=Path)
        parser.add_argument('--qualification', type=Path)
        parser.add_argument('--qualification-sha256')
        parser.add_argument('--params-dir', type=Path)
        parser.add_argument('--cache-dir', type=Path)
        parser.add_argument('--keygen-timeout-seconds', type=timeout_argument, default=180,
                            help='per-prepare local deadline, 1..86400 seconds (default: 180)')
        parser.add_argument('source', type=Path)
        parser.add_argument('output', type=Path)
        args = parser.parse_args()
        args.compiler_dir = safe_path(args.compiler_dir)
        require(':' not in str(args.compiler_dir), 'compiler path cannot contain PATH separator')
        source, output = safe_path(args.source), safe_path(args.output)
        require(source.is_file() and not source.is_relative_to(output), 'source/output alias refused')
        environment = dict(os.environ)
        environment['PATH'] = str(args.compiler_dir)+os.pathsep+environment.get('PATH','')
        if args.params_dir:
            args.params_dir = safe_path(args.params_dir)
            environment['MIDNIGHT_PP'] = str(args.params_dir)
        invocation = [str(args.compiler_dir/'compactc.bin'), '--feature-zkir-v3', str(source), str(output)]
        if args.mode == 'off':
            return subprocess.run(invocation, env=environment).returncode
        args.binary = args.binary.absolute() if args.binary else None  # retain matched sibling worker links
        if output.exists():
            require(output.stat().st_dev == output.parent.stat().st_dev, 'output mountpoint cannot use sibling staging')
        policy(args)  # preflight before the compiler deletes/recreates output
        for protected in [args.compiler_dir, args.params_dir, args.qualification.resolve(), args.binary.resolve(),
                          (args.binary.parent/'midnight-zkir-forge-zkir31-worker').resolve()]:
            require(not protected.is_relative_to(output) and not output.is_relative_to(protected),
                    'compiler output overlaps qualified input')
        cache = safe_path(args.cache_dir or Path(os.environ.get('MIDNIGHT_ZKIR_FORGE_DIR') or str(Path.home()/'.midnight-zkir-forge')))
        require(not cache.is_relative_to(output) and not output.is_relative_to(cache), 'cache/output overlap refused')
        # Explicit CLI worker settings must win over inherited test overrides.
        for key in ['MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER','MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER']:
            environment.pop(key, None)
        with tempfile.TemporaryDirectory(prefix='forge-compiler-hook-') as directory:
            root = Path(directory)
            config = root/'config.json'
            config.write_text(json.dumps(dict(compiler_dir=str(args.compiler_dir), binary=str(args.binary),
                params_dir=str(args.params_dir), qualification=str(args.qualification.resolve()),
                qualification_sha256=args.qualification_sha256, output=str(output), cache_dir=str(cache),
                completed=str(root/'completed'), keygen_timeout_seconds=args.keygen_timeout_seconds)))
            shim = root/'zkir-v3'
            shim.write_text('#!/bin/sh\nexec '+shlex.join([sys.executable,str(Path(__file__).resolve()),'--keygen-hook',str(config)])+' "$@"\n')
            shim.chmod(0o700)
            environment['PATH'] = str(root)+os.pathsep+environment['PATH']
            status = subprocess.run(invocation, env=environment).returncode
            if status: return status
            require((root/'completed').is_file(), 'compiler did not complete cached keygen hook')
            require((output/'compiler/contract-manifest.json').is_file(), 'compiler did not emit final integrity manifest')
            return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError, CompilerInterrupted) as error:
        print('Forge compiler wrapper refused: '+str(error), file=sys.stderr)
        return 1


class CompilerInterrupted(Exception):
    pass


def interrupted(_signal, _frame):
    # Allow a supervising qualifier to stop the hook's separately owned Forge
    # process group before terminating the surrounding compiler group.
    raise CompilerInterrupted('compiler wrapper interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
