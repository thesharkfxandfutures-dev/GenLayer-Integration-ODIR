// Acceptance (plan A4): a tampered template fails the hash check. In layers:
//   1. inside the bundle: whole-file sha256 (any change, style too) and template hash (any word);
//      getBase / getModule refuse, verifyRelease() reports;
//   2. across the files: SHA256SUMS, the manifest's bundle sha256 and template list;
//   3. a rebuild from the tag: catches even a tamper that rewrote every recorded hash consistently.
import assert from 'node:assert/strict';
import test from 'node:test';
import { makeRelease, makeSchemaLoader, ReleaseError } from '../src/runtime.js';
import { stableJson } from '../src/assemble.js';
import { OUTPUTS, importText, releaseNotes, sha256, termsHashesOf } from '../src/build.js';
import { gitSource } from '../src/gitsource.js';
import { verifyRelease } from '../src/verify.js';
import { sha256Hex } from '../src/sha256.js';
import { build, makeRepo, tag } from './helpers.js';

const TAG = 'templates-v1.0.0';
const repo = makeRepo();
tag(repo.dir, TAG);
const { outputs, manifest } = await build(repo.dir, { tag: TAG });
const bundle = outputs[OUTPUTS.bundle];
const rebuildSource = gitSource(repo.dir, { tag: TAG });
const p2p = manifest.templates.find((t) => t.key === 'P2P');

// Edit the JSON-encoded text of templates/bases/p2p.json inside the bundle.
function editEmbedded(text, path, edit) {
  const marker = `"path": "${path}",`;
  const at = text.indexOf(marker);
  const start = text.indexOf('"text": ', at) + '"text": '.length;
  const end = text.indexOf('\n', start) - (text[text.indexOf('\n', start) - 1] === ',' ? 1 : 0);
  const old = JSON.parse(text.slice(start, end));
  return text.slice(0, start) + JSON.stringify(edit(old)) + text.slice(end);
}
function embedded(text, path) {
  const start = text.indexOf('"text": ', text.indexOf(`"path": "${path}",`)) + '"text": '.length;
  const end = text.indexOf('\n', start) - (text[text.indexOf('\n', start) - 1] === ',' ? 1 : 0);
  return JSON.parse(text.slice(start, end));
}
const reword = (t) => t.replace(/("text": "[^"]*?)\bthe\b/, '$1a');
const restyle = (t) => { const v = JSON.parse(t); v.style = { ...(v.style || {}), ink: v.style?.ink === 'navy' ? 'sepia' : 'navy' }; return `${JSON.stringify(v, null, 2)}\n`; };
const withBundle = (b) => ({ ...outputs, [OUTPUTS.bundle]: b });
function consistent(b) { // an attacker who rewrites the manifest and SHA256SUMS to match a tampered bundle
  const m = JSON.parse(outputs[OUTPUTS.manifest]);
  m.bundle.sha256 = sha256(b); m.bundle.bytes = Buffer.byteLength(b);
  const files = { ...outputs, [OUTPUTS.bundle]: b, [OUTPUTS.manifest]: `${stableJson(m)}\n` };
  files[OUTPUTS.sums] = [OUTPUTS.notes, OUTPUTS.manifest, OUTPUTS.bundle].sort().map((f) => `${sha256(files[f])}  ${f}\n`).join('');
  return files;
}

test('the untouched release verifies, with a byte-identical rebuild', async () => {
  const r = await verifyRelease(outputs, { rebuildSource });
  assert.deepEqual(r.problems, []);
});

test('one changed word in an embedded template: every layer catches it, and getBase refuses', async () => {
  const bad = editEmbedded(bundle, p2p.path, reword);
  assert.notEqual(bad, bundle);
  const B = await importText(bad);
  assert.throws(() => B.getBase('P2P'), (e) => e instanceof B.ReleaseError && /whole-file sha256 does not match/.test(e.message) && /template hash does not match/.test(e.message));
  assert.throws(() => B.getBase('P2P'), B.ReleaseError); // a failed check is never cached
  assert.throws(() => B.templateText(p2p.path), B.ReleaseError);
  assert.equal(B.getBase('B2P').key, 'B2P'); // the untouched template is still handed out
  const v = B.verifyRelease();
  assert.equal(v.ok, false);
  assert.equal(v.problems.length, 2);
  const r = await verifyRelease(withBundle(bad));
  const all = r.problems.join('\n');
  for (const re of [/odir-templates\.mjs: sha256 does not match SHA256SUMS/, /odir-templates\.mjs: sha256 does not match the manifest/, /p2p\.json: whole-file sha256/, /p2p\.json: template hash/]) assert.match(all, re);
});

