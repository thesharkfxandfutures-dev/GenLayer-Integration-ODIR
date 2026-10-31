// The live-recorded D1 reply (read from Studionet on 2026-10-31 through genlayer-js@1.1.8,
// state latest-final). These tests run against the recorded bytes, not the network, so they
// are deterministic; what they establish is that the adapter's encoding and reconciliation agree
// with what the deployed contract actually stored.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { digest, sha256 } from '../src/canon.js';
import { observe } from '../src/observe.js';
import { reconcile } from '../src/reconcile.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, '..', '..', 'fixtures', 'd1');
const raw = fs.readFileSync(path.join(dir, 'get_slice.live.2026-10-31.json'), 'utf8');
const config = JSON.parse(fs.readFileSync(path.join(dir, 'config.json'), 'utf8'));
const recorded = JSON.parse(fs.readFileSync(path.join(dir, 'observation.live.2026-10-31.json'), 'utf8'));
const livePkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.live.json'), 'utf8'));
const syntheticPkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'));
const source = { kind: 'rpc', ...config, state_selection: 'latest-final', client_version: 'genlayer-js@1.1.8' };

test('canonical encoding reproduces the task_sha256 the deployed contract computed', () => {
  const r = JSON.parse(raw);
  const { task_sha256, ...initial } = r.task;
  initial.status = 'REGISTERED'; initial.attempt = 0;
  assert.equal(digest(initial), task_sha256);
  assert.equal(digest(r.task.criteria), r.task.criteria_sha256);
  assert.equal(sha256(r.latest_attempt.evidence), r.latest_attempt.evidence_sha256);
});

test('the recorded observation is what observe() produces from the recorded bytes', () => {
  const o = observe(raw, { source, now: new Date(recorded.observed_at) });
  assert.deepEqual(o, recorded);
  assert.equal(o.raw_sha256, sha256(raw));
  assert.equal(o.task.status, 'CONSUMED');
  assert.equal(o.latest_attempt.review.verdict, 'PASS');
  assert.equal(o.latest_attempt.consumed_by.toLowerCase(), o.task.executor.toLowerCase());
});

test('the reconstructed D1 package reconciles CONSISTENT against the live state, status CONSUMED', () => {
  const r = reconcile(livePkg, recorded, config);
  assert.equal(r.decision, 'CONSISTENT');
  assert.equal(r.remote_status, 'CONSUMED');
  assert.equal(r.remote_verdict, 'PASS');
  assert.equal(r.authority, 'none');
  assert.match(r.next_action, /closed on chain/);
});

test('the synthetic package is a different evidence text: INTEGRITY_MISMATCH against the live state', () => {
  const r = reconcile(syntheticPkg, recorded, config);
  assert.equal(r.decision, 'INTEGRITY_MISMATCH');
  assert.ok(r.reasons.some((m) => /evidence on the contract is not the evidence in this package/.test(m)));
});
