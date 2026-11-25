import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assertSupported } from '../../brain/src/jsonschema.js';
import { ACCEPTANCE_CATEGORIES, CATEGORIES, CATEGORY_KEYS, SECTIONS } from '../src/categories.js';
import { baseProblems, loadSchema, moduleProblems } from '../src/validate.js';
import { clone, makeBase, makeModule } from './helpers.js';

test('the three A3 schemas use only keywords the validator enforces', () => {
  for (const n of ['base-template', 'role-template', 'agreement']) assert.equal(assertSupported(loadSchema(n)), true);
});

test('the shared $defs are identical in the base and role schemas, and the agreement schema reuses the styles', () => {
  const b = loadSchema('base-template').$defs;
  const r = loadSchema('role-template').$defs;
  const a = loadSchema('agreement').$defs;
  for (const k of ['clause', 'when', 'clause_style', 'document_style', 'field']) assert.deepEqual(b[k], r[k], k);
  assert.deepEqual(a.clause_style, b.clause_style);
  assert.deepEqual(a.document_style, b.document_style);
});

test('every schema lists exactly the 13 categories, in order', () => {
  assert.equal(CATEGORY_KEYS.length, 13);
  assert.deepEqual(loadSchema('base-template').$defs.clause.properties.category.enum, CATEGORY_KEYS);
  assert.deepEqual(loadSchema('role-template').$defs.field.properties.category.enum, CATEGORY_KEYS);
  assert.deepEqual(loadSchema('agreement').$defs.resolved_clause.properties.category.enum, CATEGORY_KEYS);
});

test('sections match the parchment viewer (C1 SECTION_ORDER) and every category has one', () => {
  // Copied from SnapLink src/components/parchment/parchmentModel.js (integration branch, 25 Nov 2026).
  const C1 = [['cover', 'Cover'], ['duties', 'Role and duties'], ['place_time', 'Place and time'], ['pay', 'Pay'], ['terms', 'Terms'], ['proof_disputes', 'Proof and disputes'], ['acceptance', 'Acceptance and seal']];
  assert.deepEqual(SECTIONS.map((s) => [s.key, s.title]), C1);
  const keys = new Set(SECTIONS.map((s) => s.key));
  for (const c of CATEGORIES) assert.ok(keys.has(c.section), c.key);
  assert.deepEqual(new Set(CATEGORIES.map((c) => c.section)), new Set(SECTIONS.map((s) => s.key).filter((k) => k !== 'acceptance')));
  for (const k of ACCEPTANCE_CATEGORIES) assert.ok(CATEGORY_KEYS.includes(k));
  assert.deepEqual(loadSchema('agreement').$defs.section.properties.key.enum, SECTIONS.map((s) => s.key));
});

test('the synthetic base and module pass', () => {
  assert.deepEqual(baseProblems(makeBase()), []);
  assert.deepEqual(baseProblems(makeBase('B2P')), []);
  assert.deepEqual(moduleProblems(makeModule()), []);
});

test('schema rules refuse unknown properties, bad ids and bad categories', () => {
  const b = makeBase();
  b.surprise = 1;
  assert.match(baseProblems(b).join('\n'), /unexpected property surprise/);
  const c = makeBase();
  c.clauses[0].id = 'Bad Id';
  assert.match(baseProblems(c).join('\n'), /does not match/);
  const d = makeBase();
  d.clauses[0].category = 'weather';
  assert.match(baseProblems(d).join('\n'), /must be one of/);
  const m = makeModule();
  m.provider.clauses[0].colour = 'red';
  assert.match(moduleProblems(m).join('\n'), /unexpected property colour/);
  const n = makeModule();
  delete n.defaults;
  assert.match(moduleProblems(n).join('\n'), /missing defaults/);
  const e = clone(makeBase());
  e.clauses[0].text = 'Line one\u0007bell';
  assert.match(baseProblems(e).join('\n'), /does not match/);
});
