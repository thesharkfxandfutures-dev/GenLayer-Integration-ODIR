// The pilot templates (slice A3): the P2P and B2P bases and the photographer module, as committed.
// Golden files pin the resolved text and terms hash. To accept an intended wording change, run
//   UPDATE_GOLDEN=1 npm test
// in resolver/ and commit the golden diff with the template change, so a reviewer sees both.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CATEGORY_KEYS } from '../src/categories.js';
import { combinations, comboName, loadTemplates } from '../src/load.js';
import { renderMarkdown, toParchment } from '../src/render.js';
import { resolve } from '../src/resolve.js';
import { allClauses, clone } from './helpers.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..', '..');
const GOLDEN = path.join(HERE, 'golden');
const UPDATE = process.env.UPDATE_GOLDEN === '1';
const { bases, modules, problems } = loadTemplates(ROOT);
const photographer = modules.get('photographer');

const docFor = (c, extra = {}) => resolve({
  base: bases.get(c.base),
  engager: c.engager ? modules.get(c.engager) : null,
  provider: c.provider ? modules.get(c.provider) : null,
  jurisdiction: c.jurisdiction,
  consumer: c.consumer,
  ...extra,
});
const pretty = (doc) => `${JSON.stringify(doc, null, 2)}\n`;
function golden(name, text) {
  const file = path.join(GOLDEN, name);
  if (UPDATE) { fs.mkdirSync(GOLDEN, { recursive: true }); fs.writeFileSync(file, text); }
  assert.equal(text, fs.readFileSync(file, 'utf8'), `${name} differs from its golden file`);
}

// Synthetic values for the agreement-mode golden: invented people and places.
const SAMPLE_VALUES = Object.freeze({
  engagement_summary: 'a product shoot for a spring campaign',
  venue: 'Example Studio, 1 Sample Street, Leeds LS1 0AA',
  engagement_date: '14 March 2027',
  start_time: '09:00',
  finish_time: '17:00',
  fee: '£900',
  rate_basis: 'a day rate',
  deposit: '£300',
  usage_media: 'online, social and in-store print',
  usage_term: '24 months',
  credit_line: 'Photo: Ada Example for Example Brand',
});

const PILOT = [
  { engager: null, provider: 'photographer', base: 'P2P', jurisdiction: 'EW', consumer: false },
  { engager: null, provider: 'photographer', base: 'P2P', jurisdiction: 'EW', consumer: true },
  { engager: null, provider: 'photographer', base: 'B2P', jurisdiction: 'SC', consumer: false },
  { engager: 'photographer', provider: null, base: 'P2P', jurisdiction: 'NI', consumer: false },
];
// A synthetic, fixed salt for the golden agreement (a real one is 32 random bytes from the server).
const SAMPLE_SALT = '5a17'.repeat(16);

test('the committed templates load with no problems', () => {
  assert.deepEqual(problems, []);
  assert.deepEqual([...bases.keys()].sort(), ['B2P', 'P2P']);
  assert.deepEqual([...modules.keys()], ['photographer']);
});

test('the photographer module matches SnapLink’s registry entry and the design', () => {
  // SnapLink base44/shared/taxonomy/registry.js: role('photographer', 'Photographer', 'Visual Arts', 'MAKER', ['photography'])
  assert.equal(photographer.role_key, 'photographer');
  assert.equal(photographer.role_label, 'Photographer');
  assert.equal(photographer.family, 'MAKER');
  assert.deepEqual(photographer.provider.bases, ['P2P', 'B2P']);
  assert.deepEqual(photographer.engager.bases, ['P2P']);
  assert.deepEqual(photographer.drafted_against, { P2P: 1, B2P: 1 });
  for (const slot of ['engager', 'provider']) {
    assert.deepEqual(new Set(photographer[slot].clauses.map((c) => c.category)), new Set(CATEGORY_KEYS), `${slot} covers all 13 categories`);
  }
  const checkable = photographer.provider.clauses.filter((c) => c.checkable);
  assert.ok(checkable.length >= 5 && checkable.length <= 10, `${checkable.length} checkable provider duties`);
});

