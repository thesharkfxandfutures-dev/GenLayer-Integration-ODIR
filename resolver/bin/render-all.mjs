#!/usr/bin/env node
// CI gate (slice A3): check every template and render every role × base pair that exists, in
// every jurisdiction and consumer variant, against odir.agreement.v1. A STALE module (drafted
// against another base version) fails. Exit 0 only when everything renders.
//   node resolver/bin/render-all.mjs [--root <repo>] [--out <dir>] [--json]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { combinations, comboName, loadTemplates } from '../src/load.js';
import { renderMarkdown } from '../src/render.js';
import { resolve } from '../src/resolve.js';

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
    const doc = resolve({
      base: bases.get(c.base),
      engager: c.slot === 'engager' ? modules.get(c.role) : null,
      provider: c.slot === 'provider' ? modules.get(c.role) : null,
      jurisdiction: c.jurisdiction,
      consumer: c.consumer,
    });
    const stale = ['engager_module', 'provider_module'].filter((k) => doc.sources[k]?.stale);
    if (stale.length) failures.push(`${name}: STALE — ${c.role} was drafted against ${c.base} v${modules.get(c.role).drafted_against[c.base]}, the base is v${bases.get(c.base).version}`);
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
