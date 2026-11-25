// Static guards: the Brain's code has no merge, deploy, key or delete path, and the agent
// settings deny them too (until the Brain has its own GitHub identity, ruleset and CODEOWNERS,
// "never merges" rests on .claude/settings.json).
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { here } from './helpers.js';

const root = path.join(here, '..', '..');
const src = fs.readdirSync(path.join(here, '..', 'src')).map((f) => [f, fs.readFileSync(path.join(here, '..', 'src', f), 'utf8')]);

test('brain/src has no merge, deploy, signing, key or ref-delete path', () => {
  const banned = [/\/merge\b/, /merge_pull_request/, /genlayer\s+(deploy|write|account|keygen)/, /privateKey|mnemonic|PRIVATE_KEY/, /sendTransaction|submit_raw_transaction|signTransaction/, /--delete\b|push\s+[^\n]*\s:/, /deleteRef\s*\(/];
  for (const [f, text] of src) for (const re of banned) assert.equal(re.test(text), false, `${f} matches ${re}`);
});

test('the only DELETE mention is the guard that refuses it', () => {
  const hits = src.filter(([, t]) => /'DELETE'/.test(t)).map(([f]) => f);
  assert.deepEqual(hits, ['refstores.js']);
  assert.match(src.find(([f]) => f === 'refstores.js')[1], /if \(method === 'DELETE'\) throw/);
});

test('.claude/settings.json denies merges, pushes to main, lock deletion and key tools', () => {
  const deny = JSON.parse(fs.readFileSync(path.join(root, '.claude', 'settings.json'), 'utf8')).permissions.deny;
  for (const rule of [
    'mcp__github__merge_pull_request',
    'mcp__github__enable_pr_auto_merge',
    'Bash(gh pr merge:*)',
    'Bash(gh api -X PUT:*)',
    'Bash(gh api --method PUT:*)',
    'Bash(git push origin main:*)',
    'Bash(git push origin HEAD:main:*)',
    'Bash(git push origin HEAD:refs/heads/main:*)',
    'Bash(git push origin --delete:*)',
    'Bash(git push origin :brain/lock:*)',
    'Bash(npx genlayer account:*)',
    'Bash(npx genlayer keygen:*)',
    'mcp__genskill__genlayer_submit_raw_transaction',
  ]) assert.ok(deny.includes(rule), `missing deny ${rule}`);
});

test('the CI workflow has read-only permissions and uses no secrets', () => {
  const wf = fs.readFileSync(path.join(root, '.github', 'workflows', 'brain-ci.yml'), 'utf8');
  assert.match(wf, /permissions:\s*\n\s+contents: read/);
  assert.equal(/secrets\./.test(wf), false);
  assert.equal(/pull_request_target/.test(wf), false);
});
