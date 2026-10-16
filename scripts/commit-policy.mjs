import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
export function conventional(subject) {
  return /^(feat|fix|docs|test|refactor|perf|build|ci|chore|style|revert)(\([a-z0-9-]+\))?!?: \S.*$/.test(subject) && !subject.includes('\n');
}
export function issueNumbers(message) {
  return [...message.matchAll(/^(?:Refs|Closes|Fixes|Resolves) #([1-9]\d*)\s*$/gm)].map(m=>Number(m[1]));
}
export function validateMessage(message, author) {
  if (!conventional(message.split('\n')[0])) throw new Error('Use a Conventional Commit subject');
  const signoffs = [...message.matchAll(/^Signed-off-by: (.+) <([^<>\r\n]+)>\s*$/gm)];
  if (!signoffs.length) throw new Error('DCO sign-off required: git commit -S -s');
  if (author && !signoffs.some(m=>m[1]===author.name && m[2].toLowerCase()===author.email.toLowerCase()))
    throw new Error('DCO must match commit author name and email');
  if (!issueNumbers(message).length) throw new Error('Reference the owning issue on its own line: Refs #N');
}
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  validateMessage(readFileSync(process.argv[2], 'utf8'));
}
