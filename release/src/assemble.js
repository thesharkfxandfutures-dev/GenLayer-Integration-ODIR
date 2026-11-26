// Assembles the release bundle (slice A4): the template and schema files, the resolver and hash
// code, and the release API, as ONE ES module with no imports — the file SnapLink imports in D1.
//
// Plain text work only (no file system, no clock), so the same inputs always give the same bytes.
// Each source file is carried unchanged except for:
//   - its `import … from '<relative path>'` lines, which become reads from the bundled module;
//   - `export ` in front of its top-level declarations, which is dropped (the module is wrapped);
//   - the declared PATCHES below, each of which must match the source exactly once, so a change
//     to the source stops the build instead of being patched by guesswork.
// Anything else that ties a file to Node (another node: import, import.meta, require, process,
// Buffer) stops the build.

export class AssembleError extends Error {
  constructor(message, problems = []) {
    super(problems.length ? `${message}:\n  - ${problems.join('\n  - ')}` : message);
    this.problems = problems;
  }
}

// Dependencies first. `node` maps a node: import to a bundled module's export.
export const MODULES = Object.freeze([
  { id: 'sha256', path: 'release/src/sha256.js' },
  { id: 'runtime', path: 'release/src/runtime.js' },
  { id: 'canon', path: 'adapter/src/canon.js', node: { 'node:crypto': { module: 'sha256', name: 'cryptoShim' } } },
  { id: 'jsonschema', path: 'brain/src/jsonschema.js' },
  { id: 'categories', path: 'resolver/src/categories.js' },
  { id: 'validate', path: 'resolver/src/validate.js' },
  { id: 'hash', path: 'resolver/src/hash.js' },
  { id: 'resolve', path: 'resolver/src/resolve.js' },
  { id: 'render', path: 'resolver/src/render.js' },
].map(Object.freeze));

// The schema files the resolver reads (validate.js loadSchema), embedded in the bundle.
export const SCHEMA_FILES = Object.freeze(['schema/agreement.v1.json', 'schema/base-template.v1.json', 'schema/role-template.v1.json']);

// validate.js reads schema/ from disk; in the bundle it reads the embedded, hash-checked copies.
export const PATCHES = Object.freeze({
  'resolver/src/validate.js': Object.freeze([
    {
      find: "import fs from 'node:fs';\nimport path from 'node:path';\nimport { fileURLToPath } from 'node:url';\n",
      replace: '',
    },
    {
      find: "const SCHEMA_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'schema');\nconst cache = new Map();\nexport function loadSchema(name) {\n  if (!cache.has(name)) cache.set(name, JSON.parse(fs.readFileSync(path.join(SCHEMA_DIR, `${name}.v1.json`), 'utf8')));\n  return cache.get(name);\n}\n",
      replace: '// Release bundle: the schema files are embedded and checked against their whole-file sha256\n// before first use (release/src/runtime.js makeSchemaLoader).\nexport function loadSchema(name) {\n  return __loadSchema(name);\n}\n',
    },
  ].map(Object.freeze)),
});

// What the bundle exports, by bundled module. The release API comes from makeRelease.
export const PUBLIC = Object.freeze({
  canon: ['CanonError', 'canonical', 'digest', 'sha256'],
  categories: ['ACCEPTANCE_CATEGORIES', 'BASES', 'CATEGORIES', 'CATEGORY_KEYS', 'CHECKABLE_MAX', 'CHECKABLE_MIN', 'FAMILIES', 'FIELD_TYPES', 'JURISDICTIONS', 'PAY_TYPES', 'SCHEMA_IDS', 'SECTIONS', 'SLOTS'],
  validate: ['TemplateError', 'agreementProblems', 'assertBase', 'assertModule', 'formatProblem'],
  hash: ['HASH_PREFIX', 'overridesHash', 'templateContent', 'templateHash', 'termsCanonical', 'termsHash', 'termsInput'],
  resolve: ['ResolveError', 'resolve'],
  render: ['renderMarkdown', 'toParchment'],
  runtime: ['ReleaseError'],
});
export const RELEASE_API = Object.freeze(['getBase', 'getModule', 'listSchemas', 'listTemplates', 'templateText', 'verifyRelease']);

