import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { canonical, digest } from '../../adapter/src/canon.js';
import { templateHash, termsCanonical, termsHash, termsInput } from '../src/hash.js';
import { resolve } from '../src/resolve.js';
import { clone, makeBase, makeModule } from './helpers.js';

const shuffleKeys = (v) => {
  if (Array.isArray(v)) return v.map(shuffleKeys);
  if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).reverse().map((k) => [k, shuffleKeys(v[k])]));
  return v;
};
const run = (over = {}) => resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW', ...over });

test('the same inputs always give the same document and hash, whatever the key order', () => {
  const a = run();
  const b = run();
  assert.equal(JSON.stringify(a), JSON.stringify(b));
  const c = resolve({ base: shuffleKeys(makeBase()), provider: shuffleKeys(makeModule()), jurisdiction: 'EW' });
  assert.equal(c.terms_hash, a.terms_hash);
  assert.equal(c.sources.base.sha256, a.sources.base.sha256);
  assert.equal(c.sources.provider_module.sha256, a.sources.provider_module.sha256);
});

test('the terms hash is sha256 of the canonical encoding of the document without style and without the hash', () => {
  const doc = run();
  assert.equal(doc.terms_hash, `sha256:${digest(termsInput(doc))}`);
  assert.equal(termsHash(doc), doc.terms_hash);
  const input = termsInput(doc);
  assert.equal(input.terms_hash, undefined);
  assert.equal(input.style, undefined);
  assert.ok(doc.style, 'the document itself keeps its style for display');
  assert.equal(termsCanonical(doc), canonical(input));
});

test('one changed clause word changes the hash — in the base, a module or an override', () => {
  const ref = run().terms_hash;
  const b = makeBase();
  b.clauses.find((c) => c.id === 'p2p.place.1').text = 'Base place clause for [[Engager]] and the [[provider]].';
  assert.notEqual(run({ base: b }).terms_hash, ref);
  const m = makeModule();
  m.provider.clauses[0].text = m.provider.clauses[0].text.replace('duty', 'task');
  assert.notEqual(run({ provider: m }).terms_hash, ref);
  const o1 = run({ overrides: [{ id: 'o.a', category: 'pay', text: 'Cash on the day.' }] }).terms_hash;
  const o2 = run({ overrides: [{ id: 'o.a', category: 'pay', text: 'Card on the day.' }] }).terms_hash;
  assert.notEqual(o1, o2);
  assert.notEqual(o1, ref);
});

test('a word changed in a clause that this variant leaves out still changes the hash (the base hash is covered)', () => {
  const ref = run().terms_hash;
  const b = makeBase();
  b.clauses.find((c) => c.id === 'p2p.cancel.sc').text = 'A different Scottish-only clause.';
  const doc = run({ base: b });
  assert.notEqual(doc.sources.base.sha256, run().sources.base.sha256);
  assert.notEqual(doc.terms_hash, ref);
});

test('a changed style changes neither the template hashes nor the terms hash', () => {
  const ref = run();
  const b = makeBase();
  b.style = { paper: 'plain-parchment', ink: 'navy', heading_font: 'small-caps', seal_colour: 'green' };
  b.clauses[0].style = { emphasis: 'boxed', keep_with_next: true };
  const m = makeModule();
  delete m.style;
  m.provider.clauses[0].style = { emphasis: 'strong' };
  const doc = run({ base: b, provider: m });
  assert.equal(templateHash(b), templateHash(makeBase()));
  assert.equal(templateHash(m), templateHash(makeModule()));
  assert.equal(doc.terms_hash, ref.terms_hash);
  assert.notDeepEqual(doc.style, ref.style);
  assert.deepEqual(doc.sections[0].clauses[0].style, { emphasis: 'boxed', keep_with_next: true });
});

test('every other part of the document is hashed: blanks, labels, defaults, jurisdiction, consumer, mode, values, order', () => {
  const ref = run().terms_hash;
  const variants = [];
  const b1 = makeBase(); b1.fields[0].label = 'Fee (GBP)'; variants.push(run({ base: b1 }));
  const b2 = makeBase(); b2.fields[1].default = '30'; variants.push(run({ base: b2 }));
  const b3 = makeBase(); b3.party_labels.engager = 'the Customer'; variants.push(run({ base: b3 }));
  const b4 = makeBase(); b4.version = 2; variants.push(run({ base: b4 }));
  const b5 = makeBase(); [b5.clauses[3], b5.clauses[4]] = [b5.clauses[4], b5.clauses[3]]; variants.push(run({ base: b5 }));
  const b6 = makeBase(); b6.clauses[5].locked = true; variants.push(run({ base: b6 }));
  variants.push(run({ jurisdiction: 'NI' }));
  variants.push(run({ consumer: true }));
  variants.push(run({ title: 'A different title' }));
  const filled1 = run({ mode: 'agreement', values: { fee: '£100' } }).terms_hash;
  const filled2 = run({ mode: 'agreement', values: { fee: '£101' } }).terms_hash;
  for (const v of variants) assert.notEqual(v.terms_hash, ref);
  assert.equal(new Set(variants.map((v) => v.terms_hash)).size, variants.length);
  assert.notEqual(filled1, filled2);
  assert.notEqual(filled1, ref);
});

test('templateHash leaves out only style blocks, not a field or clause that happens to be named like one', () => {
  const b = makeBase();
  const c = clone(b);
  c.fields.push({ key: 'style', label: 'Style of shoot', category: 'role_duties', type: 'text' });
  assert.notEqual(templateHash(c), templateHash(b));
});

test('Node and CPython encode the hash input to the same bytes (skipped without python3)', (t) => {
  const py = spawnSync('python3', ['-c', 'import sys,json; v=json.load(sys.stdin); sys.stdout.write(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True))'], {
    input: JSON.stringify(termsInput(run({ consumer: true, overrides: [{ id: 'o.a', category: 'pay', text: 'Paid in £ — or € — “cash”.' }] }))),
    encoding: 'utf8',
  });
  if (py.error || py.status !== 0) { t.skip('python3 not available'); return; }
  const doc = run({ consumer: true, overrides: [{ id: 'o.a', category: 'pay', text: 'Paid in £ — or € — “cash”.' }] });
  assert.equal(py.stdout, termsCanonical(doc));
});
