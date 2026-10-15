import { mkdtempSync,writeFileSync,rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
const directory=mkdtempSync(join(tmpdir(),'forge-commit-policy-'));
try{
  const path=join(directory,'message');
  const valid='test(factory): synthetic policy fixture\n\nRefs #1\n\nSigned-off-by: Test Fixture <fixture@example.invalid>\n';
  for(const [message,accepted] of [[valid,true],[valid.replace('test(factory):','invalid'),false],[valid.replace(/Signed-off-by:.*\n/,''),false],[valid.replace('Refs #1',''),false]]){
    writeFileSync(path,message);
    assert.equal(spawnSync(process.execPath,['scripts/commit-policy.mjs',path],{encoding:'utf8'}).status===0,accepted);
  }
  console.log('Commit policy: valid fixture accepted; bad grammar/DCO/issue refused');
}finally{rmSync(directory,{recursive:true,force:true});}