test('a style-only change keeps the template hash, and is still caught by the whole-file sha256', async () => {
  const bad = editEmbedded(bundle, 'templates/bases/b2p.json', restyle);
  const B = await importText(bad);
  assert.throws(() => B.getBase('B2P'), /whole-file sha256 does not match/);
  assert.deepEqual(B.verifyRelease().problems, ['templates/bases/b2p.json: whole-file sha256 does not match the release']);
});

test('a tamper that also rewrites the recorded hashes, the manifest and SHA256SUMS is caught by the rebuild', async () => {
  let bad = editEmbedded(bundle, p2p.path, reword);
  const newText = embedded(bad, p2p.path);
  assert.notEqual(newText, embedded(bundle, p2p.path));
  const B0 = await importText(bundle);
  const newHash = B0.templateHash(JSON.parse(newText));
  bad = bad.replace(p2p.file_sha256, sha256Hex(newText)).replace(p2p.sha256, newHash);
  const B = await importText(bad);
  assert.deepEqual(B.verifyRelease(), { ok: true, problems: [] }); // self-consistent, so the bundle alone cannot tell
  const files = consistent(bad);
  assert.match((await verifyRelease(files)).problems.join('\n'), /different templates or hashes/);
  const m = JSON.parse(files[OUTPUTS.manifest]);
  m.templates = B.listTemplates();
  files[OUTPUTS.manifest] = `${stableJson(m)}\n`;
  assert.match((await verifyRelease(files)).problems.join('\n'), /terms hashes are not the ones the bundle computes/);
  m.terms_hashes = termsHashesOf(B).termsHashes;
  files[OUTPUTS.manifest] = `${stableJson(m)}\n`;
  files[OUTPUTS.notes] = releaseNotes(m);
  files[OUTPUTS.sums] = [OUTPUTS.notes, OUTPUTS.manifest, OUTPUTS.bundle].sort().map((f) => `${sha256(files[f])}  ${f}\n`).join('');
  assert.deepEqual((await verifyRelease(files)).problems, []); // ...nor the files alone
  const r = await verifyRelease(files, { rebuildSource });
  assert.match(r.problems.join('\n'), /odir-templates\.mjs: differs from a rebuild of templates-v1\.0\.0/);
  assert.match(r.problems.join('\n'), /odir-templates\.manifest\.json: differs from a rebuild/);
});

test('a manifest that names other hashes, or another release, is caught', async () => {
  const m = JSON.parse(outputs[OUTPUTS.manifest]);
  m.templates[0].sha256 = `sha256:${'0'.repeat(64)}`;
  const files = { ...outputs, [OUTPUTS.manifest]: `${stableJson(m)}\n` };
  assert.match((await verifyRelease(files)).problems.join('\n'), /sha256 does not match SHA256SUMS[\s\S]*different templates or hashes/);
  const m2 = JSON.parse(outputs[OUTPUTS.manifest]);
  m2.commit = 'f'.repeat(40);
  assert.match((await verifyRelease({ ...outputs, [OUTPUTS.manifest]: `${stableJson(m2)}\n` })).problems.join('\n'), /name different releases/);
});

test('a manifest that is not an object, or not odir.template-release.v1, fails closed', async () => {
  for (const bad of ['null', '[]', '5', '"x"', '{}']) {
    const r = await verifyRelease({ ...outputs, [OUTPUTS.manifest]: `${bad}\n` });
    assert.equal(r.ok, false, bad);
    assert.match(r.problems.join('\n'), /not an object|missing schema/, bad);
  }
});

