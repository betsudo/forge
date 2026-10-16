import {pathToFileURL} from 'node:url';
import {conventional, issueNumbers, validateMessage} from './commit-policy.mjs';
export async function verify({repo,number,head,base}, api) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !/^[1-9]\d*$/.test(String(number)) || !/^[a-f0-9]{40}$/.test(head) || !/^[a-f0-9]{40}$/.test(base)) throw new Error('Invalid PR context');
  const route=`/repos/${repo}/pulls/${number}`;
  const pr=await api(route);
  if (pr.state!=='open' || pr.head.sha!==head || pr.base.repo.full_name!==repo || pr.base.sha!==base) throw new Error('PR context/head changed');
  if (!conventional(pr.title)) throw new Error('Conventional PR title required');
  if (!pr.commits || pr.commits>250) throw new Error('PR must have 1–250 commits; split larger changes');
  const checked=new Set();
  async function issues(text) {
    const numbers=issueNumbers(text || '');
    if (!numbers.length) throw new Error('Explicit linked issue required: Refs #N');
    for (const n of numbers) {
      if (!Number.isSafeInteger(n)) throw new Error('Invalid issue number');
      if (checked.has(n)) continue;
      const issue=await api(`/repos/${repo}/issues/${n}`);
      if (issue.pull_request || issue.number!==n || issue.repository_url?.toLowerCase()!==`https://api.github.com/repos/${repo}`.toLowerCase()) throw new Error('Reference must identify a real issue, not a PR');
      checked.add(n);
    }
  }
  await issues(pr.body);
  const commits=[];
  for (let page=1;commits.length<pr.commits;page++) {
    const batch=await api(`${route}/commits?per_page=100&page=${page}`);
    if (!Array.isArray(batch) || !batch.length || page>3) throw new Error('Incomplete commit enumeration');
    commits.push(...batch);
  }
  if (commits.length!==pr.commits || new Set(commits.map(c=>c.sha)).size!==commits.length || commits.at(-1).sha!==head) throw new Error('Commit set/head mismatch');
  for (const c of commits) {
    const v=c.commit.verification;
    if (v?.verified!==true || v.reason!=='valid' || !v.signature?.startsWith('-----BEGIN PGP SIGNATURE-----')) throw new Error(`Verified OpenPGP signature required: ${c.sha}`);
    if (!c.commit.author?.name || !c.commit.author?.email) throw new Error('Commit author required');
    validateMessage(c.commit.message,c.commit.author);
    await issues(c.commit.message);
  }
  const latest=await api(route);
  if (latest.head.sha!==head || latest.title!==pr.title || latest.body!==pr.body || latest.commits!==pr.commits || latest.state!=='open' || latest.base.sha!==base || latest.base.ref!==pr.base.ref || latest.base.repo.full_name!==repo) throw new Error('PR changed during verification; rerun');
  return {commits:commits.length,issues:checked.size,head};
}
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const token=process.env.GH_TOKEN;
  if (!token) throw new Error('Read-only GitHub token required');
  const api=async path=>{
    const response=await fetch(`https://api.github.com${path}`,{headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},signal:AbortSignal.timeout(30000)});
    if (!response.ok) throw new Error(`GitHub API request failed: ${response.status}`);
    return response.json();
  };
  console.log(JSON.stringify(await verify({repo:process.env.GITHUB_REPOSITORY,number:process.env.PR_NUMBER,head:process.env.HEAD_SHA,base:process.env.BASE_SHA},api)));
}
