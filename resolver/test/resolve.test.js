import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORY_KEYS, SECTIONS } from '../src/categories.js';
import { ResolveError, resolve } from '../src/resolve.js';
import { agreementProblems } from '../src/validate.js';
import { allClauses, clause, makeBase, makeModule } from './helpers.js';

const problemsOf = (fn) => {
  try { fn(); } catch (e) { if (e instanceof ResolveError || e.problems) return e.problems; throw e; }
  throw new Error('expected a ResolveError');
};
const has = (problems, re) => assert.ok(problems.some((p) => re.test(p)), `expected ${re} in:\n${problems.join('\n')}`);

test('a base alone resolves to a valid odir.agreement.v1 with all 7 sections and all 13 categories', () => {
  const doc = resolve({ base: makeBase(), jurisdiction: 'EW' });
  assert.deepEqual(agreementProblems(doc), []);
  assert.deepEqual(doc.sections.map((s) => s.key), SECTIONS.map((s) => s.key));
  assert.deepEqual(new Set(allClauses(doc).map((c) => c.category)), new Set(CATEGORY_KEYS));
  assert.equal(doc.mode, 'template');
  assert.deepEqual(doc.roles, { engager: null, provider: null });
  assert.equal(doc.sources.engager_module, null);
  assert.match(doc.terms_hash, /^sha256:[0-9a-f]{64}$/);
});

test('merge order is base < engager < provider, clauses grouped by category in that order', () => {
  const doc = resolve({ base: makeBase(), engager: makeModule('alpha'), provider: makeModule('beta'), jurisdiction: 'EW' });
  const pay = doc.sections.find((s) => s.key === 'pay').clauses.filter((c) => c.category === 'pay').map((c) => c.source);
  assert.deepEqual(pay, ['base', 'engager_module', 'provider_module']);
  const order = doc.sections.find((s) => s.key === 'pay').clauses.map((c) => c.category);
  assert.deepEqual(order, [...order].sort((a, b) => CATEGORY_KEYS.indexOf(a) - CATEGORY_KEYS.indexOf(b)));
  assert.equal(doc.parties[0].label, 'the Tester');
  assert.equal(doc.parties[0].role, 'alpha');
  assert.equal(doc.parties[1].role, 'beta');
});

test('a later layer replaces an earlier clause in place, and the replacement is marked', () => {
  const p = makeModule();
  p.provider.clauses.push({ id: 'tester.provider.pay.swap', category: 'pay', text: 'The Provider is paid on the day.', replaces: 'p2p.pay.1' });
  const doc = resolve({ base: makeBase(), provider: p, jurisdiction: 'EW' });
  const pay = doc.sections.find((s) => s.key === 'pay').clauses;
  assert.equal(pay[0].id, 'tester.provider.pay.swap');
  assert.deepEqual(pay[0].replaces, { id: 'p2p.pay.1', source: 'base' });
  assert.equal(clause(doc, 'p2p.pay.1'), undefined);
  assert.equal(doc.fields.some((f) => f.key === 'fee'), false, 'a blank only the replaced clause used is gone');
});

test('the provider module may replace an engager-module clause, never the other way round', () => {
  const e = makeModule('alpha');
  const p = makeModule('beta');
  p.provider.clauses.push({ id: 'beta.provider.swap', category: 'pay', text: 'Paid weekly.', replaces: 'alpha.engager.pay.1' });
  const doc = resolve({ base: makeBase(), engager: e, provider: p, jurisdiction: 'EW' });
  assert.deepEqual(clause(doc, 'beta.provider.swap').replaces, { id: 'alpha.engager.pay.1', source: 'engager_module' });
  const e2 = makeModule('alpha');
  e2.engager.clauses.push({ id: 'alpha.engager.swap', category: 'pay', text: 'Paid monthly.', replaces: 'beta.provider.pay.1' });
  has(problemsOf(() => resolve({ base: makeBase(), engager: e2, provider: makeModule('beta'), jurisdiction: 'EW' })), /replaces beta\.provider\.pay\.1, which is not in this variant/);
});

