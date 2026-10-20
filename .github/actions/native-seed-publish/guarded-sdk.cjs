// This file is part of Midnight ZKIR Forge.
// Copyright (C) 2026 Midnight Foundation
// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
let active = false;

function verifySdk() {
  const root = path.dirname(require.resolve('@actions/cache/package.json'));
  const contract = JSON.parse(fs.readFileSync(path.join(__dirname, 'sdk-contract.json')));
  assert.equal(contract.version, '5.0.5');
  assert.equal(JSON.parse(fs.readFileSync(path.join(root, 'package.json'))).version, contract.version);
  for (const [name, expected] of Object.entries(contract.files)) {
    const file = path.join(root, name);
    assert(fs.lstatSync(file).isFile(), 'SDK contract requires original regular files');
    assert.equal(hash(file), expected, 'unknown/mutated SDK implementation: ' + name);
  }
  return root;
}

async function saveGuarded(snapshot, key, admit, maxBytes = 268435456, live = () => {}) {
  assert(!active, 'one publication per process at a time');
  const root = verifySdk();
  const cache = require('@actions/cache');
  const utils = require(path.join(root, 'lib/internal/cacheUtils.js'));
  const http = require(path.join(root, 'lib/internal/cacheHttpClient.js'));
  const originalSize = utils.getArchiveFileSizeInBytes;
  const originalUpload = http.saveCache;
  const core = require('@actions/core');
  const logs = Object.fromEntries(['debug','info','warning','error'].map(name => [name, core[name]]));
  // The SDK may include service URLs in errors; retain structured state, not raw logs.
  let measured, failure, uploaded = false;
  const state = { archive_measured: false, admitted: false, upload_started: false, upload_completed: false, finalized: false };
  active = true;
  for (const name of Object.keys(logs)) core[name] = () => {};
  utils.getArchiveFileSizeInBytes = archive => {
    try {
      assert(!measured, 'unexpected repeated SDK size callback');
      verifySdk();
      const stat = fs.lstatSync(archive);
      assert(stat.isFile() && !stat.isSymbolicLink(), 'SDK archive must be a regular file');
      const bytes = originalSize(archive);
      assert(Number.isSafeInteger(bytes) && bytes > 0 && bytes <= maxBytes, 'actual SDK archive exceeds byte limit');
      measured = { path: archive, bytes, sha256: hash(archive) };
      state.archive_measured = true;
      const admission = admit(measured); // Deliberately synchronous: before CreateCacheEntry.
      assert(admission && admission.allowed === true, 'actual archive admission refused');
      verifySdk();
      measured.admission = admission;
      state.admitted = true;
      return bytes;
    } catch (error) { failure = error; throw error; }
  };
  http.saveCache = async (...args) => {
    try {
      assert(measured && !failure, 'upload without measured admission');
      assert.equal(args[1], measured.path, 'SDK changed the admitted upload archive');
      assert.equal(originalSize(args[1]), measured.bytes);
      assert.equal(hash(args[1]), measured.sha256, 'SDK upload archive mutated');
      verifySdk();
      live(); // Revalidate original source/tool/parameters immediately before upload.
      state.upload_started = true;
      const result = await originalUpload(...args);
      state.upload_completed = true;
      assert.equal(hash(args[1]), measured.sha256, 'archive changed during upload');
      uploaded = true;
      return result;
    } catch (error) { failure = error; throw error; }
  };
  try {
    const config = require(path.join(root, 'lib/internal/config.js'));
    assert.equal(config.getCacheServiceVersion(), 'v2', 'only qualified cache service v2 is supported');
    const cacheId = await cache.saveCache([snapshot], key, {}, false);
    if (failure) throw failure; // SDK logs/swallowing must never become acceptance.
    assert(measured && uploaded && Number.isSafeInteger(cacheId) && cacheId > 0, 'SDK did not finalize a publication');
    state.finalized = true;
    return { state, cache_id: cacheId, archive_bytes: measured.bytes, archive_sha256: measured.sha256,
      admission: measured.admission, sdk: '5.0.5' };
  } catch (error) {
    const refused = new Error('SDK publication refused or not finalized');
    refused.publication_state = { ...state, reservation_possible: state.admitted, finalization_unknown: state.upload_completed && !state.finalized };
    if (measured) Object.assign(refused.publication_state, { archive_bytes: measured.bytes, archive_sha256: measured.sha256 });
    throw refused;
  } finally {
    for (const [name, original] of Object.entries(logs)) core[name] = original;
    utils.getArchiveFileSizeInBytes = originalSize;
    http.saveCache = originalUpload;
    active = false;
  }
}
module.exports = { verifySdk, saveGuarded };
