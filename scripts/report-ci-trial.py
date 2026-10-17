#!/usr/bin/env python3
"""Compare complete hosted CI jobs against a predeclared plan; never runs tests."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

LANES = ('uncached', 'cold', 'warm', 'partial', 'unavailable')
STAGES = ('setup_ms', 'codegen_ms', 'key_prepare_ms', 'proof_verify_ms',
          'download_ms', 'upload_ms')
COUNTS = ('proofs', 'verifications', 'assertions', 'negative_controls')
IDENTITY = ('repository', 'workflow_repository', 'consumer_commit', 'workload_sha256', 'toolchain_sha256',
            'forge_sha256', 'worker_sha256', 'profile', 'parameters_sha256', 'runner_image', 'runner_arch')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, label, integer=False, positive=False):
    require(type(value) in ((int,) if integer else (int, float)), label + ': number required')
    require(math.isfinite(value) and (value > 0 if positive else value >= 0),
            label + ': finite ' + ('positive' if positive else 'nonnegative') + ' value required')
    return value


def load(path, with_digest=False):
    with path.open('rb') as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    require(len(raw) <= 16 * 1024 * 1024, 'receipt exceeds 16 MiB')
    def fields(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON field: ' + key)
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=fields,
                       parse_constant=lambda value: number(float(value), 'JSON number'))
    return (value, hashlib.sha256(raw).hexdigest()) if with_digest else value


def counts(value):
    require(isinstance(value, dict) and set(value) == set(COUNTS), 'correctness counts required')
    for key in COUNTS:
        number(value[key], key, integer=True, positive=True)
    require(value['verifications'] >= value['proofs'], 'verification count below proof count')
    require(value['negative_controls'] >= 2, 'invalid-statement and corrupt-proof controls required')


def summarize(plan, rows, plan_sha256):
    require(type(plan['schema']) is int and plan['schema'] == 1, 'unsupported plan schema')
    require(plan['scope'] == 'whole-job', 'whole-job scope required')
    repetitions = number(plan['repetitions'], 'repetitions', integer=True)
    require(3 <= repetitions <= 1000, 'three to 1000 repetitions required')
    threshold = number(plan['minimum_saving_ms'], 'minimum_saving_ms', positive=True)
    requests = number(plan['cache_requests'], 'cache_requests', integer=True, positive=True)
    require(requests >= 2, 'partial lane needs at least two cache requests')
    identity = plan['identity']
    require(isinstance(identity, dict) and set(identity) == set(IDENTITY), 'exact identity fields required')
    for key in IDENTITY:
        require(isinstance(identity[key], str) and identity[key].strip(), 'nonempty identity: ' + key)
        if key.endswith('_sha256'):
            require(re.fullmatch(r'[0-9a-f]{64}', identity[key]) is not None, 'invalid digest: ' + key)
    require(re.fullmatch(r'[0-9a-f]{40}', identity['consumer_commit']) is not None, 'full consumer commit required')
    for key in ('repository', 'workflow_repository'):
        require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', identity[key]) is not None,
                'owner/repository required: ' + key)
    require(identity['runner_arch'] == 'X64', 'initial pilot requires native x86_64 runner')
    counts(plan['correctness'])
    require(isinstance(rows, list) and len(rows) == repetitions * len(LANES), 'complete five-lane repetitions required')
    seen, jobs = {}, set()
    for row in rows:
        require(row['plan_sha256'] == plan_sha256, 'plan digest mismatch')
        require(row['identity'] == identity, 'comparison identity mismatch')
        require(row['scope'] == 'whole-job' and row['conclusion'] == 'success', 'successful whole-job measurement required')
        repetition = number(row['repetition'], 'repetition', integer=True)
        require(repetition < repetitions and row['lane'] in LANES, 'invalid repetition or lane')
        pair = (repetition, row['lane'])
        require(pair not in seen, 'duplicate repetition/lane')
        job = row['job_url']
        require(isinstance(job, str) and re.fullmatch(
            r'https://github\.com/' + re.escape(identity['workflow_repository']) + r'/actions/runs/[1-9][0-9]*/job/[1-9][0-9]*', job),
            'exact hosted job URL required')
        require(job not in jobs, 'hosted job reused across measurements')
        require(re.fullmatch(r'[0-9a-f]{64}', row['evidence_sha256']) is not None, 'raw evidence digest required')
        counts(row['correctness'])
        require(row['correctness'] == plan['correctness'], 'correctness count mismatch')
        timing = row['timing']
        total = number(timing['job_ms'], 'job_ms', positive=True)
        require(sum(number(timing[key], key) for key in STAGES) <= total,
                'sequential stage totals exceed whole-job time')
        for key in ('download_bytes', 'upload_bytes'):
            number(row[key], key, integer=True)
        for direction in ('download', 'upload'):
            require(row[direction + '_bytes'] == 0 or timing[direction + '_ms'] > 0,
                    'transferred bytes require measured transport time')
        lane = row['lane']
        require(type(row['transport_unavailable']) is bool, 'transport availability boolean required')
        require(row['transport_unavailable'] == (lane == 'unavailable'), 'unavailable lane mismatch')
        stats = row['cache']
        if lane in ('uncached', 'unavailable'):
            require(stats is None and row['download_bytes'] == row['upload_bytes'] == 0,
                    'official control/fallback must not use Forge cache or transfer keys')
            if lane == 'uncached':
                require(timing['download_ms'] == timing['upload_ms'] == 0, 'uncached transport time must be zero')
            else:
                require(timing['upload_ms'] == 0, 'unavailable transport cannot upload')
        else:
            require(isinstance(stats, dict), 'job-local cache deltas required')
            for key in ('requests', 'hits', 'misses', 'errors'):
                number(stats[key], key, integer=True)
            require(stats['requests'] == requests and stats['requests'] == stats['hits'] + stats['misses']
                    and stats['errors'] == 0, 'invalid cache counters or request errors')
            if lane in ('warm', 'partial'):
                require(row['download_bytes'] > 0 and stats['hits'] > 0, 'warm/partial requires actual download and hits')
                require((stats['misses'] == 0) == (lane == 'warm'), 'warm/partial miss count mismatch')
            else:
                require(row['download_bytes'] == 0 and stats['hits'] == 0, 'cold/unavailable must start without restored keys')
            if lane == 'unavailable':
                require(row['upload_bytes'] == 0, 'unavailable transport cannot upload')
        seen[pair] = row
        jobs.add(job)
    require(set(seen) == {(n, lane) for n in range(repetitions) for lane in LANES}, 'missing lane')
    summaries = {}
    for lane in LANES:
        values = sorted(seen[n, lane]['timing']['job_ms'] for n in range(repetitions))
        summaries[lane] = {'samples': repetitions, 'median_job_ms': statistics.median(values),
                           'p95_job_ms': values[math.ceil(.95 * repetitions) - 1],
                           'download_bytes': sum(seen[n, lane]['download_bytes'] for n in range(repetitions)),
                           'upload_bytes': sum(seen[n, lane]['upload_bytes'] for n in range(repetitions))}
    paired = [seen[n, 'uncached']['timing']['job_ms'] - seen[n, 'warm']['timing']['job_ms']
              for n in range(repetitions)]
    saving = statistics.median(paired)
    return {'schema': 1, 'plan_sha256': plan_sha256, 'identity': identity, 'scope': 'whole-job',
            'lanes': summaries, 'paired_warm_saving_ms': paired, 'median_paired_warm_saving_ms': saving,
            'minimum_saving_ms': threshold, 'threshold_met': saving >= threshold,
            'correctness_per_job': plan['correctness'],
            'limits': 'Producer-declared timings and correctness counts; raw evidence and genuine proof execution require independent audit. No billed-minute, monetary or adoption claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--runs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        plan, plan_hash = load(args.plan, with_digest=True)
        rows, rows_hash = load(args.runs, with_digest=True)
        report = summarize(plan, rows, plan_hash)
        report['runs_sha256'] = rows_hash
        encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
        with args.output.open('x') as stream:
            stream.write(encoded)
    except (ValueError, KeyError, TypeError, OverflowError, OSError) as error:
        print('CI trial report refused: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps({'output': str(args.output), 'threshold_met': report['threshold_met']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
