#!/usr/bin/env python3
"""Local adapter failure controls; synthetic fixtures are not proof evidence."""
import contextlib
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('adapter', ROOT/'scripts/compiler-local.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


@contextlib.contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='forge-adapter-test-') as directory:
        work = Path(directory).resolve()
        output = work/'output'
        sources = output/'zkir'
        sources.mkdir(parents=True)
        source = sources/'proof.zkir'
        source.write_bytes(b'{}')
        exports = work/'exports'
        exports.mkdir()
        inventory, hashes = [], {}
        for kind, data in [('source',b'{}'),('binary_ir',b'ir'),('prover',b'pk'),('verifier',b'vk')]:
            p = exports/kind
            p.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            hashes[kind] = digest
            inventory.append(dict(kind=kind,path=str(p),bytes=len(data),sha256=digest))
        descriptor = {'record':{'name':'proof'}}
        row = dict(descriptor=descriptor,official_artifact_sha256=hashes)
        config = dict(compiler_dir=str(work),binary=str(work/'forge'),params_dir=str(work),
            qualification=str(work/'qualification'),qualification_sha256='a'*64,
            output=str(output),cache_dir=str(work/'cache'))
        prepared = dict(descriptor=descriptor,export=dict(files=inventory))
        with patch.object(adapter,'policy',return_value={'materialization':[row]}), \
             patch.object(adapter,'command',return_value=json.dumps(prepared)) as mocked:
            yield work, source, config, mocked


