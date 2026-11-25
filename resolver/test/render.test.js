import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderMarkdown, toParchment } from '../src/render.js';
import { resolve } from '../src/resolve.js';
import { makeBase, makeModule } from './helpers.js';

const FIELD = /\{\{\s*([a-z0-9_.-]{1,64})\s*\}\}/gi; // the parchment viewer's blank pattern (C1)

test('toParchment gives the shape the C1 parchment viewer reads', () => {
  const doc = resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW' });
  const p = toParchment(doc);
  assert.equal(p.base, 'P2P');
  assert.equal(p.jurisdiction, 'EW');
  assert.equal(p.terms_hash, doc.terms_hash);
  assert.equal(p.seal, null);
  assert.deepEqual(p.parties.map((x) => x.slot), ['engager', 'provider']);
  assert.deepEqual(p.parties.map((x) => x.name), ['Client', 'Tester']);
  assert.equal(new Set(p.sections.map((s) => s.key)).size, p.sections.length);
  for (const s of p.sections) for (const c of s.clauses) {
    assert.equal(typeof c.id, 'string');
    assert.equal(typeof c.text, 'string');
    for (const m of c.text.matchAll(FIELD)) assert.ok(p.fields[m[1]], `blank ${m[1]} has a label`);
  }
  assert.deepEqual(p.values, {});
  assert.deepEqual(p.fields.pay_days, { label: 'Days to pay', default: '14' });
});

test('toParchment carries names, filled values and replacement marks', () => {
  const m = makeModule();
  m.provider.clauses.push({ id: 'tester.provider.pay.swap', category: 'pay', text: 'Paid on the day.', replaces: 'p2p.pay.1' });
  const doc = resolve({ base: makeBase(), provider: m, jurisdiction: 'EW', mode: 'agreement', values: {} });
  const p = toParchment(doc, { names: { engager: 'Ada Example', provider: 'Sam Sample' } });
  assert.deepEqual(p.parties.map((x) => x.name), ['Ada Example', 'Sam Sample']);
  assert.equal(p.values.item_count, '3');
  const swap = p.sections.flatMap((s) => s.clauses).find((c) => c.id === 'tester.provider.pay.swap');
  assert.equal(swap.marked, 'replaces base clause p2p.pay.1');
});

test('renderMarkdown lists every section, numbers clauses and marks replacements, sources and blanks', () => {
  const m = makeModule();
  m.provider.clauses.push({ id: 'tester.provider.pay.swap', category: 'pay', text: 'Paid on the day.', replaces: 'p2p.pay.1' });
  const doc = resolve({ base: makeBase(), provider: m, jurisdiction: 'EW', overrides: [{ id: 'o.a', category: 'pay', text: 'Tips welcome.' }] });
  const md = renderMarkdown(doc);
  for (const s of doc.sections) assert.match(md, new RegExp(`## (\\d+\\. )?${s.title}`));
  assert.match(md, /\*\*\(replaces base clause p2p\.pay\.1\)\*\*/);
  assert.match(md, /Tips welcome\. _\[pay, parties’ override\]_/);
  assert.match(md, /Terms hash: `sha256:[0-9a-f]{64}`/);
  assert.match(md, /Overrides: 1 `sha256:/);
  assert.match(md, /## Blanks/);
  assert.match(md, /`\{\{item_count\}\}` Items \(number, role_duties\) — default: 3/);
  assert.equal(renderMarkdown(doc), md);
  assert.ok(md.endsWith('\n') && !md.endsWith('\n\n'));
});

test('renderMarkdown shows a stale module', () => {
  const m = makeModule();
  m.drafted_against.P2P = 9;
  assert.match(renderMarkdown(resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' })), /\*\*STALE\*\*/);
});
