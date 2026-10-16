// API contract fixtures test policy; they do not simulate cryptographic verification.
import assert from 'node:assert/strict';
import {verify} from './check-pr-integrity.mjs';
import {conventional,issueNumbers} from './commit-policy.mjs';
const head='a'.repeat(40),repo='fixture/forge';
const base='b'.repeat(40);
const context={repo,number:1,head,base};
const author={name:'Test Fixture',email:'fixture@example.invalid'};
const message='ci(policy): enforce review\n\nRefs #2\n\nSigned-off-by: Test Fixture <fixture@example.invalid>\n';
const initial={pr:{state:'open',head:{sha:head},base:{sha:base,ref:'main',repo:{full_name:repo}},title:'ci(policy): enforce review',body:'Refs #2',commits:1},commits:[{sha:head,commit:{author,message,verification:{verified:true,reason:'valid',signature:'-----BEGIN PGP SIGNATURE-----\nfixture'}}}],issue:{number:2,repository_url:`https://api.github.com/repos/${repo}`}};
let assertions=0;
async function check(edit,accepted,after){
 const state=structuredClone(initial);edit(state);let reads=0;
 const api=async path=>{
  if(path===`/repos/${repo}/pulls/1`){reads++;return structuredClone(reads>1&&after?after(state.pr):state.pr);}
  if(path.includes('/commits?')){const page=Number(new URL('https://fixture.invalid'+path).searchParams.get('page'));return state.commits.slice((page-1)*100,page*100);}
  if(path===`/repos/${repo}/issues/2`)return state.issue;
  throw new Error('Unexpected fixture API path');
 };
 if(accepted)await verify(context,api);else await assert.rejects(()=>verify(context,api));
 assertions++;
}
await check(()=>{},true);
for(const edit of [
 s=>s.pr.title='unstructured',s=>s.pr.body='',s=>s.pr.body='Refs #0',
 s=>s.pr.head.sha='b'.repeat(40),s=>s.pr.base.repo.full_name='other/repo',
 s=>s.pr.commits=251,s=>s.pr.commits=2,s=>s.commits=[],
 s=>s.issue.pull_request={},s=>s.issue.number=9,s=>s.issue.repository_url='https://api.github.com/repos/other/repo',s=>s.pr.base.sha='c'.repeat(40),
 s=>s.commits[0].commit.verification.verified=false,
 s=>s.commits[0].commit.verification.reason='unknown_key',
 s=>s.commits[0].commit.verification.signature='-----BEGIN SSH SIGNATURE-----',
 s=>s.commits[0].commit.message=message.replace('ci(policy):','invalid'),
 s=>s.commits[0].commit.message=message.replace('Refs #2',''),
 s=>s.commits[0].commit.message=message.replace('Signed-off-by:','Other:'),
 s=>s.commits[0].commit.author.email='other@example.invalid',
 s=>s.commits[0].commit.author.name='Other',s=>s.pr.state='closed',
])await check(edit,false);
await check(()=>{},false,p=>({...p,head:{sha:'b'.repeat(40)}}));
await check(()=>{},false,p=>({...p,body:'Refs #3'}));
await check(()=>{},false,p=>({...p,base:{...p.base,sha:'c'.repeat(40)}}));
await check(()=>{},false,p=>({...p,base:{...p.base,ref:'other'}}));
await check(s=>{const c=s.commits[0];s.commits=Array.from({length:101},(_,i)=>({...structuredClone(c),sha:i===100?head:i.toString(16).padStart(40,'0')}));s.pr.commits=101;},true);
await check(s=>{s.commits.push(structuredClone(s.commits[0]));s.pr.commits=2;},false);
for(const subject of ['feat!: breaking','fix(cache): valid','revert: restore behavior'])assert.ok(conventional(subject));
for(const subject of ['feat!!: invalid','feat: ','feat: x\nmalicious','feat(): empty scope'])assert.ok(!conventional(subject));
assert.deepEqual(issueNumbers('Refs #2trailing\nRefs #0\nRefs #3\n'),[3]);
console.log(`PR integrity policy: ${assertions} API controls plus grammar controls passed`);
