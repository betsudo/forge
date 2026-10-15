import { readFileSync } from 'node:fs';
const message=readFileSync(process.argv[2], 'utf8');
const subject=message.split('\n')[0];
if(!/^(feat|fix|docs|test|refactor|perf|build|ci|chore)(\([a-z0-9-]+\))?!?: .+/.test(subject)) throw new Error('Use a Conventional Commit subject');
if(!/^Signed-off-by: .+ <[^<>]+>$/m.test(message)) throw new Error('DCO sign-off required: git commit -S -s');
if(!/^(Refs|Closes|Fixes) #\d+/m.test(message)) throw new Error('Reference the owning issue');
