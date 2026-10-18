#!/usr/bin/env python3
"""Synthetic reporter acceptance/refusal tests; no proof or CI performance evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('report', ROOT/'scripts/report-ci-trial.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def fixture(warm_ms=700):
    identity = {key: 'a' * 64 for key in report.IDENTITY}
    identity.update(repository='example/consumer', workflow_repository='betsudo/forge',
                    consumer_commit='b' * 40, profile='synthetic-json31-test-only',
                    runner_image='synthetic-ubuntu-image-version', runner_arch='X64')
    correctness = dict(proofs=2, verifications=2, assertions=18, negative_controls=4)
    plan = dict(schema=1, scope='whole-job', repetitions=3, minimum_saving_ms=100,
                cache_requests=2, identity=identity, correctness=correctness)
    rows = []
    for repetition in range(3):
        for lane in report.LANES:
            hits = 2 if lane == 'warm' else 1 if lane == 'partial' else 0
            download = 100 if hits else 0
            stats = None if lane in ('uncached','unavailable') else dict(requests=2, hits=hits, misses=2-hits, errors=0)
            rows.append(dict(plan_sha256='c'*64, identity=copy.deepcopy(identity), scope='whole-job',
                conclusion='success', repetition=repetition, lane=lane,
                job_url=f'https://github.com/betsudo/forge/actions/runs/123/job/{len(rows)+1}',
                evidence_sha256='d'*64, correctness=copy.deepcopy(correctness),
                timing=dict(job_ms=warm_ms if lane == 'warm' else 1000,
                            setup_ms=100, codegen_ms=50, key_prepare_ms=50,
                            proof_verify_ms=100, download_ms=10 if download else 0, upload_ms=0),
                download_bytes=download, upload_bytes=0,
                transport_unavailable=lane == 'unavailable', cache=stats))
    return plan, rows


class Reporter(unittest.TestCase):
    def test_complete_positive_and_negative_results(self):
        for warm, saving, met in [(700, 300, True), (1200, -200, False), (950, 50, False)]:
            plan, rows = fixture(warm)
            value = report.summarize(plan, rows, 'c'*64)
            self.assertEqual(value['paired_warm_saving_ms'], [saving]*3)
            self.assertEqual(value['threshold_met'], met)
            self.assertEqual(value['lanes']['warm']['median_job_ms'], warm)

    def test_tail_and_paired_statistics(self):
        plan, rows = fixture()
        for row in rows:
            if row['lane'] == 'warm':
                row['timing']['job_ms'] = [500, 900, 2000][row['repetition']]
        value = report.summarize(plan, rows, 'c'*64)
        self.assertEqual(value['lanes']['warm']['p95_job_ms'], 2000)
        self.assertEqual(value['median_paired_warm_saving_ms'], 100)
        self.assertEqual(value['paired_warm_saving_ms'], [500, 100, -1000])

    def test_invalid_measurements_refused(self):
        mutations = [
            ('missing lane', lambda p, r: r.pop()),
            ('duplicate lane', lambda p, r: r.__setitem__(1, copy.deepcopy(r[0]))),
            ('reused job', lambda p, r: r[1].update(job_url=r[0]['job_url'])),
            ('plan mismatch', lambda p, r: r[0].update(plan_sha256='e'*64)),
            ('profile mismatch', lambda p, r: r[1]['identity'].update(profile='other')),
            ('fewer controls', lambda p, r: r[2]['correctness'].update(negative_controls=2)),
            ('no proofs', lambda p, r: r[2]['correctness'].update(proofs=0)),
            ('failed tests', lambda p, r: r[2].update(conclusion='failure')),
            ('not hosted', lambda p, r: r[2].update(job_url='local-test')),
            ('wrong repo', lambda p, r: r[2].update(job_url='https://github.com/other/repo/actions/runs/1/job/2')),
            ('no raw digest', lambda p, r: r[2].update(evidence_sha256='')),
            ('local stage only', lambda p, r: r[2].update(scope='keygen')),
            ('zero whole job', lambda p, r: r[2]['timing'].update(job_ms=0)),
            ('negative duration', lambda p, r: r[2]['timing'].update(setup_ms=-1)),
            ('NaN duration', lambda p, r: r[2]['timing'].update(job_ms=float('nan'))),
            ('infinite duration', lambda p, r: r[2]['timing'].update(job_ms=float('inf'))),
            ('boolean duration', lambda p, r: r[2]['timing'].update(job_ms=True)),
            ('stage overlap', lambda p, r: r[2]['timing'].update(setup_ms=1000)),
            ('no download', lambda p, r: r[2].update(download_bytes=0)),
            ('unmeasured download', lambda p, r: r[2]['timing'].update(download_ms=0)),
            ('request errors', lambda p, r: r[2]['cache'].update(errors=1)),
            ('inherited stats', lambda p, r: r[2]['cache'].update(requests=200, hits=200)),
            ('warm miss', lambda p, r: r[2]['cache'].update(hits=1, misses=1)),
            ('fake partial', lambda p, r: r[3]['cache'].update(hits=2, misses=0)),
            ('availability relabel', lambda p, r: r[4].update(transport_unavailable=False)),
            ('unavailable forged cache', lambda p, r: r[4].update(cache=dict(requests=2,hits=0,misses=2,errors=0))),
            ('uncached upload', lambda p, r: r[0].update(upload_bytes=10)),
            ('posthoc short sample', lambda p, r: p.update(repetitions=1)),
            ('zero adoption threshold', lambda p, r: p.update(minimum_saving_ms=0)),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                plan, rows = fixture()
                mutate(plan, rows)
                with self.assertRaises(ValueError):
                    report.summarize(plan, rows, 'c'*64)

    def test_duplicate_json_and_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.json'
            for raw in ['{"schema":1,"schema":1}', '{"time":NaN}', '{"time":Infinity}']:
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    report.load(path)

    def test_cli_preserves_existing_output_and_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, rows = fixture()
            (root/'plan.json').write_text(json.dumps(plan))
            digest = hashlib.sha256((root/'plan.json').read_bytes()).hexdigest()
            for row in rows:
                row['plan_sha256'] = digest
            (root/'runs.json').write_text(json.dumps(rows))
            command = [sys.executable, str(ROOT/'scripts/report-ci-trial.py'),
                       '--plan', str(root/'plan.json'), '--runs', str(root/'runs.json'),
                       '--output', str(root/'report.json')]
            subprocess.run(command, check=True, capture_output=True)
            original = (root/'report.json').read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((root/'report.json').read_bytes(), original)
            (root/'report.json').unlink()
            rows.pop()
            (root/'runs.json').write_text(json.dumps(rows))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root/'report.json').exists())

            # Finite inputs may overflow an even-sample median. Refuse before
            # creating output, rather than leave a partially serialized report.
            plan, rows = fixture()
            plan['repetitions'] = 4
            extra = copy.deepcopy(rows[:5])
            for index, row in enumerate(extra):
                row['repetition'] = 3
                row['job_url'] = f'https://github.com/betsudo/forge/actions/runs/123/job/{100+index}'
            rows += extra
            (root/'plan.json').write_text(json.dumps(plan))
            digest = hashlib.sha256((root/'plan.json').read_bytes()).hexdigest()
            for row in rows:
                row['plan_sha256'] = digest
                row['timing']['job_ms'] = 1e308
            (root/'runs.json').write_text(json.dumps(rows))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root/'report.json').exists())


if __name__ == '__main__':
    unittest.main()
