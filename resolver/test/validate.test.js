import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TemplateError, assertBase, assertModule, baseProblems, lintText, moduleProblems } from '../src/validate.js';
import { makeBase, makeModule } from './helpers.js';

const has = (problems, re) => assert.ok(problems.some((p) => re.test(p)), `expected ${re} in:\n${problems.join('\n')}`);

test('lintText accepts well-formed blanks and terms and refuses everything else', () => {
  assert.deepEqual(lintText('[[Engager]] pays {{fee}} under [[jurisdiction]] law.', 'x'), []);
  has(lintText('Pays {{ fee }}.', 'x'), /malformed blank/);
  has(lintText('Pays {{Fee}}.', 'x'), /malformed blank/);
  has(lintText('Pays {fee}.', 'x'), /malformed blank/);
  has(lintText('Pays {{fee}.', 'x'), /malformed blank/);
  has(lintText('[[client]] pays.', 'x'), /unknown term/);
  has(lintText('[[Engager] pays.', 'x'), /malformed term/);
  has(lintText(' Pays.', 'x'), /whitespace/);
  has(lintText('Pays  twice.', 'x'), /repeated whitespace/);
});

test('base: ids carry the base prefix and are unique', () => {
  const b = makeBase();
  b.clauses[1].id = 'b2p.role_duties.1';
  has(baseProblems(b), /must start with "p2p\."/);
  const c = makeBase();
  c.clauses[1].id = c.clauses[0].id;
  has(baseProblems(c), /duplicate clause id/);
});

test('base: every category needs an unconditional clause', () => {
  const b = makeBase();
  b.clauses = b.clauses.filter((c) => c.category !== 'place');
  has(baseProblems(b), /no unconditional clause in category place/);
  const c = makeBase();
  c.clauses.find((x) => x.category === 'place').when = { jurisdictions: ['EW'] };
  has(baseProblems(c), /no unconditional clause in category place/);
});

test('base: kinds must match the base key, consumer variant only for a person engager', () => {
  const b = makeBase('B2P');
  b.engager_kind = 'person';
  has(baseProblems(b), /B2P is organisation → person/);
  const c = makeBase('B2P', { consumer: false });
  c.consumer_variant = true;
  has(baseProblems(c), /consumer variant/);
});

test('base: no replaces, no checkable, no base condition, no foreign blanks; acceptance only for two categories', () => {
  const b = makeBase();
  b.clauses[2].replaces = 'p2p.parties_authority.1';
  has(baseProblems(b), /cannot replace/);
  const c = makeBase();
  c.clauses[2].checkable = true;
  has(baseProblems(c), /checkable duty statements belong in role modules/);
  const d = makeBase();
  d.clauses.push({ id: 'p2p.x.1', category: 'place', text: 'x', when: { bases: ['P2P'] } });
  has(baseProblems(d), /cannot be conditional on the base/);
  const e = makeBase();
  e.clauses[3].text = 'Pays {{tip}}.';
  has(baseProblems(e), /blank \{\{tip\}\} is not a field of this base/);
  const f = makeBase();
  f.clauses.find((x) => x.category === 'pay').section = 'acceptance';
  has(baseProblems(f), /may sit under Acceptance and seal/);
  const g = makeBase();
  g.fields.push({ key: 'fee', label: 'Again', category: 'pay', type: 'money' });
  has(baseProblems(g), /duplicate field key/);
  const h = makeBase();
  h.fields[0].refines = true;
  has(baseProblems(h), /cannot refine/);
  const i = makeBase('B2P', { consumer: false });
  i.clauses.push({ id: 'b2p.c.1', category: 'pay', text: 'x', when: { consumer: true } });
  has(baseProblems(i), /consumer condition is not allowed/);
  const j = makeBase();
  j.jurisdictions = ['EW'];
  has(baseProblems(j), /jurisdiction SC, which is not offered/);
  const k = makeBase();
  k.fields[1].default = '{{fee}}';
  has(baseProblems(k), /default cannot hold a blank/);
  const l = makeBase();
  l.fields[1].default = 'fourteen';
  has(baseProblems(l), /default: must be a whole number/);
  const m = makeBase();
  m.clauses[0].text = 'Hidden\u200bjoin.';
  has(baseProblems(m), /invisible or direction-changing/);
  const n = makeBase();
  n.title = 'Cafe\u0301 base';
  has(baseProblems(n), /\$\.title: not in Unicode NFC form/);
  const o = makeBase();
  o.fields[0].label = 'Fee\u202e';
  has(baseProblems(o), /label: holds an invisible/);
});

test('module: prefixes, coverage of all 13 categories per slot, checkable counts', () => {
  const m = makeModule();
  m.provider.clauses[0].id = 'tester.engager.x.1';
  has(moduleProblems(m), /must start with "tester\.provider\."/);
  const n = makeModule();
  n.engager.clauses = n.engager.clauses.map((c) => (c.category === 'pay' ? { ...c, category: 'place' } : c));
  has(moduleProblems(n), /engager: no clause in category pay/);
  const o = makeModule();
  o.provider.clauses = o.provider.clauses.filter((c) => !c.checkable || c.id.endsWith('.1'));
  has(moduleProblems(o), /1 checkable duty statements \(need 5 to 10\)/);
  const p = makeModule();
  for (let i = 6; i <= 11; i++) p.provider.clauses.push({ id: `tester.provider.more.${i}`, category: 'role_duties', text: 'More.', checkable: true });
  has(moduleProblems(p), /11 checkable duty statements/);
  const q = makeModule();
  delete q.engager;
  delete q.provider;
  has(moduleProblems(q), /needs an engager or a provider slot/);
});

test('module: drafted_against, conditions and consumer rules', () => {
  const m = makeModule();
  delete m.drafted_against.B2P;
  has(moduleProblems(m), /takes base B2P but drafted_against has no version/);
  const n = makeModule();
  n.provider.clauses.push({ id: 'tester.provider.b.1', category: 'pay', text: 'x', when: { bases: ['STAFF'] } });
  has(moduleProblems(n), /names base STAFF, which this layer does not take/);
  const o = makeModule();
  o.engager.clauses.push({ id: 'tester.engager.c.1', category: 'pay', text: 'x', when: { consumer: true } });
  has(moduleProblems(o), /consumer condition is not allowed/);
  const p = makeModule();
  p.provider.clauses.push({ id: 'tester.provider.self', category: 'pay', text: 'x', replaces: 'tester.provider.self' });
  has(moduleProblems(p), /cannot replace itself/);
  const q = makeModule();
  q.provider.clauses.push({ ...q.engager.clauses[0] });
  has(moduleProblems(q), /must start with/);
});

test('assertBase / assertModule throw a TemplateError listing the problems, and refuse the wrong kind', () => {
  assert.throws(() => assertBase(makeModule()), /not a base template/);
  assert.throws(() => assertModule(makeBase()), /not a role module/);
  const b = makeBase();
  b.version = 0;
  assert.throws(() => assertBase(b), (e) => e instanceof TemplateError && e.problems.length === 1 && /below 1/.test(e.problems[0]));
});
