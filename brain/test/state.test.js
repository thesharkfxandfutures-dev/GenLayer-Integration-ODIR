import test from 'node:test';
import assert from 'node:assert/strict';
import { parseQueue, queueOrder, QueueFormatError } from '../src/queue.js';
import { deriveState, promotedKeys } from '../src/state.js';
import { evaluateStops, firstRunStop, pickAction, STOP_REASONS } from '../src/stops.js';
import { snapshotOf, repoWith, queueMd } from './helpers.js';

const snap = snapshotOf();
const stopsFor = async (opts, extra = {}) => {
  const state = await deriveState({ repo: repoWith(opts), snapshot: snap, pulls: extra.pulls || [] });
  const stops = evaluateStops({ snapshot: snap, snapshotProblem: extra.problem || null, state, genskillAvailable: extra.genskill ?? true });
  return { state, stops, stop: firstRunStop(stops), action: pickAction({ stops, state }) };
};

test('QUEUE.md: pin, order and listed roles parse; a missing file means unpinned registry order', () => {
  const q = parseQueue(queueMd({ pin: 'a'.repeat(64), order: 'listed', listed: ['retoucher', 'photographer'] }));
  assert.deepEqual(q, { exists: true, pinned_registry_sha256: 'a'.repeat(64), order: 'listed', listed: ['retoucher', 'photographer'] });
  assert.deepEqual(parseQueue(null), { exists: false, pinned_registry_sha256: null, order: 'registry', listed: [] });
  assert.equal(parseQueue(queueMd()).pinned_registry_sha256, null);
});

test('QUEUE.md: malformed files are refused', () => {
  for (const bad of [
    '# no pin\norder: registry\n',
    'registry_sha256: abc\n',
    'registry_sha256: unpinned\nregistry_sha256: unpinned\n',
    'registry_sha256: unpinned\norder: random\n',
    'registry_sha256: unpinned\n## Queue\n- photographer\n- photographer\n',
    'registry_sha256: unpinned\n## Queue\n- Photographer!\n',
  ]) assert.throws(() => parseQueue(bad), QueueFormatError, bad);
});

test('queue order: listed first then registry order; "listed" keeps only listed; unknown keys reported', () => {
  const reg = queueOrder(parseQueue(queueMd({ listed: ['retoucher', 'ghost'] })), snap);
  assert.deepEqual(reg.order, ['retoucher', 'photographer', 'makeup_artist', 'model_fashion']);
  assert.deepEqual(reg.unknown, ['ghost']);
  const listed = queueOrder(parseQueue(queueMd({ order: 'listed', listed: ['model_fashion'] })), snap);
  assert.deepEqual(listed.order, ['model_fashion']);
});

test('the four stop checks run in order and all are evaluated', async () => {
  const { stops } = await stopsFor({ pin: snap.registry_sha256 });
  assert.deepEqual(stops.map((s) => s.reason), STOP_REASONS);
});

test('a registry-hash change stops the run before anything else', async () => {
  const { stop, action, stops } = await stopsFor({ pin: 'b'.repeat(64), bases: false });
  assert.equal(stop.reason, 'registry_hash_changed');
  assert.match(stop.detail, new RegExp(`pinned b{64}, Inspector observed ${snap.registry_sha256}`));
  assert.equal(action.would_do, 'none');
  assert.equal(stops.find((s) => s.reason === 'bases_not_merged').open, true, 'later checks still evaluated');
});

test('an unpinned registry, a bad snapshot or an unreadable QUEUE.md also stop at the registry check', async () => {
  assert.match((await stopsFor({ pin: null })).stop.detail, /not pinned/);
  assert.match((await stopsFor({ pin: snap.registry_sha256 }, { problem: 'schema failed' })).stop.detail, /snapshot unusable/);
  const bad = repoWith({ pin: snap.registry_sha256 });
  bad.trees.main['brain/QUEUE.md'] = 'order: registry\n';
  const state = await deriveState({ repo: bad, snapshot: snap });
  const stop = firstRunStop(evaluateStops({ snapshot: snap, state, genskillAvailable: true }));
  assert.equal(stop.reason, 'registry_hash_changed');
  assert.match(stop.detail, /QUEUE\.md unreadable/);
});