test('every role x base pair that exists renders (render-all exits 0)', () => {
  const r = spawnSync('node', [path.join(HERE, '..', 'bin', 'render-all.mjs'), '--root', ROOT, '--json'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stdout);
  const j = JSON.parse(r.stdout);
  assert.equal(j.rendered.length, 24);
  assert.ok(j.rendered.some((r) => r.name === 'photographer+photographer.pair.P2P.EW.business'), 'a photographer booking a photographer');
  assert.deepEqual(j.skipped, []);
  assert.deepEqual(j.failures, []);
});

test('golden: the terms hash of every combination', () => {
  const { combos } = combinations({ bases, modules });
  const hashes = Object.fromEntries(combos.map((c) => [comboName(c), docFor(c).terms_hash]));
  golden('hashes.json', `${JSON.stringify(hashes, null, 2)}\n`);
});

test('golden: the full resolved text of the four pilot documents (JSON and Markdown)', () => {
  for (const c of PILOT) {
    const doc = docFor(c);
    golden(`${comboName(c)}.json`, pretty(doc));
    golden(`${comboName(c)}.md`, renderMarkdown(doc));
    assert.equal(pretty(docFor(c)), pretty(doc), 'a second run gives the same bytes');
  }
});

test('golden: a filled B2P agreement (agreement mode, synthetic values)', () => {
  const c = { engager: null, provider: 'photographer', base: 'B2P', jurisdiction: 'EW', consumer: false };
  const doc = docFor(c, { mode: 'agreement', values: SAMPLE_VALUES, title: 'Product photography for a spring campaign', salt: SAMPLE_SALT });
  assert.equal(doc.salt, SAMPLE_SALT);
  for (const cl of allClauses(doc)) assert.doesNotMatch(cl.text, /\{\{|\[\[/);
  golden('agreement.photographer.provider.B2P.EW.json', pretty(doc));
});

test('on the real templates: one changed word changes the hash, a changed style does not', () => {
  const c = PILOT[0];
  const ref = docFor(c).terms_hash;
  const p2p = clone(bases.get('P2P'));
  const cl = p2p.clauses.find((x) => x.id === 'p2p.place.1');
  cl.text = cl.text.replace('unless', 'except where');
  assert.notEqual(resolve({ base: p2p, provider: photographer, jurisdiction: 'EW' }).terms_hash, ref);
  const mod = clone(photographer);
  const d = mod.provider.clauses.find((x) => x.id === 'photographer.provider.duties.deliver');
  d.text = d.text.replace('edited', 'retouched');
  assert.notEqual(resolve({ base: bases.get('P2P'), provider: mod, jurisdiction: 'EW' }).terms_hash, ref);
  const styled = clone(bases.get('P2P'));
  styled.style = { paper: 'plain-parchment', ink: 'navy' };
  for (const x of styled.clauses) x.style = { emphasis: 'strong' };
  const restyled = clone(photographer);
  restyled.style = { seal_colour: 'green' };
  assert.equal(resolve({ base: styled, provider: restyled, jurisdiction: 'EW' }).terms_hash, ref);
});

test('UK rules the design requires are in the pilot documents', () => {
  const cons = docFor(PILOT[1]);
  const text = allClauses(cons).map((c) => c.text).join('\n');
  assert.match(text, /cancel within 14 days of the day both parties sign/);
  assert.match(text, /includes any VAT/);
  assert.match(text, /18 or over/);
  assert.match(text, /private and domestic purposes/);
  for (const id of ['p2p.cancel.consumer_right', 'p2p.cancel.consumer_early', 'p2p.pay.vat_consumer', 'p2p.accept.age', 'p2p.disputes.record']) {
    assert.equal(allClauses(cons).find((c) => c.id === id)?.locked, true, `${id} is locked`);
  }
  const b2p = docFor(PILOT[2]);
  const t2 = allClauses(b2p).map((c) => c.text).join('\n');
  assert.match(t2, /representative who confirms they have authority/);
  assert.match(t2, /Late Payment of Commercial Debts/);
  assert.match(t2, /the law of Scotland, and the Scottish courts/);
  assert.doesNotMatch(t2, /consumer/i);
  for (const doc of [cons, b2p]) {
    assert.deepEqual(doc.sections.find((s) => s.key === 'acceptance').clauses.map((c) => c.category), ['parties_authority', 'disputes_record']);
  }
});

test('the pilot documents open in the parchment viewer’s shape, every blank labelled', () => {
  for (const c of PILOT) {
    const p = toParchment(docFor(c));
    for (const s of p.sections) for (const cl of s.clauses) {
      for (const m of cl.text.matchAll(/\{\{\s*([a-z0-9_.-]{1,64})\s*\}\}/gi)) assert.ok(p.fields[m[1]]?.label, `${comboName(c)}: {{${m[1]}}} has a label`);
    }
  }
});
