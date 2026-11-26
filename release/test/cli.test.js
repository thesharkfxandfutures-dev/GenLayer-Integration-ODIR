// The two commands and the workflows that run them.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { OUTPUTS } from '../src/build.js';
import { ROOT, commitChange, makeRepo, runNode, tag, tmp } from './helpers.js';

const BUILD = path.join(ROOT, 'release/bin/build-release.mjs');
const VERIFY = path.join(ROOT, 'release/bin/verify-release.mjs');
const TAG = 'templates-v0.2.0';

test('build-release writes the four files; a second run writes the same bytes; verify-release passes with a rebuild', () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  const [a, b] = [tmp('odir-out-'), tmp('odir-out-')];
  const one = runNode([BUILD, '--tag', TAG, '--out', a, '--root', dir]);
  assert.equal(one.code, 0, one.stdout + one.stderr);
  assert.match(one.stdout, /24 combinations reproduce their golden terms hashes/);
  assert.equal(runNode([BUILD, '--tag', TAG, '--out', b, '--root', dir]).code, 0);
  for (const f of Object.values(OUTPUTS)) assert.ok(fs.readFileSync(path.join(a, f)).equals(fs.readFileSync(path.join(b, f))), f);
  const v = runNode([VERIFY, '--dir', a, '--rebuild', '--tag', TAG, '--root', dir]);
  assert.equal(v.code, 0, v.stdout);
  assert.match(v.stdout, /rebuild byte-identical/);
});

test('verify-release exits 1 on a tampered bundle; build-release exits 1 when refused and 2 on bad usage', () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  const out = tmp('odir-out-');
  assert.equal(runNode([BUILD, '--tag', TAG, '--out', out, '--root', dir]).code, 0);
  const file = path.join(out, OUTPUTS.bundle);
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replace('Person to person', 'Person to persons'));
  const v = runNode([VERIFY, '--dir', out, '--root', dir]);
  assert.equal(v.code, 1);
  assert.match(v.stdout, /FAIL odir-templates\.mjs: sha256 does not match SHA256SUMS/);

  commitChange(dir, 'templates/bases/p2p.json', (t) => t.replace(/("text": "[^"]*?)\bthe\b/, '$1a'));
  const refused = runNode([BUILD, '--ref', 'HEAD', '--out', tmp('odir-out-'), '--root', dir]);
  assert.equal(refused.code, 1);
  assert.match(refused.stdout, /^REFUSED /);
  assert.equal(runNode([BUILD, '--ref', 'HEAD', '--root', dir]).code, 2);
  assert.equal(runNode([BUILD, '--tag', 'v1', '--out', out, '--root', dir]).code, 2);
  assert.equal(runNode([VERIFY, '--root', dir]).code, 2);
});

const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

test('release-draft.yml: only on templates-v* tags on main, drafts and never publishes, no secrets', () => {
  const wf = read('.github/workflows/release-draft.yml');
  assert.match(wf, /on:\n {2}push:\n {4}tags:\n {6}- 'templates-v\*'\n\n/);
  assert.doesNotMatch(wf, /pull_request|workflow_dispatch|schedule|branches:/);
  assert.match(wf, /^permissions:\n {2}contents: read$/m);
  assert.equal((wf.match(/contents: write/g) || []).length, 1);
  assert.match(wf, /merge-base --is-ancestor .* origin\/main/);
  assert.match(wf, /gh release create "\$TAG" --draft --verify-tag/);
  assert.doesNotMatch(wf, /--draft=false|release edit|release upload|--latest/);
  assert.doesNotMatch(wf.replace('${{ github.token }}', ''), /secrets\.|\$\{\{ secrets/);
  assert.match(wf, /persist-credentials: false/);
  assert.match(wf, /build-release\.mjs --tag "\$TAG" --out "\$RUNNER_TEMP\/dist"\n.*--out "\$RUNNER_TEMP\/dist2"\n\s*diff -r/);
  assert.match(wf, /verify-release\.mjs --dir "\$RUNNER_TEMP\/dist" --rebuild --tag "\$TAG"/);
  assert.match(wf, /\(cd release && npm test\)/);
});

test('brain-ci.yml runs the release tests and a check build that must be byte-identical and verify', () => {
  const wf = read('.github/workflows/brain-ci.yml');
  assert.match(wf, /working-directory: release\n\s+run: npm test/);
  assert.match(wf, /build-release\.mjs --ref HEAD --out "\$RUNNER_TEMP\/r1"[\s\S]*diff -r "\$RUNNER_TEMP\/r1" "\$RUNNER_TEMP\/r2"[\s\S]*verify-release\.mjs --dir "\$RUNNER_TEMP\/r1" --rebuild --ref HEAD/);
  assert.match(wf, /^permissions:\n {2}contents: read$/m);
  assert.doesNotMatch(wf, /contents: write/);
});
