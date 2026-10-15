import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const expected={
  'midnight-zkir':'2.1.1','midnight-transient-crypto':'2.1.1',
  'midnight-base-crypto':'1.0.2','midnight-serialize':'1.1.1',
  'midnight-proofs':'0.7.1','midnight-circuits':'6.1.0',
  'midnight-curves':'0.2.0','midnight-zk-stdlib':'1.1.0',
};
const git=new Set(['midnight-zkir','midnight-transient-crypto','midnight-base-crypto','midnight-serialize']);
const entries=readFileSync('Cargo.lock','utf8').split('[[package]]').slice(1).map(block=>({
  name:/^name = "([^"]+)"/m.exec(block)?.[1],version:/^version = "([^"]+)"/m.exec(block)?.[1],source:/^source = "([^"]+)"/m.exec(block)?.[1],
}));
for(const [name,version] of Object.entries(expected)){
  const matches=entries.filter(entry=>entry.name===name);
  assert.equal(matches.length,1,name);
  assert.equal(matches[0].version,version,name);
  if(git.has(name)) assert.equal(matches[0].source,'git+https://github.com/midnightntwrk/midnight-ledger?rev=b5d3e965a18e4cac17fac4f38446fc55c524439a#b5d3e965a18e4cac17fac4f38446fc55c524439a');
  else assert.equal(matches[0].source,'registry+https://github.com/rust-lang/crates.io-index');
}
assert.ok(!entries.some(entry=>entry.name?.includes('zkir-v3')),'V3 must stay in its separate worker graph');
console.log('Official ledger8-8.1.3 dependency profile: OK');

const worker=readFileSync('workers/zkir3/Cargo.lock','utf8').split('[[package]]').slice(1).map(block=>({name:/^name = "([^"]+)"/m.exec(block)?.[1],version:/^version = "([^"]+)"/m.exec(block)?.[1],source:/^source = "([^"]+)"/m.exec(block)?.[1]}));
const v3={...expected,'midnight-zkir-v3':'3.0.0-rc.1','midnight-transient-crypto':'2.1.0','midnight-base-crypto':'1.0.0','midnight-serialize':'1.1.0'};
delete v3['midnight-zkir'];
for(const [name,version] of Object.entries(v3)){
  const matches=worker.filter(entry=>entry.name===name);assert.equal(matches.length,1,name);assert.equal(matches[0].version,version,name);
  if(git.has(name)||name==='midnight-zkir-v3') assert.equal(matches[0].source,'git+https://github.com/midnightntwrk/midnight-ledger?rev=3a7ae0361d03e6eed4fc91e31f6600f334f605d5#3a7ae0361d03e6eed4fc91e31f6600f334f605d5');
}
console.log('Isolated consumer ZKIR3 profile: OK');
