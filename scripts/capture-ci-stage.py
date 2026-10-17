#!/usr/bin/env python3
"""Capture one bounded sequential stage; never invent whole-job or transport data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import selectors
import time

STAGES = ('setup_ms','codegen_ms','key_prepare_ms','proof_verify_ms','download_ms','upload_ms')
LIMIT = 16*1024**2


def capture(command, output, stage, clock, timeout, context=None):
    if not command or not 1 <= timeout <= 7200:
        raise ValueError('argument-array command and timeout 1..7200 required')
    stdout = output.with_suffix('.stdout.log')
    stderr = output.with_suffix('.stderr.log')
    with output.open('x') as receipt, stdout.open('xb') as out, stderr.open('xb') as err:
        started = time.monotonic_ns()
        reason, status = None, -1
        def stop(process, force=False):
            try: os.killpg(process.pid,signal.SIGKILL if force else signal.SIGTERM)
            except ProcessLookupError: pass
            except PermissionError:
                # Some macOS exit races return EPERM for the old group. Ensure
                # the leader is stopped too; inherited pipes still have a bound.
                if process.poll() is None:
                    try: process.kill()
                    except ProcessLookupError: pass
        try:
            with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True) as process:
                deadline = time.monotonic()+timeout
                draining_until = None
                with selectors.DefaultSelector() as selector:
                    for source, destination in [(process.stdout,out),(process.stderr,err)]:
                        os.set_blocking(source.fileno(),False)
                        selector.register(source,selectors.EVENT_READ,[destination,0])
                    try:
                        while selector.get_map():
                            now = time.monotonic()
                            if now >= deadline and reason is None:
                                reason = 'TimeoutExpired'
                                stop(process)
                            if (reason is not None or process.poll() is not None) and draining_until is None:
                                stop(process)
                                draining_until = now+(1 if process.poll() is not None else 3)
                            if draining_until is not None and now >= draining_until:
                                reason = reason or 'inherited_pipes'
                                stop(process,force=True)
                                break
                            for key, _ in selector.select(.05):
                                try: chunk = os.read(key.fd,128*1024)
                                except BlockingIOError: continue
                                if not chunk:
                                    selector.unregister(key.fileobj)
                                    continue
                                destination, total = key.data
                                destination.write(chunk[:max(0,LIMIT-total)])
                                key.data[1] += len(chunk)
                                if key.data[1] > LIMIT:
                                    reason = 'output_limit'
                                    stop(process)
                        if process.poll() is None:
                            status = process.wait(timeout=max(.01,deadline-time.monotonic()))
                        else: status = process.returncode
                    except BaseException as error:
                        reason = reason or type(error).__name__
                        stop(process)
                        try: process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            stop(process,force=True)
                            process.wait(timeout=1)
                    finally:
                        process.stdout.close()
                        process.stderr.close()
                        stop(process)
                        # EOF and a successful leader do not prove its workers
                        # exited: a background child may ignore TERM and use
                        # DEVNULL. Always finish the owned group after grace.
                        time.sleep(.1)
                        stop(process,force=True)
        except OSError as error:
            reason = type(error).__name__
        out.flush()
        err.flush()
        value = {'schema':1,'stage':stage,'clock':clock,'command':command,'start_ns':started,
            'end_ns':time.monotonic_ns(),'returncode':status if reason is None else -1,'failure':reason,
            'stdout':stdout.name,'stderr':stderr.name,
            'producer':context or {'evidence_kind':'synthetic'}}
        for key, path in [('stdout',stdout),('stderr',stderr)]:
            with path.open('rb') as stream:
                value[key+'_sha256'] = hashlib.file_digest(stream,'sha256').hexdigest()
        receipt.write(json.dumps(value,indent=2)+'\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    parser.add_argument('--clock',required=True,help='same job/boot clock identity for every stage')
    parser.add_argument('--timeout',type=int,default=1800)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--run-id',required=True,type=int)
    parser.add_argument('--run-attempt',required=True,type=int)
    parser.add_argument('--job-id',required=True,type=int)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not re.fullmatch('[0-9a-f]{64}',args.plan_sha256) or min(args.run_id,args.run_attempt,args.job_id) < 1:
        raise ValueError('exact plan digest and positive run/attempt/job IDs required')
    hosted = (os.environ.get('GITHUB_ACTIONS') == 'true' and platform.system() == 'Linux' and
              platform.machine() == 'x86_64' and os.environ.get('RUNNER_ARCH') == 'X64')
    context = {'evidence_kind':'hosted' if hosted else 'local','plan_sha256':args.plan_sha256,
        'run_id':args.run_id,'run_attempt':args.run_attempt,'job_id':args.job_id}
    value = capture(command,args.output,args.stage,args.clock,args.timeout,context)
    return 0 if value['returncode'] == 0 else 1


class CaptureInterrupted(Exception):
    pass


def interrupted(_signal, _frame):
    raise CaptureInterrupted('stage capture interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM,interrupted)
    sys.exit(main())
