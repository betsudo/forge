#!/usr/bin/env python3
"""Explicit real local CLI acceptance, including a killed writer. Requires parameters."""
import argparse,json,pathlib,sqlite3,subprocess,tempfile,time
p=argparse.ArgumentParser();p.add_argument('--binary',required=True,type=pathlib.Path);p.add_argument('--input',type=pathlib.Path);a=p.parse_args()
binary=a.binary.resolve();fixture=a.input.resolve() if a.input else pathlib.Path(__file__).resolve().parent.parent/'fixtures/assert.zkir'
with tempfile.TemporaryDirectory(prefix='forge-cli-acceptance-') as directory:
    root=pathlib.Path(directory);cache=root/'cache';cache.mkdir()
    command=[str(binary),'--cache-dir',str(cache)]
    registration=subprocess.run([*command,'import',str(fixture)],check=True,capture_output=True,text=True)
    bundle=json.loads(registration.stdout)['bundle_id']
    worker=subprocess.Popen([*command,'ensure',bundle],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    killed=False;deadline=time.monotonic()+5
    while worker.poll() is None and time.monotonic()<deadline:
        db=sqlite3.connect(cache/'index.sqlite3',timeout=0)
        try:
            db.execute('BEGIN IMMEDIATE');db.rollback()
        except sqlite3.OperationalError as error:
            if 'locked' not in str(error):raise
            worker.kill();killed=True;break
        finally:db.close()
        time.sleep(.002)
    stdout,stderr=worker.communicate(timeout=10)
    assert killed,'did not observe active writer in time; no crash-recovery claim'
    db=sqlite3.connect(cache/'index.sqlite3')
    assert db.execute('SELECT ready FROM bundles WHERE id=?',(bundle,)).fetchone()==(0,)
    db.close()
    recovered=subprocess.run([*command,'ensure',bundle],check=True,capture_output=True,text=True)
    recovered=json.loads(recovered.stdout)
    assert not recovered['cache']['hit']
    assert len(recovered['export']['files'])==4
    for entry in recovered['export']['files']:assert pathlib.Path(entry['path']).is_file()
    resolved=subprocess.run([*command,'resolve',bundle,'--artifact','prover'],check=True,capture_output=True,text=True)
    assert len(json.loads(resolved.stdout)['export']['files'])==1
    bad=subprocess.run([*command,'ensure','../escape'],capture_output=True,text=True)
    assert bad.returncode!=0 and json.loads(bad.stdout)['error']['code']
    print(json.dumps({'killed_writer_recovered':True,'partial_ready_rejected':True,'single_artifact_resolved':True,'structured_error':True}))
