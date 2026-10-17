#!/usr/bin/env python3
"""Collect a complete terminal-job roster before producing any CI comparison."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('report', ROOT/'scripts/report-ci-trial.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
require = report.require


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def instant(value):
    parsed = datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    require(parsed.tzinfo is not None, 'timezone required on terminal job time')
    return parsed.timestamp()


def raw_file(root, relative, expected):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe evidence reference')
    path = root/path
    require(path.is_file() and not any(p.is_symlink() for p in [path,*path.parents]),
            'regular nonsymlink evidence required')
    require(path.stat().st_size <= 16*1024**2 and digest(path) == expected, 'raw evidence digest/size mismatch')
    return path


def measured_row(plan, plan_hash, run, job, slot, root):
    require(job['status'] == 'completed' and job['conclusion'] == 'success', 'job is not terminal success')
    start, end = instant(job['started_at']), instant(job['completed_at'])
    require(end > start, 'positive terminal job duration required')
    require(job['run_id'] == run['id'] and job['run_attempt'] == run['run_attempt'], 'job run/attempt mismatch')
    repository = plan['identity']['workflow_repository']
    require(job['html_url'] == f"https://github.com/{repository}/actions/runs/{run['id']}/job/{job['id']}",
            'job URL mismatch')
    receipt_path = root/(str(job['id'])+'.json')
    require(not receipt_path.is_symlink(), 'receipt symlink refused')
    receipt = report.load(receipt_path)
    require(receipt['schema'] == 1 and receipt['evidence_kind'] == 'hosted', 'actual hosted receipt required; synthetic is not evidence')
    require(receipt['plan_sha256'] == plan_hash and receipt['identity'] == plan['identity'], 'receipt plan/identity mismatch')
    require(receipt['run_id'] == run['id'] and receipt['run_attempt'] == run['run_attempt'] and
            receipt['job_id'] == job['id'], 'receipt job identity mismatch')
    require(receipt['lane'] == slot['lane'] and receipt['repetition'] == slot['repetition'], 'receipt slot mismatch')
    timing = {key:0 for key in report.STAGES}
    timing['job_ms'] = (end-start)*1000
    previous = -1
    seen, captured = set(), {}
    context = {'evidence_kind':'hosted','plan_sha256':plan_hash,'run_id':run['id'],
               'run_attempt':run['run_attempt'],'job_id':job['id']}
    first = None
    for reference in receipt['stages']:
        stage = report.load(raw_file(root,reference['receipt'],reference['sha256']))
        require(stage['producer'] == context, 'capture belongs to another job/attempt/plan')
        name = stage['stage']
        require(name in report.STAGES and name not in seen, 'unknown/duplicate measured stage')
        seen.add(name)
        captured[name] = stage
        require(stage['clock'] == receipt['clock'] and stage['returncode'] == 0, 'stage failed or clock domain changed')
        begin = report.number(stage['start_ns'],'start_ns',integer=True)
        finish = report.number(stage['end_ns'],'end_ns',integer=True)
        require(finish >= begin >= previous, 'overlapping or unordered stage intervals')
        if first is None: first = begin
        previous = finish
        timing[name] = (finish-begin)/1e6
        for stream in ('stdout','stderr'):
            raw_file(root, stage[stream], stage[stream+'_sha256'])
    require({'setup_ms','codegen_ms','key_prepare_ms','proof_verify_ms'} <= seen, 'missing workload stage')
    require((previous-first)/1e6 <= timing['job_ms'], 'full monotonic stage span exceeds terminal job')
    require(receipt['proof_receipt'] == captured['proof_verify_ms']['stdout'] and
            receipt['proof_receipt_sha256'] == captured['proof_verify_ms']['stdout_sha256'], 'proof receipt is not captured proof-stage output')
    proof = report.load(raw_file(root,receipt['proof_receipt'],receipt['proof_receipt_sha256']))
    correctness = dict(proofs=0,verifications=0,assertions=0,negative_controls=0)
    for lane in proof['lanes']:
        control = lane['proof_controls']
        require(all(control.get(flag) is True for flag in ('valid_proof_verified',
            'invalid_statement_rejected','corrupt_proof_rejected')), 'missing actual SDK proof controls')
        correctness['proofs'] += report.number(control['proof_count'],'proof_count',integer=True,positive=True)
        correctness['verifications'] += report.number(control['verification_count'],'verification_count',integer=True,positive=True)
        correctness['negative_controls'] += report.number(control['negative_controls'],'negative_controls',integer=True,positive=True)
        correctness['assertions'] += report.number(lane['execution']['assertions'],'assertions',integer=True,positive=True)
    require(correctness == receipt['correctness'] == plan['correctness'], 'raw proof/assertion count mismatch')
    transferred = {'download':0,'upload':0}
    attempts = {'download':0,'upload':0}
    for transfer in receipt['transport']:
        direction = transfer['direction']
        require(direction in transferred, 'invalid transfer direction')
        attempts[direction] += 1
        require(transfer['attempt'] == attempts[direction], 'omitted/duplicate/reordered transfer retry')
        require(transfer['outcome'] in ('success','miss','unavailable'), 'hard transport failure cannot become a miss')
        stage = captured[direction+'_ms']
        require(transfer['receipt'] == stage['stdout'] and transfer['receipt_sha256'] == stage['stdout_sha256'],
                'transport receipt is not captured transport-stage output')
        envelope = report.load(raw_file(root, transfer['receipt'], transfer['receipt_sha256']))
        require(envelope['producer'] == context, 'transport belongs to another job/attempt/plan')
        require(type(transfer['attempt']) is int and transfer['attempt'] <= len(envelope['attempts']),
                'missing raw transport attempt')
        raw = envelope['attempts'][transfer['attempt']-1]
        require(raw['unit'] == 'compressed-payload-bytes' and raw['actual_bytes'] == transfer['bytes'] and
                raw['outcome'] == transfer['outcome'] and raw['direction'] == direction,
                'raw actual transport bytes/outcome mismatch')
        amount = report.number(transfer['bytes'],'actual transport bytes',integer=True)
        require(transfer['outcome'] == 'success' or amount == 0, 'partial failed transfer needs explicit measured policy')
        if transfer['outcome'] == 'success':
            require(amount > 0 and re.fullmatch('[0-9a-f]{64}',raw['payload_sha256']), 'successful transfer lacks payload digest/bytes')
            require(raw['key'] and raw['seed_job_url'] and raw['snapshot_sha256'], 'seed/key/snapshot provenance required')
            if direction == 'download':
                require({key:raw[key] for key in ('key','seed_job_url','snapshot_sha256','payload_sha256','actual_bytes')} ==
                        plan['collection']['seeds'][slot['lane']], 'download differs from frozen seed')
                require(raw['restore']['restored'] is True and raw['restore']['result']['snapshot_id'] == raw['snapshot_sha256'],
                        'verified restore does not match frozen snapshot')
            else:
                require(raw['namespace'] == 'quarantine', 'only quarantined candidate uploads allowed')
        transferred[direction] += amount
    for direction, amount in transferred.items():
        if direction+'_ms' in captured:
            envelope = report.load(root/captured[direction+'_ms']['stdout'])
            require(envelope['producer'] == context, 'transport belongs to another job/attempt/plan')
            require(len(envelope['attempts']) == attempts[direction], 'unretained transport attempt')
        require(not attempts[direction] or direction+'_ms' in seen, 'transport attempt lacks interval')
        require(not amount or timing[direction+'_ms'] > 0, 'transport bytes lack measured time')
    unavailable = receipt['transport_unavailable']
    require(not unavailable or any(t['outcome'] == 'unavailable' for t in receipt['transport']),
            'unavailable lane requires actual classified transport refusal')
    # A measured candidate upload is quarantined. Reusable publication is a
    # separate trusted promotion after terminal success, outside this job timer.
    require(receipt['reusable_cache_published'] is False, 'lane must not promote reusable caches before terminal conclusion')
    return {'plan_sha256':plan_hash,'identity':receipt['identity'],'scope':'whole-job','conclusion':'success',
        'repetition':slot['repetition'],'lane':slot['lane'],'job_url':job['html_url'],
        'evidence_sha256':digest(receipt_path),'correctness':receipt['correctness'],'cache':receipt['cache'],
        'transport_unavailable':unavailable,'timing':timing,
        'download_bytes':transferred['download'],'upload_bytes':transferred['upload']}


def collect(plan, plan_hash, run, jobs, root):
    policy = plan['collection']
    require(run['repository']['full_name'] == plan['identity']['workflow_repository'], 'run repository mismatch')
    require(run['head_sha'] == policy['head_sha'] and run['event'] == 'workflow_dispatch', 'untrusted run/source')
    require(run['run_attempt'] == policy['run_attempt'] == 1, 'initial pilot forbids retry selection; retain every attempt and freeze a new plan')
    require(jobs['total_count'] == len(jobs['jobs']), 'incomplete paginated GitHub job roster')
    qualification = report.load(raw_file(root,policy['qualification'],policy['qualification_sha256']))
    require(qualification['status'] == 'passed' and qualification['native_host']['system'] == 'Linux' and
            qualification['native_host']['machine'] == 'x86_64', 'exact native Linux consumer qualification required')
    require(qualification['consumer_commit'] == plan['identity']['consumer_commit'] and
            qualification['tools']['forge'] == plan['identity']['forge_sha256'] and
            qualification['tools']['worker'] == plan['identity']['worker_sha256'], 'unqualified consumer/tool cohort')
    for key in ('workload_sha256','toolchain_sha256','parameters_sha256'):
        raw_file(root,policy['inventories'][key],plan['identity'][key])
    require(len({j['id'] for j in jobs['jobs']}) == len(jobs['jobs']), 'duplicate observed job ID')
    slots = policy['schedule']
    expected = {(n,lane) for n in range(plan['repetitions']) for lane in report.LANES}
    require({(s['repetition'],s['lane']) for s in slots} == expected and len(slots) == len(expected),
            'frozen complete five-lane schedule required')
    require(len({s['job_name'] for s in slots}) == len(slots), 'duplicate frozen job name')
    roster, rows, failures = [], [], []
    auxiliary = policy.get('auxiliary_jobs', {})
    require(isinstance(auxiliary, dict), 'auxiliary roles/failure policy required')
    allowed_names = {s['job_name'] for s in slots} | set(auxiliary)
    for name, role in auxiliary.items():
        require(role in ('collector','seed'), 'unknown auxiliary role')
        matched = [j for j in jobs['jobs'] if j['name'] == name]
        if (len(matched) != 1 or
            (role == 'seed' and (matched[0]['status'] != 'completed' or matched[0]['conclusion'] != 'success')) or
            (role == 'collector' and matched[0]['status'] == 'completed' and matched[0]['conclusion'] != 'success')):
            failures.append({'error':'missing, duplicate or unsuccessful auxiliary job: '+name})
    if any(j['name'] not in allowed_names for j in jobs['jobs']):
        failures.append({'error':'unplanned jobs in complete roster'})
    for slot in slots:
        matches = [job for job in jobs['jobs'] if job['name'] == slot['job_name']]
        roster.append({'expected':slot,'observed':matches})
        try:
            require(len(matches) == 1, 'missing/duplicate expected job')
            rows.append(measured_row(plan, plan_hash, run, matches[0], slot, root))
        except (ValueError,KeyError,TypeError,OSError) as error:
            failures.append({'slot':slot,'error':str(error)})
    observed_starts = [instant(j['observed'][0]['started_at']) for j in roster if len(j['observed']) == 1 and j['observed'][0].get('started_at')]
    if observed_starts != sorted(observed_starts):
        failures.append({'error':'observed lane start order differs from frozen schedule'})
    for row in rows:
        if row['timing']['job_ms'] > report.number(policy['max_job_ms'],'max_job_ms',positive=True):
            failures.append({'job':row['job_url'],'error':'frozen per-job resource budget exceeded'})
    comparison = None
    if not failures:
        try: comparison = report.summarize(plan, rows, plan_hash)
        except (ValueError,KeyError,TypeError,OverflowError) as error:
            failures.append({'error':str(error)})
    return {'schema':1,'status':'refused' if failures else 'validated','plan_sha256':plan_hash,
        'roster':roster,'all_observed_jobs':jobs['jobs'],'failures':failures,
        'rows':rows,'comparison':comparison,
        'publication':'No reusable promotion performed; terminal-success authorization is a separate step.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan','run','jobs','evidence-dir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    args = parser.parse_args()
    plan, plan_hash = report.load(args.plan,with_digest=True)
    require(plan_hash == args.plan_sha256, 'independently frozen plan digest mismatch')
    root = args.evidence_dir.resolve(strict=True)
    require(not args.output.resolve().is_relative_to(root), 'collection output must be outside raw evidence')
    files = list(root.rglob('*'))
    require(len(files) <= 4096 and not any(p.is_symlink() for p in files), 'bounded nonsymlink evidence tree required')
    require(all(p.is_dir() or p.is_file() for p in files) and
            sum(p.stat().st_size for p in files if p.is_file()) <= 64*1024**2,
            'regular evidence files within 64 MiB required')
    run, jobs = report.load(args.run), report.load(args.jobs)
    try:
        value = collect(plan,plan_hash,run,jobs,root)
    except (ValueError,KeyError,TypeError,OverflowError,OSError) as error:
        value = {'schema':1,'status':'refused','plan_sha256':plan_hash,'comparison':None,
            'all_observed_jobs':jobs.get('jobs',[]),'run':run,'failures':[{'error':str(error)}]}
    # Bind every retained input, never the output to itself. The raw input folder
    # is preserved by its owner, including all unsuccessful attempts.
    value['inputs_sha256'] = {'plan':plan_hash,'run':digest(args.run),'jobs':digest(args.jobs),
        'evidence':{str(p.relative_to(args.evidence_dir)):digest(p)
                    for p in sorted(args.evidence_dir.rglob('*')) if p.is_file() and not p.is_symlink()}}
    encoded = json.dumps(value,indent=2,allow_nan=False)+'\n'
    with args.output.open('x') as stream:
        stream.write(encoded)
    print(json.dumps({'output':str(args.output),'status':value['status']}))
    return 0 if value['status'] == 'validated' else 1


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError,KeyError,TypeError,OverflowError,OSError) as error:
        print('CI collection refused: '+str(error),file=sys.stderr)
        sys.exit(1)
