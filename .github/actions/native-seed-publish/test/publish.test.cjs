// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { main, snapshotFiles, checkedCompactGuard, checkPlanBindings } = require('../publish.cjs');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
test('default off needs no prepared/key/window/API/SDK access', async () => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'forge-default-off-'));
  try {
    const output=path.join(root,'report.json');
    const report=await main({INPUT_ENABLED:'false',INPUT_OUTPUT:output});
    assert.equal(report.reason,'default_off'); assert.equal(report.published,false);
    assert.equal(JSON.parse(fs.readFileSync(output)).reason,'default_off');
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
test('snapshot byte inventory refuses missing extra mutated and symlink payloads',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'forge-snapshot-bytes-'));
  const identity='a'.repeat(64),partition='b'.repeat(64);
  const bytes=Buffer.from('official snapshot bytes');
  try {
    fs.writeFileSync(path.join(root,'payload'),bytes);
    fs.writeFileSync(path.join(root,'snapshot.json'),JSON.stringify({snapshot_id:identity,partition,
      files:[{path:'payload',bytes:bytes.length,sha256:hash(bytes)}]}));
    assert.equal(snapshotFiles(root,identity,partition).payload,hash(bytes));
    fs.appendFileSync(path.join(root,'payload'),'changed');
    assert.throws(()=>snapshotFiles(root,identity,partition));
    fs.writeFileSync(path.join(root,'payload'),bytes);fs.writeFileSync(path.join(root,'extra'),'unexpected');
    assert.throws(()=>snapshotFiles(root,identity,partition));fs.unlinkSync(path.join(root,'extra'));
    fs.unlinkSync(path.join(root,'payload'));assert.throws(()=>snapshotFiles(root,identity,partition));
    fs.symlinkSync(path.join(root,'snapshot.json'),path.join(root,'payload'));assert.throws(()=>snapshotFiles(root,identity,partition));
    assert.throws(()=>snapshotFiles(root,'c'.repeat(64),partition));
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});

test('only original keyed Compact guard executes and live tool refusal propagates', () => {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'forge-compact-guard-'));
  const name='tools/compact-rust-backend/prepare_native_seed.py', guard=path.join(root,name), plan=path.join(root,'plan');
  fs.mkdirSync(path.dirname(guard),{recursive:true});fs.mkdirSync(plan);
  const tool=path.join(plan,'tool');fs.writeFileSync(tool,'original');
  const source="import pathlib,sys\nassert sys.argv[1]=='--guard-plan'\nassert (pathlib.Path(sys.argv[2])/'tool').read_text()=='original'\n";
  fs.writeFileSync(guard,source);
  const key={workspace:root,inputs:[{path:name,sha256:hash(source)}]};
  try {
    const live=checkedCompactGuard(key,guard,plan);live();
    fs.writeFileSync(tool,'changed');assert.throws(live);fs.writeFileSync(tool,'original');
    fs.appendFileSync(guard,'# changed');assert.throws(live);fs.writeFileSync(guard,source);
    assert.throws(()=>checkedCompactGuard({...key,inputs:[]},guard,plan));
    assert.throws(()=>checkedCompactGuard(key,path.join(root,'other.py'),plan));
  } finally {fs.rmSync(root,{recursive:true,force:true});}
});

test('official report inputs cannot mix another plan key baseline store or executable', () => {
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'forge-plan-bindings-')));
  const plan=path.join(root,'plan'), other=path.join(root,'other');fs.mkdirSync(plan);fs.mkdirSync(other);
  const binary=path.join(root,'forge');fs.writeFileSync(binary,'original executable');
  for (const folder of [plan,other]) {
    fs.mkdirSync(path.join(folder,'cache'));fs.writeFileSync(path.join(folder,'key.json'),'{}');fs.writeFileSync(path.join(folder,'baseline.json'),'{}');
  }
  fs.writeFileSync(path.join(plan,'invocation.json'),JSON.stringify({tools:{forge:{path:binary,sha256:hash('original executable')}}}));
  const env={'INPUT_COMPACT-PLAN':plan,INPUT_KEY:path.join(plan,'key.json'),INPUT_BASELINE:path.join(plan,'baseline.json'),'INPUT_CACHE-DIR':path.join(plan,'cache'),INPUT_BINARY:binary};
  try {
    checkPlanBindings(env);
    for (const [input,name] of [['INPUT_KEY','key.json'],['INPUT_BASELINE','baseline.json'],['INPUT_CACHE-DIR','cache']])
      assert.throws(()=>checkPlanBindings({...env,[input]:path.join(other,name)}));
    const alternate=path.join(root,'alternate');fs.writeFileSync(alternate,'original executable');
    assert.throws(()=>checkPlanBindings({...env,INPUT_BINARY:alternate}));
    fs.writeFileSync(binary,'changed');assert.throws(()=>checkPlanBindings(env));
  } finally {fs.rmSync(root,{recursive:true,force:true});}
});