test('overrides come last, may replace a module clause, and are marked', () => {
  const doc = resolve({
    base: makeBase(), provider: makeModule(), jurisdiction: 'EW',
    overrides: [
      { id: 'o.travel', category: 'expenses_equipment', text: 'Parking is paid by the Client.' },
      { id: 'o.pay', category: 'pay', text: 'Paid in cash on the day.', replaces: 'tester.provider.pay.1' },
    ],
  });
  const o = clause(doc, 'o.pay');
  assert.deepEqual(o.replaces, { id: 'tester.provider.pay.1', source: 'provider_module' });
  assert.equal(o.source, 'override');
  assert.equal(clause(doc, 'o.travel').source, 'override');
  assert.equal(doc.sources.overrides.count, 2);
  assert.match(doc.sources.overrides.sha256, /^sha256:/);
  const exp = doc.sections.find((s) => s.key === 'pay').clauses.filter((c) => c.category === 'expenses_equipment');
  assert.equal(exp.at(-1).id, 'o.travel');
});

test('locked clauses cannot be replaced, by a module or by an override', () => {
  const p = makeModule();
  p.provider.clauses.push({ id: 'tester.provider.x', category: 'parties_authority', text: 'x', replaces: 'p2p.parties_authority.1' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: p, jurisdiction: 'EW' })), /p2p\.parties_authority\.1 is locked/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', consumer: true, overrides: [{ id: 'o.x', category: 'cancellation_no_show', text: 'No refunds.', replaces: 'p2p.cancel.consumer' }] })), /is locked/);
});

test('replacement must name an earlier clause present in this variant, of the same category, from an earlier layer', () => {
  const p = makeModule();
  p.provider.clauses.push({ id: 'tester.provider.x', category: 'pay', text: 'x', replaces: 'p2p.nothing' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: p, jurisdiction: 'EW' })), /replaces p2p\.nothing, which is not in this variant/);
  const q = makeModule();
  q.provider.clauses.push({ id: 'tester.provider.y', category: 'place', text: 'y', replaces: 'p2p.pay.1' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: q, jurisdiction: 'EW' })), /must keep the category/);
  const r = makeModule();
  r.provider.clauses.push({ id: 'tester.provider.z', category: 'cancellation_no_show', text: 'z', replaces: 'p2p.cancel.sc' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: r, jurisdiction: 'EW' })), /not in this variant/);
  assert.ok(resolve({ base: makeBase(), provider: r, jurisdiction: 'SC' }));
  has(problemsOf(() => resolve({
    base: makeBase(), jurisdiction: 'EW',
    overrides: [{ id: 'o.a', category: 'pay', text: 'a' }, { id: 'o.b', category: 'pay', text: 'b', replaces: 'o.a' }],
  })), /only replace a clause from an earlier layer/);
});

test('an id used twice across layers is refused (no silent overwrite)', () => {
  has(problemsOf(() => resolve({
    base: makeBase(), jurisdiction: 'EW',
    overrides: [{ id: 'o.a', category: 'pay', text: 'a' }, { id: 'o.a', category: 'place', text: 'b' }],
  })), /id already used/);
});

