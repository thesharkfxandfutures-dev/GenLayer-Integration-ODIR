#!/usr/bin/env node
// CI gate (slice A3): every role commit in base..head touches only its own role folder.
//   node resolver/bin/check-role-commits.mjs --base <rev> --head <rev> [--repo <dir>]
import { checkRoleCommits, commitsInRange } from '../src/rolecommits.js';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const base = opt('--base');
const head = opt('--head') || 'HEAD';
const repo = opt('--repo') || process.cwd();
if (!base) {
  process.stderr.write('usage: check-role-commits.mjs --base <rev> [--head <rev>] [--repo <dir>]\n');
  process.exit(2);
}
let range;
try { range = commitsInRange(repo, base, head); } catch (e) {
  process.stderr.write(`cannot read ${base}..${head}: ${e.message.split('\n')[0]}\n`);
  process.exit(2);
}
const problems = checkRoleCommits(range.commits);
const short = (r) => (/^[0-9a-f]{40}$/.test(r) ? r.slice(0, 10) : r);
process.stdout.write(`${range.commits.length} commit(s) checked in ${short(base)}..${short(String(head))}${range.merges.length ? `, ${range.merges.length} merge commit(s) not checked` : ''}\n`);
for (const p of problems) process.stdout.write(`FAIL ${p}\n`);
process.exit(problems.length ? 1 : 0);
