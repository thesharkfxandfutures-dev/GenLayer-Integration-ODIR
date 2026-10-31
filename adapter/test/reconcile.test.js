import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { observe } from '../src/observe.js';
import { reconcile } from '../src/reconcile.js';
import { sha256 } from '../src/canon.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, '..', '..', 'fixtures', 'd1');
const pkg = () => JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'));
const config = JSON.parse(fs.readFileSync(path.join(dir, 'config.json'), 'utf8'));
const source = { kind: 'file', ...config };
const now = new Date('2026-10-31T12:00:00Z');
const reply = (n, mutate = (r) => r) => JSON.stringify(mutate(JSON.parse(fs.readFileSync(path.join(dir, n), 'utf8'))));
const obs = (n, mutate, src = source) => observe(reply(n, mutate), { source: src, now });

test('matching PASS: CONSISTENT, verdict surfaced, authority none', () => {
  const r = reconcile(pkg(), obs('get_slice.reviewed_pass.json'), config);
  assert.equal(r.decision, 'CONSISTENT');
  assert.equal(r.exit_code, 0);
  assert.equal(r.remote_verdict, 'PASS');
  assert.equal(r.authority, 'none');
  assert.match(r.next_action, /advisory/);
});

test('submitted but unreviewed: PENDING_REVIEW, do not resubmit', () => {
  const r = reconcile(pkg(), obs('get_slice.submitted.json'), config);
  assert.equal(r.decision, 'PENDING_REVIEW');
  assert.match(r.next_action, /do not resubmit/);
});

test('attempt not yet on chain: NOT_SUBMITTED', () => {
  const r = reconcile(pkg(), obs('get_slice.submitted.json', (x) => { x.task.attempt = 0; x.task.status = 'REGISTERED'; delete x.latest_attempt; return x; }), config);
  assert.equal(r.decision, 'NOT_SUBMITTED');
});

test('a later attempt on chain: SUPERSEDED', () => {
  const r = reconcile(pkg(), obs('get_slice.reviewed_pass.json', (x) => { x.task.attempt = 2; x.latest_attempt.attempt = 2; return x; }), config);
  assert.equal(r.decision, 'SUPERSEDED');
});

test('wrong chain or wrong contract: CONFIG_MISMATCH before anything else is compared', () => {
  const wrongChain = reconcile(pkg(), obs('get_slice.reviewed_pass.json', undefined, { ...source, chain_id: 4221 }), config);
  assert.equal(wrongChain.decision, 'CONFIG_MISMATCH');
  const wrongContract = reconcile(pkg(), obs('get_slice.reviewed_pass.json', undefined, { ...source, contract_address: '0x0000000000000000000000000000000000000001' }), config);
  assert.equal(wrongContract.decision, 'CONFIG_MISMATCH');
  const wrongCode = reconcile(pkg(), obs('get_slice.reviewed_pass.json'), { ...config, contract_code_sha256: 'ab'.repeat(32) });
  assert.equal(wrongCode.decision, 'CONFIG_MISMATCH');
  assert.equal(wrongCode.exit_code, 5);
});

test('same slice and attempt, different evidence: INTEGRITY_MISMATCH, stop', () => {
  const p = pkg();
  p.evidence.text = 'A different paragraph that was never submitted.';
  p.evidence.sha256 = sha256(p.evidence.text); // internally consistent, but not what the chain holds
  const r = reconcile(p, obs('get_slice.reviewed_pass.json'), config);
  assert.equal(r.decision, 'INTEGRITY_MISMATCH');
  assert.equal(r.exit_code, 4);
  assert.match(r.next_action, /do not retry/);
});

test('criteria changed locally after registration: INTEGRITY_MISMATCH', () => {
  const p = pkg(); p.criteria[0].text = 'Explain who owns inventory and stock';
  const r = reconcile(p, obs('get_slice.reviewed_pass.json'), config);
  assert.equal(r.decision, 'INTEGRITY_MISMATCH');
  assert.match(r.local_criteria_sha256, /^[0-9a-f]{64}$/);
});

test('observed after accept_until: EXPIRED even though the chain says PASS', () => {
  const p = pkg(); p.lifetime.accept_until = '2026-10-31T11:00:00Z';
  const r = reconcile(p, obs('get_slice.reviewed_pass.json'), config);
  assert.equal(r.decision, 'EXPIRED');
});

test('a paused contract is reported on a consistent record', () => {
  const r = reconcile(pkg(), obs('get_slice.reviewed_pass.json', (x) => { x.paused = true; return x; }), config);
  assert.equal(r.decision, 'CONSISTENT');
  assert.equal(r.remote_paused, true);
  assert.ok(r.reasons.some((m) => /paused/.test(m)));
});
