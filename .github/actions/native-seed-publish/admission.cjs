// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const assert = require('node:assert/strict');
const child = require('node:child_process');
const ACTIVE = ['queued', 'in_progress', 'waiting', 'pending', 'requested'];
function pages(value, field) {
  assert(Array.isArray(value) && value.length > 0, 'complete API pages required');
  const total = value[0].total_count;
  assert(Number.isSafeInteger(total) && total >= 0 && total <= 5000, 'bounded API total required');
  const rows = value.flatMap(page => {
    assert.equal(page.total_count, total, 'API inventory changed during pagination');
    assert(Array.isArray(page[field]), 'API page rows missing');
    return page[field];
  });
  assert.equal(rows.length, total, 'incomplete API inventory');
  assert.equal(new Set(rows.map(row => row.id)).size, total, 'duplicate API inventory rows');
  assert(rows.every(row => Number.isSafeInteger(row.id) && row.id > 0), 'invalid service IDs');
  return rows;
}
function ghPages(endpoint, token) {
  let raw;
  try { raw = child.execFileSync('gh', ['api', '--paginate', '--slurp', endpoint], {
    encoding: 'utf8', timeout: 30000, maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, GH_TOKEN: token, GH_DEBUG: '' }
  }); } catch { throw new Error('GitHub inventory unavailable or over finite limit'); }
  return JSON.parse(raw);
}
function admit(context, archive, read = endpoint => ghPages(endpoint, context.token)) {
  const { policy, env, window, key, partition } = context;
  assert.equal(env.GITHUB_EVENT_NAME, 'workflow_dispatch', 'manual event required');
  assert.equal(env.GITHUB_REPOSITORY, policy.repository);
  assert.equal(env.GITHUB_REF, policy.trusted_ref);
  assert.deepEqual(Object.keys(window).sort(), ['approval', 'repository', 'run_id', 'trusted_ref']);
  assert.equal(window.repository, policy.repository);
  assert.equal(window.run_id, env.GITHUB_RUN_ID);
  assert.equal(window.trusted_ref, policy.trusted_ref);
  assert(typeof window.approval === 'string' && /^[A-Za-z0-9_.:/ -]{1,160}$/.test(window.approval), 'explicit operator-window approval label required');
  const prefix = 'repos/' + policy.repository + '/actions/';
  const caches = pages(read(prefix + 'caches?per_page=100'), 'actions_caches');
  let total = 0;
  for (const cache of caches) {
    assert(Number.isSafeInteger(cache.size_in_bytes) && cache.size_in_bytes >= 0 && typeof cache.key === 'string' && typeof cache.ref === 'string' && typeof cache.version === 'string' && cache.version,  'cache size/key/ref unknown');
    total += cache.size_in_bytes;
    assert(Number.isSafeInteger(total), 'cache total overflow');
  }
  const seeds = caches.filter(row => row.ref === policy.trusted_ref && row.key.startsWith('forge-v1-' + partition + '-'));
  assert(!seeds.some(row => row.key === key), 'immutable seed already exists; no replacement');
  assert(seeds.length < policy.max_generations, 'seed generation budget exhausted');
  assert(Number.isSafeInteger(archive.bytes) && archive.bytes > 0 && archive.bytes <= policy.max_archive_bytes, 'actual archive bound unknown/over limit');
  assert(total + archive.bytes <= policy.quota_bytes, 'aggregate retained plus actual archive exceeds decimal quota');
  let observedRuns = 0;
  for (const status of ACTIVE) {
    const runs = pages(read(prefix + 'runs?status=' + status + '&per_page=100'), 'workflow_runs');
    for (const run of runs) {
      assert.equal(run.status, status, 'workflow state changed/unknown during window audit');
      assert.equal(String(run.id), env.GITHUB_RUN_ID, 'other active or queued workflow: operational window not exclusive');
      observedRuns++;
    }
  }
  assert.equal(observedRuns, 1, 'current active workflow identity missing/ambiguous');
  const jobs = pages(read(prefix + 'runs/' + env.GITHUB_RUN_ID + '/jobs?filter=latest&per_page=100'), 'jobs');
  const activeJobs = jobs.filter(job => job.status !== 'completed');
  assert.equal(activeJobs.length, 1, 'other active/queued jobs could publish caches');
  assert.equal(activeJobs[0].status, 'in_progress');
  assert.equal(activeJobs[0].name, policy.job_name, 'unknown active cachewriter job');
  const latest = pages(read(prefix + 'caches?per_page=100'), 'actions_caches');
  const identity = rows => rows.map(row => [row.id,row.key,row.ref,row.version,row.size_in_bytes]).sort((a,b)=>a[0]-b[0]);
  assert.deepEqual(identity(latest), identity(caches), 'cache inventory changed during operational audit');
  return { allowed: true, retained_bytes: total, archive_bytes: archive.bytes,
    projected_bytes: total + archive.bytes, cache_entries: caches.length,
    existing_seed_generations: seeds.length, operator_window: window,
    audit_scope: 'observed complete API state plus explicit operator-exclusive-window assumption; not an atomic mutex against future independent writers' };
}
module.exports = { pages, admit, ACTIVE };
