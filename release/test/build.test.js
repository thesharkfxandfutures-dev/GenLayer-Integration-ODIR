// Acceptance (plan A4): two runs on the same tag give byte-identical output. And the build reads
// only git objects at that commit, refuses a template that does not reproduce its golden terms
// hash, and refuses anything under templates/ that is not a template.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { validate } from '../../brain/src/jsonschema.js';
import { OUTPUTS, ReleaseBuildError } from '../src/build.js';
import { gitSource } from '../src/gitsource.js';
import { ROOT, build, commitChange, git, makeRepo, runNode, tag, tmp } from './helpers.js';

const TAG = 'templates-v0.1.0';
const refused = (re) => (e) => e instanceof ReleaseBuildError && re.test(e.message);

test('two runs on the same tag give byte-identical output (all four files)', async () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  const one = await build(dir, { tag: TAG });
  const two = await build(dir, { tag: TAG });
  assert.deepEqual(Object.keys(one.outputs).sort(), Object.values(OUTPUTS).sort());
  for (const name of Object.values(OUTPUTS)) assert.equal(one.outputs[name], two.outputs[name], name);
  assert.equal(one.manifest.tag, TAG);
});

test('a second, independent repository with the same commit gives the same bytes', async () => {
  const a = makeRepo();
  const b = makeRepo();
  assert.equal(a.commit, b.commit);
  tag(a.dir, TAG); tag(b.dir, TAG);
  const [x, y] = [await build(a.dir, { tag: TAG }), await build(b.dir, { tag: TAG })];
  for (const name of Object.values(OUTPUTS)) assert.equal(x.outputs[name], y.outputs[name], name);
});

test('the build reads git objects, not the working tree: uncommitted edits change nothing', async () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  const before = await build(dir, { tag: TAG });
  fs.writeFileSync(path.join(dir, 'templates/bases/p2p.json'), fs.readFileSync(path.join(dir, 'templates/bases/p2p.json'), 'utf8').replace('Person to person', 'Edited on disk'));
  fs.writeFileSync(path.join(dir, 'templates/bases/stray.txt'), 'not committed');
  const after = await build(dir, { tag: TAG });
  for (const name of Object.values(OUTPUTS)) assert.equal(after.outputs[name], before.outputs[name], name);
});

test('the bundle carries every template byte for byte, with the hashes the A3 resolver gives', async () => {
  const { dir, commit } = makeRepo();
  const { outputs, manifest } = await build(dir, { ref: 'HEAD' });
  assert.equal(manifest.commit, commit);
  assert.equal(manifest.tag, null);
  const { loadTemplates } = await import('../../resolver/src/load.js');
  const { templateHash } = await import('../../resolver/src/hash.js');
  const { bases, modules } = loadTemplates(ROOT);
  assert.equal(manifest.templates.length, bases.size + modules.size);
  for (const t of manifest.templates) {
    const value = t.kind === 'base' ? bases.get(t.key) : modules.get(t.key);
    assert.equal(t.sha256, templateHash(value), t.path);
    assert.equal(t.version, value.version);
  }
  const golden = JSON.parse(fs.readFileSync(path.join(ROOT, 'resolver/test/golden/hashes.json'), 'utf8'));
  assert.deepEqual(manifest.terms_hashes, golden);
  assert.ok(outputs[OUTPUTS.bundle].startsWith('// odir-templates.mjs — GENERATED'));
});

test('the manifest is odir.template-release.v1 and SHA256SUMS lists the other three files', async () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  const { outputs, manifest } = await build(dir, { tag: TAG });
  const schema = JSON.parse(fs.readFileSync(path.join(ROOT, 'schema/template-release.v1.json'), 'utf8'));
  assert.deepEqual(validate(schema, manifest).problems, []);
  assert.deepEqual(validate(schema, { ...manifest, extra: 1 }).ok, false);
  assert.deepEqual(validate(schema, { ...manifest, tag: 'v1' }).ok, false);
  for (const h of Object.values(manifest.terms_hashes)) assert.match(h, /^sha256:[0-9a-f]{64}$/);
  const lines = outputs[OUTPUTS.sums].trimEnd().split('\n');
  assert.deepEqual(lines.map((l) => l.split('  ')[1]), [OUTPUTS.notes, OUTPUTS.manifest, OUTPUTS.bundle].sort());
  assert.match(outputs[OUTPUTS.notes], new RegExp(`--rebuild --tag ${TAG}`));
  assert.match(outputs[OUTPUTS.notes], /not legal advice/);
});

