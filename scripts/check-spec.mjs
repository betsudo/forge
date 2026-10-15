import { readFileSync, readdirSync } from 'node:fs';
import assert from 'node:assert/strict';
for(const change of readdirSync('openspec/changes').filter(name=>name!=='archive')){
const root=`openspec/changes/${change}/`;
const capabilities=readdirSync(root+'specs');
for(const capability of capabilities){
for(const name of ['proposal.md','design.md','tasks.md',`specs/${capability}/spec.md`]) assert.ok(readFileSync(root+name,'utf8').length>100,name);
const spec=readFileSync(root+`specs/${capability}/spec.md`,'utf8');
for(const requirement of spec.split('### Requirement:').slice(1)){
  assert.match(requirement,/\bSHALL\b/);
  assert.match(requirement,/#### Scenario:/);
  assert.match(requirement,/\*\*WHEN\*\*/);
  assert.match(requirement,/\*\*THEN\*\*/);
}
}}
console.log('OpenSpec structure: OK (semantic evidence remains tests and review)');
