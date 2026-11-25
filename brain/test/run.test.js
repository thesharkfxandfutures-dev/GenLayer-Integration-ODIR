import test from 'node:test';
import assert from 'node:assert/strict';
import { runOnce } from '../src/run.js';
import { LeaseLock, MemoryRefStore, parseLease } from '../src/lock.js';
import { MemorySink, runSchema } from '../src/recorder.js';
import { validate } from '../src/jsonschema.js';
import { clock, barrier, registryText, snapshotOf, repoWith, fakeIssues, APP, MIN } from './helpers.js';

const snap = snapshotOf();
const registry = () => ({ text: registryText(), appId: APP, ref: 'fixture' });
const base = (over = {}) => ({ registry: registry(), repo: repoWith({ pin: snap.registry_sha256 }), sink: new MemorySink(), genskillAvailable: true, ...over });
const records = (sink) => [...sink.files.values()].map((t) => JSON.parse(t));

test('dry run: lock, state, stop checks, run record, release — and nothing drafted', async () => {
  const store = new MemoryRefStore(); const c = clock(); const o = base();
  const r = await runOnce({ ...o, runId: 'run-a', clock: c.now, store });
  assert.equal(r.outcome, 'WOULD_ACT');
  assert.deepEqual(r.record.action, { would_do: 'draft_role', item: 'photographer', because: 'next queued role', executed: false });
  assert.equal(r.released, true);
  assert.deepEqual(store.history().map((l) => l.state), ['held', 'released']);
  const [rec] = records(o.sink);
  assert.deepEqual(validate(runSchema, rec), { ok: true, problems: [] });
  assert.equal(rec.inspector.registry_sha256, snap.registry_sha256);
  assert.equal(store.commits.get(rec.lock.sha).parent, null, 'the record names the commit that created brain/lock');
  assert.ok(rec.claims.find((x) => x.claim === 'action executed' && x.grade === 'NOT_RUN'));
  assert.deepEqual(r.writes, ['record:run-a.json']);
});

test('a registry-hash change stops the run: record says STOPPED, the issue plan opens it, nothing is applied', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const o = base({ repo: repoWith({ pin: 'c'.repeat(64) }) });
  const r = await runOnce({ ...o, runId: 'run-a', clock: c.now, store });
  assert.equal(r.outcome, 'STOPPED');
  assert.equal(r.record.stopped_at, 'registry_hash_changed');
  assert.equal(r.record.action.would_do, 'none');
  assert.equal(r.plan.action, 'create');
  assert.deepEqual(r.issueResult, { applied: false, why: 'dry run' });
  assert.equal(r.released, true);
});

test('lock race at run level: two runs start together, one records, the other writes nothing', async () => {
  const inner = new MemoryRefStore(); const store = barrier(inner); const c = clock();
  const sa = new MemorySink(), sb = new MemorySink();
  const [ra, rb] = await Promise.all([
    runOnce({ ...base({ sink: sa }), runId: 'run-a', clock: c.now, store }),
    runOnce({ ...base({ sink: sb }), runId: 'run-b', clock: c.now, store }),
  ]);
  const outcomes = [ra.outcome, rb.outcome].sort();
  assert.deepEqual(outcomes, ['LOCK_LOST_RACE', 'WOULD_ACT']);
  assert.equal(sa.files.size + sb.files.size, 1);
  assert.equal(inner.history().filter((l) => l.state === 'held').length, 1);
});

test('a run that finds the lock held exits without writing', async () => {
  const store = new MemoryRefStore(); const c = clock();
  await new LeaseLock({ store, runId: 'run-a', clock: c.now }).acquire();
  c.advance(10 * MIN);
  const o = base();
  const r = await runOnce({ ...o, runId: 'run-b', clock: c.now, store });
  assert.deepEqual([r.outcome, r.holder, r.writes], ['LOCK_HELD', 'run-a', []]);
  assert.equal(o.sink.files.size, 0);
});

