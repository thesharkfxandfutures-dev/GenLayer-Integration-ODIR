import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { observe, ObservationError } from '../src/observe.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = (n) => fs.readFileSync(path.join(here, '..', '..', 'fixtures', 'd1', n), 'utf8');
const source = { kind: 'file', chain_id: 61999, contract_address: '0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646', contract_code_sha256: 'f27688d0bf79f65900e4c7145909ed7b90d2a220ac8b987ed2906c94ffde5341' };

test('a REVIEWED_PASS reply becomes an observation with no evidence text and no authority', () => {
  const o = observe(fx('get_slice.reviewed_pass.json'), { source, now: new Date('2026-10-31T12:00:00Z') });
  assert.equal(o.task.status, 'REVIEWED_PASS');
  assert.equal(o.latest_attempt.review.verdict, 'PASS');
  assert.equal(o.latest_attempt.evidence, undefined);
  assert.equal(o.authority, 'none');
  assert.equal(o.assurance, 'supplied_file_unverified');
  assert.match(o.raw_sha256, /^[0-9a-f]{64}$/);
});

test('a SUBMITTED reply with no review is accepted as pending', () => {
  const o = observe(fx('get_slice.submitted.json'), { source });
  assert.equal(o.latest_attempt.status, 'SUBMITTED');
  assert.equal(o.latest_attempt.review, null);
});

test('malformed replies are rejected, never coerced', () => {
  assert.throws(() => observe('not json', { source }), ObservationError);
  assert.throws(() => observe('{"task":{}}', { source }), ObservationError);
  const r = JSON.parse(fx('get_slice.reviewed_pass.json'));
  r.latest_attempt.evidence += ' tampered';
  assert.throws(() => observe(JSON.stringify(r), { source }), (e) => e instanceof ObservationError && e.problems.some((m) => /does not hash/.test(m)));
  const s = JSON.parse(fx('get_slice.reviewed_pass.json'));
  s.latest_attempt.review = null;
  assert.throws(() => observe(JSON.stringify(s), { source }), ObservationError);
  const v = JSON.parse(fx('get_slice.reviewed_pass.json'));
  v.latest_attempt.review.verdict = 'APPROVED';
  assert.throws(() => observe(JSON.stringify(v), { source }), ObservationError);
});

test('the source must name a chain and a contract', () => {
  assert.throws(() => observe(fx('get_slice.submitted.json'), { source: { kind: 'file' } }), ObservationError);
});
