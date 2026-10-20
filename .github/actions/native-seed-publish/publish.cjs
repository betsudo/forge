// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const { saveGuarded } = require('./guarded-sdk.cjs');
const { admit } = require('./admission.cjs');
function json(file) {
  const stat = fs.lstatSync(file);
  assert(stat.isFile() && stat.size <= 16 * 1024 * 1024, 'bounded original metadata required');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
function snapshotFiles(snapshot, identity, partition) {
  const manifest = json(path.join(snapshot, 'snapshot.json'));
  assert.equal(manifest.snapshot_id, identity);
  assert.equal(manifest.partition, partition);
  assert(Array.isArray(manifest.files) && manifest.files.length > 0 && manifest.files.length <= 4096);
  const files = { 'snapshot.json': hash(path.join(snapshot, 'snapshot.json')) };
  for (const row of manifest.files) {
    assert(typeof row.path === 'string' && row.path && !path.isAbsolute(row.path)
      && row.path.split('/').every(part => part && part !== '.' && part !== '..'), 'snapshot path escapes inventory');
    assert(!Object.hasOwn(files, row.path), 'duplicate snapshot inventory');
    const file = path.join(snapshot, row.path);
    const stat = fs.lstatSync(file);
    assert(stat.isFile() && stat.size === row.bytes, 'snapshot original file/size changed');
    assert.equal(hash(file), row.sha256, 'snapshot file changed after prepare-save');
    files[row.path] = row.sha256;
  }
  const actual = [];
  function walk(folder) {
    for (const name of fs.readdirSync(folder)) {
      const file = path.join(folder, name), stat = fs.lstatSync(file);
      if (stat.isDirectory()) walk(file);
      else { assert(stat.isFile(), 'snapshot links/special files refused'); actual.push(path.relative(snapshot, file)); }
    }
  }
  walk(snapshot);
  assert.deepEqual(actual.sort(), Object.keys(files).sort(), 'snapshot inventory differs from prepared scope');
  return files;
}


function checkedCompactGuard(key, guard, plan) {
  const name = 'tools/compact-rust-backend/prepare_native_seed.py';
  assert(guard && plan && path.isAbsolute(guard) && path.isAbsolute(plan), 'explicit original Compact guard/plan required');
  assert.equal(guard, path.join(key.workspace, name), 'only the keyed Compact guard may execute');
  const rows = key.inputs.filter(row => row.path === name);
  assert.equal(rows.length, 1, 'Compact guard must be an original keyed workload input');
  function run() {
    assert(fs.lstatSync(guard).isFile(), 'original regular Compact guard required');
    assert.equal(hash(guard), rows[0].sha256, 'Compact guard differs from keyed source');
    execFileSync('python3', ['-B', guard, '--guard-plan', plan], { timeout: 120000, maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] });
  }
  assert.equal(hash(guard), rows[0].sha256, 'Compact guard differs from keyed source');
  return run;
}


function checkPlanBindings(env) {
  const plan = env['INPUT_COMPACT-PLAN'];
  assert(plan && path.isAbsolute(plan) && fs.realpathSync(plan) === plan, 'original canonical native plan required');
  for (const [input, name] of [['INPUT_KEY', 'key.json'], ['INPUT_BASELINE', 'baseline.json'], ['INPUT_CACHE-DIR', 'cache']]) {
    const expected = path.join(plan, name);
    assert.equal(env[input], expected, 'publication inputs must belong to the same native plan: ' + name);
    assert.equal(fs.realpathSync(expected), expected, 'native plan aliases refused');
  }
  const invocation = json(path.join(plan, 'invocation.json'));
  const binary = env.INPUT_BINARY;
  assert(binary && path.isAbsolute(binary), 'explicit original Forge tool required');
  assert.equal(fs.realpathSync(binary), fs.realpathSync(invocation.tools.forge.path), 'Forge tool differs from native invocation');
  assert.equal(hash(fs.realpathSync(binary)), invocation.tools.forge.sha256, 'Forge executable differs from original native plan');
}


function checkGrowth(prepared, current, key) {
  assert.equal(prepared.schema, 1); assert.equal(current.schema, 1);
  for (const field of ['key_id', 'partition']) {
    assert.equal(prepared[field], key[field], 'prepare-save report differs from native key');
    assert.equal(current[field], key[field], 'live report differs from native key');
  }
  assert.deepEqual(prepared.delta, current.delta, 'prepare-save report differs from live original baseline');
  assert(Number.isSafeInteger(current.delta.misses) && current.delta.misses > 0, 'current generation growth required');
  assert.equal(current.delta.errors, 0, 'live official report has request errors');
}
function verifySnapshot(helper, env, snapshot, identity, run = execFileSync) {
  const temporary = fs.mkdtempSync(path.join(env.RUNNER_TEMP, 'forge-seed-verify-'));
  try {
    const verified = JSON.parse(run('python3', [helper, '--binary', env.INPUT_BINARY, 'restore',
      '--key', env.INPUT_KEY, '--cache-dir', path.join(temporary, 'verified-cache'),
      '--snapshot', snapshot, '--max-bytes', '268435456', '--expected-id', identity],
      { encoding: 'utf8', timeout: 120000, maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] }));
    assert.equal(verified.schema, 1); assert.equal(verified.restored, true, 'official snapshot verification required');
    return { verified: true, method: 'official_restore_into_disposable_private_store', snapshot_id: identity };
  } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
}