test('conditions: consumer, jurisdiction and base variants', () => {
  const ew = resolve({ base: makeBase(), jurisdiction: 'EW' });
  const sc = resolve({ base: makeBase(), jurisdiction: 'SC' });
  const cons = resolve({ base: makeBase(), jurisdiction: 'EW', consumer: true });
  assert.equal(clause(ew, 'p2p.cancel.sc'), undefined);
  assert.ok(clause(sc, 'p2p.cancel.sc'));
  assert.ok(clause(cons, 'p2p.cancel.consumer'));
  assert.equal(clause(cons, 'p2p.cancel.business'), undefined);
  assert.ok(clause(ew, 'p2p.cancel.business'));
  assert.equal(clause(ew, 'p2p.cancel.consumer'), undefined);
  const m = makeModule();
  m.provider.clauses.push({ id: 'tester.provider.b2p_only', category: 'pay', text: 'Invoices go to accounts.', when: { bases: ['B2P'] } });
  assert.equal(clause(resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' }), 'tester.provider.b2p_only'), undefined);
  assert.ok(clause(resolve({ base: makeBase('B2P', { consumer: false }), provider: m, jurisdiction: 'EW' }), 'tester.provider.b2p_only'));
});

test('terms are filled from the party labels and the jurisdiction', () => {
  const doc = resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'SC' });
  assert.equal(clause(doc, 'p2p.place.1').text, 'Base place clause for The Client and the Tester.');
  assert.equal(clause(doc, 'p2p.disputes_record.law').text, 'The law of Scotland applies and the Scottish courts decide.');
  assert.equal(doc.jurisdiction_name, 'Scotland');
  for (const c of allClauses(doc)) assert.doesNotMatch(c.text, /\[\[|\]\]/);
});

test('consumer rules: only on a base with a consumer variant, never with an engager module', () => {
  has(problemsOf(() => resolve({ base: makeBase('B2P', { consumer: false }), jurisdiction: 'EW', consumer: true })), /no consumer variant/);
  has(problemsOf(() => resolve({ base: makeBase(), engager: makeModule(), jurisdiction: 'EW', consumer: true })), /no engager module/);
});

test('slot and jurisdiction rules', () => {
  has(problemsOf(() => resolve({ base: makeBase('B2P', { consumer: false }), engager: makeModule(), jurisdiction: 'EW' })), /does not take the engager slot under B2P/);
  has(problemsOf(() => resolve({ base: makeBase('B2P', { consumer: false }), provider: makeModule('tester', { bases: ['P2P'] }), jurisdiction: 'EW' })), /does not take the provider slot under B2P/);
  const b = makeBase();
  b.jurisdictions = ['EW'];
  b.clauses = b.clauses.filter((c) => !c.when?.jurisdictions);
  has(problemsOf(() => resolve({ base: b, jurisdiction: 'SC' })), /not offered in jurisdiction "SC"/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'XX' })), /not offered/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', mode: 'draft' })), /mode must be/);
});

