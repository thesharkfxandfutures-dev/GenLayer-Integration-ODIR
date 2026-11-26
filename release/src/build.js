// Builds an ODIR template release (slice A4) from one source (a commit, usually a tag):
//   odir-templates.mjs            the bundle — templates, hashes, resolver and hash code, one ES module
//   odir-templates.manifest.json  every template's hashes, the bundle's sha256, the terms hash of
//                                 every role × base combination
//   RELEASE_NOTES.md              what the release holds and how to check it
//   SHA256SUMS                    sha256sum -c format, for the three files above
// No clock, no randomness, no file order: the same commit and tag give the same bytes.
//
// The hashes in the bundle are computed by the bundled code itself (a first pass imports a probe
// bundle), and the finished bundle must reproduce every golden terms hash committed at the same
// commit (resolver/test/golden/hashes.json) — a template edited without its golden diff is refused.
//
// The build tooling (this file and what it imports, read from the checkout that runs it) must be
// byte-identical to the same files at the commit being built, so a dirty checkout, or newer tooling
// building an older tag, is refused instead of giving other bytes. Build a tag from its own checkout.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { combinations, comboName } from '../../resolver/src/load.js';
import { AssembleError, MODULES, SCHEMA_FILES, assembleBundle, stableJson } from './assemble.js';

export const OUTPUTS = Object.freeze({
  bundle: 'odir-templates.mjs',
  manifest: 'odir-templates.manifest.json',
  notes: 'RELEASE_NOTES.md',
  sums: 'SHA256SUMS',
});
export const RELEASE_SCHEMA = 'odir.template-release.v1';
export const NOTICE = 'Drafts, not legal advice. A UK solicitor reviews the templates before any real member signs.';
export const GOLDEN = 'resolver/test/golden/hashes.json';

export class ReleaseBuildError extends Error {
  constructor(message, problems = []) {
    super(problems.length ? `${message}:\n  - ${problems.join('\n  - ')}` : message);
    this.problems = problems;
  }
}

export const sha256 = (data) => crypto.createHash('sha256').update(typeof data === 'string' ? Buffer.from(data, 'utf8') : data).digest('hex');
export const importText = (text) => import(`data:text/javascript;base64,${Buffer.from(text, 'utf8').toString('base64')}`);

// The tooling a build runs from the checkout: its own files and everything they import.
export const TOOLING = Object.freeze([
  'release/src/assemble.js', 'release/src/build.js', 'release/src/gitsource.js', 'release/src/verify.js',
  'release/bin/build-release.mjs', 'release/bin/verify-release.mjs',
  'resolver/src/load.js', 'resolver/src/categories.js', 'resolver/src/validate.js', 'brain/src/jsonschema.js',
  'schema/template-release.v1.json',
]);
export const TOOLING_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

function toolingProblems(source) {
  const out = [];
  for (const p of TOOLING) {
    let atCommit;
    try { atCommit = source.read(p); } catch { out.push(`${p}: not in commit ${source.commit} — this commit has no release tooling`); continue; }
    let here;
    try { here = fs.readFileSync(path.join(TOOLING_ROOT, p), 'utf8'); } catch { out.push(`${p}: missing from the checkout running the build`); continue; }
    if (here !== atCommit) out.push(`${p}: the checkout running the build differs from commit ${source.commit} — build from a clean checkout of that commit`);
  }
  return out;
}

// The terms hash of every role × base combination of the bundle's templates (template mode).
export function termsHashesOf(bundle) {
  const problems = [];
  const bases = new Map();
  const modules = new Map();
  for (const t of bundle.listTemplates()) {
    if (t.kind === 'base') bases.set(t.key, bundle.getBase(t.key)); else modules.set(t.key, bundle.getModule(t.key));
  }
  const { combos, skipped } = combinations({ bases, modules });
  const termsHashes = {};
  for (const c of combos) {
    const name = comboName(c);
    try {
      termsHashes[name] = bundle.resolve({
        base: bases.get(c.base), engager: c.engager ? modules.get(c.engager) : null, provider: c.provider ? modules.get(c.provider) : null,
        jurisdiction: c.jurisdiction, consumer: c.consumer,
      }).terms_hash;
    } catch (e) { problems.push(`${name}: ${e.message}`); }
  }
  for (const s of skipped) problems.push(`${s.role}.${s.slot}.${s.base}: ${s.reason}`);
  return { termsHashes, problems };
}

