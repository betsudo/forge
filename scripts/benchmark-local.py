#!/usr/bin/env python3
"""Fresh one-circuit cold/warm/eviction experiment. Never records test passes as cache entries."""
import argparse,json,os,pathlib,subprocess,tempfile,time
p=argparse.ArgumentParser()
p.add_argument('--binary',required=True,type=pathlib.Path)
p.add_argument('--output',required=True,type=pathlib.Path)
a=p.parse_args();binary=a.binary.resolve()
fixture=pathlib.Path(__file__).resolve().parent.parent/'fixtures/assert.zkir'
with tempfile.TemporaryDirectory(prefix='zkir-forge-benchmark-') as directory:
    root=pathlib.Path(directory)
    def run(label,*args):
        usage=root/(label+'.usage')
        command=[str(binary),'--cache-dir',str(root/'cache'),*args]
        if os.uname().sysname=='Darwin':command=['/usr/bin/time','-l','-o',str(usage),*command]
        clock=time.monotonic();result=subprocess.run(command,text=True,capture_output=True,check=True)
        value=json.loads(result.stdout)
        entry={'result':value,'process_wall_ms':(time.monotonic()-clock)*1000}
        if usage.exists():
            text=usage.read_text();entry['time_l']=text
            for line in text.splitlines():
                if 'maximum resident set size' in line:entry['peak_process_rss_bytes']=int(line.split()[0])
        return entry
    cold=run('cold','prepare',str(fixture));bundle=cold['result']['bundle_id']
    warm=run('warm','prepare',str(fixture))
    assert not cold['result']['cache']['hit'] and warm['result']['cache']['hit']
    assert cold['result']['artifact_set_id']==warm['result']['artifact_set_id']
    evict=run('evict','evict',bundle)
    regenerated=run('regenerated','ensure',bundle)
    assert not regenerated['result']['cache']['hit']
    assert cold['result']['artifact_set_id']==regenerated['result']['artifact_set_id']
    stats=run('stats','stats')
    profile=run('profile','profile')
    record={'schema':1,'fixture':'fixtures/assert.zkir','profile':profile['result'],'scope':'one genuine minimal assert circuit; fresh private store; process RSS includes runtime and parameters, excludes compilation and other processes; temporary exports removed after experiment','cold':cold,'warm':warm,'evict':evict,'regenerated':regenerated,'stats':stats,'wall_speedup':cold['process_wall_ms']/warm['process_wall_ms']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'cold_wall_ms':cold['process_wall_ms'],'warm_wall_ms':warm['process_wall_ms'],'cold_ensure_ms':cold['result']['cache']['elapsed_ms'],'warm_ensure_ms':warm['result']['cache']['elapsed_ms'],'wall_speedup':record['wall_speedup'],'evidence':str(a.output)}))
