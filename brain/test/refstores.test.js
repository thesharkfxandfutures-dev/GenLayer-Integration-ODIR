import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { LeaseLock, LeaseLostError, parseLease } from '../src/lock.js';
import { GitRefStore, GitHubRefStore } from '../src/refstores.js';
import { clock, barrier, MIN } from './helpers.js';

function tempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'brain-lock-'));
  execFileSync('git', ['init', '-q', dir]);
  return dir;
}
const git = (dir, ...a) => execFileSync('git', ['-C', dir, ...a], { encoding: 'utf8' }).trim();

test('git store: real git compare-and-swap lets exactly one of two racing runs create brain/lock', async () => {
  const dir = tempRepo(); const c = clock();
  const store = barrier(new GitRefStore({ dir }));
  const rs = await Promise.all(['run-a', 'run-b'].map((id) => new LeaseLock({ store, runId: id, clock: c.now }).acquire()));
  assert.equal(rs.filter((r) => r.ok).length, 1);
  assert.equal(rs.find((r) => !r.ok).reason, 'lost_race');
  assert.equal(git(dir, 'rev-list', '--count', 'refs/heads/brain/lock'), '1');
});

test('git store: takeover race on an expired lease, a lost lease, and release by fast-forward', async () => {
  const dir = tempRepo(); const c = clock();
  const plain = new GitRefStore({ dir });
  await new LeaseLock({ store: plain, runId: 'run-crashed', clock: c.now }).acquire();
  c.advance(41 * MIN);
  const store = barrier(plain);
  const locks = ['run-a', 'run-b'].map((id) => new LeaseLock({ store, runId: id, clock: c.now }));
  const rs = await Promise.all(locks.map((l) => l.acquire()));
  assert.equal(rs.filter((r) => r.ok).length, 1);
  const winner = locks[rs.findIndex((r) => r.ok)];
  const loser = locks[rs.findIndex((r) => !r.ok)];
  await assert.rejects(loser.assertHeld(), LeaseLostError);
  await winner.release();
  assert.equal(git(dir, 'rev-list', '--count', 'refs/heads/brain/lock'), '3', 'crashed → takeover → released, all on one line');
  const head = await plain.getRef();
  assert.equal(parseLease(head.message).state, 'released');
  const leaseJson = JSON.parse(git(dir, 'show', 'refs/heads/brain/lock:LEASE.json'));
  assert.equal(leaseJson.state, 'released');
  assert.equal(git(dir, 'ls-tree', '--name-only', 'refs/heads/brain/lock'), 'LEASE.json');
});

test('git store: a stale fast-forward is refused and a second create is refused', async () => {
  const dir = tempRepo();
  const s = new GitRefStore({ dir });
  const msg = (id) => `h\n\n{"at":"2026-11-25T12:00:00.000Z","expires_at":"2026-11-25T12:40:00.000Z","run_id":"${id}","schema":"odir-brain-lease/1","state":"held"}\n`;
  const a = await s.createRef(msg('a'));
  assert.equal(a.ok, true);
  assert.deepEqual(await s.createRef(msg('b')), { ok: false, reason: 'exists' });
  const b = await s.fastForward(a.sha, msg('b'));
  assert.equal(b.ok, true);
  assert.deepEqual(await s.fastForward(a.sha, msg('c')), { ok: false, reason: 'not_fast_forward' });
  assert.equal(parseLease((await s.getRef()).message).run_id, 'b');
});

test('git store: a broken lock directory is an error, not a lost race', async () => {
  const notRepo = fs.mkdtempSync(path.join(os.tmpdir(), 'brain-notrepo-'));
  const lock = new LeaseLock({ store: new GitRefStore({ dir: path.join(notRepo, 'missing') }), runId: 'run-a', clock: clock().now });
  await assert.rejects(lock.acquire(), /read brain\/lock/);
});