async function main(env = process.env) {
  assert.equal(process.versions.node.split('.')[0], '24', 'Node24 action required');
  const report = { schema: 1, published: false, accepted: false, scope: 'single stopped native seed; no proof/consumer qualification or global mutex claim' };
  const output = env.INPUT_OUTPUT;
  assert(output && path.isAbsolute(output) && !fs.existsSync(output), 'fresh absolute report required');
  try {
    if (env.INPUT_ENABLED !== 'true') {
      report.reason = 'default_off';
      return report;
    }
    assert(process.platform === 'linux' && process.arch === 'x64', 'native Linux x86_64 publisher required');
    const policy = json(path.join(__dirname, 'policy.json'));
    const prepared = json(env.INPUT_PREPARED), key = json(env.INPUT_KEY), window = json(env.INPUT_WINDOW);
    if (prepared.publish === false) { report.reason = 'official_prepare_save:' + prepared.reason; return report; }
    assert.equal(prepared.publish, true, 'official prepare-save grant required');
    assert.equal(prepared.authority, 'planning only; workflow/server-side cache scope supplies authorization');
    assert.equal(key.kind, 'forge-ci-key/v1');
    assert.equal(key.selector, 'ledger8-v2');
    assert.deepEqual(key.tool.platform, { os: 'Linux', arch: 'x86_64' });
    assert.equal(prepared.key, key.primary);
    const partition = key.partition, identity = prepared.snapshot.snapshot_id;
    assert(/^[0-9a-f]{64}$/.test(partition) && /^[0-9a-f]{64}$/.test(identity), 'exact official identities required');
    assert(new RegExp('^forge-v1-' + partition + '-[0-9a-f]{64}-[A-Za-z0-9_-]{1,80}$').test(key.primary), 'exact primary namespace required');
    assert.equal(prepared.snapshot.partition, partition);
    const snapshot = path.join(env.RUNNER_TEMP, 'forge-linux-supplied-snapshot');
    assert.equal(prepared.snapshot.path, snapshot, 'publisher/restore path-version must match');
    assert(fs.lstatSync(snapshot).isDirectory() && fs.realpathSync(snapshot) === snapshot, 'original regular snapshot directory required');
    for (const field of ['build_fingerprint', 'ledger_revision', 'profile']) assert.equal(prepared.snapshot.producer[field], key.tool.root[field]);
    assert(Number.isSafeInteger(prepared.snapshot.bytes) && prepared.snapshot.bytes > 0 && prepared.snapshot.bytes <= 268435456);
    const token = env['INPUT_GITHUB-TOKEN'];
    assert(token, 'read-only inventory token required');
    const helper = path.resolve(__dirname, '../../../scripts/forge-ci.py');
    checkPlanBindings(env);
    const guard = env['INPUT_COMPACT-GUARD'], plan = env['INPUT_COMPACT-PLAN'];
    const guardCheck = checkedCompactGuard(key, guard, plan);
    const bindingFiles = [helper, env.INPUT_BASELINE, guard, path.join(plan, 'invocation.json'), path.join(plan, 'key.json')];
    for (const file of bindingFiles) assert(file && path.isAbsolute(file) && fs.lstatSync(file).isFile(), 'original official helper/baseline required');
    assert(env.INPUT_BINARY && path.isAbsolute(env.INPUT_BINARY) && env['INPUT_CACHE-DIR'] && path.isAbsolute(env['INPUT_CACHE-DIR']), 'explicit original tool/store required');
    const originals = Object.fromEntries([env.INPUT_PREPARED, env.INPUT_KEY, env.INPUT_WINDOW, path.join(__dirname, 'policy.json'), ...bindingFiles].map(file => [file, hash(file)]));
    const inventory = snapshotFiles(snapshot, identity, partition);
    function live() {
      checkPlanBindings(env);
      for (const [file, expected] of Object.entries(originals)) assert.equal(hash(file), expected, 'publication input changed');
      assert.deepEqual(snapshotFiles(snapshot, identity, partition), inventory, 'prepared snapshot mutated');
      guardCheck();
      const current = JSON.parse(execFileSync('python3', [helper, '--binary', env.INPUT_BINARY, 'report', '--key', env.INPUT_KEY, '--cache-dir', env['INPUT_CACHE-DIR'], '--baseline', env.INPUT_BASELINE], { encoding: 'utf8', timeout: 120000, maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] }));
      checkGrowth(prepared.report, current, key);
    }
    Object.assign(report, { key: key.primary, snapshot_id: identity, partition, source_sha: env.GITHUB_SHA,
      repository: env.GITHUB_REPOSITORY, run_id: env.GITHUB_RUN_ID, run_attempt: env.GITHUB_RUN_ATTEMPT });
    live();
    report.snapshot_verification = { ...verifySnapshot(helper, env, snapshot, identity), partition };
    live();
    const result = await saveGuarded(snapshot, key.primary,
      archive => { live(); return admit({ policy, env, window, key: key.primary, partition, token }, archive); }, policy.max_archive_bytes, live);
    Object.assign(report, result, { published: true });
    live();
    Object.assign(report, { accepted: true, reason: 'measured_archive_admitted_and_finalized' });
    return report;
  } catch (error) {
    report.reason = 'refused'; report.error = 'publication input, admission or service refused';
    if (error.publication_state) {
      report.publication_state = error.publication_state;
      if (error.publication_state.finalization_unknown) report.published = null;
    }
    // A failed postguard must not hide an already finalized side effect.
    if (report.state?.finalized) report.published = true;
    process.exitCode = 1;
    return report;
  } finally {
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
  }
}
if (require.main === module) main().then(report => console.log(JSON.stringify(report)));
module.exports = { main, snapshotFiles, checkedCompactGuard, checkPlanBindings, checkGrowth, verifySnapshot };
