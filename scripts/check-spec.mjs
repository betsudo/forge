import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const root='openspec/changes/local-cache-mvp/';
for(const name of ['proposal.md','design.md','tasks.md','specs/local-artifact-cache/spec.md']) assert.ok(readFileSync(root+name,'utf8').length>100,name);
const spec=readFileSync(root+'specs/local-artifact-cache/spec.md','utf8');
for(const requirement of spec.split('### Requirement:').slice(1)){
  assert.match(requirement,/\bSHALL\b/);
  assert.match(requirement,/#### Scenario:/);
  assert.match(requirement,/\*\*WHEN\*\*/);
  assert.match(requirement,/\*\*THEN\*\*/);
}
console.log('OpenSpec structure: OK (semantic evidence remains tests and review)');
