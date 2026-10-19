#!/usr/bin/env python3
"""Pure material boundary tests; no builds or source/profile admission."""
import importlib.util
from pathlib import Path
import unittest
import os
import subprocess

spec = importlib.util.spec_from_file_location('material', Path(__file__).with_name('build-nix-material.py'))
material = importlib.util.module_from_spec(spec)
spec.loader.exec_module(material)


class MaterialTests(unittest.TestCase):
    def test_source_mixing_refuses(self):
        material.producer_identity('a' * 40, 'a' * 40)
        for expected in ('main', 'b' * 40, ''):
            with self.assertRaises(ValueError):
                material.producer_identity('a' * 40, expected)

    def test_exact_output_derivation_only(self):
        row = dict(system='x86_64-linux', env=dict(out='/nix/store/root'))
        self.assertEqual(material.derivation({'derivations': {'drv': row}}, Path('/nix/store/root')), row)
        with self.assertRaises(ValueError):
            material.derivation({'drv': row}, Path('/relocated/root'))
        with self.assertRaises(ValueError):
            material.derivation({'drv': dict(row, system='aarch64-darwin')}, Path('/nix/store/root'))

    def test_complete_inventory_and_budget(self):
        row = dict(narSize=12, narHash='sha256-' + 'A' * 43 + '=')
        self.assertEqual(material.inventory_size({'/nix/store/root': row}, ['/nix/store/root']), 12)
        with self.assertRaises(ValueError):
            material.inventory_size([dict(row, path='/nix/store/root'), dict(row, path='/nix/store/root')], ['/nix/store/root'])
        for value in ({}, {'/nix/store/root': dict(row, narHash='sha256-notcanonical')}, {'/nix/store/root': dict(row, narSize=2147483649)},
                      {'/nix/store/root': dict(row, narHash=None)}):
            with self.assertRaises(ValueError):
                material.inventory_size(value, ['/nix/store/root'])

    def test_false_manual_or_reusable_input_explicitly_refuses(self):
        text = (Path(__file__).resolve().parents[1] / '.github/workflows/qualify-linux.yml').read_text()
        self.assertIn("if: github.event_name == 'workflow_dispatch' || inputs.producer-source != '' || inputs.material-only == true", text)
        self.assertIn("inputs.material-only != true && inputs.producer-source == ''", text)
        guard = next(line.strip() for line in text.splitlines() if '[[ "$MATERIAL_ONLY"' in line)
        for value, expected in [('true', 0), ('false', 1), ('', 1)]:
            result = subprocess.run(['bash', '-c', guard], env=dict(os.environ, MATERIAL_ONLY=value), capture_output=True)
            self.assertEqual(result.returncode, expected)

    def test_reusable_material_does_not_replace_pr_proofs(self):
        workflow = Path(__file__).resolve().parents[1] / '.github/workflows/qualify-linux.yml'
        text = workflow.read_text()
        self.assertIn('workflow_call:', text)
        self.assertIn("- 'scripts/build-nix-material.py'", text)
        self.assertIn("- 'scripts/test-build-nix-material.py'", text)
        self.assertIn('producer-attempt: ${{ steps.produce.outputs.producer-attempt }}', text)
        self.assertIn('repository: betsudo/forge', text)
        self.assertIn('ref: ${{ env.FORGE_PRODUCER_SOURCE }}', text)
        self.assertIn("if: github.event_name == 'pull_request' && inputs.material-only != true", text)
        self.assertIn('scripts/qualify-linux.py --candidate', text)
        self.assertIn('invalid_statement_rejected', text)
        self.assertIn('retention-days: 3', text)


if __name__ == '__main__':
    unittest.main()
