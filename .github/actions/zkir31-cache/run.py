#!/usr/bin/env python3
"""Thin phase orchestration. Forge's installed helper owns cache semantics."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(name):
    value = os.environ.get(name, '')
    require(value and not any(ord(c) < 32 for c in value), name + ' is required and must be one line')
    return value


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
            'regular bounded metadata file required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate metadata field')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def outputs(**values):
    with Path(text('GITHUB_OUTPUT')).open('a') as stream:
        for key, value in values.items():
            value = str(value)
            delimiter = 'FORGE_' + hashlib.sha256(value.encode()).hexdigest()
            require(delimiter not in value.splitlines(), 'output delimiter collision')
            stream.write(f'{key}<<{delimiter}\n{value}\n{delimiter}\n')


def require_platform():
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64',
            'this pilot Action supports native x86_64 Linux only')


def paths():
    require_platform()
    slot = text('FORGE_SLOT')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', slot), 'unsafe job slot')
    temp = Path(text('RUNNER_TEMP'))
    require(temp.is_absolute() and temp.is_dir(), 'absolute runner temporary directory required')
    root = temp / 'midnight-zkir-forge-action' / slot
    # The runner's temp path itself may be canonicalized by the runner. Never follow
    # a caller-created symlink in the Action-owned suffix.
    for path in (root.parent, root):
        require(not path.is_symlink(), 'Action state symlink refused')
    return root


def binary():
    path = Path(text('FORGE_BINARY'))
    require(path.is_absolute(), 'absolute installed Forge CLI path required')
    return path.resolve(strict=True)


def invoke(tool, *args):
    result = subprocess.run([str(tool), *map(str, args)], capture_output=True,
                            text=True, timeout=600)
    try:
        value = json.loads(result.stdout)
    except ValueError:
        raise ValueError('Forge CI helper did not return JSON') from None
    require(result.returncode == 0, 'Forge CI helper refused: ' + value.get('error', {}).get('message', 'request failed'))
    return value


def helper_for(cli):
    tool = cli.parent / 'midnight-zkir-forge-ci'
    require(tool.is_file(), 'matched installed Forge CI helper required beside CLI')
    return tool


def array(name):
    value = json.loads(text(name))
    require(isinstance(value, list) and 0 < len(value) <= 512
            and all(isinstance(item, str) and item for item in value), name + ' must be a nonempty JSON string array')
    return value


def state(root):
    value = read(root / 'state.json')
    require(value['schema'] == 1 and value['binary'] == str(binary()), 'Action binary/state changed')
    require(isinstance(value['max_bytes'], int) and 0 < value['max_bytes'] <= 1024**3,
            'invalid snapshot budget')
    require(re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+', value['trusted_ref']), 'invalid trusted ref')
    return value


def plan():
    phase = text('FORGE_PHASE')
    require(phase in ('restore', 'save'), 'phase must be restore or save')
    root = paths()
    cli = binary()
    if phase == 'save':
        state(root)
        return
    require(not os.path.lexists(root), 'slot already exists; choose a unique slot for each restore')
    budget = int(text('FORGE_MAX_BYTES'))
    require(0 < budget <= 1024**3, 'snapshot budget must be positive and at most 1 GiB')
    trusted_ref = text('FORGE_TRUSTED_REF')
    require(re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+', trusted_ref), 'explicit trusted branch ref required')
    workspace = Path(text('GITHUB_WORKSPACE')).resolve(strict=True)
    params = Path(text('FORGE_PARAMS_DIR'))
    require(params.is_absolute(), 'absolute verified parameter directory required')
    parameters, files = array('FORGE_PARAMETERS'), array('FORGE_WORKLOAD_FILES')
    generation = hashlib.sha256(json.dumps([text('GITHUB_RUN_ID'), text('GITHUB_RUN_ATTEMPT'),
                                           text('GITHUB_JOB'), os.environ.get('FORGE_JOB_INDEX', ''),
                                           text('FORGE_SLOT')]).encode()).hexdigest()[:32]
    root.mkdir(parents=True)
    tool = helper_for(cli)
    args = ['--binary', cli, 'key', '--workspace', workspace, '--params-dir', params,
            '--profile', 'zkir31', '--workload', text('FORGE_WORKLOAD'), '--generation', generation,
            '--output', root / 'key.json']
    for name in parameters:
        args += ['--parameter', name]
    for name in files:
        args += ['--input', name]
    key = invoke(tool, *args)
    write(root / 'state.json', {'schema': 1, 'binary': str(cli), 'max_bytes': budget,
                              'trusted_ref': trusted_ref, 'transport_started_ns': time.monotonic_ns()})
    outputs(cache_dir=root / 'store', snapshot=root / 'transport', primary=key['primary'],
            restore_keys='\n'.join(key['restore_keys']))


def restore():
    root = paths()
    config = state(root)
    key = read(root / 'key.json')
    matched = os.environ.get('FORGE_MATCHED_KEY', '')
    snapshot = root / 'transport'
    require(bool(matched) == os.path.lexists(snapshot), 'transport result and snapshot presence disagree')
    require(not matched or any(matched.startswith(prefix) for prefix in key['restore_keys']),
            'remote snapshot is outside the planned partition')
    tool = helper_for(binary())
    result = invoke(tool, '--binary', binary(), 'restore', '--key', root / 'key.json',
                    '--cache-dir', root / 'store', '--snapshot', snapshot,
                    '--max-bytes', config['max_bytes'])
    if result['restored']:
        snapshot.rename(root / 'restored-snapshot')
    invoke(tool, '--binary', binary(), 'baseline', '--key', root / 'key.json',
           '--cache-dir', root / 'store', '--output', root / 'baseline.json')
    write(root / 'restore.json', {'restored': result['restored'], 'matched_key': matched,
                                'restore_and_download_ms': (time.monotonic_ns() - config['transport_started_ns']) / 1e6})
    outputs(restored=str(result['restored']).lower())


def save():
    root = paths()
    config = state(root)
    require(text('FORGE_TESTS_PASSED') in ('true', 'false'), 'tests-passed must be true or false')
    require((root / 'baseline.json').is_file(), 'restore phase did not finish')
    tool = helper_for(binary())
    metrics = invoke(tool, '--binary', binary(), 'report', '--key', root / 'key.json',
                     '--cache-dir', root / 'store', '--baseline', root / 'baseline.json')
    if text('FORGE_JOB_STATUS') != 'success':
        result = {'publish': False, 'reason': 'prior_step_failed_or_cancelled'}
    else:
        tool = helper_for(binary())
        args = ['--binary', binary(), 'prepare-save', '--key', root / 'key.json',
                '--cache-dir', root / 'store', '--baseline', root / 'baseline.json',
                '--snapshot', root / 'transport', '--max-bytes', config['max_bytes'],
                '--trusted-ref', config['trusted_ref']]
        if text('FORGE_TESTS_PASSED') == 'true':
            args.append('--tests-passed')
        result = invoke(tool, *args)
    result.setdefault('report', metrics)
    write(root / 'save.json', result)
    outputs(publish=str(result['publish']).lower(), report_file=root / 'save.json',
            snapshot=root / 'transport', primary=read(root / 'key.json')['primary'])
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in ('plan', 'restore', 'save'), 'explicit phase command required')
        {'plan': plan, 'restore': restore, 'save': save}[sys.argv[1]]()
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'error': {'code': 'action_cache_refused', 'message': str(error)}}))
        sys.exit(1)
