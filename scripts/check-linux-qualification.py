#!/usr/bin/env python3
"""Fast host precondition tests; these do not qualify a native payload."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('qualification', Path(__file__).with_name('qualify-linux.py'))
qualification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualification)


class Preconditions(unittest.TestCase):
    def invoke(self):
        with patch.object(sys, 'argv', ['qualify-linux.py', '--candidate', '/unused/candidate', '--output', '/unused/output']):
            qualification.main()

    def test_non_linux_refused_before_processes(self):
        with patch.object(qualification.platform, 'system', return_value='Darwin'), patch.object(qualification, 'run') as run:
            with self.assertRaisesRegex(AssertionError, 'native x86_64 Linux'):
                self.invoke()
            run.assert_not_called()

    def test_arm_linux_refused_before_processes(self):
        with patch.object(qualification.platform, 'system', return_value='Linux'), patch.object(qualification.platform, 'machine', return_value='aarch64'), patch.object(qualification, 'run') as run:
            with self.assertRaisesRegex(AssertionError, 'native x86_64 Linux'):
                self.invoke()
            run.assert_not_called()

    def test_dirty_source_refused_before_output_or_docker(self):
        with patch.object(qualification.platform, 'system', return_value='Linux'), patch.object(qualification.platform, 'machine', return_value='x86_64'), patch.dict(qualification.os.environ, {'RUNNER_ARCH': 'X64'}), patch.object(qualification, 'run', return_value=' M tracked-file\n') as run:
            with self.assertRaisesRegex(AssertionError, 'clean committed source'):
                self.invoke()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[-2:], ('status', '--porcelain'))


if __name__ == '__main__':
    unittest.main()
