#!/usr/bin/env python3
"""Synthetic collector/process tests only; no proof or hosted performance evidence."""
import copy
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import time
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


collector = module('collect-ci-trial')
fixture = module('check-ci-trial').fixture
capture = module('capture-ci-stage')


def write(root, name, value):
    path = root/name
    path.write_text(json.dumps(value)+'\n')
    return collector.digest(path)


def inputs(root):
    # Entirely synthetic fixtures of the hosted API/receipt shapes. 'hosted'
    # exercises validation; no fixture is exported as an actual measurement.
    plan, rows = fixture()
    policy = {'head_sha':'b'*40,'run_attempt':1,'schedule':[], 'max_job_ms':2000,
              'qualification':'qualification.json','inventories':{},'seeds':{}}
    plan['collection'] = policy
    for key in ('workload_sha256','toolchain_sha256','parameters_sha256'):
        name = key+'.json'
        plan['identity'][key] = write(root,name,{'synthetic':key})
        policy['inventories'][key] = name
    policy['qualification_sha256'] = write(root,'qualification.json',{
        'status':'passed','native_host':{'system':'Linux','machine':'x86_64'},
        'consumer_commit':plan['identity']['consumer_commit'],
        'tools':{'forge':plan['identity']['forge_sha256'],'worker':plan['identity']['worker_sha256']}})
    proof_template = {'lanes':[{'execution':{'assertions':18},'proof_controls':{
        'valid_proof_verified':True,'invalid_statement_rejected':True,'corrupt_proof_rejected':True,
        'proof_count':2,'verification_count':2,'negative_controls':4}}]}
    run = {'id':123,'repository':{'full_name':'betsudo/forge'},'head_sha':'b'*40,
           'run_attempt':1,'event':'workflow_dispatch'}
    jobs = {'total_count':15,'jobs':[]}
    for index, row in enumerate(rows):
        job_id = index+1
        name = f"r{row['repetition']}-{row['lane']}"
        policy['schedule'].append({'job_name':name,'repetition':row['repetition'],'lane':row['lane']})
        job = {'name':name,'id':job_id,'run_id':123,'run_attempt':1,'status':'completed','conclusion':'success',
            'html_url':row['job_url'],'started_at':f'2026-10-17T00:00:{index*2:02d}Z',
            'completed_at':f'2026-10-17T00:00:{index*2+1:02d}Z'}
        jobs['jobs'].append(job)
        context = {'evidence_kind':'hosted','plan_sha256':'c'*64,'run_id':123,'run_attempt':1,'job_id':job_id}
        transfers = []
        raw_transport = {'producer':context,'attempts':[]}
        if row['lane'] in ('warm','partial','unavailable'):
            outcome = 'unavailable' if row['lane'] == 'unavailable' else 'success'
            raw = {'unit':'compressed-payload-bytes','actual_bytes':row['download_bytes'],
                'outcome':outcome,'direction':'download','payload_sha256':'e'*64,
                'key':'synthetic-'+row['lane'],'seed_job_url':'https://github.com/betsudo/forge/actions/runs/1/job/1',
                'snapshot_sha256':'f'*64,'restore':{'restored':True,'result':{'snapshot_id':'f'*64}}}
            policy['seeds'][row['lane']] = {key:raw[key] for key in
                ('key','seed_job_url','snapshot_sha256','payload_sha256','actual_bytes')}
            raw_transport['attempts'].append(raw)
        stages = []
        proof_name, proof_hash = None, None
        for stage_index, stage in enumerate(collector.report.STAGES):
            if stage == 'upload_ms': continue
            if stage == 'download_ms' and not raw_transport['attempts']: continue
            name = f'{job_id}-{stage}'
            out_name, err_name = name+'.stdout.log', name+'.stderr.log'
            if stage == 'proof_verify_ms':
                proof_name = out_name
                proof_hash = write(root,out_name,proof_template)
            elif stage == 'download_ms':
                out_hash = write(root,out_name,raw_transport)
                transfers.append({'direction':'download','attempt':1,'bytes':row['download_bytes'],
                    'outcome':outcome,'receipt':out_name,'receipt_sha256':out_hash})
            else: (root/out_name).write_bytes(b'synthetic stage output')
            (root/err_name).write_bytes(b'')
            captured = {'schema':1,'stage':stage,'clock':'synthetic-same-job-clock','returncode':0,
                'producer':context,'start_ns':stage_index*1000000,'end_ns':(stage_index+1)*1000000,
                'stdout':out_name,'stdout_sha256':collector.digest(root/out_name),
                'stderr':err_name,'stderr_sha256':collector.digest(root/err_name)}
            stages.append({'receipt':name+'.json','sha256':write(root,name+'.json',captured)})
        write(root,str(job_id)+'.json',{'schema':1,'evidence_kind':'hosted','clock':'synthetic-same-job-clock',
            'plan_sha256':'c'*64,'identity':plan['identity'],'run_id':123,'run_attempt':1,'job_id':job_id,
            'lane':row['lane'],'repetition':row['repetition'],'stages':stages,'transport':transfers,
            'correctness':row['correctness'],'cache':row['cache'],'transport_unavailable':row['transport_unavailable'],
            'proof_receipt':proof_name,'proof_receipt_sha256':proof_hash,'reusable_cache_published':False})
    return plan,run,jobs


