#!/usr/bin/env node
// Check a built ODIR template release (slice A4).
//   node release/bin/verify-release.mjs --dir <folder>                        (the files on their own)
//   node release/bin/verify-release.mjs --dir <folder> --rebuild --tag <tag>  (and rebuild from the tag)
//   node release/bin/verify-release.mjs --dir <folder> --rebuild --ref <rev>
//   [--root <repo>]
// Exit 0 intact · 1 a check failed (printed) · 2 usage.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { OUTPUTS } from '../src/build.js';
import { gitSource } from '../src/gitsource.js';
import { verifyRelease } from '../src/verify.js';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] ?? null : null; };
const usage = (msg) => { process.stderr.write(`${msg}\nusage: verify-release.mjs --dir <folder> [--rebuild (--tag <tag> | --ref <rev>)] [--root <repo>]\n`); process.exit(2); };

const dir = opt('--dir');
if (!dir) usage('--dir is required');
const root = path.resolve(opt('--root') || path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..'));
let rebuildSource = null;
if (args.includes('--rebuild')) {
  try { rebuildSource = gitSource(root, { tag: opt('--tag'), ref: opt('--ref') }); } catch (e) { usage(e.message); }
}

const files = {};
for (const name of Object.values(OUTPUTS)) {
  const p = path.join(dir, name);
  if (fs.existsSync(p)) files[name] = fs.readFileSync(p, 'utf8');
}
const { ok, problems, manifest } = await verifyRelease(files, { rebuildSource });
for (const p of problems) process.stdout.write(`FAIL ${p}\n`);
if (ok) process.stdout.write(`ok   release ${manifest.tag ?? '(untagged)'} at ${manifest.commit}: ${manifest.templates.length} templates, bundle ${manifest.bundle.sha256}${rebuildSource ? ', rebuild byte-identical' : ''}\n`);
process.exit(ok ? 0 : 1);
