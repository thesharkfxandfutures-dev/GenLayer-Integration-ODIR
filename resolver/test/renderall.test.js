import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { combinations, comboName, loadTemplates } from '../src/load.js';
import { makeBase, makeModule } from './helpers.js';

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'render-all.mjs');

function tree({ bases = { 'p2p.json': makeBase() }, roles = { tester: makeModule('tester') } } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'odir-templates-'));
  fs.mkdirSync(path.join(root, 'templates', 'bases'), { recursive: true });
  for (const [f, b] of Object.entries(bases)) fs.writeFileSync(path.join(root, 'templates', 'bases', f), JSON.stringify(b));
  for (const [d, m] of Object.entries(roles)) {
    fs.mkdirSync(path.join(root, 'templates', 'roles', d), { recursive: true });
    if (m) fs.writeFileSync(path.join(root, 'templates', 'roles', d, 'module.json'), JSON.stringify(m));
  }
  return root;
}
const cli = (root, ...extra) => spawnSync('node', [BIN, '--root', root, ...extra], { encoding: 'utf8' });

test('combinations: each base alone, each role x base x slot it takes, every jurisdiction, consumer only provider-side', () => {
  const root = tree({ bases: { 'p2p.json': makeBase(), 'b2p.json': makeBase('B2P', { consumer: false }) } });
  const t = loadTemplates(root);
  assert.deepEqual(t.problems, []);
  const { combos, skipped } = combinations(t);
  const names = combos.map(comboName);
  assert.equal(names.length, 6 + 3 + 3 + 6 + 3 + 3); // P2P alone, B2P alone, engager P2P, provider P2P (x consumer), provider B2P, the pair under P2P
  assert.ok(names.includes('tester.provider.P2P.EW.consumer'));
  assert.ok(names.includes('tester+tester.pair.P2P.SC.business'));
  assert.ok(!names.includes('tester.engager.P2P.EW.consumer'));
  assert.ok(!names.some((n) => n.includes('.pair.') && n.endsWith('consumer')));
  assert.ok(!names.some((n) => n.includes('B2P') && n.endsWith('consumer')));
  assert.equal(new Set(names).size, names.length);
  assert.deepEqual(skipped, []);
});

test('render-all passes a good tree and writes JSON and Markdown with --out', () => {
  const root = tree();
  const out = path.join(root, 'out');
  const r = cli(root, '--out', out);
  assert.equal(r.status, 0, r.stdout);
  assert.match(r.stdout, /templates: 1 base\(s\), 1 role module\(s\)/);
  assert.match(r.stdout, /skip tester\.provider\.B2P: base not present/);
  assert.match(r.stdout, /18 rendered, 1 skipped, 0 failed/);
  assert.ok(fs.existsSync(path.join(out, 'tester.provider.P2P.SC.consumer.json')));
  assert.ok(fs.existsSync(path.join(out, 'tester.provider.P2P.SC.consumer.md')));
  const j = JSON.parse(cli(root, '--json').stdout);
  assert.equal(j.ok, true);
  assert.equal(j.rendered.length, 18);
});

test('render-all fails on a stale module, a misnamed file or folder, a stray file, an invalid template, or no bases', () => {
  const stale = makeModule('tester');
  stale.drafted_against.P2P = 2;
  let r = cli(tree({ roles: { tester: stale } }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /FAIL tester\.provider\.P2P\.EW\.business: STALE/);

  r = cli(tree({ roles: { other: makeModule('tester') } }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /role_key tester must equal its folder name/);

  r = cli(tree({ bases: { 'base1.json': makeBase() } }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /name it p2p\.json/);

  const root = tree();
  fs.writeFileSync(path.join(root, 'templates', 'roles', 'tester', 'notes.txt'), 'x');
  fs.writeFileSync(path.join(root, 'templates', 'bases', 'README.md'), 'x');
  r = cli(root);
  assert.equal(r.status, 1);
  assert.match(r.stdout, /unexpected files notes\.txt/);
  assert.match(r.stdout, /only <base>\.json files belong here/);

  const bad = makeBase();
  bad.clauses[0].text = '{{nope}}';
  r = cli(tree({ bases: { 'p2p.json': bad } }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /templates\/bases\/p2p\.json: base P2P is invalid/);

  r = cli(tree({ bases: {}, roles: {} }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /no base templates found/);

  r = cli(tree({ roles: { empty: null } }));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /templates\/roles\/empty\/module\.json: missing/);
});