class Collection(unittest.TestCase):
    def test_complete_and_failed_rosters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            plan,run,jobs = inputs(root)
            value = collector.collect(plan,'c'*64,run,jobs,root)
            self.assertEqual(value['status'],'validated')
            self.assertEqual(len(value['roster']),15)
            for conclusion in ('failure','cancelled','skipped',None):
                failed = copy.deepcopy(jobs)
                failed['jobs'][0]['conclusion'] = conclusion
                value = collector.collect(plan,'c'*64,run,failed,root)
                self.assertEqual(value['status'],'refused')
                self.assertIsNone(value['comparison'])
                self.assertEqual(len(value['all_observed_jobs']),15)

    def test_receipt_failures_never_produce_comparison(self):
        mutations = [
            lambda r:r.update(evidence_kind='synthetic'),
            lambda r:r['stages'][0].update(sha256='0'*64),
            lambda r:r['stages'][0].update(receipt='1-setup_ms.json',sha256=collector.digest(ROOT/'scripts/check-ci-trial.py')),
            lambda r:r.update(plan_sha256='0'*64),
            lambda r:r.update(proof_receipt_sha256='0'*64),
            lambda r:r.update(reusable_cache_published=True),
            lambda r:r.update(job_id=999),
            lambda r:r['transport'][0].update(bytes=101),
            lambda r:r['transport'][0].update(attempt=2),
            lambda r:r['transport'][0].update(outcome='unauthorized'),
            lambda r:r['stages'][0].update(receipt='../escape'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                plan,run,jobs = inputs(root)
                path = root/'3.json'  # warm
                receipt = json.loads(path.read_text())
                mutate(receipt)
                path.write_text(json.dumps(receipt))
                value = collector.collect(plan,'c'*64,run,jobs,root)
                self.assertEqual(value['status'],'refused')
                self.assertIsNone(value['comparison'])

    def test_missing_jobs_attempts_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            plan,run,jobs = inputs(root)
            jobs['jobs'].pop()
            with self.assertRaisesRegex(ValueError,'paginated'):
                collector.collect(plan,'c'*64,run,jobs,root)
            jobs['total_count'] -= 1
            value = collector.collect(plan,'c'*64,run,jobs,root)
            self.assertEqual(value['status'],'refused')
            self.assertEqual(value['roster'][-1]['observed'],[])
            run['run_attempt'] = 2
            with self.assertRaisesRegex(ValueError,'retry selection'):
                collector.collect(plan,'c'*64,run,jobs,root)
            run['run_attempt'] = 1
            jobs['jobs'][0]['started_at'] = '2026-10-17T00:00:10Z'
            value = collector.collect(plan,'c'*64,run,jobs,root)
            self.assertTrue(any('order' in f['error'] for f in value['failures']))

    def test_bound_capture_and_payload_tampering(self):
        for field, value in [('start_ns',-1),('clock','other'),('returncode',1),('end_ns',10**15)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                plan,run,jobs = inputs(root)
                receipt = json.loads((root/'3.json').read_text())
                reference = receipt['stages'][0]
                captured = json.loads((root/reference['receipt']).read_text())
                captured[field] = value
                reference['sha256'] = write(root,reference['receipt'],captured)
                write(root,'3.json',receipt)
                self.assertEqual(collector.collect(plan,'c'*64,run,jobs,root)['status'],'refused')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            plan,run,jobs = inputs(root)
            # Correctly hashed capture from another job still cannot be reused.
            receipt = json.loads((root/'3.json').read_text())
            receipt['stages'][0] = {'receipt':'1-setup_ms.json','sha256':collector.digest(root/'1-setup_ms.json')}
            write(root,'3.json',receipt)
            self.assertEqual(collector.collect(plan,'c'*64,run,jobs,root)['status'],'refused')

    def test_stage_span_restore_and_auxiliary_failures(self):
        for mode in ('span','restore','payload','auxiliary'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                plan,run,jobs = inputs(root)
                receipt = json.loads((root/'3.json').read_text())
                if mode == 'span':
                    for index, reference in enumerate(receipt['stages']):
                        captured = json.loads((root/reference['receipt']).read_text())
                        captured['start_ns'] += index*10**12
                        captured['end_ns'] += index*10**12
                        reference['sha256'] = write(root,reference['receipt'],captured)
                    write(root,'3.json',receipt)
                elif mode == 'restore':
                    transfer = receipt['transport'][0]
                    envelope = json.loads((root/transfer['receipt']).read_text())
                    envelope['attempts'][0]['restore']['restored'] = False
                    transfer['receipt_sha256'] = write(root,transfer['receipt'],envelope)
                    reference = receipt['stages'][-1]
                    captured = json.loads((root/reference['receipt']).read_text())
                    captured['stdout_sha256'] = transfer['receipt_sha256']
                    reference['sha256'] = write(root,reference['receipt'],captured)
                    write(root,'3.json',receipt)
                elif mode == 'payload':
                    plan['collection']['seeds']['warm']['payload_sha256'] = '0'*64
                else:
                    plan['collection']['auxiliary_jobs'] = {'collector':'collector'}
                    auxiliary = dict(jobs['jobs'][0],name='collector',id=999,conclusion='failure')
                    jobs['jobs'].append(auxiliary)
                    jobs['total_count'] += 1
                value = collector.collect(plan,'c'*64,run,jobs,root)
                self.assertEqual(value['status'],'refused')
                self.assertIsNone(value['comparison'])

    def test_cli_retains_refusal_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root/'evidence'
            evidence.mkdir()
            plan = {'identity':{'workflow_repository':'betsudo/forge'},'collection':{}}
            plan_hash = write(root,'plan.json',plan)
            write(root,'run.json',{'repository':{'full_name':'other/repository'}})
            write(root,'jobs.json',{'total_count':0,'jobs':[]})
            command = [sys.executable,str(ROOT/'scripts/collect-ci-trial.py'),
                '--plan',str(root/'plan.json'),'--plan-sha256',plan_hash,
                '--run',str(root/'run.json'),'--jobs',str(root/'jobs.json'),
                '--evidence-dir',str(evidence),'--output',str(root/'collection.json')]
            result = subprocess.run(command,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            original = (root/'collection.json').read_bytes()
            value = json.loads(original)
            self.assertEqual(value['status'],'refused')
            self.assertIsNone(value['comparison'])
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual((root/'collection.json').read_bytes(),original)

    def test_detached_pipe_descendant_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable,'-c',
                'import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True); print(p.pid,flush=True)']
            started = time.monotonic()
            result = capture.capture(command,root/'detached.json','setup_ms','test',5)
            try:
                self.assertLess(time.monotonic()-started,3)
                self.assertEqual(result['failure'],'inherited_pipes')
            finally:
                pid = int((root/'detached.stdout.log').read_text())
                try: os.kill(pid,signal.SIGKILL)
                except ProcessLookupError: pass

    def test_capture_termination_retains_failed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'child.pid'
            child = 'import os,pathlib,time;pathlib.Path('+repr(str(marker))+').write_text(str(os.getpid()));time.sleep(30)'
            command = [sys.executable,str(ROOT/'scripts/capture-ci-stage.py'),
                '--output',str(root/'cancelled.json'),'--stage','setup_ms','--clock','test',
                '--plan-sha256','a'*64,'--run-id','1','--run-attempt','1','--job-id','1',
                '--',sys.executable,'-c',child]
            process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not marker.exists() and time.monotonic() < deadline: time.sleep(.01)
                self.assertTrue(marker.exists())
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=5)
                self.assertNotEqual(process.returncode,0)
                receipt = json.loads((root/'cancelled.json').read_text())
                self.assertEqual(receipt['failure'],'CaptureInterrupted')
                self.assertNotEqual(receipt['returncode'],0)
            finally:
                if process.poll() is None: process.kill();process.communicate(timeout=1)
                if marker.exists():
                    try: os.killpg(int(marker.read_text()),signal.SIGKILL)
                    except (ProcessLookupError,PermissionError): pass

    def test_ignoring_background_worker_is_killed_after_successful_leader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker, late = root/'worker.pid', root/'late'
            worker = ('import os,pathlib,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                'pathlib.Path('+repr(str(marker))+').write_text(str(os.getpid()));time.sleep(.7);'
                'pathlib.Path('+repr(str(late))+').write_text("survived");time.sleep(30)')
            leader = ('import subprocess,sys,pathlib,time;subprocess.Popen([sys.executable,"-c",'+repr(worker)+
                '],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);'
                'p=pathlib.Path('+repr(str(marker))+');\nwhile not p.exists(): time.sleep(.01)\n')
            try:
                result = capture.capture([sys.executable,'-c',leader],root/'background.json','setup_ms','test',5)
                self.assertEqual(result['returncode'],0)
                time.sleep(.8)
                self.assertFalse(late.exists(),'TERM-ignoring worker survived final group cleanup')
            finally:
                if marker.exists():
                    try: os.kill(int(marker.read_text()),signal.SIGKILL)
                    except (ProcessLookupError,PermissionError): pass

    def test_omitted_all_upload_references_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            plan,run,jobs = inputs(root)
            receipt = json.loads((root/'2.json').read_text())  # cold
            reference = receipt['stages'][-1]
            captured = json.loads((root/reference['receipt']).read_text())
            envelope = {'producer':captured['producer'],'attempts':[{
                'direction':'upload','unit':'compressed-payload-bytes','actual_bytes':100,
                'outcome':'success','payload_sha256':'e'*64,'snapshot_sha256':'f'*64,
                'key':'run-attempt-quarantine','seed_job_url':jobs['jobs'][1]['html_url'],'namespace':'quarantine'}]}
            out_hash = write(root,'2-upload.stdout.log',envelope)
            captured.update(stage='upload_ms',start_ns=6000000,end_ns=7000000,
                            stdout='2-upload.stdout.log',stdout_sha256=out_hash)
            receipt['stages'].append({'receipt':'2-upload.json','sha256':write(root,'2-upload.json',captured)})
            self.assertEqual(receipt['transport'],[])
            write(root,'2.json',receipt)
            value = collector.collect(plan,'c'*64,run,jobs,root)
            self.assertEqual(value['status'],'refused')
            self.assertIsNone(value['comparison'])

    def test_capture_failure_limits_and_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = capture.capture([sys.executable,'-c','print("ok")'],root/'ok.json','setup_ms','test',1)
            self.assertEqual(result['returncode'],0)
            self.assertGreater(result['end_ns'],result['start_ns'])
            with self.assertRaises(FileExistsError):
                capture.capture([sys.executable,'-c','pass'],root/'ok.json','setup_ms','test',1)
            result = capture.capture([sys.executable,'-c','raise SystemExit(7)'],root/'bad.json','proof_verify_ms','test',1)
            self.assertEqual(result['returncode'],7)
            result = capture.capture([sys.executable,'-c','import time; time.sleep(30)'],root/'timeout.json','setup_ms','test',1)
            self.assertEqual(result['failure'],'TimeoutExpired')
            result = capture.capture([sys.executable,'-c','import sys; sys.stdout.write("x"*17000000)'],root/'large.json','setup_ms','test',1)
            self.assertEqual(result['failure'],'output_limit')
            self.assertLessEqual((root/'large.stdout.log').stat().st_size,capture.LIMIT)


if __name__ == '__main__':
    unittest.main()