test('one changed word in a committed template, without its golden diff, is refused', async () => {
  const { dir } = makeRepo();
  commitChange(dir, 'templates/bases/p2p.json', (t) => t.replace(/("text": "[^"]*?)\bthe\b/, '$1a'), 'edit a clause');
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/differs from the golden .* a template changed without its golden diff/));
});

test('a golden file that lists a combination these templates do not make is refused', async () => {
  const { dir } = makeRepo();
  commitChange(dir, 'resolver/test/golden/hashes.json', (t) => {
    const g = JSON.parse(t);
    g['drone_pilot.provider.P2P.EW.business'] = `sha256:${'0'.repeat(64)}`;
    return `${JSON.stringify(g, null, 2)}\n`;
  }, 'extra golden');
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/drone_pilot\.provider\.P2P\.EW\.business: in the golden file but not a combination/));
});

test('a style-only change keeps every template hash and golden, but changes the whole-file sha256 and the bundle', async () => {
  const { dir } = makeRepo();
  const before = await build(dir, { ref: 'HEAD' });
  commitChange(dir, 'templates/bases/b2p.json', (t) => { const v = JSON.parse(t); v.style = { ...(v.style || {}), ink: v.style?.ink === 'navy' ? 'sepia' : 'navy' }; return `${JSON.stringify(v, null, 2)}\n`; }, 'restyle');
  const after = await build(dir, { ref: 'HEAD' });
  const pick = (m) => m.templates.find((t) => t.key === 'B2P');
  assert.equal(pick(after.manifest).sha256, pick(before.manifest).sha256);
  assert.notEqual(pick(after.manifest).file_sha256, pick(before.manifest).file_sha256);
  assert.deepEqual(after.manifest.terms_hashes, before.manifest.terms_hashes);
  assert.notEqual(after.manifest.bundle.sha256, before.manifest.bundle.sha256);
});

test('anything under templates/ that is not a template is refused; so are CRLF line endings', async () => {
  const { dir } = makeRepo();
  fs.writeFileSync(path.join(dir, 'templates/bases/notes.md'), 'x\n');
  git(dir, ['add', '-A']); git(dir, ['commit', '-q', '-m', 'stray']);
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/templates\/bases\/notes\.md: not a template file/));

  const crlf = makeRepo();
  fs.writeFileSync(path.join(crlf.dir, '.gitattributes'), '* -text\n');
  commitChange(crlf.dir, 'templates/bases/b2p.json', (t) => t.replace(/\n/g, '\r\n'), 'crlf');
  await assert.rejects(build(crlf.dir, { ref: 'HEAD' }), refused(/b2p\.json: has a carriage return/));
});

test('a template whose key does not match its file name is refused', async () => {
  const { dir } = makeRepo();
  git(dir, ['mv', 'templates/bases/b2p.json', 'templates/bases/b2b.json']);
  git(dir, ['commit', '-q', '-m', 'misnamed']);
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/b2b\.json: holds "B2P", which does not match its file name/));
});

test('a bundled source that drifts from a declared patch stops the build (built from its own checkout)', () => {
  const { dir } = makeRepo();
  commitChange(dir, 'resolver/src/validate.js', (t) => t.replace("const cache = new Map();", "const cache = new Map(); // drift"), 'drift');
  const r = runNode([path.join(dir, 'release/bin/build-release.mjs'), '--ref', 'HEAD', '--out', tmp('odir-out-'), '--root', dir]);
  assert.equal(r.code, 1);
  assert.match(r.stdout, /REFUSED[\s\S]*validate\.js: release patch matches 0 times/);
});

test('the build tooling must be the commit\'s own: other tooling is refused; the commit\'s own checkout builds', async () => {
  const { dir } = makeRepo();
  commitChange(dir, 'release/src/assemble.js', (t) => t.replace('// rebuild from the tag instead.', '// rebuild from the tag instead (changed).'), 'tooling change');
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/build tooling is not the tooling of the commit[\s\S]*release\/src\/assemble\.js: the checkout running the build differs/));
  const out = tmp('odir-out-');
  const r = runNode([path.join(dir, 'release/bin/build-release.mjs'), '--ref', 'HEAD', '--out', out, '--root', dir]);
  assert.equal(r.code, 0, r.stdout);
  assert.match(fs.readFileSync(path.join(out, OUTPUTS.bundle), 'utf8'), /rebuild from the tag instead \(changed\)/);
  const old = makeRepo();
  git(old.dir, ['rm', '-q', 'release/src/verify.js']); git(old.dir, ['commit', '-q', '-m', 'no tooling']);
  await assert.rejects(build(old.dir, { ref: 'HEAD' }), refused(/release\/src\/verify\.js: not in commit .* has no release tooling/));
});

