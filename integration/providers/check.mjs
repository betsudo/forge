// Test fixture plus optional real Forge provider-view endpoint.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createHash, randomBytes} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {NodeZkConfigProvider} from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import {FetchZkConfigProvider} from '@midnight-ntwrk/midnight-js-fetch-zk-config-provider';
import * as rt from '@midnight-ntwrk/compact-runtime';

const [bundleArg, bareArg, worker, params, workArg] = process.argv.slice(2);
assert.ok(bundleArg && bareArg && worker && params && workArg, 'five explicit qualification paths required');
const bundle = path.resolve(bundleArg), bare = path.resolve(bareArg), work = path.resolve(workArg);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const manifest = await fs.readFile(path.join(bundle, 'compiler/contract-manifest.json'));
const anchor = hash(manifest);
const options = {expectedManifestHash: anchor}; // retain default verify=require
const name = 'increment';
const files = ['compiler/contract-manifest.json', 'compiler/contract-info.json',
  `zkir/${name}.bzkir`, `keys/${name}.prover`, `keys/${name}.verifier`];
const originals = new Map(await Promise.all(files.map(async f => [f, await fs.readFile(path.join(bundle, f))])));
const token = randomBytes(32).toString('hex');
let fault;
const requests = [];
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://fixture.invalid');
    const parts = url.pathname.split('/').slice(1);
    const prefix = parts.shift(), relative = parts.join('/');
    if (!['plain', 'gzip', 'private'].includes(prefix) || !originals.has(relative)) {
      res.writeHead(404).end(); return;
    }
    // Private fixture authentication happens before any response/cache lookup.
    if (prefix === 'private' && req.headers.authorization !== `Bearer ${token}`) {
      res.writeHead(401, {'Cache-Control':'no-store'}).end(); return;
    }
    if (!['GET', 'HEAD'].includes(req.method)) {res.writeHead(405).end(); return;}
    requests.push({prefix, relative, method:req.method}); // no headers/tokens
    if (fault === 'missing-manifest' && relative.endsWith('contract-manifest.json')) {
      res.writeHead(404).end(); return;
    }
    if (fault === 'html') {
      res.writeHead(200, {'Content-Type':'text/html'}).end('<html>missing</html>'); return;
    }
    let bytes = await fs.readFile(path.join(bundle, relative));
    const headers = {'Content-Type':relative.endsWith('.json')?'application/json':'application/octet-stream',
      'Cache-Control':prefix==='private'?'no-store':'public, max-age=31536000, immutable',
      'Access-Control-Allow-Origin':'http://127.0.0.1', 'Vary':'Accept-Encoding'};
    if (prefix === 'gzip') {bytes = gzipSync(bytes); headers['Content-Encoding']='gzip';}
    headers.ETag = `"${hash(bytes)}"`;
    if (req.headers['if-none-match'] === headers.ETag) {res.writeHead(304, headers).end(); return;}
    headers['Content-Length'] = bytes.length;
    res.writeHead(200, headers).end(req.method === 'HEAD' ? undefined : bytes);
  } catch {res.writeHead(500).end();}
});
const {Contract, ledger} = await import(pathToFileURL(path.join(bundle, 'contract/index.js')).href);
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const lanes = [], controls = [];
const api = process.env.FORGE_PROVIDER_VIEW_URL;
const apiToken = process.env.FORGE_PROVIDER_VIEW_TOKEN;
const apiOptions = {...options, fetchFunc:(url, init)=>fetch(url, {...init, headers:{...init.headers, Authorization:`Bearer ${apiToken}`}})};
try {
  for (const [lane, provider] of [
    ['local', new NodeZkConfigProvider(bundle, options)],
    ['http', new FetchZkConfigProvider(`${base}/plain`, options)],
    ['http-gzip', new FetchZkConfigProvider(`${base}/gzip`, options)],
    ['http-private', new FetchZkConfigProvider(`${base}/private`, {...options,
      fetchFunc:(url, init)=>fetch(url, {...init, headers:{...init.headers, Authorization:`Bearer ${token}`}})})]
    , ...(api ? [['forge-api', new FetchZkConfigProvider(api, apiOptions)]] : [])
  ]) {
    assert.equal(await provider.getArtifactRuntimeVersion(), '0.20.0');
    const ir = await provider.getZKIR(name), prover = await provider.getProverKey(name), verifier = await provider.getVerifierKey(name);
    const data = {bzkir:ir, prover, verifier};
    for (const [extension, bytes] of Object.entries(data)) {
      const relative = extension==='bzkir'?`zkir/${name}.bzkir`:`keys/${name}.${extension}`;
      assert.deepEqual(Buffer.from(bytes), originals.get(relative));
    }
    const directory = path.join(work, lane);
    await fs.mkdir(directory);
    for (const [extension, bytes] of Object.entries(data)) await fs.writeFile(path.join(directory, `circuit.${extension}`), bytes);
    // Each lane performs a fresh contract execution and actual proof.
    const contract = new Contract({});
    const initial = await contract.initialState(rt.createConstructorContext({}, '0'.repeat(64)));
    const context = rt.createCircuitContext({circuitId:name, contractAddress:'1'.repeat(64),
      coinPublicKeyOrZswapState:initial.currentZswapLocalState, contractState:initial.currentContractState,
      privateState:initial.currentPrivateState, time:1700000000000});
    assert.equal(ledger(context.callContext.currentQueryContext.state).counter, 0n);
    const result = await contract.impureCircuits.increment(context);
    assert.equal(ledger(result.context.callContext.currentQueryContext.state).counter, 1n);
    assert.equal(result.context.callProofDataTrace.length, 1);
    const proofData = result.context.callProofDataTrace[0];
    const preimage = rt.proofDataIntoSerializedPreimage(proofData.input, proofData.output,
      proofData.publicTranscript, proofData.privateTranscriptOutputs, name);
    const preimageFile = path.join(directory, 'preimage.bin');
    await fs.writeFile(preimageFile, preimage);
    const proof = JSON.parse(execFileSync(worker, ['prove-preimage','--params-dir',params,
      '--preimage',preimageFile,'--output',directory], {input:await fs.readFile(path.join(bundle,`zkir/${name}.zkir`)), timeout:120000}));
    for (const flag of ['valid_proof_verified','invalid_statement_rejected','corrupt_proof_rejected']) {
      assert.equal(proof.proof_controls[flag], true);
    }
    lanes.push({lane, artifact_runtime_version:'0.20.0', execution_assertions:3,
      artifact_sha256:Object.fromEntries(Object.entries(data).map(([k,v])=>[k,hash(v)])),
      proof_controls:proof.proof_controls});
  }
  const refuses = async (label, operation) => {await assert.rejects(operation); controls.push(label);};
  await refuses('bare-export-default-integrity', ()=>new NodeZkConfigProvider(bare).getProverKey(name));
  await refuses('bare-export-missing-runtime', ()=>new NodeZkConfigProvider(bare).getArtifactRuntimeVersion());
  await refuses('wrong-local-manifest-anchor', ()=>new NodeZkConfigProvider(bundle,{expectedManifestHash:'0'.repeat(64)}).getProverKey(name));
  await refuses('wrong-fetch-manifest-anchor', ()=>new FetchZkConfigProvider(`${base}/plain`,{expectedManifestHash:'0'.repeat(64)}).getProverKey(name));
  const proverPath = path.join(bundle, `keys/${name}.prover`), originalProver = originals.get(`keys/${name}.prover`);
  const changed = Buffer.from(originalProver); changed[changed.length-1] ^= 1;
  try {
    await fs.writeFile(proverPath, changed);
    await refuses('corrupt-local-prover', ()=>new NodeZkConfigProvider(bundle,options).getProverKey(name));
    await refuses('corrupt-fetch-prover', ()=>new FetchZkConfigProvider(`${base}/plain`,options).getProverKey(name));
  } finally {await fs.writeFile(proverPath, originalProver);}
  fault = 'missing-manifest';
  await refuses('missing-fetch-manifest', ()=>new FetchZkConfigProvider(`${base}/plain`,options).getProverKey(name));
  fault = 'html';
  await refuses('html-fallback', ()=>new FetchZkConfigProvider(`${base}/plain`,options).getProverKey(name));
  fault = undefined;
  await refuses('missing-authentication', ()=>new FetchZkConfigProvider(`${base}/private`,options).getProverKey(name));
  await refuses('unsafe-local-name', ()=>new NodeZkConfigProvider(bundle,options).getProverKey('../escape'));
  await refuses('unsafe-fetch-name', ()=>new FetchZkConfigProvider(`${base}/plain`,options).getProverKey('../escape'));
  const response = await fetch(`${base}/plain/keys/${name}.prover`,{method:'HEAD'});
  assert.equal(response.status,200); assert.equal(Number(response.headers.get('content-length')), originalProver.length);
  assert.equal((await response.arrayBuffer()).byteLength,0);
  const conditional = await fetch(`${base}/plain/keys/${name}.prover`, {headers:{'If-None-Match':response.headers.get('etag')}});
  assert.equal(conditional.status,304);
  controls.push('head-length','conditional-etag');
  assert.equal(hash(await fs.readFile(path.join(bundle,'compiler/contract-manifest.json'))),anchor);
  if (api) {
    await refuses('forge-api-wrong-anchor', ()=>new FetchZkConfigProvider(api,{...apiOptions, expectedManifestHash:'0'.repeat(64)}).getProverKey(name));
    assert.equal((await fetch(`${api}/keys/${name}.prover`)).status,401);
    const head = await fetch(`${api}/keys/${name}.prover`,{method:'HEAD',headers:{Authorization:`Bearer ${apiToken}`}});
    assert.equal(head.status,200);
    assert.equal(Number(head.headers.get('content-length')),originalProver.length);
    controls.push('forge-api-auth','forge-api-head');
  }
  console.log(JSON.stringify({schema:1, manifest_sha256:anchor, lanes, controls, requests,
    scope:'native developer-host Node providers and isolated HTTP/gzip/auth fixture; genuine proofs; not browser, TLS/CDN, production Forge provider API or Linux qualification'}));
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