const BASE_FILE = /^templates\/bases\/([a-z0-9]+)\.json$/;
const MODULE_FILE = /^templates\/roles\/([a-z][a-z0-9_]*)\/module\.json$/;

// The template files at the source, with kind, key and version read from each (checked later by
// the bundled validator). Any other file under templates/ stops the build, as it does render-all.
function readTemplates(source, problems) {
  const out = [];
  for (const path of source.list('templates')) {
    const kind = BASE_FILE.test(path) ? 'base' : MODULE_FILE.test(path) ? 'module' : null;
    if (!kind) { problems.push(`${path}: not a template file (templates/bases/<base>.json or templates/roles/<role>/module.json)`); continue; }
    const text = source.read(path);
    if (text.includes('\r')) { problems.push(`${path}: has a carriage return (LF line endings only)`); continue; }
    let value;
    try { value = JSON.parse(text); } catch (e) { problems.push(`${path}: not JSON (${e.message})`); continue; }
    const key = kind === 'base' ? value?.key : value?.role_key;
    const named = kind === 'base' ? BASE_FILE.exec(path)[1] : MODULE_FILE.exec(path)[1];
    if (typeof key !== 'string' || (kind === 'base' ? key.toLowerCase() : key) !== named) problems.push(`${path}: holds ${JSON.stringify(key)}, which does not match its file name`);
    out.push({ path, kind, key, version: value?.version ?? null, sha256: null, file_sha256: sha256(text), text });
  }
  if (!out.some((f) => f.kind === 'base')) problems.push('no base template under templates/bases');
  return out;
}

/**
 * buildRelease(source) → { outputs: { [file]: string }, manifest }
 * source: { tag, commit, read(path), list(prefix) } (see gitsource.js).
 */
