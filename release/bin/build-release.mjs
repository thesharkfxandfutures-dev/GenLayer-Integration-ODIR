#!/usr/bin/env node
// Build an ODIR template release (slice A4) from git objects — never from the working tree.
//   node release/bin/build-release.mjs --tag templates-v1.0.0 --out dist     (a tagged release)
//   node release/bin/build-release.mjs --ref HEAD --out dist                 (an untagged check build)
//   [--root <repo>]  the repository to read (default: this one)
// Writes odir-templates.mjs, odir-templates.manifest.json, RELEASE_NOTES.md and SHA256SUMS.
// Exit 0 built · 1 refused (the problems are printed) · 2 usage.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { OUTPUTS, ReleaseBuildError, buildRelease } from '../src/build.js';
import { gitSource } from '../src/gitsource.js';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] ?? null : null; };
const usage = (msg) => { process.stderr.write(`${msg}\nusage: build-release.mjs (--tag templates-vX.Y.Z | --ref <rev>) --out <dir> [--root <repo>]\n`); process.exit(2); };

const out = opt('--out');
if (!out) usage('--out is required');
const root = path.resolve(opt('--root') || path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..'));

let source;
try { source = gitSource(root, { tag: opt('--tag'), ref: opt('--ref') }); } catch (e) { usage(e.message); }

try {
  const { outputs, manifest } = await buildRelease(source);
  fs.mkdirSync(out, { recursive: true });
  for (const name of Object.values(OUTPUTS)) fs.writeFileSync(path.join(out, name), outputs[name]);
  process.stdout.write(`release ${manifest.tag ?? '(untagged)'} at ${manifest.commit}\n`);
  for (const t of manifest.templates) process.stdout.write(`ok   ${t.path}  ${t.kind} ${t.key} v${t.version}  ${t.sha256}\n`);
  process.stdout.write(`ok   ${Object.keys(manifest.terms_hashes).length} combinations reproduce their golden terms hashes\n`);
  process.stdout.write(`${OUTPUTS.bundle}  sha256 ${manifest.bundle.sha256}  ${manifest.bundle.bytes} bytes\n`);
  process.stdout.write(outputs[OUTPUTS.sums]);
} catch (e) {
  if (!(e instanceof ReleaseBuildError)) throw e;
  process.stdout.write(`REFUSED ${e.message}\n`);
  process.exit(1);
}
