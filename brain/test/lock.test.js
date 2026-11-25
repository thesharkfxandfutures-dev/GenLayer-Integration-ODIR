import test from 'node:test';
import assert from 'node:assert/strict';
import { LeaseLock, LeaseLostError, MemoryRefStore, parseLease, formatLease, LEASE_MS, newRunId } from '../src/lock.js';
import { clock, barrier, T0, MIN } from './helpers.js';

const lockFor = (store, runId, c) => new LeaseLock({ store, runId, clock: c.now });

test('first run creates brain/lock with a 40-minute lease', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  const r = await a.acquire();
  assert.equal(r.ok, true); assert.equal(r.mode, 'created');
  const lease = parseLease((await store.getRef()).message);
  assert.equal(lease.run_id, 'run-a'); assert.equal(lease.state, 'held');
  assert.equal(Date.parse(lease.expires_at) - T0, LEASE_MS);
  assert.equal(LEASE_MS, 40 * MIN);
});

test('lock race: two runs read the same empty state, exactly one wins the create', async () => {
  const store = barrier(new MemoryRefStore()); const c = clock();
  const [ra, rb] = await Promise.all([lockFor(store, 'run-a', c).acquire(), lockFor(store, 'run-b', c).acquire()]);
  const wins = [ra, rb].filter((r) => r.ok);
  const losses = [ra, rb].filter((r) => !r.ok);
  assert.equal(wins.length, 1); assert.equal(losses.length, 1);
  assert.equal(losses[0].reason, 'lost_race');
});

test('lock race on an expired lease: both see it expired, exactly one fast-forward wins', async () => {
  const inner = new MemoryRefStore(); const c = clock();
  await lockFor(inner, 'run-crashed', c).acquire();
  c.advance(41 * MIN);
  const store = barrier(inner);
  const [ra, rb] = await Promise.all([lockFor(store, 'run-a', c).acquire(), lockFor(store, 'run-b', c).acquire()]);
  assert.equal([ra, rb].filter((r) => r.ok).length, 1);
  assert.equal([ra, rb].find((r) => !r.ok).reason, 'lost_race');
  const hist = inner.history();
  assert.equal(hist.length, 2, 'one takeover commit on top of the crashed lease');
  assert.equal(hist[1].took_over_from, 'run-crashed');
});

test('a valid lease is respected; a stale lease is taken over at expiry', async () => {
  const store = new MemoryRefStore(); const c = clock();
  await lockFor(store, 'run-a', c).acquire(); // run-a then crashes: never releases
  c.advance(39 * MIN);
  const held = await lockFor(store, 'run-b', c).acquire();
  assert.deepEqual([held.ok, held.reason, held.holder], [false, 'held', 'run-a']);
  c.advance(1 * MIN); // exactly at expiry
  const b = lockFor(store, 'run-c', c);
  const took = await b.acquire();
  assert.equal(took.ok, true); assert.equal(took.mode, 'took_over_expired');
  assert.deepEqual(took.previous, { run_id: 'run-a', state: 'held' });
  assert.equal(parseLease((await store.getRef()).message).took_over_from, 'run-a');
});

test('release is a fast-forward to a released child; the branch is never deleted', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  await a.release();
  assert.equal(typeof store.deleteRef, 'undefined');
  const b = lockFor(store, 'run-b', c);
  const r = await b.acquire();
  assert.equal(r.mode, 'after_release');
  assert.deepEqual(store.history().map((l) => `${l.run_id}:${l.state}`), ['run-a:held', 'run-a:released', 'run-b:held']);
});

test('lost lease mid-run: after a takeover, assertHeld throws "moved" and release does not move the branch', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  await a.assertHeld();
  c.advance(41 * MIN);
  await lockFor(store, 'run-b', c).acquire();
  await assert.rejects(a.assertHeld('push'), (e) => e instanceof LeaseLostError && e.reason === 'moved');
  const head = (await store.getRef()).sha;
  await assert.rejects(a.release(), LeaseLostError);
  assert.equal((await store.getRef()).sha, head, 'run-b still holds the lock');
});

test('lost lease mid-run: an expired lease with no takeover still stops writes', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  c.advance(40 * MIN);
  await assert.rejects(a.assertHeld(), (e) => e.reason === 'expired');
});

test('the safety margin: a write needs more than 60 s of lease left', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  c.advance(38 * MIN + 59 * 1000); // 61 s left
  await a.assertHeld();
  c.advance(1000); // 60 s left
  await assert.rejects(a.assertHeld(), (e) => e.reason === 'expired');
});

test('renewal extends the lease by fast-forward; a lost lease cannot renew', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  c.advance(30 * MIN);
  await a.renew();
  c.advance(30 * MIN); // 60 min after start, 30 after renewal
  await a.assertHeld();
  const b = await lockFor(store, 'run-b', c).acquire();
  assert.equal(b.reason, 'held');
  c.advance(11 * MIN);
  await lockFor(store, 'run-c', c).acquire();
  await assert.rejects(a.renew(), LeaseLostError);
});

test('assertHeld before acquire, and after release, refuses', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await assert.rejects(a.assertHeld(), (e) => e.reason === 'not_held');
  await a.acquire(); await a.release();
  await assert.rejects(a.assertHeld(), (e) => e.reason === 'not_held');
});

test('an unreadable lease fails closed and is not taken over', async () => {
  const store = new MemoryRefStore(); const c = clock();
  await store.createRef('hand-edited\n\n{"schema":"odir-brain-lease/2","run_id":"x","state":"held"}');
  const head = (await store.getRef()).sha;
  c.advance(24 * 60 * MIN);
  const r = await lockFor(store, 'run-a', c).acquire();
  assert.deepEqual([r.ok, r.reason], [false, 'unreadable']);
  assert.equal((await store.getRef()).sha, head);
});

test('a lease whose run id was rewritten is not this run\'s', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const a = lockFor(store, 'run-a', c);
  await a.acquire();
  // someone fast-forwards a lease claiming a different holder
  const fake = formatLease({ schema: 'odir-brain-lease/1', run_id: 'run-x', state: 'held', at: new Date(c.now()).toISOString(), expires_at: new Date(c.now() + LEASE_MS).toISOString() });
  await store.fastForward((await store.getRef()).sha, fake);
  await assert.rejects(a.assertHeld(), (e) => e.reason === 'moved');
});

test('parseLease refuses malformed leases', () => {
  const ok = { schema: 'odir-brain-lease/1', run_id: 'r1', state: 'held', at: '2026-11-25T12:00:00.000Z', expires_at: '2026-11-25T12:40:00.000Z' };
  assert.equal(parseLease(formatLease(ok)).run_id, 'r1');
  for (const bad of [
    'no body',
    'h\n\nnot json',
    formatLease({ ...ok, schema: 'x' }),
    formatLease({ ...ok, state: 'free' }),
    formatLease({ ...ok, run_id: 'bad id with spaces' }),
    formatLease({ ...ok, expires_at: 'soon' }),
  ]) assert.throws(() => parseLease(bad));
});

test('run ids are unique and well-formed', () => {
  const a = newRunId(T0), b = newRunId(T0);
  assert.match(a, /^brain-20261125T120000Z-[0-9a-f]{6}$/);
  assert.notEqual(a, b);
});
