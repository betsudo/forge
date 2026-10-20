// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { admit, pages, ACTIVE } = require('../admission.cjs');
const policy = require('../policy.json');
function fixture() {
  const partition = 'a'.repeat(64), key = 'forge-v1-' + partition + '-' + 'b'.repeat(64) + '-pilot';
  const env = { GITHUB_EVENT_NAME: 'workflow_dispatch', GITHUB_REPOSITORY: policy.repository,
    GITHUB_REF: policy.trusted_ref, GITHUB_RUN_ID: '10' };
  const window = { repository: policy.repository, run_id: '10', trusted_ref: policy.trusted_ref, approval: 'owner-approved-exclusive-window' };
  const state = { caches: [{id:1,key:'other',ref:policy.trusted_ref,size_in_bytes:100,version:'original-version'}], otherRun:false, extraJob:false };
  const page = (field, rows) => [{ total_count:rows.length,[field]:rows }];
  const read = endpoint => {
    if(endpoint.includes('/caches?')) return page('actions_caches', state.caches);
    if(endpoint.includes('/jobs?')) return page('jobs', [{id:30,status:'in_progress',name:policy.job_name},...(state.extraJob?[{id:31,status:'queued',name:'unknown writer'}]:[])]);
    const status = ACTIVE.find(value => endpoint.includes('status='+value+'&'));
    assert(status, 'unexpected API');
    return page('workflow_runs', status==='in_progress'?[{id:10,status},...(state.otherRun?[{id:11,status}]:[])]:[]);
  };
  return { context:{policy,env,window,key,partition}, state, read };
}
test('complete live inventory plus exact archive admits within reviewed assumption',()=>{
  const f=fixture(); const result=admit(f.context,{bytes:200},f.read);
  assert.equal(result.projected_bytes,300); assert.match(result.audit_scope,/not an atomic mutex/);
});
test('budget/generation/writer/window/API refusals fail closed',()=>{
  for(const change of [f=>f.state.caches[0].size_in_bytes=policy.quota_bytes,
    f=>f.state.caches.push({id:2,key:'forge-v1-'+f.context.partition+'-'+'c'.repeat(64)+'-old',ref:policy.trusted_ref,size_in_bytes:1,version:'original-version'}),
    f=>f.state.otherRun=true, f=>f.state.extraJob=true, f=>f.context.window.approval='',
    f=>f.context.env.GITHUB_EVENT_NAME='pull_request', f=>f.context.env.GITHUB_REF='refs/heads/other']) {
    const f=fixture();change(f);assert.throws(()=>admit(f.context,{bytes:200},f.read));
  }
  const f=fixture();assert.throws(()=>admit(f.context,{bytes:1},()=>{throw Error('API unavailable');}));
});
test('missing pages, duplicate rows and unknown sizes refuse',()=>{
  assert.throws(()=>pages([{total_count:2,actions_caches:[{id:1}]}],'actions_caches'));
  assert.throws(()=>pages([{total_count:2,actions_caches:[{id:1},{id:1}]}],'actions_caches'));
  const f=fixture();delete f.state.caches[0].size_in_bytes;assert.throws(()=>admit(f.context,{bytes:1},f.read));
});