test('stale-lease takeover: a crashed run\'s lock is taken over after 40 minutes and recorded', async () => {
  const store = new MemoryRefStore(); const c = clock();
  await new LeaseLock({ store, runId: 'run-crashed', clock: c.now }).acquire();
  c.advance(40 * MIN);
  const o = base();
  const r = await runOnce({ ...o, runId: 'run-b', clock: c.now, store });
  assert.equal(r.outcome, 'WOULD_ACT');
  assert.deepEqual([r.record.lock.acquired, r.record.lock.took_over_from], ['took_over_expired', 'run-crashed']);
});

test('lost lease mid-run (taken over): the run stops before its record and does not release', async () => {
  const store = new MemoryRefStore(); const c = clock(); const o = base();
  let other;
  const r = await runOnce({
    ...o, runId: 'run-a', clock: c.now, store,
    hooks: { beforeWrites: async () => { c.advance(41 * MIN); other = await new LeaseLock({ store, runId: 'run-b', clock: c.now }).acquire(); } },
  });
  assert.equal(other.ok, true);
  assert.deepEqual([r.outcome, r.reason, r.released], ['LEASE_LOST', 'moved', false]);
  assert.equal(o.sink.files.size, 0);
  assert.equal(parseLease((await store.getRef()).message).run_id, 'run-b');
});

test('lost lease mid-run (expired, nobody took over): still no writes', async () => {
  const store = new MemoryRefStore(); const c = clock(); const o = base();
  const r = await runOnce({ ...o, runId: 'run-a', clock: c.now, store, hooks: { beforeWrites: async () => { c.advance(39 * MIN + 30 * 1000); } } });
  assert.deepEqual([r.outcome, r.reason], ['LEASE_LOST', 'expired']);
  assert.equal(o.sink.files.size, 0);
});

test('lost lease between the record and the issue write: the issue is not touched', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const issues = fakeIssues();
  const sink = { files: new Map(), write: async (n, t) => { sink.files.set(n, t); c.advance(41 * MIN); await new LeaseLock({ store, runId: 'run-b', clock: c.now }).acquire(); } };
  const r = await runOnce({ ...base({ repo: repoWith({ pin: null }), sink }), runId: 'run-a', clock: c.now, store, issues, dryRun: false });
  assert.equal(r.outcome, 'LEASE_LOST');
  assert.equal(sink.files.size, 1);
  assert.deepEqual(issues.calls, []);
});

