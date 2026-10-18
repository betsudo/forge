#!/usr/bin/env python3
"""Synthetic orchestration/refusal controls; no native consumer qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


linux = module('qualify-passport-linux')
stage = module('stage-passport-linux')


class Controls(unittest.TestCase):
    def test_changed_inputs_and_receipt_collisions_refuse_before_processes(self):
        for mutation in ('compiler','source','parameter','scratch','result-policy-collision','existing-policy'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                repo = root/'repo'
                source = root/'source'
                compiler = root/'compiler'
                binary = root/'package/bin/zkir-forge'
                params = root/'params'
                for path in (repo/'.local',source,compiler,binary.parent,params): path.mkdir(parents=True)
                elf = b'\x7fELF\x02\x01'+b'\0'*12+b'\x3e\0'
                tools = {'compactc.bin':compiler/'compactc.bin','zkir-v3':compiler/'zkir-v3','zkir':compiler/'zkir',
                    'forge':binary,'worker':binary.parent/'midnight-zkir-forge-zkir31-worker',
                    'helper':binary.parent/'midnight-zkir-forge-ci',
                    'helper_payload':binary.parent.parent/'share/midnight-zkir-forge/forge-ci.py'}
                for path in tools.values():
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(elf)
                    path.chmod(0o755)
                source_file = source/'contract.compact'
                source_file.write_bytes(b'synthetic Compact source')
                source_digest = linux.passport.sha(source_file)
                closure = {'revision':'a'*40,'files':{'contract.compact':{'sha256':source_digest,
                    'git_blob':hashlib.sha1(b'blob '+str(source_file.stat().st_size).encode()+b'\0'+source_file.read_bytes()).hexdigest()}}}
                parameter = params/'bls_midnight_2p4'
                parameter.write_bytes(b'synthetic parameter, never used for proving')
                parameter_digest = linux.passport.sha(parameter)
                def document(name,value):
                    path = repo/name
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(value))
                document('docs/evidence/passport-full-models-local.json',{'source_closure':closure})
                document('benchmarks/passport/consumer-files.json',{'files':{'contract.compact':source_digest}})
                document('docs/evidence/passport-adapter-qualification-local.json',{'materialization':[
                    {'descriptor':{'record':{'k':4,'parameter_digest':parameter_digest}}}]})
                document('integration/providers/package-lock.json',{'synthetic':True})
                cohort = root/'cohort.json'
                cohort.write_text(json.dumps({'schema':1,'platform':'x86_64-linux',
                    'sdk_lock_sha256':linux.passport.sha(repo/'integration/providers/package-lock.json'),
                    'tool_sha256':{name:linux.passport.sha(path) for name,path in tools.items()},
                    'parameters':{'bls_midnight_2p4':parameter_digest}}))
                args = argparse.Namespace(binary=binary,compiler_dir=compiler,source=source,params_dir=params,
                    cohort=cohort,cohort_sha256=linux.passport.sha(cohort),work=repo/'.local/scratch',output=repo/'.local/result.json')
                with patch.object(linux,'ROOT',repo), patch.object(linux,'native_host',return_value={}), \
                     patch.object(linux.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)), \
                     patch.object(linux,'command') as command:
                    linux.preflight(args)
                    self.assertFalse(args.work.exists())
                    if mutation == 'compiler': (compiler/'compactc.bin').write_bytes(elf+b'changed')
                    elif mutation == 'source': source_file.write_bytes(b'changed source')
                    elif mutation == 'parameter': parameter.write_bytes(b'changed parameter')
                    elif mutation == 'scratch': args.work.mkdir()
                    elif mutation == 'result-policy-collision': args.output = args.output.with_name('passport-adapter-qualification-linux.json')
                    else: args.output.with_name('passport-adapter-qualification-linux.json').write_text('{}')
                    with self.assertRaises(ValueError): linux.preflight(args)
                    command.assert_not_called()
                    self.assertFalse((repo/'.local/result.json').exists())

    def test_wrong_host_refuses_before_reads_or_processes(self):
        for system, machine in [('Darwin','arm64'),('Linux','aarch64')]:
            with self.subTest(system=system), patch.object(linux.platform,'system',return_value=system), \
                 patch.object(linux.platform,'machine',return_value=machine), \
                 patch.object(Path,'read_bytes') as read, patch.object(linux.subprocess,'Popen') as process:
                with self.assertRaisesRegex(ValueError,'native x86_64 Linux'):
                    linux.preflight(argparse.Namespace())
                read.assert_not_called()
                process.assert_not_called()

    def test_bad_cohort_refuses_without_creating_scratch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cohort = root/'cohort.json'
            cohort.write_text('{}')
            args = argparse.Namespace(cohort=cohort,cohort_sha256='0'*64,work=root/'unused')
            with patch.object(linux,'native_host',return_value={}), patch.object(linux,'command') as command:
                with self.assertRaisesRegex(ValueError,'cohort digest mismatch'):
                    linux.preflight(args)
                command.assert_not_called()
                self.assertFalse(args.work.exists())

    def test_native_elf_check_rejects_arm_and_launchers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'compiler'
            for raw in [b'#!/bin/sh\n', b'\x7fELF\x02\x01'+b'\0'*12+b'\xb7\0']:
                path.write_bytes(raw)
                path.chmod(0o755)
                with self.assertRaisesRegex(ValueError,'native x86_64 ELF'):
                    linux.executable(path)

    def test_failed_and_timed_out_commands_never_return_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError,'command failed'):
                linux.command([sys.executable,'-c','raise SystemExit(3)'],root/'failed.log')
            with self.assertRaises(subprocess.TimeoutExpired):
                linux.command([sys.executable,'-c','import time; time.sleep(30)'],root/'timeout.log',.05)
            self.assertTrue((root/'failed.log').is_file())
            self.assertFalse((root/'receipt.json').exists())
            with self.assertRaises(FileExistsError):
                linux.command([sys.executable,'-c','pass'],root/'failed.log')

    def test_archive_path_link_and_size_refusal(self):
        for name, link, size in [('../escape',False,1),('link',True,0),('large',False,2*1024**3+1)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                archive = root/'tools.tar'
                with tarfile.open(archive,'w') as tar:
                    entry = tarfile.TarInfo(name)
                    if link:
                        entry.type = tarfile.SYMTYPE
                        entry.linkname = '/tmp'
                    else:
                        entry.size = size
                    # Header-only adversarial input; refusal must precede reads.
                    tar.fileobj.write(entry.tobuf())
                with self.assertRaises(ValueError):
                    stage.extract(archive,root/'output')
                self.assertFalse((root/'escape').exists())

    def test_failed_baseline_does_not_enter_qualifier_or_write_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            argv = ['qualify-passport-linux.py']
            for name, value in [('binary','binary'),('compiler-dir','compiler'),('params-dir','params'),
                    ('source','source'),('work','work'),('output','result.json'),('cohort','cohort.json')]:
                argv += ['--'+name,str(root/value)]
            argv += ['--cohort-sha256','a'*64]
            with patch.object(sys,'argv',argv), patch.object(linux,'preflight',return_value=({}, {}, {})), \
                 patch.object(linux,'command',side_effect=[{},ValueError('failed baseline')]), \
                 patch.object(linux.passport,'qualify') as qualify:
                with self.assertRaisesRegex(ValueError,'failed baseline'):
                    linux.main()
                qualify.assert_not_called()
                self.assertFalse((root/'result.json').exists())


if __name__ == '__main__':
    unittest.main()
