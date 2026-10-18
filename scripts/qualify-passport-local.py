#!/usr/bin/env python3
"""Full-roster local adapter qualification; selected genuine Passport proofs, owned scratch only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT/'integration/providers'
NAMES = ['deposit_unshielded','activate_initial_device_with_jubjub']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def inventory(root):
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def qualify(args):
    binary = args.binary.absolute()
    compiler, params, source, baseline = [p.resolve(strict=True) for p in
        [args.compiler_dir,args.params_dir,args.source,args.baseline]]
    args.output = args.output.resolve()
    saved_qualification = args.output.with_name(getattr(args, 'qualification_name', 'passport-adapter-qualification-local.json'))
    assert args.output != saved_qualification, 'result and qualification policy must be distinct'
    assert not args.output.exists() and not saved_qualification.exists(), 'fresh receipts required'
    for removed in [baseline,*(baseline.parent/name for name in ['independent-cache','adapter-cache','local-cold','local-warm'])]:
        assert not args.output.is_relative_to(removed) and not saved_qualification.is_relative_to(removed), 'receipt inside cleanup target'
    assert not args.output.resolve().is_relative_to(baseline), 'receipt cannot be removed with baseline'
    baseline.relative_to(getattr(args, 'work', ROOT/'.local/milestone-2026.10.1/passport'))
    assert baseline.name == 'native-off', 'only explicitly owned baseline allowed'
    expected = json.loads((ROOT/'benchmarks/passport/consumer-files.json').read_text())
    for name,digest in expected['files'].items(): assert sha(source/name) == digest
    closure = json.loads((baseline.parent/'source-inventory.json').read_text())
    anchored = json.loads((ROOT/'docs/evidence/passport-full-models-local.json').read_text())['source_closure']
    assert closure == anchored and closure['revision'] == expected['commit']
    for name, facts in closure['files'].items():
        assert sha(source/name) == facts['sha256'], 'changed imported Compact source'
        data = (source/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == facts['git_blob']
    official = getattr(args, 'cohort', None)
    if official is None:
        assert platform.system() == 'Darwin' and platform.machine() == 'arm64', 'historical Mac cohort requires native ARM64 macOS'
        old = json.loads((ROOT/'docs/evidence/passport-exact-profile.json').read_text())
        official = {'tool_sha256':{name:old['tool_sha256']['tools/compiler/'+name] for name in ['compactc.bin','zkir-v3']}}
    for name in ['compactc.bin','zkir-v3']:
        assert sha(compiler/name) == official['tool_sha256'][name]
    assert {p.name:sha(p) for p in (baseline/'zkir').glob('*.zkir')} == expected['emitted_zkir_sha256']
    worker = binary.parent/'midnight-zkir-forge-zkir31-worker'
    reference = inventory(baseline)
    baseline_size = sum(p.stat().st_size for p in baseline.rglob('*') if p.is_file())
    assert shutil.disk_usage(baseline).free > 2*baseline_size+10*1024**3, 'insufficient scratch headroom for full-roster qualification'
    environment = dict(os.environ, MIDNIGHT_PP=str(params))
    for key in ['MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER','MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER',
                'FORGE_PROVIDER_VIEW_URL','FORGE_PROVIDER_VIEW_TOKEN']:
        environment.pop(key,None)

    def run(command, **kwargs):
        import signal
        with subprocess.Popen(list(map(str,command)), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=environment, start_new_session=True, **kwargs) as process:
            try: stdout, stderr = process.communicate(timeout=7200)
            except BaseException:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.communicate()
                raise
            if process.returncode: raise RuntimeError(str(command[:2])+': '+stderr[-4000:])
            return stdout

    def cli(cache,*command):
        return json.loads(run([binary,'--cache-dir',cache,'--params-dir',params,*command]))

    proof_scratch = PROJECT/'.local'
    proof_scratch.mkdir(exist_ok=True)

    def proofs(bundle):
        with tempfile.TemporaryDirectory(prefix='passport-proof-',dir=proof_scratch) as directory:
            return json.loads(run(['node',PROJECT/'passport.mjs',bundle,worker,params,Path(directory).resolve()]))

    # Independent official artifacts are compared before the hook receipt exists.
    work = baseline.parent
    cache = work/'independent-cache'
    assert not cache.exists(), 'independent cache must start absent'
    materialization = []
    for circuit in sorted(expected['emitted_zkir_sha256']):
        name = Path(circuit).stem
        started = time.monotonic()
        prepared = cli(cache,'--profile','zkir31','prepare',baseline/'zkir'/circuit,'--name',name)
        assert prepared['cache']['hit'] is False
        descriptor = prepared['descriptor']
        assert descriptor['record']['worker']['executable_sha256'] == sha(worker)
        artifacts = {}
        for entry in prepared['export']['files']:
            target = {'source':baseline/'zkir'/circuit,'binary_ir':baseline/'zkir'/(name+'.bzkir'),
                      'prover':baseline/'keys'/(name+'.prover'),'verifier':baseline/'keys'/(name+'.verifier')}[entry['kind']]
            assert sha(target) == entry['sha256'] == sha(Path(entry['path']))
            artifacts[entry['kind']] = entry['sha256']
        materialization.append({'circuit':name,'descriptor':descriptor,'official_artifact_sha256':artifacts,
                                'cold_prepare_ms':(time.monotonic()-started)*1000})
        print(json.dumps({'independently_matched':name,'count':len(materialization),'of':52}),flush=True)
    assert len(materialization) == 52
    native_proof_started = time.monotonic()
    provider_checks = proofs(baseline)
    native_proof_wall_ms = (time.monotonic()-native_proof_started)*1000
    provider_budget = {'full_bundle_bytes':baseline_size,
        'largest_file_bytes':max(p.stat().st_size for p in baseline.rglob('*') if p.is_file()),
        'max_file_bytes':1024**3,'max_view_bytes':4*1024**3}
    if baseline_size > 4*1024**3 or provider_budget['largest_file_bytes'] > 1024**3:
        probe = subprocess.run([binary,'--cache-dir',work/'limit-probe-cache','publish-view',baseline,
            '--manifest-sha256',sha(baseline/'compiler/contract-manifest.json'),
            '--provider-root',work/'limit-probe-views'],capture_output=True,text=True,env=environment,timeout=60)
        assert probe.returncode != 0 and (not (work/'limit-probe-views').exists() or not any((work/'limit-probe-views').iterdir()))
        provider_budget.update({'complete_http_view_qualified':False,'actual_publication_refusal':json.loads(probe.stdout)})
        if (work/'limit-probe-views').exists(): shutil.rmtree(work/'limit-probe-views')
        if (work/'limit-probe-cache').exists():shutil.rmtree(work/'limit-probe-cache')
    else:
        provider_budget['complete_http_view_qualified'] = False  # Node-only consumer harness
    qualification = {'schema':1,'status':'passed','tool_sha256':{name:sha(path) for name,path in
        [('compactc.bin',compiler/'compactc.bin'),('zkir-v3',compiler/'zkir-v3'),('forge',binary),('worker',worker)]},
        'materialization':materialization,'provider_checks':provider_checks,
        'scope':'All52 intercepted artifact triples independently match official output; genuine selected-two Node SDK proofs only, ' + getattr(args, 'platform_scope', 'native macOS ARM64') + '.'}
    qpath = work/'adapter-qualification.json'
    assert not qpath.exists()
    qpath.write_text(json.dumps(qualification,indent=2)+'\n')
    qhash = sha(qpath)
    native_start = json.loads((work/'native-off-start.json').read_text())
    native_status = json.loads((work/'native-off-result.json').read_text())
    assert native_status['returncode'] == 0
    native_wall_ms = native_status.get('wall_ms')
    if native_wall_ms is None:
        native_wall_ms = ((baseline/'compiler/contract-manifest.json').stat().st_mtime-native_start['process_start_epoch'])*1000
    rows = [{'lane':'native-off','original_inventory':reference,'provider_checks':provider_checks,
             'compile_wall_ms' if 'wall_ms' in native_status else 'compile_wall_ms_approx':native_wall_ms,'compile_timing_scope':native_start['measurement'],
             'proof_test_wall_ms':native_proof_wall_ms,
             'compiler_command':['compiler-local.py','--mode','off','--feature-zkir-v3 (native invocation)','account.compact','native-off'],
             'compiler_completed_manifest':True,'compiler_exit_status':native_status['returncode']}]
    # Preserve hashes/evidence, never several extra full-roster key copies.
    shutil.rmtree(cache)
    shutil.rmtree(baseline)
    cache = work/'adapter-cache'
    assert not cache.exists()
    for label in ['local-cold','local-warm']:
        out = work/label
        assert not out.exists()
        invocation = [sys.executable,ROOT/'scripts/compiler-local.py','--mode','local',
            '--compiler-dir',compiler,'--binary',binary,'--params-dir',params,
            '--cache-dir',cache,'--qualification',qpath,'--qualification-sha256',qhash,
            '--keygen-timeout-seconds','1800',source/'contract/contracts/account.compact',out]
        lane_started = time.monotonic()
        start = time.monotonic()
        run(invocation)
        compile_ms = (time.monotonic()-start)*1000
        assert inventory(out) == reference, 'original full compiler output/metadata changed'
        start = time.monotonic()
        provider = proofs(out)
        proof_ms = (time.monotonic()-start)*1000
        stats = cli(cache,'stats')
        rows.append({'lane':label,'compile_wall_ms':compile_ms,'proof_test_wall_ms':proof_ms,
                     'whole_lane_wall_ms':(time.monotonic()-lane_started)*1000,'provider_checks':provider,'stats':stats,
                     'original_inventory_byte_identical':True})
        print(json.dumps({'lane':label,'compile_ms':compile_ms,'proof_ms':proof_ms}),flush=True)
        if label == 'local-cold': shutil.rmtree(out)
    cold,warm = rows[1]['stats']['totals'],rows[2]['stats']['totals']
    assert cold['requests'] == 52 and cold['misses'] == 52 and cold['hits'] == 0 and cold['errors'] == 0
    assert warm['requests']-cold['requests'] == 52 and warm['hits']-cold['hits'] == 52
    assert warm['misses'] == cold['misses'] and warm['errors'] == 0
    # Consumer-specific recovery: every repaired path feeds fresh SDK proofs.
    out = work/'local-warm'
    selected = out/'zkir/deposit_unshielded.zkir'
    prepared = cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded')
    identity = prepared['artifact_set_id']
    descriptor = prepared['descriptor']
    controls = []
    # Damage the final compiler output, not just the Forge export cache. The
    # original compiler manifest stays independently pinned throughout repair.
    consumer_prover = out/'keys/deposit_unshielded.prover'
    original_prover = consumer_prover.read_bytes()
    consumer_prover.write_bytes(b'damaged final compiler output')
    try:
        try: proofs(out)
        except RuntimeError as error:
            assert 'ZkArtifactIntegrityError' in str(error), 'unexpected SDK failure during integrity control'
        else: raise AssertionError('SDK accepted damaged compiler output')
    finally:
        consumer_prover.write_bytes(original_prover)
    assert inventory(out) == reference
    controls.append({'control':'final-compiler-output-integrity-refusal-explicit-exact-repair',
                     'provider_checks':proofs(out)})

    def refused(*command):
        result = subprocess.run(list(map(str,[binary,'--cache-dir',cache,'--params-dir',params,*command])),
                                capture_output=True,text=True,timeout=180,env=environment)
        assert result.returncode != 0
        error = json.loads(result.stdout)['error']
        assert not error['availability_fallback']
        return error['code']

    def repaired_proofs(label, recovered):
        assert recovered['artifact_set_id'] == identity and recovered['descriptor'] == descriptor
        for entry in recovered['export']['files']:
            kind = entry['kind']
            if kind == 'source': continue
            destination = {'binary_ir':selected.with_suffix('.bzkir'),
                'prover':out/'keys/deposit_unshielded.prover','verifier':out/'keys/deposit_unshielded.verifier'}[kind]
            assert sha(Path(entry['path'])) == entry['sha256'] == sha(destination)
            shutil.copyfile(entry['path'],destination)
        return {'control':label,'artifact_identity_preserved':True,'provider_checks':proofs(out)}

    pk = next(entry for entry in prepared['export']['files'] if entry['kind'] == 'prover')
    cas = cache/'objects'/pk['sha256']
    with cas.open('r+b') as stream:
        stream.seek(-1,2);tail=stream.read(1);stream.seek(-1,2);stream.write(bytes([tail[0]^1]))
    try: assert refused('--profile','zkir31','prepare',selected,'--name','deposit_unshielded') == 'integrity_error'
    finally:
        with cas.open('r+b') as stream: stream.seek(-1,2);stream.write(tail)
    controls.append(repaired_proofs('corrupt-CAS-refusal-owner-restores-exact-byte',
        cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded')))
    export = Path(prepared['export']['base'])
    export.relative_to(cache/'exports')
    Path(pk['path']).write_bytes(b'corrupt owned consumer export')
    assert refused('--profile','zkir31','prepare',selected,'--name','deposit_unshielded') == 'integrity_error'
    shutil.rmtree(export)
    repaired = cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded')
    assert repaired['cache']['hit']
    controls.append(repaired_proofs('corrupt-export-refusal-explicit-owner-repair',repaired))
    shutil.rmtree(export)
    recovered = cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded')
    assert recovered['cache']['hit']
    controls.append(repaired_proofs('missing-export-warm-reconstruction',recovered))
    cli(cache,'evict',prepared['bundle_id'])
    regenerated = cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded')
    assert not regenerated['cache']['hit']
    controls.append(repaired_proofs('eviction-regeneration-verifier-identity',regenerated))
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_results = list(pool.map(lambda _:cli(cache,'--profile','zkir31','prepare',selected,'--name','deposit_unshielded'),range(2)))
    assert all(result['cache']['hit'] and result['artifact_set_id'] == identity for result in concurrent_results)
    controls.append(repaired_proofs('concurrent-local-callers-same-identity',concurrent_results[0]))
    assert refused('--profile','zkir3','prepare',selected,'--name','deposit_unshielded') == 'profile_format_mismatch'
    wrong = invocation.copy()
    wrong[wrong.index('--qualification-sha256')+1] = '0'*64
    before = sha(out/'compiler/contract-manifest.json')
    result = subprocess.run(list(map(str,wrong)),capture_output=True,text=True,timeout=30,env=environment)
    assert result.returncode and 'qualification digest mismatch' in result.stderr
    assert sha(out/'compiler/contract-manifest.json') == before
    controls.append({'control':'wrong-profile-and-qualification-refuse-before-compiler-cleanup'})
    final_stats = cli(cache,'stats')
    # Keep fresh qualification policy as evidence; cache/compiled/private proof copies go away.
    saved_qualification = args.output.with_name(getattr(args, 'qualification_name', 'passport-adapter-qualification-local.json'))
    assert not saved_qualification.exists() and not saved_qualification.is_relative_to(cache)
    assert inventory(out) == reference, 'recovery changed original complete compiler output'
    saved_qualification.write_bytes(qpath.read_bytes())
    assert sha(saved_qualification) == qhash
    shutil.rmtree(out)
    shutil.rmtree(cache)
    receipt = {'schema':1,'status':'passed','host':platform.platform(),
        'native_host':getattr(args, 'qualification_host', None),
        'cohort_sha256':getattr(args, 'cohort_sha256', None),
        'cohort_tool_sha256':getattr(args, 'cohort', {}).get('tool_sha256'),'consumer_commit':expected['commit'],
        'source_closure':json.loads((work/'source-inventory.json').read_text()),
        'tools':qualification['tool_sha256'],'qualification_sha256':qhash,
        'qualified_artifact_circuits':52,'application_proof_circuits':NAMES,
        'provider_budget':provider_budget,'full_bundle_bytes':baseline_size,'rows':rows,'recovery_controls':controls,'post_controls_stats':final_stats,
        'saved_qualification':saved_qualification.name,'cleanup':'owned baseline, independent/adapter stores, compiled lane outputs and private proof/preimage copies removed after evidence capture',
        'scope':getattr(args, 'platform_scope', 'Native macOS ARM64')+' full compiler adapter/Node provider; selected2 application proofs, not52 proofs or hostedCI savings. Full large-bundle HTTP serving is a separate qualification.',
        'source_inventory_sha256':sha(work/'source-inventory.json'),
        'sdk_package_lock_sha256':sha(PROJECT/'package-lock.json'),
        'harness_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),PROJECT/'passport.mjs',ROOT/'scripts/compiler-local.py',ROOT/'benchmarks/passport/make-preimage.mjs']}}
    with args.output.open('x') as stream:
        json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(args.output),'qualified_artifacts':52,'selected_proofs':sum(len(row['provider_checks']['lanes']) for row in rows)+sum(len(control.get('provider_checks',{}).get('lanes',[])) for control in controls)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['binary','compiler-dir','params-dir','source','baseline','output']:
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    qualify(args)


def interrupted(_signal, _frame):
    raise RuntimeError('Passport qualification interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM,interrupted)
    main()
