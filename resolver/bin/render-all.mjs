#!/usr/bin/env node
// CI gate (slice A3): check every template and render every role × base pair that exists, in
// every jurisdiction and consumer variant, against odir.agreement.v1. A STALE module (drafted
// against another base version) fails. Exit 0 only when everything renders.
// Each combination is also filled once in agreement mode with sample values for every blank that
// has no default, so the defaults and the value rules are exercised too.
//   node resolver/bin/render-all.mjs [--root <repo>] [--out <dir>] [--json]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { combinations, comboName, loadTemplates } from '../src/load.js';
import { renderMarkdown } from '../src/render.js';
import { resolve } from '../src/resolve.js';

const SAMPLE = { text: 'Sample', date: '1 January 2027', time: '09:00', money: '£100', number: '1', duration: '1 day' };
const SAMPLE_SALT = '0'.repeat(64);

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const root = path.resolve(opt('--root') || path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..'));
const outDir = opt('--out');

const { bases, modules, problems } = loadTemplates(root);
const failures = [...problems];
const rows = [];
const { combos, skipped } = combinations({ bases, modules });
if (!bases.size) failures.push('no base templates found under templates/bases');
for (const c of combos) {
  const name = comboName(c);
  try {
    const input = {
      base: bases.get(c.base),
      engager: c.engager ? modules.get(c.engager) : null,
      provider: c.provider ? modules.get(c.provider) : null,
      jurisdiction: c.jurisdiction,
      consumer: c.consumer,
    };
    const doc = resolve(input);
    const stale = [['engager_module', c.engager], ['provider_module', c.provider]].filter(([k]) => doc.sources[k]?.stale);
    for (const [, role] of stale) failures.push(`${name}: STALE — ${role} was drafted against ${c.base} v${modules.get(role).drafted_against[c.base]}, the base is v${bases.get(c.base).version}`);
    const values = Object.fromEntries(doc.fields.filter((f) => f.default === null).map((f) => [f.key, SAMPLE[f.type]]));
    const filled = resolve({ ...input, mode: 'agreement', values, salt: SAMPLE_SALT });
    if (filled.sections.some((s) => s.clauses.some((x) => /\{\{|\[\[/.test(x.text)))) failures.push(`${name}: a blank is left after filling`);
    const clauses = doc.sections.reduce((n, s) => n + s.clauses.length, 0);
    rows.push({ name, terms_hash: doc.terms_hash, clauses, blanks: doc.fields.length, stale: stale.length > 0 });
    if (outDir) {
      fs.mkdirSync(outDir, { recursive: true });
      fs.writeFileSync(path.join(outDir, `${name}.json`), `${JSON.stringify(doc, null, 2)}\n`);
      fs.writeFileSync(path.join(outDir, `${name}.md`), renderMarkdown(doc));
    }
  } catch (e) {
    failures.push(`${name}: ${e.message}`);
  }
}

if (args.includes('--json')) {
  process.stdout.write(`${JSON.stringify({ ok: failures.length === 0, rendered: rows, skipped, failures }, null, 2)}\n`);
} else {
  process.stdout.write(`templates: ${bases.size} base(s), ${modules.size} role module(s)\n`);
  for (const r of rows) process.stdout.write(`ok   ${r.name}  ${r.clauses} clauses, ${r.blanks} blanks  ${r.terms_hash}\n`);
  for (const s of skipped) process.stdout.write(`skip ${s.role}.${s.slot}.${s.base}: ${s.reason}\n`);
  for (const f of failures) process.stdout.write(`FAIL ${f}\n`);
  process.stdout.write(`${rows.length - rows.filter((r) => r.stale).length} rendered, ${skipped.length} skipped, ${failures.length} failed\n`);
}
process.exit(failures.length ? 1 : 0);
