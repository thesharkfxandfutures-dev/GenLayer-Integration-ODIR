import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectRegistry, verifySnapshot, InspectorError } from '../src/inspector.js';
import { validate } from '../src/jsonschema.js';
import { snapshotSchema } from '../src/inspector.js';
import { registryText, APP } from './helpers.js';

const inspect = (t) => inspectRegistry(t, { appId: APP, ref: 'fixture' });

test('the synthetic registry parses into a schema-valid, hashed snapshot', () => {
  const s = inspect(registryText());
  assert.equal(s.schema, 'odir-inspector-snapshot/1');
  assert.deepEqual(s.roles.map((r) => r.key), ['photographer', 'makeup_artist', 'model_fashion', 'retoucher']);
  assert.deepEqual(s.roles[1], { key: 'makeup_artist', label: 'Makeup Artist', family: 'CRAFT', sectors: ['hair_beauty_makeup'] });
  assert.equal(s.role_count, 4);
  assert.equal(s.sectors.length, 3);
  assert.equal(s.taxonomy_revision, 1);
  assert.match(s.registry_sha256, /^[0-9a-f]{64}$/);
  assert.equal(validate(snapshotSchema, s).ok, true);
  assert.deepEqual(verifySnapshot(s), { ok: true, problems: [] });
});

test('same text, same hashes (deterministic)', () => {
  const a = inspect(registryText()), b = inspect(registryText());
  assert.equal(a.registry_sha256, b.registry_sha256);
  assert.equal(a.snapshot_sha256, b.snapshot_sha256);
});

test('a role added, renamed, re-familied or reordered changes the registry hash', () => {
  const base = inspect(registryText()).registry_sha256;
  const t = registryText();
  const variants = {
    added: t.replace("  role('retoucher'", "  role('barber', 'Barber', 'Beauty & Grooming', 'CRAFT', ['hair_beauty_makeup']),\n  role('retoucher'"),
    renamed: t.replace("'Retoucher', 'Post-Production'", "'Photo Retoucher', 'Post-Production'"),
    family: t.replace("'Retoucher', 'Post-Production', 'MAKER'", "'Retoucher', 'Post-Production', 'CRAFT'"),
    sectors: t.replace("'TALENT', ['modelling_talent']", "'TALENT', ['modelling_talent', 'photography']"),
    reordered: t.replace("  role('photographer', 'Photographer', 'Visual Arts', 'MAKER', ['photography']),\n", '').replace("  role('retoucher'", "  role('photographer', 'Photographer', 'Visual Arts', 'MAKER', ['photography']),\n  role('retoucher'"),
  };
  for (const [name, text] of Object.entries(variants)) {
    assert.notEqual(text, t, `${name} variant must differ`);
    assert.notEqual(inspect(text).registry_sha256, base, name);
  }
});

test('search synonyms, legacy groups and comments do not change the registry hash', () => {
  const t = registryText();
  const base = inspect(t);
  const syn = inspect(t.replace("['mua', 'make-up artist']", "['mua']"));
  const legacy = inspect(t.replace("'Visual Arts', 'MAKER'", "'Imaging', 'MAKER'"));
  const comment = inspect(t.replace('// a comment between rows is allowed', '/* another comment */'));
  for (const s of [syn, legacy, comment]) assert.equal(s.registry_sha256, base.registry_sha256);
  assert.notEqual(syn.source.file_sha256, base.source.file_sha256, 'the raw file hash still records the change');
});

test('the Inspector refuses shapes it does not understand instead of guessing', () => {
  const t = registryText();
  const bad = {
    signature: t.replace('(key, label, legacyGroup, family, sectors, synonyms = [])', '(key, family, label, legacyGroup, sectors, synonyms = [])'),
    template: t.replace("'Retoucher', 'Post", '`Retoucher`, \'Post'),
    concat: t.replace("'Retoucher', 'Post", "'Re' + 'toucher', 'Post"),
    call: t.replace("['photography'], [])", "['photography'], makeList())"),
    family: t.replace("'Retoucher', 'Post-Production', 'MAKER'", "'Retoucher', 'Post-Production', 'WIZARD'"),
    sector: t.replace("'TALENT', ['modelling_talent']", "'TALENT', ['underwater']"),
    dupe: t.replace("role('retoucher'", "role('photographer'"),
    key: t.replace("role('retoucher'", "role('Retoucher'"),
    arity: t.replace("role('retoucher', 'Retoucher', 'Post-Production', 'MAKER', ['photography'], [])", "role('retoucher', 'Retoucher', 'MAKER')"),
    revision: t.replace('TAXONOMY_REVISION = 1;', 'TAXONOMY_REVISION = REV;'),
    spread: t.replace("  role('retoucher'", "  ...more,\n  role('retoucher'"),
    empty: t.replace(/export const ROLES = freezeAll\(\[[\s\S]*?\]\);/, 'export const ROLES = freezeAll([\n]);'),
    sevenArgs: t.replace("role('retoucher', 'Retoucher', 'Post-Production', 'MAKER', ['photography'], [])", "role('retoucher', 'Retoucher', 'Post-Production', 'MAKER', ['photography'], [], 'extra')"),
    twoRoleBlocks: `${t}\nexport const ROLES = freezeAll([\n  role('barber', 'Barber', 'Beauty', 'CRAFT', ['hair_beauty_makeup']),\n]);\n`,
    twoFamilyLists: t.replace('/** Bumped', "// export const ROLE_FAMILIES = Object.freeze(['WIZARD']);\n/** Bumped"),
    twoRevisions: t.replace('/** Bumped', '// export const TAXONOMY_REVISION = 7;\n/** Bumped'),
    newlineInString: t.replace("'Retoucher', 'Post", "'Re\ntoucher', 'Post"),
  };
  for (const [name, text] of Object.entries(bad)) {
    assert.notEqual(text, t, `${name} variant must differ`);
    assert.throws(() => inspect(text), InspectorError, name);
  }
});

test('the registry text is parsed, never executed', () => {
  delete globalThis.__brainPwned;
  const t = registryText().replace("'Retoucher', 'Post", "(globalThis.__brainPwned = 1), 'Post");
  assert.throws(() => inspect(t), InspectorError);
  assert.equal(globalThis.__brainPwned, undefined);
});

test('verifySnapshot catches a tampered role, count or field', () => {
  const s = inspect(registryText());
  const roleEdit = structuredClone(s); roleEdit.roles[0].label = 'Photo';
  const count = structuredClone(s); count.role_count = 5;
  const field = structuredClone(s); field.source.ref = 'other';
  const extra = structuredClone(s); extra.note = 'x';
  assert.match(verifySnapshot(roleEdit).problems.join(), /registry_sha256/);
  assert.match(verifySnapshot(count).problems.join(), /role_count/);
  assert.match(verifySnapshot(field).problems.join(), /snapshot_sha256/);
  assert.match(verifySnapshot(extra).problems.join(), /unexpected property note/);
});
