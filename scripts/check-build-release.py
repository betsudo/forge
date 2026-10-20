#!/usr/bin/env python3
"""Release tag admission controls; no Nix build or native qualification."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('builder', Path(__file__).with_name('build-release.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class TagAdmission(unittest.TestCase):
    def test_invalid_or_wrong_version_refused_before_build_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen = Path(directory)
            (frozen/'Cargo.toml').write_text('[package]\nversion = "2026.10.0-rc.1"\n')
            output = frozen/'output'
            for tag, reason in [('latest', 'semantic release tag'),
                                ('v2026.10.0', 'committed Cargo version'),
                                ('v2026.10.0-rc.2', 'committed Cargo version')]:
                with self.subTest(tag=tag), patch.object(builder, 'run') as run:
                    with self.assertRaisesRegex(ValueError, reason):
                        builder._prepare(tag, output, 'a'*40, frozen)
                    run.assert_not_called()
                    self.assertFalse(output.exists())

    def test_matching_frozen_rc_and_stable_versions_reach_exact_commit_build(self):
        with tempfile.TemporaryDirectory() as directory:
            frozen = Path(directory)
            for version in ['2026.10.0-rc.1', '2026.10.0']:
                (frozen/'Cargo.toml').write_text('[package]\nversion = "'+version+'"\n')
                with self.subTest(version=version), patch.object(builder, 'run', side_effect=RuntimeError('build boundary')) as run:
                    with self.assertRaisesRegex(RuntimeError, 'build boundary'):
                        builder._prepare('v'+version, frozen/'output', 'a'*40, frozen)
                    self.assertEqual(run.call_args.args[-1], f'git+file://{builder.ROOT}?rev={"a"*40}#default')


if __name__ == '__main__':
    unittest.main()