const IDENT = /^[A-Za-z_$][\w$]*$/;
const IMPORT = /^import\s+(?:([A-Za-z_$][\w$]*)|\{([^}]*)\})\s+from\s+'([^']+)';[ \t]*\n/gm;
const EXPORT = /^export (const|function|class) ([A-Za-z_$][\w$]*)/gm;

const dirname = (p) => p.split('/').slice(0, -1).join('/');
function joinPath(dir, rel) {
  const out = dir ? dir.split('/') : [];
  for (const part of rel.split('/')) {
    if (part === '.' || part === '') continue;
    if (part === '..') { if (!out.length) return null; out.pop(); } else out.push(part);
  }
  return out.join('/');
}
const countOf = (text, find) => text.split(find).length - 1;

// Lines of code with // comments and string/regex contents ignored is more than this needs: the
// checks below look for Node-only constructs on non-comment lines, which is where they would be.
const codeLines = (code) => code.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l));
const FORBIDDEN = [
  [/^\s*import\b/, 'an import statement remains'],
  [/\bimport\s*\(/, 'a dynamic import'],
  [/\bimport\.meta\b/, 'import.meta'],
  [/\brequire\s*\(/, 'require()'],
  [/\bprocess\./, 'process.*'],
  [/\bBuffer\b/, 'Buffer'],
  [/['"]node:/, 'a node: module'],
  [/^\s*export\b/, 'an export form the assembler does not handle'],
];

// One source file → the body of its module wrapper and its exported names.
export function transformModule(mod, text, problems) {
  let code = text;
  if (code.includes('\r')) problems.push(`${mod.path}: has a carriage return (LF line endings only)`);
  for (const p of PATCHES[mod.path] || []) {
    const n = countOf(code, p.find);
    if (n !== 1) { problems.push(`${mod.path}: release patch matches ${n} times, expected once — the source changed; update release/src/assemble.js PATCHES`); continue; }
    code = code.replace(p.find, () => p.replace);
  }
  const deps = [];
  code = code.replace(IMPORT, (m, def, named, spec) => {
    if (spec.startsWith('node:')) {
      const map = mod.node?.[spec];
      if (!map || !def) { problems.push(`${mod.path}: imports ${spec}, which the bundle cannot carry`); return m; }
      deps.push(map.module);
      return `const ${def} = __m_${map.module}.${map.name};\n`;
    }
    if (!spec.startsWith('.')) { problems.push(`${mod.path}: imports package ${spec}; the bundle has no dependencies`); return m; }
    const target = joinPath(dirname(mod.path), spec);
    const dep = MODULES.find((x) => x.path === target);
    if (!dep) { problems.push(`${mod.path}: imports ${spec} (${target}), which is not a bundled module`); return m; }
    if (def) { problems.push(`${mod.path}: default import of ${spec}; bundled modules have named exports only`); return m; }
    const names = named.split(',').map((s) => s.trim()).filter(Boolean).map((s) => {
      const [from, as] = s.split(/\s+as\s+/);
      if (!IDENT.test(from) || (as !== undefined && !IDENT.test(as))) problems.push(`${mod.path}: cannot read import ${s}`);
      return as ? `${from}: ${as}` : from;
    });
    deps.push(dep.id);
    return `const { ${names.join(', ')} } = __m_${dep.id};\n`;
  });
  const exported = [];
  code = code.replace(EXPORT, (m, kind, name) => { exported.push(name); return `${kind} ${name}`; });
  for (const line of codeLines(code)) {
    for (const [re, what] of FORBIDDEN) if (re.test(line)) problems.push(`${mod.path}: ${what}: ${line.trim().slice(0, 100)}`);
  }
  const order = MODULES.findIndex((x) => x.id === mod.id);
  for (const d of deps) if (MODULES.findIndex((x) => x.id === d) >= order) problems.push(`${mod.path}: depends on ${d}, which comes later in MODULES`);
  return { code, exported: exported.sort() };
}

// Stable JSON: keys sorted at every level, two-space indent.
export function stableJson(value) {
  const sort = (v) => (Array.isArray(v) ? v.map(sort)
    : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, sort(v[k])])) : v);
  return JSON.stringify(sort(value), null, 2);
}

export const DATA_START = '// ── data (generated; every file is checked against its sha256 before use) ──';
export const DATA_END = '// ── end of data ──';

/**
 * assembleBundle({ release, files, sources, sourceHashes })
 *   release:  { schema, tag, commit, notice, sources: [{ path, file_sha256 }] }
 *   files:    [{ path, kind: 'base'|'module'|'schema', key, version, sha256, file_sha256, text }]
 *   sources:  Map path → text for every MODULES path
 *   sourceHashes: Map path → whole-file sha256 (hex)
 * → the bundle text. Throws AssembleError.
 */
export function assembleBundle({ release, files, sources, sourceHashes }) {
  const problems = [];
  const parts = [];
  const exportsOf = new Map();
  for (const mod of MODULES) {
    const text = sources.get(mod.path);
    if (typeof text !== 'string') { problems.push(`${mod.path}: missing`); continue; }
    const { code, exported } = transformModule(mod, text, problems);
    exportsOf.set(mod.id, exported);
    parts.push([
      `// ── ${mod.path} · sha256 ${sourceHashes.get(mod.path)} ──`,
      `const __m_${mod.id} = (() => {`,
      code.replace(/\n+$/, ''),
      `return Object.freeze({ ${exported.join(', ')} });`,
      '})();',
      ...(mod.id === 'runtime' ? ['const __loadSchema = __m_runtime.makeSchemaLoader(__DATA.files, __m_sha256.sha256Hex);'] : []),
      '',
    ].join('\n'));
  }
  for (const [id, names] of Object.entries(PUBLIC)) {
    for (const n of names) if (!(exportsOf.get(id) || []).includes(n)) problems.push(`public export ${n} is not exported by ${id}`);
  }
  if (problems.length) throw new AssembleError('cannot assemble the release bundle', problems);

  const sorted = [...files].sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  const data = { release, files: sorted.map(({ path, kind, key, version, sha256, file_sha256, text }) => ({ path, kind, key, version, sha256, file_sha256, text })) };
  const label = release.tag ?? `untagged build of ${release.commit}`;
  const header = [
    '// odir-templates.mjs — GENERATED by release/bin/build-release.mjs (ODIR slice A4). Do not edit by hand:',
    '// rebuild from the tag instead. The build is reproducible: the same tag gives these exact bytes.',
    `// Release: ${label}`,
    `// Commit:  ${release.commit}`,
    '//',
    '// Role-contract templates, their hashes, and the resolver and hash code as one ES module with no',
    '// imports. Drafts, not legal advice: a UK solicitor reviews the templates before any real member signs.',
    '//',
    '// Exports: RELEASE, getBase, getModule, listTemplates, listSchemas, templateText, verifyRelease, resolve, the hash',
    '// functions (templateHash, termsHash, …), toParchment, renderMarkdown and the fixed vocabulary.',
    '// getBase / getModule refuse a template whose whole-file sha256 or template hash does not match.',
    '',
  ].join('\n');
  const dataBlock = [DATA_START, `const __DATA = ${stableJson(data)};`, DATA_END, ''].join('\n');
  const tail = [
    '// ── release API and exports ──',
    'const __release = __m_runtime.makeRelease(__DATA, {',
    '  sha256Hex: __m_sha256.sha256Hex, templateHash: __m_hash.templateHash,',
    '  assertBase: __m_validate.assertBase, assertModule: __m_validate.assertModule, SCHEMA_IDS: __m_categories.SCHEMA_IDS,',
    '});',
    'export const RELEASE = __release.RELEASE;',
    `export const { ${RELEASE_API.join(', ')} } = __release;`,
    ...Object.entries(PUBLIC).map(([id, names]) => `export const { ${names.join(', ')} } = __m_${id};`),
    '',
  ].join('\n');
  return [header, dataBlock, ...parts, tail].join('\n');
}

// The bundle without its data block, for checks on the code alone.
export function codeOf(bundle) {
  const a = bundle.indexOf(DATA_START);
  const b = bundle.indexOf(DATA_END);
  return a >= 0 && b > a ? bundle.slice(0, a) + bundle.slice(b + DATA_END.length) : bundle;
}
