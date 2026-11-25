// Derived state. The run keeps no state file of its own: everything is worked out from `main`,
// the holding-bay branch `brain/holding` and the open pull requests, so a crashed or overlapping
// run cannot corrupt it.
//
// A repo view is { readFile(ref, path) -> string|null, listTree(ref) -> string[]|null }.
// Open pull requests are [{ number, head_ref, labels: [name], body }]. A promotion PR lists its
// items in its body as `<!-- brain-items: key1,key2 -->`.
import { parseQueue, queueOrder } from './queue.js';

export const QUEUE_PATH = 'brain/QUEUE.md';
export const HOLDING_BRANCH = 'brain/holding';
// Phase 1 (slice A3): nothing is drafted before these are on main.
export const PHASE1_FILES = [
  'schema/role-template.v1.json',
  'schema/agreement.v1.json',
  'templates/bases/p2p.json',
  'templates/bases/b2p.json',
];
export const STAGES = ['queued', 'holding', 'promoted', 'approved'];

const ITEMS = /<!--\s*brain-items:\s*([a-z0-9_,\s]*)-->/;

export function promotedKeys(pulls) {
  const out = new Map();
  for (const p of pulls || []) {
    const m = ITEMS.exec(p.body || '');
    if (!m) continue;
    for (const k of m[1].split(',').map((s) => s.trim()).filter(Boolean)) if (!out.has(k)) out.set(k, p.number);
  }
  return out;
}

export async function deriveState({ repo, snapshot, pulls = [] }) {
  const state = { queue: null, queue_error: null, bases: null, stages: {}, counts: {}, next_queued: null, holding_exists: false, unknown_queue_keys: [] };
  let queue = null;
  try { queue = parseQueue(await repo.readFile('main', QUEUE_PATH)); } catch (e) { state.queue_error = e.message; }
  const mainTree = new Set((await repo.listTree('main')) || []);
  const missing = PHASE1_FILES.filter((p) => !mainTree.has(p));
  state.bases = { merged: missing.length === 0, missing };
  const holdingTree = await repo.listTree(HOLDING_BRANCH);
  state.holding_exists = holdingTree !== null;
  const holding = new Set(holdingTree || []);
  if (queue) state.queue = { exists: queue.exists, order: queue.order, pinned_registry_sha256: queue.pinned_registry_sha256, listed: queue.listed.length };
  if (!snapshot || !queue) return state;

  const { order, unknown, source } = queueOrder(queue, snapshot);
  state.queue.source = source;
  state.queue.length = order.length;
  state.unknown_queue_keys = unknown;
  const family = new Map(snapshot.roles.map((r) => [r.key, r.family.toLowerCase()]));
  const promoted = promotedKeys(pulls);
  for (const s of STAGES) state.counts[s] = 0;
  for (const key of order) {
    let stage = 'queued';
    if (mainTree.has(`templates/roles/${key}/module.json`)) stage = 'approved';
    else if (promoted.has(key)) stage = 'promoted';
    else if (holding.has(`holding/templates/${family.get(key)}/${key}/module.json`)) stage = 'holding';
    state.stages[key] = stage;
    state.counts[stage]++;
  }
  state.next_queued = order.find((k) => state.stages[k] === 'queued') || null;
  return state;
}
