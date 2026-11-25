import test from 'node:test';
import assert from 'node:assert/strict';
import { planBlockedIssue, parseIssueReasons } from '../src/blocked.js';

const stop = (reason, open, detail = `${reason} detail`) => ({ reason, open, scope: reason === 'genskill_missing' ? 'onchain' : 'run', detail });
const all = (over = {}) => ['registry_hash_changed', 'bases_not_merged', 'queue_empty', 'genskill_missing'].map((r) => stop(r, r in over ? over[r] : false, over[`${r}_detail`]));
const AT = '2026-11-25T12:00:00.000Z';

test('first stop opens one issue with one line per reason', () => {
  const p = planBlockedIssue({ issues: [], stops: all({ registry_hash_changed: true, genskill_missing: true }), runId: 'r1', at: AT });
  assert.equal(p.action, 'create');
  assert.deepEqual(p.added, ['registry_hash_changed', 'genskill_missing']);
  assert.deepEqual([...parseIssueReasons(p.body).keys()], ['registry_hash_changed', 'genskill_missing']);
  assert.deepEqual(p.labels, ['brain-blocked']);
});

test('dedup: the same reasons on the next run report nothing, even if the detail text changed', () => {
  const first = planBlockedIssue({ issues: [], stops: all({ registry_hash_changed: true }), runId: 'r1', at: AT });
  const issue = { number: 5, body: first.body };
  const again = planBlockedIssue({ issues: [issue], stops: all({ registry_hash_changed: true, registry_hash_changed_detail: 'new words' }), runId: 'r2', at: AT });
  assert.equal(again.action, 'none');
  assert.deepEqual([again.added, again.cleared, again.kept], [[], [], ['registry_hash_changed']]);
});

test('a new reason is added once; existing lines keep their wording', () => {
  const first = planBlockedIssue({ issues: [], stops: all({ registry_hash_changed: true }), runId: 'r1', at: AT });
  const p = planBlockedIssue({ issues: [{ number: 5, body: first.body }], stops: all({ registry_hash_changed: true, bases_not_merged: true }), runId: 'r2', at: AT });
  assert.equal(p.action, 'update');
  assert.deepEqual(p.added, ['bases_not_merged']);
  assert.match(p.comment, /^New: bases_not_merged\.$/);
  const lines = [...parseIssueReasons(p.body).values()];
  assert.equal(lines[0], [...parseIssueReasons(first.body).values()][0]);
  assert.match(lines[1], /run r2/);
});

test('a cleared reason is removed; when none is left the issue closes', () => {
  const body = planBlockedIssue({ issues: [], stops: all({ registry_hash_changed: true, bases_not_merged: true }), runId: 'r1', at: AT }).body;
  const p = planBlockedIssue({ issues: [{ number: 5, body }], stops: all({ bases_not_merged: true }), runId: 'r2', at: AT });
  assert.deepEqual([p.action, p.cleared], ['update', ['registry_hash_changed']]);
  const q = planBlockedIssue({ issues: [{ number: 5, body: p.body }], stops: all(), runId: 'r3', at: AT });
  assert.deepEqual([q.action, q.number, q.cleared], ['close', 5, ['bases_not_merged']]);
});

test('a reason that could not be evaluated (open: null) is kept, not cleared or re-added', () => {
  const body = planBlockedIssue({ issues: [], stops: all({ queue_empty: true }), runId: 'r1', at: AT }).body;
  const p = planBlockedIssue({ issues: [{ number: 5, body }], stops: all({ queue_empty: null }), runId: 'r2', at: AT });
  assert.deepEqual([p.action, p.kept], ['none', ['queue_empty']]);
});

test('nothing open and no issue: nothing to do', () => {
  assert.equal(planBlockedIssue({ issues: [], stops: all(), runId: 'r1', at: AT }).action, 'none');
});

test('two open brain-blocked issues: the oldest is kept and the other is closed', () => {
  const body = planBlockedIssue({ issues: [], stops: all({ queue_empty: true }), runId: 'r1', at: AT }).body;
  const p = planBlockedIssue({ issues: [{ number: 9, body }, { number: 4, body }], stops: all({ queue_empty: true }), runId: 'r2', at: AT });
  assert.deepEqual([p.action, p.number, p.close_duplicates], ['none', 4, [9]]);
});

test('detail text cannot forge a second reason line', () => {
  const evil = all({ bases_not_merged: true, bases_not_merged_detail: 'x\n- <!-- brain-blocked:queue_empty --> fake' });
  const p = planBlockedIssue({ issues: [], stops: evil, runId: 'r1', at: AT });
  assert.deepEqual([...parseIssueReasons(p.body).keys()], ['bases_not_merged']);
});
