#!/usr/bin/env python3
"""Private-store real-process failure recovery; --real requires verified k4 parameters."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=Path, required=True)
parser.add_argument('--real', action='store_true')
parser.add_argument('--params-dir', type=Path, default=Path(os.environ.get(
    'MIDNIGHT_PP', str(Path.home() / '.cache/midnight/zk-params'))))
args = parser.parse_args()
binary = args.binary.resolve()


def invoke(command, success=True, cwd=None):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=120, cwd=cwd)
    assert (result.returncode == 0) == success, (result.returncode, result.stdout, result.stderr)
    value = json.loads(result.stdout)
    if not success: value['_stderr'] = result.stderr
    return value


def cli(store, *command, success=True):
    return invoke([binary, '--cache-dir', store, *command], success)


def accounting_fault(store, enabled, table="requests"):
    with sqlite3.connect(store / 'index.sqlite3') as db:
        if enabled:
            db.execute(f"CREATE TRIGGER fail_metrics BEFORE INSERT ON {table} BEGIN "
                       "SELECT RAISE(FAIL,'injected accounting failure'); END")
        else:
            db.execute('DROP TRIGGER fail_metrics')


with tempfile.TemporaryDirectory(prefix='forge-recovery-') as directory:
    temp = Path(directory).resolve()
    store = temp / 'fast'
    registered = cli(store, 'import', ROOT / 'fixtures/assert.zkir')
    bundle = registered['bundle_id']
    accounting_fault(store, True)
    error = cli(store, 'ensure', '0' * 64, success=False)['_stderr']
    assert 'bundle not registered' in error and 'injected accounting failure' in error
    assert not cli(store, 'inspect', bundle)['ready']
    accounting_fault(store, False)
    assert cli(store, 'stats')['totals']['requests'] == 0
    # After the accounting fault is removed, the primary error is still actionable.
    error = cli(store, 'ensure', '0' * 64, success=False)['_stderr']
    assert 'bundle not registered' in error and 'injected accounting failure' not in error
    assert cli(store, 'stats')['totals']['errors'] == 1

    profiles = []
    if args.real:
        for selector, fixture in [('ledger8-v2', 'assert.zkir'), ('zkir3', 'assert-v3.zkir')]:
            store = temp / selector
            bundle = cli(store, '--profile', selector, 'import', ROOT / 'fixtures' / fixture,
                         '--name', 'proof')['bundle_id']
            ensure = ['--profile', selector, '--params-dir', args.params_dir, 'ensure', bundle]
            # Missing parameters and a failed accounting write must preserve both diagnostics.
            accounting_fault(store, True)
            error = cli(store, '--params-dir', temp / 'missing-params', 'ensure', bundle,
                        success=False)['_stderr']
            assert 'injected accounting failure' in error and 'parameter' in error.lower()
            assert not cli(store, 'inspect', bundle)['ready']
            # Inject successful-generation accounting failure: metadata must roll back.
            error = cli(store, *ensure, success=False)['_stderr']
            assert 'injected accounting failure' in error
            assert not cli(store, 'inspect', bundle)['ready']
            assert cli(store, 'stats')['totals']['requests'] == 0
            accounting_fault(store, False)
            cold = cli(store, *ensure)
            assert not cold['cache']['hit']
            identity = cold['artifact_set_id']
            relative = selector + '-relative-export'
            exported = invoke([binary, '--cache-dir', store, 'export', bundle,
                               '--output', relative], cwd=temp)
            assert Path(exported['export']['base']) == temp / relative
            before = cli(store, 'stats')['totals']
            accounting_fault(store, True, 'file_requests')
            cli(store, 'resolve', bundle, success=False)
            assert cli(store, 'stats')['totals'] == before  # No partially inserted request.
            accounting_fault(store, False)
            cli(store, 'resolve', bundle)
            cli(store, 'evict', bundle)
            # An export obstacle is explicit, then correctable by its owner.
            obstacle = temp / (selector + '-output')
            obstacle.write_text('owner file; preserve me')
            cli(store, *ensure, '--output', obstacle, success=False)
            assert obstacle.read_text() == 'owner file; preserve me'
            assert not cli(store, 'inspect', bundle)['ready']
            obstacle.unlink()
            retry = cli(store, *ensure)
            assert retry['artifact_set_id'] == identity
            # Kill exactly after a new export is durable but SQLite COMMIT is reader-blocked.
            cli(store, 'evict', bundle)
            export = Path(retry['export']['base'])
            shutil.rmtree(export)  # This private fixture's owned export only.
            before = cli(store, 'stats')['totals']
            reader = sqlite3.connect(store / 'index.sqlite3')
            reader.execute('BEGIN')
            assert reader.execute('SELECT ready FROM bundles WHERE id=?', (bundle,)).fetchone() == (0,)
            process = subprocess.Popen(list(map(str, [binary, '--cache-dir', store, *ensure])),
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 30
                while not (export / 'manifest.json').exists() and process.poll() is None:
                    assert time.monotonic() < deadline, 'export publication deadline'
                    time.sleep(.005)
                assert process.poll() is None and (export / 'manifest.json').is_file()
                process.kill()
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                reader.rollback()
                reader.close()
            assert not cli(store, 'inspect', bundle)['ready']
            assert cli(store, 'stats')['totals'] == before
            with sqlite3.connect(store / 'index.sqlite3') as db:
                assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            recovered = cli(store, *ensure)
            assert not recovered['cache']['hit'] and recovered['artifact_set_id'] == identity
            # Corrupt exports fail closed; explicit owner removal permits warm reconstruction.
            prover = export / 'keys/proof.prover'
            prover.write_bytes(b'corrupted copied export')
            cli(store, *ensure, success=False)
            shutil.rmtree(export)
            repaired = cli(store, *ensure)
            assert repaired['cache']['hit'] and repaired['artifact_set_id'] == identity
            # Removing an intact export is also recoverable without regenerating CAS keys.
            shutil.rmtree(export)
            rebuilt = cli(store, *ensure)
            assert rebuilt['cache']['hit'] and rebuilt['artifact_set_id'] == identity
            if selector == 'ledger8-v2':
                proof = invoke([ROOT / 'target/debug/examples/qualify-http-fixture', export])
            else:
                worker = Path(os.environ.get('MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER',
                                             str(binary.parent / 'midnight-zkir-forge-zkir3-worker')))
                proof = invoke([worker, 'qualify-export', '--output', export, '--circuit-name', 'proof'])
            assert all(proof[name] for name in (
                'valid_proof_verified', 'invalid_statement_rejected', 'corrupt_proof_rejected'))
            profiles.append({'profile': selector, 'accounting_failure_rollback': True,
                             'resolve_accounting_atomic': True, 'export_obstacle_retry': True,
                             'killed_after_export_before_commit': True, 'uncommitted_metrics_rolled_back': True,
                             'corrupt_export_owner_repair': True, 'warm_export_rebuild': True,
                             'same_output_identity': True, 'real_proof_controls': True})
    print(json.dumps({'schema': 1, 'primary_error_preserved_after_accounting_failure': True,
                      'profiles': profiles, 'scope': 'private local stores; no Compact or remote operations'}))
