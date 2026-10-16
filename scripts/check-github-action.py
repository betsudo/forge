#!/usr/bin/env python3
"""Action phase/trust regressions; --real uses actual installed JSON3.1 keys/proofs.

The local phase tests deliberately bypass only the Action's platform preflight on
non-Linux developer hosts. They do not qualify native x86_64 portability.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('forge_action', ROOT/'.github/actions/zkir31-cache/run.py')
action = importlib.util.module_from_spec(spec)
spec.loader.exec_module(action)


def refuses(command, message):
    try:
        command()
    except (ValueError, OSError) as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError('expected refusal: '+message)


def command(*args):
    result = subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


def phase(name):
    with contextlib.redirect_stdout(io.StringIO()):
        getattr(action, name)()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--params-dir', type=Path, default=Path.home()/'.cache/midnight/zk-params')
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()
    controls = []
    with patch.dict(os.environ, {'FORGE_PHASE': 'unknown'}):
        refuses(action.plan, 'phase must be')
    with patch.object(action.platform, 'system', return_value='Darwin'):
        refuses(action.require_platform, 'x86_64 Linux')
    with patch.object(action.platform, 'system', return_value='Linux'), patch.object(action.platform, 'machine', return_value='aarch64'):
        refuses(action.require_platform, 'x86_64 Linux')
    with tempfile.TemporaryDirectory(prefix='forge-action-e2e-') as directory:
        temp = Path(directory).resolve()
        environment = {**os.environ, 'RUNNER_TEMP': str(temp), 'GITHUB_OUTPUT': str(temp/'outputs'),
            'FORGE_SLOT': 'default', 'FORGE_PHASE': 'restore', 'FORGE_MAX_BYTES': '10485760',
            'FORGE_TRUSTED_REF': 'refs/heads/main', 'GITHUB_WORKSPACE': str(temp),
            'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': 'proof-test',
            'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main',
            'FORGE_PARAMETERS': '["bls_midnight_2p4"]', 'FORGE_WORKLOAD_FILES': '["circuit.zkir"]',
            'FORGE_WORKLOAD': 'actual assert fixture; JSON3.1', 'FORGE_TESTS_PASSED': 'true',
            'FORGE_JOB_STATUS': 'success', 'FORGE_MATCHED_KEY': ''}
        with patch.dict(os.environ, environment, clear=True), patch.object(action, 'require_platform', lambda: None):
            for slot in ['../escape', '/tmp/elsewhere', 'one\ntwo']:
                os.environ['FORGE_SLOT'] = slot
                refuses(action.paths, 'slot' if '\n' not in slot else 'one line')
            os.environ['FORGE_SLOT'] = 'default'
            (temp/'midnight-zkir-forge-action').symlink_to(temp/'other')
            refuses(action.paths, 'symlink')
            (temp/'midnight-zkir-forge-action').unlink()
            os.environ['FORGE_PARAMETERS'] = '[1]'
            refuses(lambda: action.array('FORGE_PARAMETERS'), 'JSON string array')
            os.environ['FORGE_PARAMETERS'] = '["bls_midnight_2p4"]'
            controls += ['unsupported-platform', 'unsafe-slot', 'state-symlink', 'input-array']
            proofs = []
            if args.real:
                assert args.binary, '--binary required with --real'
                cli = args.binary.resolve(strict=True)
                params = args.params_dir.resolve(strict=True)
                os.environ['FORGE_BINARY'] = str(cli)
                os.environ['FORGE_PARAMS_DIR'] = str(params)
                (temp/'circuit.zkir').write_bytes((ROOT/'fixtures/assert-v31.zkir').read_bytes())
                worker = cli.parent/'midnight-zkir-forge-zkir31-worker'
                def new_slot(slot):
                    os.environ['FORGE_SLOT'] = slot
                    os.environ['FORGE_PHASE'] = 'restore'
                    os.environ['FORGE_MATCHED_KEY'] = ''
                    phase('plan')
                    return action.paths()
                def prepare(root):
                    result = command(cli, '--cache-dir', root/'store', '--params-dir', params,
                                     '--profile', 'zkir31', 'prepare', temp/'circuit.zkir', '--name', 'proof')
                    proof = command(worker, 'qualify-export', '--output', result['export']['base'],
                                    '--circuit-name', 'proof', '--params-dir', params)
                    assert all(proof[key] for key in ('valid_proof_verified', 'invalid_statement_rejected', 'corrupt_proof_rejected'))
                    proofs.append(proof)
                    return result
                cold = new_slot('cold')
                refuses(action.plan, 'slot already exists')
                phase('restore')
                first = prepare(cold)
                assert not first['cache']['hit']
                phase('save')
                assert action.read(cold/'save.json')['publish']
                seed = cold/'transport'
                seed_key = action.read(cold/'key.json')['primary']
                warm = new_slot('warm')
                shutil.copytree(seed, warm/'transport')
                os.environ['FORGE_MATCHED_KEY'] = seed_key
                phase('restore')
                second = prepare(warm)
                assert second['cache']['hit'] and second['artifact_set_id'] == first['artifact_set_id']
                assert action.read(warm/'restore.json')['restored']
                phase('save')
                saved = action.read(warm/'save.json')
                assert not saved['publish'] and saved['reason'] == 'no_generation_misses'
                assert saved['report']['delta']['hits'] == 1 and saved['report']['delta']['misses'] == 0
                for slot, event, ref, passed, status, reason in [
                    ('pull-request', 'pull_request', 'refs/pull/1/merge', 'true', 'success', 'untrusted_event_or_ref'),
                    ('wrong-branch', 'push', 'refs/heads/other', 'true', 'success', 'untrusted_event_or_ref'),
                    ('failed-tests', 'push', 'refs/heads/main', 'false', 'success', 'tests_not_confirmed'),
                    ('failed-step', 'push', 'refs/heads/main', 'true', 'failure', 'prior_step_failed_or_cancelled'),
                    ('cancelled-step', 'push', 'refs/heads/main', 'true', 'cancelled', 'prior_step_failed_or_cancelled')]:
                    root = new_slot(slot)
                    phase('restore')
                    os.environ.update(GITHUB_EVENT_NAME=event, GITHUB_REF=ref,
                                      FORGE_TESTS_PASSED=passed, FORGE_JOB_STATUS=status)
                    phase('save')
                    assert action.read(root/'save.json')['reason'] == reason
                    assert not (root/'transport').exists()
                    controls.append(slot)
                os.environ.update(GITHUB_EVENT_NAME='push', GITHUB_REF='refs/heads/main',
                                  FORGE_TESTS_PASSED='true', FORGE_JOB_STATUS='success')
                bad = new_slot('corrupt')
                shutil.copytree(seed, bad/'transport')
                (bad/'transport/snapshot.json').write_text('{}')
                os.environ['FORGE_MATCHED_KEY'] = seed_key
                refuses(action.restore, 'Forge CI helper refused')
                assert not (bad/'store').exists()
                wrong = new_slot('wrong-partition')
                shutil.copytree(seed, wrong/'transport')
                os.environ['FORGE_MATCHED_KEY'] = 'forge-v1-'+'0'*64+'-invalid'
                refuses(action.restore, 'outside the planned partition')
                assert not (wrong/'store').exists()
                changed = new_slot('changed-input')
                (temp/'circuit.zkir').write_text((temp/'circuit.zkir').read_text()+'\n')
                refuses(action.restore, 'workload inputs changed')
                assert not (changed/'store').exists()
                controls += ['reused-slot', 'corrupt-present-snapshot', 'wrong-partition', 'changed-workload']
    print(json.dumps({'schema': 1, 'controls': controls, 'real_proofs': proofs if args.real else [],
        'scope': 'local Action orchestration; platform gate bypassed only in test harness; no remote transfer/native portability claim'}))


if __name__ == '__main__':
    main()