// A fake GitHub with the git-data semantics the store relies on.
function fakeGitHub() {
  const objs = new Map(); const refs = new Map(); const calls = [];
  const sha = (x) => crypto.createHash('sha1').update(JSON.stringify(x) + Math.random()).digest('hex');
  const isAncestor = (a, b) => { for (let c = b; c; c = objs.get(c).parents[0]) if (c === a) return true; return false; };
  const json = (status, body) => ({ status, text: async () => (body === undefined ? '' : JSON.stringify(body)) });
  const fetch = async (url, init) => {
    const u = new URL(url); const p = u.pathname.replace('/repos/o/r', ''); const m = init.method; const body = init.body ? JSON.parse(init.body) : null;
    calls.push({ m, p, body, auth: init.headers.authorization });
    if (m === 'GET' && p.startsWith('/git/ref/heads/')) { const r = refs.get(p.slice('/git/ref/heads/'.length)); return r ? json(200, { object: { sha: r } }) : json(404, { message: 'Not Found' }); }
    if (m === 'GET' && p.startsWith('/git/commits/')) { const o = objs.get(p.slice('/git/commits/'.length)); return o ? json(200, { sha: p.split('/').pop(), message: o.message }) : json(404, {}); }
    if (m === 'POST' && p === '/git/trees') { const s = sha(body); objs.set(s, { tree: body.tree }); return json(201, { sha: s }); }
    if (m === 'POST' && p === '/git/commits') { const s = sha(body); objs.set(s, { message: body.message, tree: body.tree, parents: body.parents }); return json(201, { sha: s }); }
    if (m === 'POST' && p === '/git/refs') { const n = body.ref.replace('refs/heads/', ''); if (refs.has(n)) return json(422, { message: 'Reference already exists' }); refs.set(n, body.sha); return json(201, {}); }
    if (m === 'PATCH' && p.startsWith('/git/refs/heads/')) {
      const n = p.slice('/git/refs/heads/'.length); const cur = refs.get(n);
      if (body.force !== false) return json(400, { message: 'test fake requires force:false' });
      if (!cur || !isAncestor(cur, body.sha)) return json(422, { message: 'Update is not a fast forward' });
      refs.set(n, body.sha); return json(200, {});
    }
    return json(405, { message: `unexpected ${m} ${p}` });
  };
  return { fetch, calls, refs, objs };
}

test('GitHub store: create, race, takeover, release and lost lease through the REST git-data API', async () => {
  const gh = fakeGitHub(); const c = clock();
  const store = barrier(new GitHubRefStore({ owner: 'o', repo: 'r', token: 't', fetch: gh.fetch }));
  const locks = ['run-a', 'run-b'].map((id) => new LeaseLock({ store, runId: id, clock: c.now }));
  const rs = await Promise.all(locks.map((l) => l.acquire()));
  assert.equal(rs.filter((r) => r.ok).length, 1);
  const winner = locks[rs.findIndex((r) => r.ok)];
  c.advance(41 * MIN);
  const late = new LeaseLock({ store, runId: 'run-c', clock: c.now });
  assert.equal((await late.acquire()).mode, 'took_over_expired');
  await assert.rejects(winner.assertHeld(), LeaseLostError);
  await assert.rejects(winner.release(), LeaseLostError);
  await late.release();
  assert.equal(gh.calls.some((x) => x.m === 'DELETE'), false, 'never deletes');
  assert.ok(gh.calls.filter((x) => x.m === 'PATCH').every((x) => x.body.force === false), 'every move is force:false');
  assert.ok(gh.calls.every((x) => x.auth === 'Bearer t'));
  const head = gh.objs.get(gh.refs.get('brain/lock'));
  assert.equal(parseLease(head.message).state, 'released');
  assert.equal(gh.objs.get(head.tree).tree[0].path, 'LEASE.json');
});

test('GitHub store: unexpected HTTP statuses throw instead of being read as a lost race', async () => {
  const f = async () => ({ status: 500, text: async () => '{}' });
  const s = new GitHubRefStore({ owner: 'o', repo: 'r', fetch: f });
  await assert.rejects(s.getRef(), /HTTP 500/);
});