test('without a rebuild, the notes, the terms hashes, the sources and the schemas are still checked against the bundle', async () => {
  const resum = (files) => ({ ...files, [OUTPUTS.sums]: [OUTPUTS.notes, OUTPUTS.manifest, OUTPUTS.bundle].sort().map((f) => `${sha256(files[f])}  ${f}\n`).join('') });
  const notes = resum({ ...outputs, [OUTPUTS.notes]: outputs[OUTPUTS.notes].replace('not legal advice', 'legal advice') });
  assert.match((await verifyRelease(notes)).problems.join('\n'), /RELEASE_NOTES\.md: is not the notes this manifest gives/);
  const edit = async (change, re) => {
    const m = JSON.parse(outputs[OUTPUTS.manifest]);
    change(m);
    const files = resum({ ...outputs, [OUTPUTS.manifest]: `${stableJson(m)}\n`, [OUTPUTS.notes]: releaseNotes(m) });
    assert.match((await verifyRelease(files)).problems.join('\n'), re);
  };
  await edit((m) => { m.terms_hashes['base.none.P2P.EW.business'] = `sha256:${'1'.repeat(64)}`; }, /terms hashes are not the ones the bundle computes/);
  await edit((m) => { m.terms_hashes.extra = 'nope'; }, /terms_hashes\.extra is not a sha256: hash/);
  await edit((m) => { m.sources[0].file_sha256 = '2'.repeat(64); }, /different source files/);
  await edit((m) => { m.schemas.pop(); }, /different schema files/);
  await edit((m) => { m.notice = 'Final.'; }, /different notices/);
  const dup = `${outputs[OUTPUTS.sums]}${outputs[OUTPUTS.sums].split('\n')[0]}\n`;
  assert.match((await verifyRelease({ ...outputs, [OUTPUTS.sums]: dup })).problems.join('\n'), /lists .* twice/);
});

test('SHA256SUMS must list exactly the three files; a missing file is reported', async () => {
  const extra = `${outputs[OUTPUTS.sums]}${'0'.repeat(64)}  extra.js\n`;
  assert.match((await verifyRelease({ ...outputs, [OUTPUTS.sums]: extra })).problems.join('\n'), /must list exactly/);
  const short = outputs[OUTPUTS.sums].split('\n').slice(1).join('\n');
  assert.match((await verifyRelease({ ...outputs, [OUTPUTS.sums]: short })).problems.join('\n'), /must list exactly/);
  const { [OUTPUTS.notes]: _, ...missing } = outputs; // eslint-disable-line no-unused-vars
  assert.deepEqual((await verifyRelease(missing)).problems, ['RELEASE_NOTES.md: missing']);
  assert.match((await verifyRelease({ ...outputs, [OUTPUTS.bundle]: 'export const x = ;' })).problems.join('\n'), /does not load/);
});

test('runtime on its own: tampered file text, a wrong key or version, a tampered schema', () => {
  const B = { sha256Hex, templateHash: (v) => `h:${v.key ?? v.role_key}`, assertBase: (v) => v, assertModule: (v) => v, SCHEMA_IDS: { base: 'b', module: 'm' } };
  const text = '{"schema":"b","key":"P2P","version":1}';
  const file = { path: 'templates/bases/p2p.json', kind: 'base', key: 'P2P', version: 1, sha256: 'h:P2P', file_sha256: sha256Hex(text), text };
  const data = (f) => ({ release: { tag: null, commit: 'c' }, files: [f] });
  assert.equal(makeRelease(data(file), B).getBase('P2P').key, 'P2P');
  assert.throws(() => makeRelease(data({ ...file, text: text.replace('1', '2') }), B).getBase('P2P'), ReleaseError);
  assert.match(makeRelease(data({ ...file, version: 2 }), B).verifyRelease().problems.join(), /version 1, the release lists 2/);
  assert.match(makeRelease(data({ ...file, key: 'B2P' }), B).verifyRelease().problems.join(), /holds P2P, the release lists B2P/);
  assert.match(makeRelease(data({ ...file, sha256: 'h:other' }), B).verifyRelease().problems.join(), /template hash does not match/);
  assert.match(makeRelease({ release: {}, files: [file, { ...file }] }, B).verifyRelease().problems.join(), /listed twice/);
  assert.match(makeRelease({ release: {}, files: [file, { ...file, path: 'templates/bases/p2p-copy.json' }] }, B).verifyRelease().problems.join(), /two base files share a key/);
  const wrongSchema = '{"schema":"m","key":"P2P","version":1}';
  assert.match(makeRelease(data({ ...file, text: wrongSchema, file_sha256: sha256Hex(wrongSchema) }), B).verifyRelease().problems.join(), /schema m, expected b/);
  const schema = { path: 'schema/agreement.v1.json', kind: 'schema', file_sha256: sha256Hex('{}'), text: '{"x":1}' };
  assert.throws(() => makeSchemaLoader([schema], sha256Hex)('agreement'), /whole-file sha256/);
  assert.throws(() => makeSchemaLoader([schema], sha256Hex)('nope'), /not in this release/);
  assert.deepEqual(makeSchemaLoader([{ ...schema, text: '{}' }], sha256Hex)('agreement'), {});
});
