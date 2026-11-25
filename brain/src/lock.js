// The Brain's lock: a lease carried by the head commit of the branch `brain/lock`.
//
//   * Taking the lock creates the branch (create-only: it either succeeds or fails) or, when the
//     branch exists and its lease is released or expired, moves it to a new CHILD commit with a
//     fast-forward-only update. Two runs that read the same head both build a child of it; the
//     first update wins and the second is not a fast-forward, so it fails and that run exits.
//   * The lease lasts 40 minutes. Renewal and release are fast-forward updates too.
//   * The branch is never deleted. No store in this package has a delete operation, so a run
//     whose lease ran out cannot remove another run's lock.
//   * Before every write the run calls assertHeld(): the branch head must still be this run's own
//     commit, still `held`, and the lease must have more than `safetyMs` left. Otherwise it throws
//     LeaseLostError and the run stops writing.
//
// A store is { getRef(), createRef(message), fastForward(expectedSha, message) }:
//   getRef()       -> null | { sha, message }
//   createRef(m)   -> { ok: true, sha } | { ok: false, reason: 'exists' }
//   fastForward(e,m) builds a child of `e` carrying `m` and moves the branch to it only if that is a
//                  fast-forward of the current head -> { ok: true, sha } | { ok: false, reason: 'not_fast_forward' }
import crypto from 'node:crypto';

export const LOCK_BRANCH = 'brain/lock';
export const LEASE_SCHEMA = 'odir-brain-lease/1';
export const LEASE_MS = 40 * 60 * 1000;
export const SAFETY_MS = 60 * 1000;

export class LeaseLostError extends Error {
  constructor(reason, detail) {
    super(`lease lost (${reason}): ${detail}`);
    this.reason = reason;
  }
}

export class LeaseFormatError extends Error {}

const iso = (ms) => new Date(ms).toISOString();

export function formatLease(lease) {
  const head = lease.state === 'held'
    ? `brain-lock: held by ${lease.run_id} until ${lease.expires_at}`
    : `brain-lock: released by ${lease.run_id} at ${lease.at}`;
  const keys = Object.keys(lease).sort();
  const body = JSON.stringify(Object.fromEntries(keys.map((k) => [k, lease[k]])));
  return `${head}\n\n${body}\n`;
}

const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

export function parseLease(message) {
  if (typeof message !== 'string') throw new LeaseFormatError('commit message missing');
  const parts = message.split('\n\n');
  if (parts.length < 2) throw new LeaseFormatError('no lease body');
  let lease;
  try { lease = JSON.parse(parts.slice(1).join('\n\n').trim()); } catch { throw new LeaseFormatError('lease body is not JSON'); }
  if (!lease || lease.schema !== LEASE_SCHEMA) throw new LeaseFormatError(`lease schema is not ${LEASE_SCHEMA}`);
  if (!RUN_ID.test(String(lease.run_id))) throw new LeaseFormatError('lease run_id is invalid');
  if (lease.state !== 'held' && lease.state !== 'released') throw new LeaseFormatError('lease state must be held or released');
  if (Number.isNaN(Date.parse(lease.at))) throw new LeaseFormatError('lease at is not a time');
  if (lease.state === 'held' && Number.isNaN(Date.parse(lease.expires_at))) throw new LeaseFormatError('held lease has no expiry');
  return lease;
}

export function newRunId(nowMs, rand = () => crypto.randomBytes(3).toString('hex')) {
  return `brain-${iso(nowMs).replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')}-${rand()}`;
}

export class LeaseLock {
  constructor({ store, runId, clock = () => Date.now(), leaseMs = LEASE_MS, safetyMs = SAFETY_MS }) {
    if (!store) throw new Error('store required');
    if (!RUN_ID.test(String(runId))) throw new Error('runId invalid');
    if (!(safetyMs < leaseMs)) throw new Error('safetyMs must be shorter than the lease');
    this.store = store; this.runId = runId; this.clock = clock; this.leaseMs = leaseMs; this.safetyMs = safetyMs;
    this.sha = null; this.lease = null; this.released = false;
  }