test('invalid templates are refused before resolving', () => {
  const b = makeBase();
  b.clauses[0].text = 'Bad {{blank';
  assert.throws(() => resolve({ base: b, jurisdiction: 'EW' }), /base P2P is invalid/);
  const m = makeModule();
  m.provider.party_label = 'Photographer';
  assert.throws(() => resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' }), /module tester is invalid/);
});

test('fields: a later layer refines only when it says so, keeping type and category', () => {
  const m = makeModule();
  m.provider.fields.push({ key: 'fee', label: 'Shoot fee', category: 'pay', type: 'money' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' })), /already defined differently by base/);
  const n = makeModule();
  n.provider.fields.push({ key: 'fee', label: 'Shoot fee', category: 'pay', type: 'money', refines: true, default: '£100' });
  const doc = resolve({ base: makeBase(), provider: n, jurisdiction: 'EW' });
  assert.deepEqual(doc.fields.find((f) => f.key === 'fee'), { key: 'fee', label: 'Shoot fee', category: 'pay', type: 'money', default: '£100', value: null, source: 'provider_module' });
  const o = makeModule();
  o.provider.fields.push({ key: 'fee', label: 'Fee', category: 'pay', type: 'text', refines: true });
  has(problemsOf(() => resolve({ base: makeBase(), provider: o, jurisdiction: 'EW' })), /keeps the type and category/);
  const p = makeModule();
  p.provider.fields.push({ key: 'tip', label: 'Tip', category: 'pay', type: 'money', refines: true });
  has(problemsOf(() => resolve({ base: makeBase(), provider: p, jurisdiction: 'EW' })), /refines a field no earlier layer defines/);
  // the same blank defined identically by both sides is one blank
  const doc2 = resolve({ base: makeBase(), engager: makeModule('alpha'), provider: makeModule('beta'), jurisdiction: 'EW' });
  assert.equal(doc2.fields.filter((f) => f.key === 'item_count').length, 1);
});

test('a blank no layer defines is refused', () => {
  const m = makeModule();
  m.provider.clauses.push({ id: 'tester.provider.tip', category: 'pay', text: 'A tip of {{tip}} is welcome.' });
  has(problemsOf(() => resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' })), /blank \{\{tip\}\} is not a field of any layer/);
});

test('no variant can leave a category empty', () => {
  // A replacement keeps its target's category, so a module cannot empty one.
  const m = makeModule();
  m.provider.clauses.push({ id: 'tester.provider.swap', category: 'place', text: 'x', replaces: 'p2p.place.1' });
  const doc = resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' });
  assert.ok(allClauses(doc).some((c) => c.category === 'place'));
  // A base whose only clauses in a category are conditional is refused before any variant is built.
  const b = makeBase();
  b.clauses.find((c) => c.id === 'p2p.place.1').when = { jurisdictions: ['EW'] };
  b.clauses.push({ id: 'p2p.place.sc', category: 'place', text: 'Scottish venue rules.', when: { jurisdictions: ['SC'] } });
  assert.throws(() => resolve({ base: b, jurisdiction: 'NI' }), /no unconditional clause in category place/);
});

test('acceptance placement and the cover', () => {
  const doc = resolve({ base: makeBase(), jurisdiction: 'EW' });
  const acc = doc.sections.find((s) => s.key === 'acceptance').clauses.map((c) => c.id);
  assert.deepEqual(acc, ['p2p.acceptance.sign']);
  assert.deepEqual(doc.sections.find((s) => s.key === 'cover').clauses.map((c) => c.id), ['p2p.parties_authority.1']);
  // the parties' overrides never reach Acceptance and seal
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', overrides: [{ id: 'o.witness', category: 'disputes_record', section: 'acceptance', text: 'Signed in front of a witness.' }] })), /unexpected property section/);
});

test('overrides are plain text with a strict shape', () => {
  const bad = (o) => problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', overrides: [o] }));
  has(bad({ id: 'x', category: 'pay', text: 'a' }), /id must look like o\.<name>/);
  has(bad({ id: 'o.x', category: 'tips', text: 'a' }), /unknown category/);
  has(bad({ id: 'o.x', category: 'pay', text: 'Pay {{fee}} twice.' }), /no blanks or terms|malformed blank/);
  has(bad({ id: 'o.x', category: 'pay', text: 'Pay [[Engager]].' }), /no blanks or terms/);
  has(bad({ id: 'o.x', category: 'pay', text: 'a', locked: true }), /unexpected property locked/);
  has(bad({ id: 'o.x', category: 'pay', text: 'line\nbreak' }), /plain characters/);
  has(bad({ id: 'o.x', category: 'pay', text: '' }), /plain characters/);
  has(bad({ id: 'o.x', category: 'pay', text: 'a', section: 'cover' }), /unexpected property section/);
  has(bad({ id: 'o.x', category: 'pay', text: 'Paid \u202eyadot' }), /invisible or direction-changing/);
  has(bad({ id: 'o.x', category: 'pay', text: 'Cafe\u0301 rules.' }), /not in Unicode NFC form/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', overrides: 'none' })), /overrides must be a list/);
});

test('agreement mode fills every blank from values, then defaults, in one pass', () => {
  const doc = resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW', mode: 'agreement', values: { fee: '£250', item_count: '12' }, salt: 'a'.repeat(64) });
  assert.equal(doc.salt, 'a'.repeat(64));
  assert.equal(doc.mode, 'agreement');
  assert.equal(clause(doc, 'p2p.pay.1').text, 'The Client pays £250 within 14 days.');
  assert.match(clause(doc, 'tester.provider.duty.1').text, /deliver 12 items/);
  for (const c of allClauses(doc)) assert.doesNotMatch(c.text, /\{\{/);
  assert.equal(doc.fields.find((f) => f.key === 'pay_days').value, '14');
  assert.equal(doc.fields.find((f) => f.key === 'fee').value, '£250');
  assert.deepEqual(agreementProblems(doc), []);
});

test('agreement mode refuses missing, unknown and unsafe values', () => {
  const run = (values, extra = {}) => problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', mode: 'agreement', values, salt: 'a'.repeat(64), ...extra }));
  has(run({}), /values\.fee: missing \(Fee\)/);
  has(run({ fee: '£1', tip: '£2' }), /values\.tip: not a blank/);
  has(run({ fee: '{{pay_days}}' }), /cannot hold braces/);
  has(run({ fee: '[[Engager]]' }), /cannot hold braces/);
  has(run({ fee: '£1\n£2' }), /control or line-break/);
  has(run({ fee: '£1 £2' }), /control or line-break/);
  has(run({ fee: ' £1' }), /whitespace/);
  has(run({ fee: 'x'.repeat(301) }), /1 to 300 characters/);
  has(run({ fee: 12 }), /must be a string/);
  has(run({ fee: '£1', pay_days: 'fourteen' }), /whole number/);
  has(run({ fee: '£1', pay_days: '007' }), /without leading zeros/);
  has(run({ fee: '650' }), /an amount such as £650/);
  has(run({ fee: '£1,200' }), /an amount such as £650/);
  has(run({ fee: '£1\u200b' }), /invisible or direction-changing/);
  has(run({ fee: '£1\u202e' }), /invisible or direction-changing/);
  has(run({ fee: '£1', pay_days: '1\ufeff4' }), /invisible or direction-changing/);
  has(problemsOf(() => resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW', mode: 'agreement', salt: 'a'.repeat(64), values: { fee: '£1', item_count: 'thre\u0301e' } })), /NFC|whole number/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', values: { fee: '£1' } })), /template mode takes no values/);
  has(run({ fee: '£1' }, { salt: null }), /agreement mode needs a salt/);
  has(run({ fee: '£1' }, { salt: 'A'.repeat(64) }), /agreement mode needs a salt/);
  has(run({ fee: '£1' }, { salt: 'a'.repeat(63) }), /agreement mode needs a salt/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', salt: 'a'.repeat(64) })), /template mode takes no salt/);
  assert.equal(resolve({ base: makeBase(), jurisdiction: 'EW' }).salt, null);
});

test('a title may be given; otherwise it is built from the role and the base', () => {
  assert.equal(resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW' }).title, 'Tester — Synthetic P2P base');
  assert.equal(resolve({ base: makeBase(), engager: makeModule(), jurisdiction: 'EW' }).title, 'Tester engaging — Synthetic P2P base');
  assert.equal(resolve({ base: makeBase(), jurisdiction: 'EW', title: 'Wedding, 1 May' }).title, 'Wedding, 1 May');
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', title: 'Hi {{fee}}' })), /title must be/);
  has(problemsOf(() => resolve({ base: makeBase(), jurisdiction: 'EW', title: 'a\u202eb' })), /title must be/);
});

test('a module drafted against another base version is marked stale', () => {
  const m = makeModule();
  m.drafted_against.P2P = 2;
  const doc = resolve({ base: makeBase(), provider: m, jurisdiction: 'EW' });
  assert.equal(doc.sources.provider_module.stale, true);
  assert.equal(resolve({ base: makeBase(), provider: makeModule(), jurisdiction: 'EW' }).sources.provider_module.stale, false);
});

test('resolve never changes its inputs', () => {
  const base = makeBase();
  const prov = makeModule();
  const before = JSON.stringify([base, prov]);
  resolve({ base, provider: prov, jurisdiction: 'EW', mode: 'agreement', values: { fee: '£1' }, salt: 'a'.repeat(64) });
  assert.equal(JSON.stringify([base, prov]), before);
});
