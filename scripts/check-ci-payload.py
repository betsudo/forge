#!/usr/bin/env python3
"""Local real-process payload roundtrip/failure controls; no performance claims."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('payload', ROOT/'scripts/ci-payload.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=Path, default=ROOT/'target/debug/zkir-forge')
parser.add_argument('--real', action='store_true', help='prove freshly through restored JSON3.1 fixture keys')
parser.add_argument('--receipt', type=Path, help='new local evidence file, written only after complete success')
options = parser.parse_args()
BINARY = options.binary.resolve()
REAL_EVIDENCE = None


def cli(*args, ok=True):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=60)
    assert (result.returncode == 0) == ok, (result.returncode, result.stdout, result.stderr)
    return json.loads(result.stdout)


class Payload(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='forge-ci-payload-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        cli(BINARY, '--cache-dir', self.root/'source', 'import', ROOT/'fixtures/assert.zkir')
        self.snapshot = self.root/'snapshot'
        self.partition = 'a'*64
        value = cli(BINARY, '--cache-dir', self.root/'source', 'snapshot', '--output',
                    self.snapshot, '--partition', self.partition)
        self.common = [sys.executable, ROOT/'scripts/ci-payload.py']
        self.flags = ['--binary', BINARY, '--profile', 'ledger8-v2', '--snapshot-id',
                      value['snapshot_id'], '--partition', self.partition,
                      '--max-compressed-bytes', 1048576, '--max-expanded-bytes', 1048576]
        self.payload = self.root/'payload.tgz'

    def pack(self, output=None, ok=True, snapshot=None):
        return cli(*self.common, 'pack', *self.flags, '--snapshot', snapshot or self.snapshot,
                   '--output', output or self.payload, ok=ok)

    def restore(self, payload, sha=None, size=None, output=None, ok=True):
        return cli(*self.common, 'restore', *self.flags, '--payload', payload,
                   '--payload-sha256', sha or module.digest(payload),
                   '--payload-bytes', size if size is not None else payload.stat().st_size,
                   '--output', output or self.root/'restored', ok=ok)

    def clean(self):
        self.assertEqual(list(self.root.glob('.forge-payload-*')), [])

    def test_real_roundtrip_and_reproducibility(self):
        first = self.pack()
        second = self.pack(self.root/'second.tgz')
        self.assertEqual(first['payload_sha256'], second['payload_sha256'])
        self.assertEqual(first['actual_bytes'], self.payload.stat().st_size)
        result = self.restore(self.payload)
        self.assertTrue(result['restore']['restored'])
        self.assertEqual(first['snapshot_sha256'], result['restore']['result']['snapshot_id'])
        self.assertTrue((self.root/'restored/index.sqlite3').is_file())
        self.restore(self.payload, ok=False)
        self.pack(ok=False)
        self.clean()

    def test_only_one_verification_copy_and_streamed_mutation_refusal(self):
        args = SimpleNamespace(command='pack', binary=BINARY, profile='ledger8-v2',
            snapshot_id=self.flags[self.flags.index('--snapshot-id')+1], partition=self.partition,
            max_compressed_bytes=1048576, max_expanded_bytes=1048576,
            output=self.payload, snapshot=self.snapshot)
        original_pack = module.pack
        def checked_pack(source, target, *limits):
            self.assertFalse((target.parent/'verified').exists())
            self.assertFalse((target.parent/'snapshot').exists())
            return original_pack(source, target, *limits)
        with patch.object(module, 'restore', wraps=module.restore) as verified, \
             patch.object(module, 'pack', side_effect=checked_pack):
            result = module.execute(args)
        self.assertEqual(verified.call_count, 1)
        args = SimpleNamespace(**vars(args))
        args.command, args.output = 'restore', self.root/'restored'
        args.payload, args.payload_sha256, args.payload_bytes = self.payload, result['payload_sha256'], result['actual_bytes']
        with patch.object(module, 'restore', wraps=module.restore) as verified:
            module.execute(args)
        self.assertEqual(verified.call_count, 1)
        self.assertEqual(verified.call_args.args[2].resolve(), args.output.resolve())
        actual_restore = module.restore
        def wrong_verified_manifest(*values):
            result = actual_restore(*values)
            result['result']['manifest_sha256'] = '0'*64
            return result
        args.command, args.output = 'pack', self.root/'mutated.tgz'
        with patch.object(module, 'restore', side_effect=wrong_verified_manifest), \
             self.assertRaisesRegex(ValueError, 'verified manifest differs'):
            module.execute(args)
        sqlite = (self.snapshot/'index.sqlite3').read_bytes()
        for kind in ('bytes', 'directory'):
            def mutate(source, target, *limits):
                path = source/'index.sqlite3'
                if kind == 'bytes': path.write_bytes(b'changed after verification')
                else: path.unlink();path.mkdir()
                return original_pack(source, target, *limits)
            with patch.object(module, 'pack', side_effect=mutate), self.assertRaisesRegex(ValueError, 'changed'):
                module.execute(args)
            self.assertFalse(args.output.exists())
            path = self.snapshot/'index.sqlite3'
            if path.is_dir(): path.rmdir()
            path.write_bytes(sqlite)
        self.clean()

    def test_bounded_verifier_and_os_diagnostics(self):
        args = SimpleNamespace(binary=BINARY, profile='ledger8-v2', snapshot_id='a'*64,
                               partition=self.partition, max_expanded_bytes=1048576)
        failed = subprocess.CompletedProcess([], 23, '', 'x'*4096+' diagnostic-tail')
        with patch.object(module.subprocess, 'run', return_value=failed), \
             self.assertRaises(ValueError) as caught:
            module.restore(args, self.snapshot, self.root/'absent')
        self.assertIn('exit 23', str(caught.exception))
        self.assertIn('diagnostic-tail', str(caught.exception))
        self.assertLess(len(str(caught.exception)), 2200)
        result = cli(*self.common, 'pack', *self.flags, '--binary', self.root/'missing-binary',
                     '--snapshot', self.snapshot, '--output', self.payload, ok=False)
        self.assertEqual(result['error']['errno'], 2)
        self.assertTrue(result['error']['strerror'])

    def test_inventory_count_and_depth_are_bounded(self):
        with patch.object(module, 'MAX_FILES', 2), self.assertRaisesRegex(ValueError, 'inventory limit'):
            module.inventory(self.snapshot)
        deep = self.root/'deep'
        (deep/('/'.join(['d']*17))).mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'inventory limit'):
            module.inventory(deep)

    @unittest.skipUnless(options.real, 'explicit verified-parameter real proof run')
    def test_json31_restored_keys_generate_fresh_proof(self):
        global REAL_EVIDENCE
        params = Path(os.environ.get('MIDNIGHT_PP', str(Path.home()/'.cache/midnight/zk-params')))
        source = self.root/'real-source'
        cold = cli(BINARY, '--profile', 'zkir31', '--params-dir', params,
                   '--cache-dir', source, 'prepare', ROOT/'fixtures/assert-v31.zkir', '--name', 'proof')
        snap = self.root/'real-snapshot'
        saved = cli(BINARY, '--cache-dir', source, 'snapshot', '--output', snap,
                    '--partition', self.partition)
        self.flags[self.flags.index('--profile')+1] = 'zkir31'
        self.flags[self.flags.index('--snapshot-id')+1] = saved['snapshot_id']
        packed = self.pack(snapshot=snap)
        restored = self.restore(self.payload)
        warm = cli(BINARY, '--profile', 'zkir31', '--params-dir', params,
                   '--cache-dir', self.root/'restored', 'prepare', ROOT/'fixtures/assert-v31.zkir', '--name', 'proof')
        self.assertTrue(warm['cache']['hit'])
        self.assertEqual(cold['artifact_set_id'], warm['artifact_set_id'])
        worker = Path(os.environ['MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER'])
        proof = cli(worker, 'qualify-export', '--output', warm['export']['base'], '--circuit-name', 'proof')
        self.assertTrue(all(proof[key] for key in ('valid_proof_verified',
                         'invalid_statement_rejected', 'corrupt_proof_rejected')))
        REAL_EVIDENCE = {'profile': 'zkir31', 'fixture_sha256': module.digest(ROOT/'fixtures/assert-v31.zkir'),
                         'worker_sha256': module.digest(worker), 'artifact_set_id': warm['artifact_set_id'],
                         'warm_hit': True, 'payload': packed,
                         'restored_snapshot_id': restored['restore']['result']['snapshot_id'],
                         'proof_controls': proof}
        self.clean()

    def test_pinned_bytes_refuse_corruption_truncation_and_extra(self):
        original = self.pack()
        for index, data in enumerate((b'broken', self.payload.read_bytes()[:-8], self.payload.read_bytes()+b'extra')):
            with self.subTest(index=index):
                path = self.root/f'bad-{index}.tgz'
                path.write_bytes(data)
                self.restore(path, sha=original['payload_sha256'], size=original['actual_bytes'], ok=False)
                self.assertFalse((self.root/'restored').exists())
        self.clean()

    def test_unsafe_archive_members_and_expansion(self):
        cases = [('traversal', '../escape', tarfile.REGTYPE, b'x'),
                 ('absolute', '/escape', tarfile.REGTYPE, b'x'),
                 ('symlink', 'link', tarfile.SYMTYPE, b''),
                 ('hardlink', 'hard', tarfile.LNKTYPE, b''),
                 ('device', 'dev', tarfile.CHRTYPE, b''),
                 ('oversized', 'huge', tarfile.REGTYPE, b'0'*1048577),
                 ('duplicate', 'same', tarfile.REGTYPE, b'x')]
        for label, name, kind, data in cases:
            with self.subTest(label=label):
                path = self.root/f'{label}.tgz'
                with tarfile.open(path, 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
                    info = tarfile.TarInfo(name)
                    info.type, info.size, info.linkname = kind, len(data), '../escape'
                    tar.addfile(info, io.BytesIO(data))
                    if label == 'duplicate':
                        tar.addfile(info, io.BytesIO(data))
                self.restore(path, ok=False)
                self.assertFalse((self.root/'restored').exists())
                self.assertFalse((self.root/'escape').exists())
        self.clean()

    def test_snapshot_semantics_verified_not_just_tar(self):
        for label in ('extra', 'missing', 'symlink', 'corrupt', 'partition'):
            with self.subTest(label=label):
                changed = self.root/label
                shutil.copytree(self.snapshot, changed)
                if label == 'extra': (changed/'unexpected').write_text('unexpected')
                elif label == 'missing': (changed/'index.sqlite3').unlink()
                elif label == 'symlink': (changed/'link').symlink_to(self.snapshot/'index.sqlite3')
                elif label == 'corrupt': (changed/'index.sqlite3').write_bytes(b'corrupt')
                else:
                    manifest = json.loads((changed/'snapshot.json').read_text())
                    manifest['partition'] = 'b'*64
                    (changed/'snapshot.json').write_text(json.dumps(manifest))
                target = self.root/(label+'.tgz')
                self.pack(target, snapshot=changed, ok=False)
                self.assertFalse(target.exists())
        self.clean()

    def test_budget_and_overlapping_output(self):
        for budget in ('--max-compressed-bytes', '--max-expanded-bytes'):
            flags = list(self.flags)
            flags[flags.index(budget)+1] = 1
            cli(*self.common, 'pack', *flags, '--snapshot', self.snapshot,
                '--output', self.payload, ok=False)
            self.assertFalse(self.payload.exists())
        self.pack(self.snapshot/'nested.tgz', ok=False)
        self.assertFalse((self.snapshot/'nested.tgz').exists())
        alias = self.root/'alias'
        alias.symlink_to(self.snapshot, target_is_directory=True)
        self.pack(alias/'nested.tgz', ok=False)
        self.assertFalse((self.snapshot/'nested.tgz').exists())
        self.clean()

    def test_extensions_refused_before_body_read(self):
        for kind in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME,
                     tarfile.GNUTYPE_LONGLINK, tarfile.GNUTYPE_SPARSE):
            with self.subTest(kind=kind):
                path = self.root/('extension-'+kind.decode()+'.tgz')
                info = tarfile.TarInfo('extension')
                info.type, info.size = kind, 4*1024**3
                # No body: refusal must precede any attempt to allocate/read it.
                with gzip.open(path, 'wb') as stream:
                    stream.write(info.tobuf(format=tarfile.USTAR_FORMAT))
                with self.assertRaisesRegex(ValueError, 'extension/type refused'):
                    module.unpack(path, self.root/('unpack-'+kind.decode()), 1048576)
        self.clean()


if __name__ == '__main__':
    if options.receipt and options.receipt.exists():
        parser.error('receipt already exists')
    program = unittest.main(argv=[sys.argv[0]], exit=False)
    success = program.result.wasSuccessful()
    if success and options.receipt:
        receipt = {'schema': 1, 'status': 'passed', 'evidence_kind': 'local',
                   'platform': {'system': platform.system(), 'machine': platform.machine()},
                   'tests_run': program.result.testsRun, 'tests_skipped': len(program.result.skipped),
                   'binary_sha256': module.digest(BINARY),
                   'harness_sha256': module.digest(Path(__file__)),
                   'payload_tool_sha256': module.digest(ROOT/'scripts/ci-payload.py'),
                   'real_fixture': REAL_EVIDENCE,
                   'scope': 'local payload fixture/failure tests; no network/native Linux/Passport performance claim'}
        with options.receipt.open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
    sys.exit(0 if success else 1)