export async function buildRelease(source) {
  const problems = [];
  if (!/^[0-9a-f]{40}$/.test(source.commit)) throw new ReleaseBuildError(`commit must be a full sha, not ${JSON.stringify(source.commit)}`);
  const tooling = toolingProblems(source);
  if (tooling.length) throw new ReleaseBuildError('the build tooling is not the tooling of the commit being built', tooling);
  const templates = readTemplates(source, problems);
  const schemas = SCHEMA_FILES.map((path) => {
    const text = source.read(path);
    if (text.includes('\r')) problems.push(`${path}: has a carriage return (LF line endings only)`);
    return { path, kind: 'schema', key: null, version: null, sha256: null, file_sha256: sha256(text), text };
  });
  const sources = new Map(MODULES.map((m) => [m.path, source.read(m.path)]));
  const sourceHashes = new Map([...sources].map(([p, t]) => [p, sha256(t)]));
  const release = {
    schema: RELEASE_SCHEMA, tag: source.tag ?? null, commit: source.commit, notice: NOTICE,
    sources: MODULES.map((m) => ({ path: m.path, file_sha256: sourceHashes.get(m.path) })),
  };
  if (problems.length) throw new ReleaseBuildError('the templates at this commit cannot be released', problems);

  const assemble = (files) => {
    try { return assembleBundle({ release, files, sources, sourceHashes }); }
    catch (e) { if (e instanceof AssembleError) throw new ReleaseBuildError(e.message.split(':\n')[0], e.problems); throw e; }
  };

  // Pass 1: the bundled code computes each template's hash and checks each template.
  const probe = await importText(assemble([...templates, ...schemas]));
  for (const f of templates) {
    try {
      const value = JSON.parse(f.text);
      if (f.kind === 'base') probe.assertBase(value); else probe.assertModule(value);
      f.sha256 = probe.templateHash(value);
    } catch (e) { problems.push(`${f.path}: ${e.message}`); }
  }
  if (problems.length) throw new ReleaseBuildError('a template fails its checks', problems);

  // Pass 2: the real bundle. It must verify, and reproduce every golden terms hash.
  const bundleText = assemble([...templates, ...schemas]);
  const bundle = await importText(bundleText);
  const check = bundle.verifyRelease();
  if (!check.ok) throw new ReleaseBuildError('the assembled bundle does not verify', check.problems);

  const derived = termsHashesOf(bundle);
  const { termsHashes } = derived;
  problems.push(...derived.problems);
  let golden = null;
  try { golden = JSON.parse(source.read(GOLDEN)); } catch (e) { problems.push(`${GOLDEN}: ${e.message}`); }
  if (golden) {
    for (const [name, h] of Object.entries(termsHashes)) {
      if (!Object.hasOwn(golden, name)) problems.push(`${name}: no golden terms hash at this commit`);
      else if (golden[name] !== h) problems.push(`${name}: terms hash ${h} differs from the golden ${golden[name]} — a template changed without its golden diff`);
    }
    for (const name of Object.keys(golden)) if (!Object.hasOwn(termsHashes, name)) problems.push(`${name}: in the golden file but not a combination of these templates`);
  }
  if (problems.length) throw new ReleaseBuildError('the bundle does not reproduce the committed golden terms hashes', problems);

  const manifest = {
    schema: RELEASE_SCHEMA,
    tag: release.tag,
    commit: release.commit,
    notice: NOTICE,
    bundle: { file: OUTPUTS.bundle, sha256: sha256(bundleText), bytes: Buffer.byteLength(bundleText, 'utf8') },
    templates: bundle.listTemplates(),
    schemas: bundle.listSchemas(),
    sources: release.sources,
    terms_hashes: termsHashes,
  };
  const manifestText = `${stableJson(manifest)}\n`;
  const notes = releaseNotes(manifest);
  const outputs = { [OUTPUTS.bundle]: bundleText, [OUTPUTS.manifest]: manifestText, [OUTPUTS.notes]: notes };
  outputs[OUTPUTS.sums] = Object.keys(outputs).sort().map((f) => `${sha256(outputs[f])}  ${f}\n`).join('');
  return { outputs, manifest };
}

export function releaseNotes(m) {
  const label = m.tag ?? 'untagged build';
  const lines = [
    `# ODIR role-contract templates — ${label}`,
    '',
    `Commit \`${m.commit}\`. ${m.notice}`,
    '',
    'One ES module with no imports (`odir-templates.mjs`): every template as the exact text of its file, its',
    'whole-file sha256 and its template hash (style left out), and the resolver and hash code. SnapLink imports',
    'it in slice D1. `getBase` / `getModule` refuse a template whose hashes do not match.',
    '',
    '| Template | Kind | Version | Template hash | Whole-file sha256 |',
    '|---|---|---|---|---|',
    ...m.templates.map((t) => `| \`${t.path}\` | ${t.kind} ${t.key} | ${t.version} | \`${t.sha256}\` | \`${t.file_sha256}\` |`),
    '',
    `Bundle \`${m.bundle.file}\`: sha256 \`${m.bundle.sha256}\`, ${m.bundle.bytes} bytes. ${Object.keys(m.terms_hashes).length} role × base combinations, each terms hash equal to the golden file at this commit (listed in the manifest).`,
    '',
    '## Check it',
    '',
    '```bash',
    'sha256sum -c SHA256SUMS',
    `node release/bin/verify-release.mjs --dir <folder with these files> --rebuild${m.tag ? ` --tag ${m.tag}` : ` --ref ${m.commit}`}`,
    '```',
    '',
    'The rebuild must give the same bytes. A draft release: the owner reviews and publishes it.',
    '',
  ];
  return lines.join('\n');
}
