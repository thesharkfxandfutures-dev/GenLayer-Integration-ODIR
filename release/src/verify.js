// Checks a built release (slice A4): the four files as they were downloaded, against each other,
// against the bundle's own hash checks and, with a rebuild, against the bytes the commit gives.
//   SHA256SUMS            every listed file has that sha256, and lists exactly the three outputs
//   manifest              odir.template-release.v1; same tag, commit, notice, sources and schemas as
//                         the bundle; bundle sha256 and size; the same templates and hashes as the
//                         bundle reports; terms hashes equal to those the bundle computes now
//   notes                 exactly the notes this manifest gives
//   bundle                verifyRelease() — every embedded file against its whole-file sha256 and
//                         template hash — and getBase / getModule hand every template out
//   rebuild (optional)    building again from the commit gives the same bytes for all four files
// Without a rebuild, a forgery that rewrote every recorded hash consistently still passes: the
// rebuild (or the sha256 of the release the owner published) is the anchor.
import fs from 'node:fs';
import path from 'node:path';
import { validate } from '../../brain/src/jsonschema.js';
import { stableJson } from './assemble.js';
import { OUTPUTS, TOOLING_ROOT, buildRelease, importText, releaseNotes, sha256, termsHashesOf } from './build.js';

const MANIFEST_SCHEMA = JSON.parse(fs.readFileSync(path.join(TOOLING_ROOT, 'schema/template-release.v1.json'), 'utf8'));
const TERMS_HASH = /^sha256:[0-9a-f]{64}$/;

const same = (a, b) => stableJson(a) === stableJson(b);

// files: { [name]: string } as read from disk (UTF-8). rebuildSource: a gitSource, or null.
export async function verifyRelease(files, { rebuildSource = null } = {}) {
  const problems = [];
  for (const f of Object.values(OUTPUTS)) if (typeof files[f] !== 'string') problems.push(`${f}: missing`);
  if (problems.length) return { ok: false, problems };

  const listed = new Map();
  for (const line of files[OUTPUTS.sums].split('\n').filter(Boolean)) {
    const m = /^([0-9a-f]{64}) {2}(\S+)$/.exec(line);
    if (!m) { problems.push(`${OUTPUTS.sums}: cannot read line ${JSON.stringify(line)}`); continue; }
    if (listed.has(m[2])) problems.push(`${OUTPUTS.sums}: lists ${m[2]} twice`);
    listed.set(m[2], m[1]);
  }
  const want = [OUTPUTS.bundle, OUTPUTS.manifest, OUTPUTS.notes].sort();
  if (!same([...listed.keys()].sort(), want)) problems.push(`${OUTPUTS.sums}: must list exactly ${want.join(', ')}`);
  for (const [name, h] of listed) if (typeof files[name] === 'string' && sha256(files[name]) !== h) problems.push(`${name}: sha256 does not match ${OUTPUTS.sums}`);

  let manifest = null;
  let parsed;
  try { parsed = JSON.parse(files[OUTPUTS.manifest]); } catch (e) { problems.push(`${OUTPUTS.manifest}: not JSON (${e.message})`); }
  if (parsed !== undefined) {
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) manifest = parsed;
    else problems.push(`${OUTPUTS.manifest}: not an object`);
  }
  if (manifest) {
    const bad = validate(MANIFEST_SCHEMA, manifest).problems;
    problems.push(...bad.map((p) => `${OUTPUTS.manifest}: ${p}`));
    for (const [k, h] of Object.entries(manifest.terms_hashes || {})) if (typeof h !== 'string' || !TERMS_HASH.test(h)) problems.push(`${OUTPUTS.manifest}: terms_hashes.${k} is not a sha256: hash`);
    if (bad.length) manifest = null; // nothing below can trust its shape
    else if (files[OUTPUTS.notes] !== releaseNotes(manifest)) problems.push(`${OUTPUTS.notes}: is not the notes this manifest gives`);
  }
  const bundleText = files[OUTPUTS.bundle];
  if (manifest) {
    if (manifest.bundle?.file !== OUTPUTS.bundle) problems.push(`${OUTPUTS.manifest}: bundle.file must be ${OUTPUTS.bundle}`);
    if (manifest.bundle?.sha256 !== sha256(bundleText)) problems.push(`${OUTPUTS.bundle}: sha256 does not match the manifest`);
    if (manifest.bundle?.bytes !== Buffer.byteLength(bundleText, 'utf8')) problems.push(`${OUTPUTS.bundle}: size does not match the manifest`);
  }

  let bundle = null;
  try { bundle = await importText(bundleText); } catch (e) { problems.push(`${OUTPUTS.bundle}: does not load (${e.message})`); }
  if (bundle) {
    const check = bundle.verifyRelease();
    problems.push(...check.problems.map((p) => `${OUTPUTS.bundle}: ${p}`));
    if (manifest) {
      if (bundle.RELEASE.tag !== manifest.tag || bundle.RELEASE.commit !== manifest.commit) problems.push('the bundle and the manifest name different releases');
      if (bundle.RELEASE.notice !== manifest.notice) problems.push('the bundle and the manifest carry different notices');
      if (!same(bundle.listTemplates(), manifest.templates)) problems.push('the bundle and the manifest list different templates or hashes');
      if (!same(bundle.listSchemas(), manifest.schemas)) problems.push('the bundle and the manifest list different schema files');
      if (!same(bundle.RELEASE.sources, manifest.sources)) problems.push('the bundle and the manifest list different source files');
    }
    if (check.ok) {
      for (const t of bundle.listTemplates()) {
        try { if (t.kind === 'base') bundle.getBase(t.key); else bundle.getModule(t.key); } catch (e) { problems.push(`${t.path}: ${e.message}`); }
      }
      if (manifest) {
        const derived = termsHashesOf(bundle);
        problems.push(...derived.problems.map((p) => `${OUTPUTS.bundle}: ${p}`));
        if (!same(derived.termsHashes, manifest.terms_hashes)) problems.push('the manifest\'s terms hashes are not the ones the bundle computes');
      }
    }
  }

  if (rebuildSource) {
    try {
      const { outputs } = await buildRelease(rebuildSource);
      for (const [name, text] of Object.entries(outputs)) if (files[name] !== text) problems.push(`${name}: differs from a rebuild of ${rebuildSource.tag ?? rebuildSource.commit}`);
    } catch (e) { problems.push(`rebuild failed: ${e.message}`); }
  }
  return { ok: problems.length === 0, problems, manifest };
}