test('git replace refs cannot change what a commit reads: the bytes stay the same', async () => {
  const { dir } = makeRepo();
  const before = await build(dir, { ref: 'HEAD' });
  const blob = git(dir, ['rev-parse', 'HEAD:templates/bases/b2p.json']).toString().trim();
  const forged = path.join(tmp('odir-forge-'), 'b2p.json');
  const v = JSON.parse(fs.readFileSync(path.join(dir, 'templates/bases/b2p.json'), 'utf8'));
  v.style = { ...v.style, ink: v.style.ink === 'navy' ? 'sepia' : 'navy' };
  fs.writeFileSync(forged, `${JSON.stringify(v, null, 2)}\n`);
  const other = git(dir, ['hash-object', '-w', forged]).toString().trim();
  git(dir, ['replace', blob, other]);
  assert.notEqual(git(dir, ['cat-file', 'blob', 'HEAD:templates/bases/b2p.json']).toString(), fs.readFileSync(path.join(dir, 'templates/bases/b2p.json'), 'utf8'));
  const after = await build(dir, { ref: 'HEAD' });
  for (const name of Object.values(OUTPUTS)) assert.equal(after.outputs[name], before.outputs[name], name);
});

test('a tag on an older commit builds that commit\'s own templates', async () => {
  const { dir } = makeRepo();
  const atTag = await build(dir, { ref: 'HEAD' });
  tag(dir, TAG);
  commitChange(dir, 'templates/bases/b2p.json', (t) => { const v = JSON.parse(t); v.style = { ...v.style, ink: v.style.ink === 'navy' ? 'sepia' : 'navy' }; return `${JSON.stringify(v, null, 2)}\n`; }, 'restyle later');
  const tagged = await build(dir, { tag: TAG });
  const b2p = (m) => m.templates.find((t) => t.key === 'B2P').file_sha256;
  assert.equal(tagged.manifest.commit, atTag.manifest.commit);
  assert.equal(b2p(tagged.manifest), b2p(atTag.manifest));
  assert.notEqual(b2p((await build(dir, { ref: 'HEAD' })).manifest), b2p(atTag.manifest));
});

test('invalid UTF-8 in a template is refused, not replaced', async () => {
  const { dir } = makeRepo();
  const p = path.join(dir, 'templates/bases/b2p.json');
  const buf = fs.readFileSync(p);
  const at = buf.indexOf(Buffer.from('"title"'));
  fs.writeFileSync(p, Buffer.concat([buf.subarray(0, at + 10), Buffer.from([0xff, 0xfe]), buf.subarray(at + 10)]));
  git(dir, ['add', '-A']); git(dir, ['commit', '-q', '-m', 'bad bytes']);
  await assert.rejects(build(dir, { ref: 'HEAD' }), /b2p\.json: not valid UTF-8/);
});

test('a golden file missing a combination is refused; so is a module whose base is not in the release', async () => {
  const { dir } = makeRepo();
  commitChange(dir, 'resolver/test/golden/hashes.json', (t) => {
    const g = JSON.parse(t);
    delete g['photographer.provider.B2P.SC.business'];
    return `${JSON.stringify(g, null, 2)}\n`;
  }, 'golden missing one');
  await assert.rejects(build(dir, { ref: 'HEAD' }), refused(/photographer\.provider\.B2P\.SC\.business: no golden terms hash at this commit/));
  const skip = makeRepo();
  git(skip.dir, ['rm', '-q', 'templates/bases/b2p.json']); git(skip.dir, ['commit', '-q', '-m', 'no B2P']);
  await assert.rejects(build(skip.dir, { ref: 'HEAD' }), refused(/photographer\.provider\.B2P: base not present/));
});

test('tags: the name must be templates-vX.Y.Z and must point at the ref; no tag and no ref is refused', () => {
  const { dir } = makeRepo();
  tag(dir, TAG);
  commitChange(dir, 'README.md', (t) => `${t}\n`, 'later');
  assert.throws(() => gitSource(dir, { tag: 'v1.0.0' }), /must look like templates-v1\.2\.3/);
  assert.throws(() => gitSource(dir, { tag: 'templates-v01.0.0' }), /must look like/);
  assert.throws(() => gitSource(dir, { tag: 'templates-v9.9.9' }), /no commit for/);
  assert.throws(() => gitSource(dir, { tag: TAG, ref: 'HEAD' }), /points at .*, not /);
  assert.throws(() => gitSource(dir, {}), /give a tag/);
  assert.throws(() => gitSource(dir, { ref: '--output=x' }), /no commit for/);
  assert.throws(() => gitSource(dir, { ref: '-n1' }), /no commit for/);
  assert.equal(gitSource(dir, { tag: TAG, ref: 'HEAD~1' }).tag, TAG);
});
