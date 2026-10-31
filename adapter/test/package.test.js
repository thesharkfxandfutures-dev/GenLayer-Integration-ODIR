import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validatePackage, packageSha256, criteriaSha256, bindingSummary, PackageError } from '../src/package.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const load = () => JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'fixtures', 'd1', 'package.json'), 'utf8'));

test('the D1 fixture package validates and binds to the contract digests', () => {
  const p = validatePackage(load());
  assert.equal(criteriaSha256(p), 'e840bbab92ca069aeb9c731b877b2ccf5f8b22959d57c0182204f2e7d9e4035e');
  const s = bindingSummary(p);
  assert.equal(s.evidence_sha256, p.evidence.sha256);
  assert.match(s.package_sha256, /^[0-9a-f]{64}$/);
});

test('one changed byte anywhere is a different package', () => {
  const a = load(), b = load(), c = load(), d = load();
  b.criteria[0].text += '.';
  c.candidate.candidate_manifest_sha256 = c.candidate.candidate_manifest_sha256.replace(/c$/, 'd');
  d.destination.chain_id += 1;
  const ids = new Set([a, b, c, d].map(packageSha256));
  assert.equal(ids.size, 4);
});

test('evidence.sha256 must match evidence.text', () => {
  const p = load(); p.evidence.text += ' Extra sentence.';
  assert.throws(() => validatePackage(p), (e) => e instanceof PackageError && e.problems.some((m) => /does not match/.test(m)));
});

test('contract limits are enforced before anything is sent', () => {
  const nine = load(); nine.criteria = Array.from({ length: 9 }, (_, i) => ({ id: `C${i}`, text: `criterion ${i}`, evidence_class: 'text', version: '1' }));
  assert.throws(() => validatePackage(nine), PackageError);
  const dup = load(); dup.criteria.push({ ...dup.criteria[0], id: 'C2' });
  assert.throws(() => validatePackage(dup), PackageError);
  const four = load(); four.identity.attempt = 4;
  assert.throws(() => validatePackage(four), PackageError);
  const badSlice = load(); badSlice.identity.slice_id = 'D 1';
  assert.throws(() => validatePackage(badSlice), PackageError);
});

test('missing binding fields are refused, not defaulted', () => {
  for (const drop of ['candidate', 'authority', 'disclosure', 'destination', 'lifetime', 'idempotency', 'provenance']) {
    const p = load(); delete p[drop];
    assert.throws(() => validatePackage(p), PackageError, drop);
  }
});

test('a criterion needing observed evidence is still a valid package: sufficiency is decided later', () => {
  const p = load(); p.criteria[0].evidence_class = 'observed';
  assert.doesNotThrow(() => validatePackage(p));
});
