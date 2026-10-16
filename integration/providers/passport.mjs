// Exact selected Passport application proofs; complete compiler bundle remains unchanged.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {NodeZkConfigProvider} from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import {FetchZkConfigProvider} from '@midnight-ntwrk/midnight-js-fetch-zk-config-provider';

const [bundleArg, worker, params, workArg] = process.argv.slice(2);
assert.ok(bundleArg && worker && params && workArg);
const bundle = path.resolve(bundleArg), work = path.resolve(workArg);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const anchor = hash(await fs.readFile(path.join(bundle,'compiler/contract-manifest.json')));
const providers = [['local',new NodeZkConfigProvider(bundle,{expectedManifestHash:anchor})]];
if (process.env.FORGE_PROVIDER_VIEW_URL) {
  const token = process.env.FORGE_PROVIDER_VIEW_TOKEN;
  assert.ok(token);
  providers.push(['fetch',new FetchZkConfigProvider(process.env.FORGE_PROVIDER_VIEW_URL,{
    expectedManifestHash:anchor,fetchFunc:(url,init)=>fetch(url,{...init,
      headers:{...init.headers,Authorization:`Bearer ${token}`}})})]);
}
const lanes=[];
for (const [lane,provider] of providers) {
  assert.equal(await provider.getArtifactRuntimeVersion(),'0.20.0');
  for (const name of ['deposit_unshielded','activate_initial_device_with_jubjub']) {
    const directory=path.join(work,`${lane}-${name}`);
    await fs.mkdir(directory,{recursive:true});
    const [bzkir,prover,verifier]=await Promise.all([
      provider.getZKIR(name),provider.getProverKey(name),provider.getVerifierKey(name)]);
    const artifacts={bzkir,prover,verifier};
    for (const [extension,bytes] of Object.entries(artifacts)) {
      const relative=extension==='bzkir'?`zkir/${name}.bzkir`:`keys/${name}.${extension}`;
      assert.deepEqual(Buffer.from(bytes),await fs.readFile(path.join(bundle,relative)));
      await fs.writeFile(path.join(directory,`circuit.${extension}`),bytes);
    }
    const preimage=path.join(directory,'preimage.bin');
    // Copy exact generated JS into the pinned test npm project's owned scratch so
    // runtime imports resolve without modifying consumer dependencies or output.
    const runtime=path.join(directory,'contract');
    await fs.cp(path.join(bundle,'contract'),runtime,{recursive:true});
    const generator=path.join(directory,'make-preimage.mjs');
    await fs.copyFile(new URL('../../benchmarks/passport/make-preimage.mjs',import.meta.url),generator);
    const execution=JSON.parse(execFileSync(process.execPath,[generator,path.join(runtime,'index.js'),preimage,name],{timeout:120000}));
    const proof=JSON.parse(execFileSync(worker,['prove-preimage','--params-dir',params,
      '--preimage',preimage,'--output',directory],{
      input:await fs.readFile(path.join(bundle,`zkir/${name}.zkir`)),timeout:600000}));
    for (const flag of ['valid_proof_verified','invalid_statement_rejected','corrupt_proof_rejected'])
      assert.equal(proof.proof_controls[flag],true);
    assert.equal(execution.assertions,9);
    lanes.push({lane,circuit:name,execution,
      artifact_sha256:Object.fromEntries(Object.entries(artifacts).map(([k,v])=>[k,hash(v)])),
      proof_controls:proof.proof_controls});
  }
}
console.log(JSON.stringify({manifest_sha256:anchor,lanes,provenance:{
  node:process.version,worker_sha256:hash(await fs.readFile(worker)),
  sdk_package_lock_sha256:hash(await fs.readFile(new URL('./package-lock.json',import.meta.url))),
  proof_harness_sha256:hash(await fs.readFile(new URL(import.meta.url))),
  preimage_generator_sha256:hash(await fs.readFile(new URL('../../benchmarks/passport/make-preimage.mjs',import.meta.url)))
}}));
