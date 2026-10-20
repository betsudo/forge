// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { saveGuarded, verifySdk } = require('../guarded-sdk.cjs');
const sdkRoot = path.dirname(require.resolve('@actions/cache/package.json'));
const service = require(path.join(sdkRoot, 'lib/internal/shared/cacheTwirpClient.js'));
const http = require(path.join(sdkRoot, 'lib/internal/cacheHttpClient.js'));
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
async function exercise(allow, mutate = false) {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'forge-sdk-real-'));
  const snapshot = path.join(temporary, 'snapshot'); fs.mkdirSync(snapshot);
  fs.writeFileSync(path.join(snapshot, 'snapshot.json'), JSON.stringify({ immutable: 'real SDK archive fixture' }));
  const oldEnv = { ...process.env }, calls = [];
  Object.assign(process.env, { ACTIONS_CACHE_SERVICE_V2: 'true', RUNNER_TEMP: temporary,
    ACTIONS_RESULTS_URL: 'https://unused.invalid', ACTIONS_RUNTIME_TOKEN: 'test-never-used' });
  const factory = service.internalCacheTwirpClient, upload = http.saveCache;
  service.internalCacheTwirpClient = () => ({
    CreateCacheEntry: async request => { calls.push('reserve'); return { ok: true, signedUploadUrl: 'fake://no-network' }; },
    FinalizeCacheEntryUpload: async request => { calls.push('finalize'); if (mutate === 'finalize') throw new Error('lost finalized response'); return { ok: true, entryId: '101' }; }
  });
  let admitted, uploaded;
  http.saveCache = async (_id, archive, _url, options) => {
    calls.push('upload'); uploaded = { bytes: fs.statSync(archive).size, sha256: hash(archive) };
    assert.equal(options.archiveSizeBytes, uploaded.bytes);
    if (mutate === 'post') fs.appendFileSync(archive, 'changed after actual upload');
  };
  try {
    const task = saveGuarded(snapshot, 'forge-v1-test', archive => {
      calls.push('admit'); admitted = { bytes: archive.bytes, sha256: archive.sha256 };
      if (!allow) throw new Error('operator/budget denial');
      if (mutate === true) fs.appendFileSync(archive.path, 'mutated');
      return { allowed: true, actual: archive.bytes };
    }, 268435456, () => { if (mutate === 'live') throw new Error('original parameter changed'); });
    if (!allow || mutate) {
      await assert.rejects(task, error => {
        if (mutate === 'post' || mutate === 'finalize') {
          assert.equal(error.publication_state.upload_started, true);
          assert.equal(error.publication_state.upload_completed, true);
          assert.equal(error.publication_state.finalized, false);
          assert.equal(error.publication_state.finalization_unknown, true);
        }
        return true;
      });
      assert.equal(calls.includes('upload'), mutate === 'post' || mutate === 'finalize');
      if (!allow) assert(!calls.includes('reserve'), 'denied archive must never reserve');
    } else {
      const result = await task;
      assert.deepEqual(calls, ['admit', 'reserve', 'upload', 'finalize']);
      assert.deepEqual(uploaded, admitted, 'SDK uploaded exactly its measured archive');
      assert.equal(result.cache_id, 101);
    }
    assert(admitted.bytes > 0, 'real SDK must create and measure a compressed archive');
  } finally {
    service.internalCacheTwirpClient = factory; http.saveCache = upload;
    process.env = oldEnv; fs.rmSync(temporary, { recursive: true, force: true });
  }
}
test('exact locked SDK source contract', () => verifySdk());
test('actual SDK archive is admitted before fake reserve and same bytes uploaded', () => exercise(true));
test('actual archive denial causes zero reserve/upload', () => exercise(false));
test('mutated admitted archive cannot upload', () => exercise(true, true));

test('changed installed SDK source refuses before archive/service', () => {
  const file = path.join(sdkRoot, 'lib/cache.js'), original = fs.readFileSync(file);
  try { fs.appendFileSync(file, '\n// unexpected mutation\n'); assert.throws(() => verifySdk(), /unknown\/mutated SDK/); }
  finally { fs.writeFileSync(file, original); }
});

test('post-upload mutation reports partial side effects without false finalize', () => exercise(true, 'post'));

test('live original-input refusal prevents upload after reservation', () => exercise(true, 'live'));
test('lost finalize response retains uncertain publication state', () => exercise(true, 'finalize'));
