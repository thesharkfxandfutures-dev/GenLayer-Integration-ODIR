// The bundle is the A3 resolver: for every combination, in template and agreement mode, it gives
// the same document, hash, Markdown and parchment input as resolver/src. And it is one ES module that
// needs nothing from its host: it runs in a bare ECMAScript context with no Node or web globals.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { combinations, comboName, loadTemplates } from '../../resolver/src/load.js';
import { renderMarkdown, toParchment } from '../../resolver/src/render.js';
import { ResolveError, resolve } from '../../resolver/src/resolve.js';
import { codeOf } from '../src/assemble.js';
import { OUTPUTS, importText } from '../src/build.js';
import { ROOT, build, makeRepo, tmp } from './helpers.js';

const { outputs, manifest } = await build(makeRepo().dir, { ref: 'HEAD' });
const text = outputs[OUTPUTS.bundle];
const B = await importText(text);
const disk = loadTemplates(ROOT);
const { combos } = combinations(disk);
const SAMPLE = { text: 'Sample', date: '1 January 2027', time: '09:00', money: '£100', number: '1', duration: '1 day' };
const SALT = 'ab'.repeat(32);

const inputs = (c, from) => ({
  base: from.base(c.base), engager: c.engager ? from.module(c.engager) : null, provider: c.provider ? from.module(c.provider) : null,
  jurisdiction: c.jurisdiction, consumer: c.consumer,
});
const fromDisk = { base: (k) => disk.bases.get(k), module: (k) => disk.modules.get(k) };
const fromBundle = { base: (k) => B.getBase(k), module: (k) => B.getModule(k) };

test('every combination: the same document, terms hash, Markdown and parchment input as resolver/src', () => {
  assert.equal(combos.length, 24);
  for (const c of combos) {
    const want = resolve(inputs(c, fromDisk));
    const got = B.resolve(inputs(c, fromBundle));
    assert.deepEqual(got, want, comboName(c));
    assert.equal(B.renderMarkdown(got), renderMarkdown(want));
    assert.deepEqual(B.toParchment(got, { names: { engager: 'A', provider: 'B' } }), toParchment(want, { names: { engager: 'A', provider: 'B' } }));
    assert.equal(got.terms_hash, manifest.terms_hashes[comboName(c)]);
  }
});

test('every combination filled in agreement mode, with overrides: the same document and hash', () => {
  for (const c of combos) {
    const tpl = resolve(inputs(c, fromDisk));
    const values = Object.fromEntries(tpl.fields.filter((f) => f.default === null).map((f) => [f.key, SAMPLE[f.type]]));
    const overrides = [{ id: 'o.parking', category: 'place', text: 'Parking is on the street outside — café receipts are not expenses.' }];
    const args = { mode: 'agreement', values, salt: SALT, overrides, title: 'Spring shoot' };
    const want = resolve({ ...inputs(c, fromDisk), ...args });
    const got = B.resolve({ ...inputs(c, fromBundle), ...args });
    assert.deepEqual(got, want, comboName(c));
  }
});

test('refusals are the same: the bundle throws its own ResolveError with the same problems', () => {
  const bad = [
    (f) => ({ base: f.base('P2P'), engager: f.module('photographer'), jurisdiction: 'EW', consumer: true }),
    (f) => ({ base: f.base('B2P'), jurisdiction: 'EW', consumer: true }),
    (f) => ({ base: f.base('P2P'), jurisdiction: 'XX' }),
    (f) => ({ base: f.base('P2P'), jurisdiction: 'EW', mode: 'agreement', salt: 'short' }),
    (f) => ({ base: f.base('P2P'), jurisdiction: 'EW', overrides: [{ id: 'o.x', category: 'pay', text: 'zero​width' }] }),
  ];
  for (const make of bad) {
    let want; let got;
    try { resolve(make(fromDisk)); } catch (e) { want = e; }
    try { B.resolve(make(fromBundle)); } catch (e) { got = e; }
    assert.ok(want instanceof ResolveError && got instanceof B.ResolveError && got instanceof B.TemplateError);
    assert.deepEqual(got.problems, want.problems);
  }
});