  #lease(state, extra = {}) {
    const now = this.clock();
    const lease = { schema: LEASE_SCHEMA, run_id: this.runId, state, at: iso(now), ...extra };
    if (state === 'held') lease.expires_at = iso(now + this.leaseMs);
    return lease;
  }

  // -> { ok: true, mode: 'created' | 'after_release' | 'took_over_expired', sha, previous? }
  //  | { ok: false, reason: 'held' | 'lost_race' | 'unreadable', holder?, expires_at?, detail? }
  async acquire() {
    if (this.sha) throw new Error('acquire called twice');
    const head = await this.store.getRef();
    if (head === null) {
      const lease = this.#lease('held');
      const r = await this.store.createRef(formatLease(lease));
      if (!r.ok) return { ok: false, reason: 'lost_race', detail: 'another run created brain/lock first' };
      this.sha = r.sha; this.lease = lease;
      return { ok: true, mode: 'created', sha: r.sha };
    }
    let current;
    try { current = parseLease(head.message); } catch (e) {
      // Fail closed: an unreadable lease may belong to a newer Brain. The owner repairs it.
      return { ok: false, reason: 'unreadable', detail: e.message };
    }
    const now = this.clock();
    let mode;
    if (current.state === 'released') mode = 'after_release';
    else if (Date.parse(current.expires_at) <= now) mode = 'took_over_expired';
    else return { ok: false, reason: 'held', holder: current.run_id, expires_at: current.expires_at };
    const lease = this.#lease('held', mode === 'took_over_expired' ? { took_over_from: current.run_id } : {});
    const r = await this.store.fastForward(head.sha, formatLease(lease));
    if (!r.ok) return { ok: false, reason: 'lost_race', detail: 'brain/lock moved before the fast-forward' };
    this.sha = r.sha; this.lease = lease;
    return { ok: true, mode, sha: r.sha, previous: { run_id: current.run_id, state: current.state } };
  }

  get held() { return Boolean(this.sha) && !this.released; }

  // Call before every write. Throws LeaseLostError; never returns false.
  async assertHeld(what = 'write') {
    if (!this.sha || this.released) throw new LeaseLostError('not_held', `${what}: this run does not hold brain/lock`);
    const head = await this.store.getRef();
    if (!head) throw new LeaseLostError('moved', `${what}: brain/lock is gone`);
    if (head.sha !== this.sha) throw new LeaseLostError('moved', `${what}: brain/lock moved to ${head.sha}`);
    let lease;
    try { lease = parseLease(head.message); } catch (e) { throw new LeaseLostError('moved', `${what}: ${e.message}`); }
    if (lease.run_id !== this.runId || lease.state !== 'held') throw new LeaseLostError('moved', `${what}: lease is not this run's`);
    const left = Date.parse(lease.expires_at) - this.clock();
    if (left <= this.safetyMs) throw new LeaseLostError('expired', `${what}: lease has ${Math.max(0, Math.floor(left / 1000))} s left`);
    return true;
  }

  async renew() {
    await this.assertHeld('renew');
    const lease = this.#lease('held', { renewed: true });
    const r = await this.store.fastForward(this.sha, formatLease(lease));
    if (!r.ok) throw new LeaseLostError('moved', 'renew: brain/lock moved');
    this.sha = r.sha; this.lease = lease;
    return r.sha;
  }

  async release() {
    await this.assertHeld('release');
    const lease = this.#lease('released');
    const r = await this.store.fastForward(this.sha, formatLease(lease));
    if (!r.ok) throw new LeaseLostError('moved', 'release: brain/lock moved');
    this.sha = r.sha; this.lease = lease; this.released = true;
    return r.sha;
  }
}

// In-memory store with git's real fast-forward rule (the current head must be an ancestor of,
// or equal to, the new commit). Used by tests and by `--lock-store memory`.
export class MemoryRefStore {
  constructor() { this.commits = new Map(); this.head = null; this.log = []; this.n = 0; }
  #commit(parent, message) {
    const sha = crypto.createHash('sha1').update(`${this.n++}\0${parent}\0${message}`).digest('hex');
    this.commits.set(sha, { parent, message });
    return sha;
  }
  #isAncestor(a, b) { for (let c = b; c; c = this.commits.get(c).parent) if (c === a) return true; return false; }
  async getRef() {
    this.log.push('get');
    return this.head ? { sha: this.head, message: this.commits.get(this.head).message } : null;
  }
  async createRef(message) {
    this.log.push('create');
    if (this.head) return { ok: false, reason: 'exists' };
    this.head = this.#commit(null, message);
    return { ok: true, sha: this.head };
  }
  async fastForward(expectedSha, message) {
    this.log.push('ff');
    if (!this.commits.has(expectedSha)) return { ok: false, reason: 'unknown_parent' };
    const sha = this.#commit(expectedSha, message);
    if (!this.head || !this.#isAncestor(this.head, sha)) return { ok: false, reason: 'not_fast_forward' };
    this.head = sha;
    return { ok: true, sha };
  }
  history() {
    const out = [];
    for (let c = this.head; c; c = this.commits.get(c).parent) out.push(parseLease(this.commits.get(c).message));
    return out.reverse();
  }
}