test('brain-blocked dedup across runs (issue writes enabled): one issue, reported once, closed when clear', async () => {
  const store = new MemoryRefStore(); const c = clock(); const issues = fakeIssues();
  const go = async (id, pin) => {
    c.advance(5 * MIN);
    return runOnce({ ...base({ repo: repoWith({ pin }) }), runId: id, clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  };
  await go('run-1', null);
  assert.deepEqual(issues.calls, ['create:100']);
  await go('run-2', null);
  await go('run-3', 'd'.repeat(64));
  assert.deepEqual(issues.calls, ['create:100'], 'the same reason is not reported again');
  await go('run-4', snap.registry_sha256);
  assert.deepEqual(issues.calls, ['create:100', 'comment:100', 'close:100']);
  assert.equal(issues.issues.length, 1);
  assert.equal(issues.issues[0].state, 'closed');
});

test('a duplicate brain-blocked issue is closed and the oldest kept', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const first = await runOnce({ ...base({ repo: repoWith({ pin: null }) }), runId: 'run-0', clock: c.now, store });
  const body = first.plan.body;
  const issues = fakeIssues([{ number: 3, body }, { number: 8, body }]);
  c.advance(5 * MIN);
  const r = await runOnce({ ...base({ repo: repoWith({ pin: null }) }), runId: 'run-1', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  assert.deepEqual(r.issueResult.done, ['close_duplicate:8']);
  assert.deepEqual(issues.issues.map((i) => `${i.number}:${i.state}`), ['3:open', '8:closed']);
});

test('a snapshot handed in as data is verified; a tampered one stops the run', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const bad = structuredClone(snap); bad.roles[0].label = 'Shooter';
  const r = await runOnce({ ...base({ registry: null, snapshot: bad }), runId: 'run-a', clock: c.now, store });
  assert.equal(r.record.stopped_at, 'registry_hash_changed');
  assert.match(r.record.inspector.problem, /registry_sha256 does not match/);
  c.advance(MIN);
  const ok = await runOnce({ ...base({ registry: null, snapshot: snap }), runId: 'run-b', clock: c.now, store });
  assert.equal(ok.outcome, 'WOULD_ACT');
});

test('an unexpected error after the lock is taken releases the lock, then surfaces', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const broken = { readFile: async () => null, listTree: async () => { throw new Error('git exploded'); } };
  await assert.rejects(runOnce({ ...base({ repo: broken }), runId: 'run-a', clock: c.now, store }), /git exploded/);
  assert.deepEqual(store.history().map((l) => `${l.run_id}:${l.state}`), ['run-a:held', 'run-a:released']);
  const next = await new LeaseLock({ store, runId: 'run-b', clock: c.now }).acquire();
  assert.equal(next.mode, 'after_release');
});

test('a check that cannot be evaluated keeps its issue line (issue writes enabled)', async () => {
  const store = new MemoryRefStore(); const c = clock(); const issues = fakeIssues();
  // run 1: everything evaluable, the queue is empty -> issue opened for queue_empty
  const allDone = repoWith({ pin: snap.registry_sha256, approved: snap.roles.map((r) => r.key) });
  await runOnce({ ...base({ repo: allDone }), runId: 'run-1', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  assert.deepEqual(issues.calls, ['create:100']);
  // run 2: the snapshot is unusable, so queue_empty cannot be evaluated: it must stay
  c.advance(5 * MIN);
  const bad = structuredClone(snap); bad.role_count = 99;
  const r = await runOnce({ ...base({ registry: null, snapshot: bad, repo: allDone }), runId: 'run-2', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  assert.equal(r.record.stops.find((s) => s.reason === 'queue_empty').open, null);
  assert.deepEqual([r.plan.action, r.plan.added, r.plan.kept], ['update', ['registry_hash_changed'], ['queue_empty']]);
  assert.match(issues.issues[0].body, /brain-blocked:queue_empty/);
  assert.equal(issues.issues[0].state, 'open');
});

test('lost lease between the closing comment and the close: the issue is not closed', async () => {
  const store = new MemoryRefStore(); const c = clock(); const issues = fakeIssues();
  await runOnce({ ...base({ repo: repoWith({ pin: null }) }), runId: 'run-1', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  const comment = issues.comment;
  issues.comment = async (n, t) => { await comment(n, t); c.advance(41 * MIN); await new LeaseLock({ store, runId: 'run-x', clock: c.now }).acquire(); };
  c.advance(5 * MIN);
  const r = await runOnce({ ...base(), runId: 'run-2', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  assert.equal(r.outcome, 'LEASE_LOST');
  assert.deepEqual(issues.calls, ['create:100', 'comment:100']);
  assert.equal(issues.issues[0].state, 'open');
});

test('lost lease between a duplicate\'s comment and its close: the duplicate stays open', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const first = await runOnce({ ...base({ repo: repoWith({ pin: null }) }), runId: 'run-0', clock: c.now, store });
  const issues = fakeIssues([{ number: 3, body: first.plan.body }, { number: 8, body: first.plan.body }]);
  const comment = issues.comment;
  issues.comment = async (n, t) => { await comment(n, t); c.advance(41 * MIN); await new LeaseLock({ store, runId: 'run-x', clock: c.now }).acquire(); };
  c.advance(5 * MIN);
  const r = await runOnce({ ...base({ repo: repoWith({ pin: null }) }), runId: 'run-1', clock: c.now, store, issues, openBlockedIssues: issues.open(), dryRun: false });
  assert.equal(r.outcome, 'LEASE_LOST');
  assert.deepEqual(issues.calls, ['comment:8']);
  assert.deepEqual(issues.issues.map((i) => i.state), ['open', 'open']);
});