test('templates handed out are frozen and verified; listTemplates and templateText match the files', () => {
  const p2p = B.getBase('P2P');
  assert.ok(Object.isFrozen(p2p) && Object.isFrozen(p2p.clauses[0]));
  assert.throws(() => { p2p.clauses[0].text = 'changed'; }, TypeError);
  assert.equal(B.getBase('P2P'), p2p);
  for (const t of B.listTemplates()) {
    assert.equal(B.templateText(t.path), fs.readFileSync(path.join(ROOT, t.path), 'utf8'));
    assert.deepEqual(Object.keys(t).sort(), ['file_sha256', 'key', 'kind', 'path', 'sha256', 'version']);
  }
  assert.throws(() => B.getBase('B2B'), (e) => e instanceof B.ReleaseError && /no base "B2B"/.test(e.message));
  assert.throws(() => B.getModule('drone_pilot'), /no role module "drone_pilot"/);
  assert.throws(() => B.templateText('schema/agreement.v1.json'), /no template/);
  assert.ok(Object.isFrozen(B.RELEASE));
  assert.deepEqual(B.verifyRelease(), { ok: true, problems: [] });
});

test('hash functions are the adapter\'s canonical encoding', async () => {
  const { canonical, digest } = await import('../../adapter/src/canon.js');
  const v = { b: ['£', '€', '“q”', 1, null, true], a: { z: 'é', y: 'x\u0000' } };
  assert.equal(B.canonical(v), canonical(v));
  assert.equal(B.digest(v), digest(v));
  assert.throws(() => B.canonical({ x: 1.5 }), B.CanonError);
});

test('one ES module with no imports, and no Node-only code', () => {
  const code = codeOf(text);
  assert.doesNotMatch(code, /^\s*import\b/m);
  for (const re of [/\bimport\s*\(/, /import\.meta/, /\brequire\s*\(/, /\bprocess\./, /['"]node:/, /\bBuffer\b/]) {
    const lines = code.split('\n').filter((l) => !/^\s*\/\//.test(l) && re.test(l));
    assert.deepEqual(lines, [], String(re));
  }
  assert.ok(!text.includes('\r'));
});

test('runs in a bare ECMAScript context: no Node, no web APIs, no console', () => {
  const file = path.join(tmp('odir-bundle-'), 'odir-templates.mjs');
  fs.writeFileSync(file, text);
  const script = `
    import vm from 'node:vm';
    import fs from 'node:fs';
    const ctx = vm.createContext({});
    vm.runInContext('delete globalThis.console', ctx);
    const host = vm.runInContext('["process","Buffer","TextEncoder","TextDecoder","crypto","URL","console","require","fetch","atob"].filter((n) => n in globalThis)', ctx);
    const m = new vm.SourceTextModule(fs.readFileSync(process.argv[1], 'utf8'), { context: ctx });
    await m.link(() => { throw new Error('the bundle imported something'); });
    await m.evaluate();
    const B = m.namespace;
    const out = {};
    for (const t of B.listTemplates()) if (t.kind === 'base') for (const j of ['EW', 'SC', 'NI']) out['base.none.' + t.key + '.' + j + '.business'] = B.resolve({ base: B.getBase(t.key), jurisdiction: j }).terms_hash;
    process.stdout.write(JSON.stringify({ host: [...host], ok: B.verifyRelease().ok, out }));
  `;
  const r = JSON.parse(execFileSync(process.execPath, ['--experimental-vm-modules', '--no-warnings', '--input-type=module', '-e', script, file]).toString());
  assert.deepEqual(r.host, []);
  assert.equal(r.ok, true);
  assert.equal(Object.keys(r.out).length, 6);
  for (const [k, h] of Object.entries(r.out)) assert.equal(h, manifest.terms_hashes[k], k);
});