test('matching pin but phase 1 bases missing: stop at bases_not_merged, nothing drafted', async () => {
  const { stop, action } = await stopsFor({ pin: snap.registry_sha256, bases: false });
  assert.equal(stop.reason, 'bases_not_merged');
  assert.match(stop.detail, /schema\/role-template\.v1\.json/);
  assert.equal(action.would_do, 'none');
});

test('stages come from main, the holding bay and open PRs; the queue empties when nothing is queued', async () => {
  const pulls = [{ number: 7, head_ref: 'brain/promote-1', labels: ['brain-promote'], body: 'Promote\n<!-- brain-items: model_fashion -->' },
    { number: 8, head_ref: 'fork/x', labels: [], body: '<!-- brain-items: retoucher -->' }];
  const opts = { pin: snap.registry_sha256, approved: ['photographer'], holding: ['holding/templates/craft/makeup_artist/module.json'] };
  const { state, stop, action } = await stopsFor(opts, { pulls });
  assert.deepEqual(state.stages, { photographer: 'approved', makeup_artist: 'holding', model_fashion: 'promoted', retoucher: 'queued' });
  assert.deepEqual(state.counts, { queued: 1, holding: 1, promoted: 1, approved: 1 });
  assert.equal(stop, null);
  assert.deepEqual([action.would_do, action.item], ['draft_role', 'retoucher']);

  const all = await stopsFor({ ...opts, approved: ['photographer', 'retoucher'] }, { pulls });
  assert.equal(all.stop.reason, 'queue_empty');
});

test('the holding-bay path uses the role family; another family\'s folder does not count', async () => {
  const { state } = await stopsFor({ pin: snap.registry_sha256, holding: ['holding/templates/maker/makeup_artist/module.json'] });
  assert.equal(state.stages.makeup_artist, 'queued');
});

test('genskill missing limits on-chain steps only; template work carries on', async () => {
  const { stops, stop, action } = await stopsFor({ pin: snap.registry_sha256 }, { genskill: false });
  const g = stops.find((s) => s.reason === 'genskill_missing');
  assert.deepEqual([g.open, g.scope], [true, 'onchain']);
  assert.equal(stop, null);
  assert.deepEqual([action.would_do, action.item], ['draft_role', 'photographer']);
});

const promo = (number, body, over = {}) => ({ number, head_ref: `brain/promote-${number}`, labels: ['brain-promote'], body, ...over });

test('promotion markers are read only from the brain-items comment of a labelled brain/promote-* PR', () => {
  const m = promotedKeys([promo(3, 'mentions photographer in prose'), promo(4, '<!-- brain-items: retoucher, dj -->')]);
  assert.deepEqual([...m.entries()], [['retoucher', 4], ['dj', 4]]);
});

test('a stranger\'s PR cannot mark roles promoted: the label and the brain/promote- branch are both required', () => {
  const body = '<!-- brain-items: photographer -->';
  assert.equal(promotedKeys([promo(9, body, { labels: [] })]).size, 0, 'no label');
  assert.equal(promotedKeys([promo(9, body, { head_ref: 'evil/brain-items' })]).size, 0, 'wrong branch');
  assert.equal(promotedKeys([promo(9, body, { head_ref: 'brain/holding' })]).size, 0, 'not a promote branch');
  assert.equal(promotedKeys([promo(9, body)]).size, 1);
});

test('when two promotion PRs list one role, the first listed PR is recorded', () => {
  const m = promotedKeys([promo(5, '<!-- brain-items: retoucher -->'), promo(6, '<!-- brain-items: retoucher, dj -->')]);
  assert.deepEqual([...m.entries()], [['retoucher', 5], ['dj', 6]]);
});