class LocalAdapter(unittest.TestCase):
    def hook(self, source, config):
        adapter.materialize(config,['compile-many',str(source.parent),str(Path(config['output'])/'keys')])

    def test_private_materialization_and_empty_batch(self):
        with fixture() as (work, source, config, _):
            self.hook(source,config)
            self.assertEqual(source.with_suffix('.bzkir').read_bytes(),b'ir')
            prover = Path(config['output'])/'keys/proof.prover'
            prover.write_bytes(b'caller change')
            self.assertEqual((work/'exports/prover').read_bytes(),b'pk')
        with fixture() as (_, source, config, mocked):
            source.unlink()
            self.hook(source,config)
            mocked.assert_not_called()

    def test_stale_binary_corrupt_export_and_unsafe_target(self):
        for failure in ['stale','corrupt','symlink']:
            with self.subTest(failure=failure), fixture() as (work, source, config, _):
                sentinel = work/'sentinel'
                sentinel.write_bytes(b'keep')
                if failure == 'stale': (source.parent/'old.bzkir').write_bytes(b'old')
                if failure == 'corrupt': (work/'exports/prover').write_bytes(b'changed')
                if failure == 'symlink':
                    keys = Path(config['output'])/'keys'
                    keys.mkdir()
                    (keys/'proof.prover').symlink_to(sentinel)
                with self.assertRaises(ValueError): self.hook(source,config)
                self.assertEqual(sentinel.read_bytes(),b'keep')
                self.assertFalse(source.with_suffix('.bzkir').exists())

    def test_changed_source_fails_without_published_keys(self):
        with fixture() as (_, source, config, mocked):
            result = mocked.return_value
            def mutate(*_args):
                source.write_bytes(b'changed')
                return result
            mocked.side_effect = mutate
            with self.assertRaises(ValueError): self.hook(source,config)
            self.assertFalse((Path(config['output'])/'keys').exists())

    def test_source_set_and_qualified_swap_during_staging(self):
        for mutation in ['swap','addition']:
            with self.subTest(mutation=mutation), fixture() as (_, source, config, _):
                original = adapter.shutil.copyfile
                def change(a,b):
                    result = original(a,b)
                    if mutation == 'swap': source.write_bytes(b'other-qualified-source')
                    else: (source.parent/'added.zkir').write_bytes(b'{}')
                    return result
                with patch.object(adapter.shutil,'copyfile',side_effect=change):
                    with self.assertRaises(ValueError): self.hook(source,config)
                self.assertFalse(source.with_suffix('.bzkir').exists())

    def test_swap_to_another_actually_qualified_circuit_during_staging(self):
        with fixture() as (work, source, config, mocked):
            other = source.parent/'other.zkir'
            other.write_bytes(b'{"other":true}')
            prepared = mocked.return_value
            second = json.loads(prepared)
            second['descriptor']['record']['name'] = 'other'
            exported = work/'exports/other-source'
            exported.write_bytes(other.read_bytes())
            second_hash = adapter.sha(exported)
            for entry in second['export']['files']:
                if entry['kind'] == 'source':
                    entry.update(path=str(exported), bytes=exported.stat().st_size, sha256=second_hash)
            hashes = dict(adapter.policy.return_value['materialization'][0]['official_artifact_sha256'])
            hashes['source'] = second_hash
            adapter.policy.return_value['materialization'].append(dict(
                descriptor=second['descriptor'], official_artifact_sha256=hashes))
            mocked.side_effect = lambda args: json.dumps(second) if args[-1] == 'other' else prepared
            original = adapter.shutil.copyfile
            def swap(a, b):
                result = original(a, b)
                source.write_bytes(other.read_bytes())
                return result
            with patch.object(adapter.shutil, 'copyfile', side_effect=swap):
                with self.assertRaisesRegex(ValueError, 'source changed before publication'):
                    self.hook(source, config)
            self.assertFalse(source.with_suffix('.bzkir').exists())
            self.assertEqual(list((source.parent.parent/'keys').iterdir()), [])

    def test_missing_official_zkir_probe_is_a_preflight_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            tools = root/'tools'
            tools.mkdir()
            binary = root/'forge'
            paths = {'compactc.bin':tools/'compactc.bin', 'zkir-v3':tools/'zkir-v3',
                     'forge':binary, 'worker':root/'midnight-zkir-forge-zkir31-worker'}
            for path in paths.values(): path.write_bytes(b'synthetic executable identity')
            controls = dict(valid_proof_verified=True, invalid_statement_rejected=True, corrupt_proof_rejected=True)
            qualification = root/'qualification.json'
            qualification.write_text(json.dumps(dict(schema=1, status='passed', materialization=[{}],
                provider_checks={'lanes':[{'proof_controls':controls}]},
                tool_sha256={name:adapter.sha(path) for name,path in paths.items()})))
            args = argparse.Namespace(binary=binary, params_dir=root/'params', compiler_dir=tools,
                qualification=qualification, qualification_sha256=adapter.sha(qualification))
            with patch.object(adapter, 'command') as command:
                with self.assertRaisesRegex(ValueError, 'zkir presence probe unavailable'):
                    adapter.policy(args)
                command.assert_not_called()

    def test_successful_compiler_without_hook_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            tools = root/'tools'
            tools.mkdir()
            source = root/'source.compact'
            source.write_text('synthetic fixture')
            qualification = root/'qualification.json'
            qualification.write_text('{}')
            output = root/'output'
            invocation = ['compiler-local.py', '--mode', 'local', '--compiler-dir', str(tools),
                '--binary', str(root/'bin/forge'), '--qualification', str(qualification),
                '--qualification-sha256', '0'*64, '--params-dir', str(root/'params'),
                '--cache-dir', str(root/'cache'), str(source), str(output)]
            import io
            stderr = io.StringIO()
            with patch.object(sys, 'argv', invocation), patch.object(adapter, 'policy', return_value={}), \
                 patch.object(adapter.subprocess, 'run', return_value=argparse.Namespace(returncode=0)), \
                 contextlib.redirect_stderr(stderr):
                self.assertEqual(adapter.main(), 1)
            self.assertIn('compiler did not complete cached keygen hook', stderr.getvalue())
            self.assertFalse(output.exists())

    def test_stage_failure_publishes_nothing(self):
        with fixture() as (_, source, config, _):
            with patch.object(adapter.shutil,'copyfile',side_effect=OSError('injected copy failure')):
                with self.assertRaises(OSError): self.hook(source,config)
            self.assertFalse(source.with_suffix('.bzkir').exists())
            self.assertEqual(list((Path(config['output'])/'keys').iterdir()),[])

    def test_partial_publication_never_creates_manifest_and_can_retry(self):
        with fixture() as (_, source, config, _):
            original = adapter.os.replace
            calls = []
            def fail_second(a,b):
                calls.append(b)
                if len(calls)==2: raise OSError('injected second-file failure')
                return original(a,b)
            with patch.object(adapter.os,'replace',side_effect=fail_second):
                with self.assertRaises(OSError): self.hook(source,config)
            self.assertFalse((Path(config['output'])/'compiler/contract-manifest.json').exists())
            self.hook(source,config)
            self.assertEqual((Path(config['output'])/'keys/proof.prover').read_bytes(),b'pk')

    def test_duplicate_metadata_and_unsupported_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            p = root/'duplicate.json'
            p.write_text('{"status":"passed","status":"other"}')
            with self.assertRaises(ValueError): adapter.load(p)
            with self.assertRaises(ValueError): adapter.safe_path(root/"apostrophe'path")
            (root/'link').symlink_to(root)
            with self.assertRaises(ValueError): adapter.safe_path(root/'link/child')

    def test_default_off_and_preflight_failure_preserve_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            compiler = root/'compactc.bin'
            compiler.write_text('#!/bin/sh\nexit 7\n')
            compiler.chmod(0o700)
            source = root/'source.compact'
            source.write_text('fixture')
            output = root/'output'
            output.mkdir()
            sentinel = output/'keep'
            sentinel.write_text('keep')
            invocation = [sys.executable,str(ROOT/'scripts/compiler-local.py'),'--compiler-dir',str(root),
                          '--cache-dir',str(root/'cache'),str(source),str(output)]
            self.assertEqual(subprocess.run(invocation,capture_output=True).returncode,7)
            self.assertFalse((root/'cache').exists())
            qualification = root/'qualification.json'
            qualification.write_text('{}')
            invocation[2:2] = ['--mode','local','--binary',str(root/'unused'),
                '--params-dir',str(root),'--qualification',str(qualification),'--qualification-sha256','0'*64]
            result = subprocess.run(invocation,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('qualification digest mismatch',result.stderr)
            self.assertEqual(sentinel.read_text(),'keep')
            self.assertFalse((root/'cache').exists())


if __name__ == '__main__':
    unittest.main()
