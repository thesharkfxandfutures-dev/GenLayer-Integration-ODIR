// The assembler: imports become reads from bundled modules, exports are unwrapped, declared patches
// match exactly once, and anything that ties the bundle to Node stops the build.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { AssembleError, MODULES, PATCHES, assembleBundle, codeOf, stableJson, transformModule } from '../src/assemble.js';
import { ROOT } from './helpers.js';

const mod = (id) => MODULES.find((m) => m.id === id);
const run = (m, text) => { const problems = []; const r = transformModule(m, text, problems); return { ...r, problems }; };
const real = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

test('relative imports become reads from the bundled module; exports are unwrapped and listed', () => {
  const r = run(mod('hash'), real('resolver/src/hash.js'));
  assert.deepEqual(r.problems, []);
  assert.match(r.code, /^const \{ canonical, digest \} = __m_canon;$/m);
  assert.doesNotMatch(r.code, /^\s*(import|export)\b/m);
  assert.deepEqual(r.exported, ['HASH_PREFIX', 'overridesHash', 'templateContent', 'templateHash', 'termsCanonical', 'termsHash', 'termsInput']);
});

test('multi-line and renamed imports', () => {
  const r = run(mod('resolve'), "import {\n  A,\n  B as C,\n} from './categories.js';\nexport const x = 1;\n");
  assert.deepEqual(r.problems, []);
  assert.match(r.code, /^const \{ A, B: C \} = __m_categories;$/m);
  assert.deepEqual(r.exported, ['x']);
});

test('canon.js: node:crypto becomes the portable shim, nothing else changes', () => {
  const src = real('adapter/src/canon.js');
  const r = run(mod('canon'), src);
  assert.deepEqual(r.problems, []);
  assert.match(r.code, /^const crypto = __m_sha256\.cryptoShim;$/m);
  assert.equal(r.code, src.replace("import crypto from 'node:crypto';\n", 'const crypto = __m_sha256.cryptoShim;\n').replace(/^export (const|function|class) /gm, '$1 '));
  assert.deepEqual(r.exported, ['CanonError', 'canonical', 'digest', 'sha256']);
});

test('validate.js: the two declared patches apply once each; the rest is unchanged', () => {
  const src = real('resolver/src/validate.js');
  const r = run(mod('validate'), src);
  assert.deepEqual(r.problems, []);
  assert.match(r.code, /return __loadSchema\(name\);/);
  assert.doesNotMatch(r.code, /node:|import\.meta|readFileSync/);
  for (const p of PATCHES['resolver/src/validate.js']) assert.equal(src.split(p.find).length, 2);
});

test('a patch that no longer matches, or matches twice, stops the build', () => {
  const src = real('resolver/src/validate.js');
  assert.match(run(mod('validate'), src.replace("'node:url'", "'node:url' ")).problems.join('\n'), /matches 0 times/);
  const twice = src + PATCHES['resolver/src/validate.js'][1].find;
  assert.match(run(mod('validate'), twice).problems.join('\n'), /matches 2 times/);
});

test('Node-only constructs and unknown imports are refused', () => {
  const m = mod('render');
  const cases = [
    ["import fs from 'node:fs';\n", /imports node:fs/],
    ["import { x } from 'lodash';\n", /imports package lodash/],
    ["import x from './categories.js';\n", /\.\/categories\.js|default import/],
    ["import { x } from './nope.js';\n", /not a bundled module/],
    ['const p = process.env.X;\n', /process\.\*/],
    ['const b = Buffer.from("x");\n', /Buffer/],
    ['const r = require("x");\n', /require/],
    ['const u = import.meta.url;\n', /import\.meta/],
    ['const d = await import("./x.js");\n', /dynamic import/],
    ['export let n = 1;\n', /export form/],
    ['export default 1;\n', /export form/],
    ["export { a } from './x.js';\n", /export form/],
    ['const s = "a";\r\n', /carriage return/],
  ];
  for (const [text, re] of cases) assert.match(run(m, text).problems.join('\n'), re, text);
  assert.match(run(mod('hash'), "import { resolve } from './resolve.js';\n").problems.join('\n'), /comes later in MODULES/);
  assert.match(run(mod('canon'), "import { createHash } from 'node:crypto';\n").problems.join('\n'), /imports node:crypto, which the bundle cannot carry/);
});

test('comments may mention imports and Node; code may not', () => {
  assert.deepEqual(run(mod('render'), "// import x from 'node:fs'; process.env, Buffer, require()\nexport const ok = 1;\n").problems, []);
});

test('a missing source or a missing public export stops the build', () => {
  const sources = new Map(MODULES.map((m) => [m.path, real(m.path)]));
  const hashes = new Map(MODULES.map((m) => [m.path, '0'.repeat(64)]));
  const release = { schema: 'odir.template-release.v1', tag: null, commit: '0'.repeat(40), notice: 'n' };
  assert.ok(assembleBundle({ release, files: [], sources, sourceHashes: hashes }).length > 1000);
  const less = new Map(sources); less.delete('resolver/src/render.js');
  assert.throws(() => assembleBundle({ release, files: [], sources: less, sourceHashes: hashes }), (e) => e instanceof AssembleError && /render\.js: missing/.test(e.message));
  const noExport = new Map(sources); noExport.set('resolver/src/render.js', real('resolver/src/render.js').replace('export function toParchment', 'function toParchment'));
  assert.throws(() => assembleBundle({ release, files: [], sources: noExport, sourceHashes: hashes }), /public export toParchment is not exported by render/);
});

test('the same inputs give the same bytes; file order does not matter', () => {
  const sources = new Map(MODULES.map((m) => [m.path, real(m.path)]));
  const hashes = new Map(MODULES.map((m) => [m.path, '1'.repeat(64)]));
  const release = { schema: 'odir.template-release.v1', tag: 'templates-v1.0.0', commit: 'a'.repeat(40), notice: 'n' };
  const files = [{ path: 'b', kind: 'schema', key: null, version: null, sha256: null, file_sha256: 'x', text: 'B' }, { path: 'a', kind: 'schema', key: null, version: null, sha256: null, file_sha256: 'y', text: 'A' }];
  const one = assembleBundle({ release, files, sources, sourceHashes: hashes });
  const two = assembleBundle({ release, files: [...files].reverse(), sources: new Map([...sources].reverse()), sourceHashes: hashes });
  assert.equal(one, two);
  assert.ok(!codeOf(one).includes('"text"'));
});

test('stableJson sorts keys at every level', () => {
  assert.equal(stableJson({ b: 1, a: { d: [{ z: 1, y: 2 }], c: null } }), '{\n  "a": {\n    "c": null,\n    "d": [\n      {\n        "y": 2,\n        "z": 1\n      }\n    ]\n  },\n  "b": 1\n}');
});
