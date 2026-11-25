// The Inspector: a plain script, no LLM. The run fetches SnapLink's role registry
// (`base44/shared/taxonomy/registry.js`) read-only; this module parses that text WITHOUT running
// it, checks the result against schema/inspector-snapshot.v1.json and hashes it in the adapter's
// canonical encoding. No LLM ever reads the raw app text; it gets the snapshot as data.
//
// The parser accepts only the literal shapes the registry uses today (quoted strings and arrays
// of quoted strings inside `role(...)`, `sector(...)` calls). Anything else is refused, so a
// change to the registry's shape stops the Brain instead of being half-read.
import fs from 'node:fs';
import { digest, sha256 } from '../../adapter/src/canon.js';
import { validate } from './jsonschema.js';

export const SNAPSHOT_SCHEMA = 'odir-inspector-snapshot/1';
export const REGISTRY_HASH_SCHEMA = 'odir-role-registry/1';
export const REGISTRY_PATH = 'base44/shared/taxonomy/registry.js';
const KEY = /^[a-z][a-z0-9_]{1,59}$/;
const ROLE_FACTORY = 'const role = (key, label, legacyGroup, family, sectors, synonyms = []) =>';
const SECTOR_FACTORY = 'const sector = (key, label) =>';

export class InspectorError extends Error {}

export const snapshotSchema = JSON.parse(fs.readFileSync(new URL('../../schema/inspector-snapshot.v1.json', import.meta.url), 'utf8'));

function skip(src, i) {
  for (;;) {
    while (i < src.length && /\s/.test(src[i])) i++;
    if (src.startsWith('//', i)) { const e = src.indexOf('\n', i); i = e < 0 ? src.length : e + 1; continue; }
    if (src.startsWith('/*', i)) { const e = src.indexOf('*/', i + 2); if (e < 0) throw new InspectorError('unclosed comment'); i = e + 2; continue; }
    return i;
  }
}

function parseString(src, i) {
  const q = src[i];
  let out = '';
  for (i++; i < src.length; i++) {
    const c = src[i];
    if (c === q) return { value: out, end: i + 1 };
    if (c === '\n') break;
    if (c === '\\') {
      const n = src[++i];
      const simple = { n: '\n', t: '\t', r: '\r', '\\': '\\', "'": "'", '"': '"' };
      if (n in simple) out += simple[n];
      else if (n === 'u' && /^[0-9a-fA-F]{4}$/.test(src.slice(i + 1, i + 5))) { out += String.fromCharCode(parseInt(src.slice(i + 1, i + 5), 16)); i += 4; }
      else throw new InspectorError(`unsupported escape \\${n}`);
      continue;
    }
    out += c;
  }
  throw new InspectorError('unterminated string');
}

function parseValue(src, i) {
  i = skip(src, i);
  const c = src[i];
  if (c === "'" || c === '"') return parseString(src, i);
  if (c === '[') {
    const items = [];
    i = skip(src, i + 1);
    while (src[i] !== ']') {
      const v = parseValue(src, i);
      items.push(v.value);
      i = skip(src, v.end);
      if (src[i] === ',') i = skip(src, i + 1);
      else if (src[i] !== ']') throw new InspectorError(`expected , or ] at ${i}`);
    }
    return { value: items, end: i + 1 };
  }
  throw new InspectorError(`unsupported literal at offset ${i} (${JSON.stringify(src.slice(i, i + 20))})`);
}

// Parse `name(<literal>, ...)` calls inside an exported frozen list: `export const X = freezeAll([ ... ]);`
function parseCallList(src, exportName, fn) {
  const open = `export const ${exportName} = freezeAll([`;
  const start = src.indexOf(open);
  if (start < 0 || src.indexOf(open, start + 1) >= 0) throw new InspectorError(`expected exactly one "${open}"`);
  let i = start + open.length;
  const calls = [];
  for (;;) {
    i = skip(src, i);
    if (src.startsWith(']);', i)) return calls;
    if (!src.startsWith(`${fn}(`, i)) throw new InspectorError(`${exportName}: expected ${fn}( at offset ${i}`);
    i += fn.length + 1;
    const args = [];
    i = skip(src, i);
    while (src[i] !== ')') {
      const v = parseValue(src, i);
      args.push(v.value);
      i = skip(src, v.end);
      if (src[i] === ',') i = skip(src, i + 1);
      else if (src[i] !== ')') throw new InspectorError(`${exportName}: expected , or ) at offset ${i}`);
    }
    calls.push(args);
    i = skip(src, i + 1);
    if (src[i] === ',') i++;
    else if (!src.startsWith(']);', i)) throw new InspectorError(`${exportName}: expected , or ]); at offset ${i}`);
  }
}

function parseFrozenStringArray(src, exportName) {
  const open = `export const ${exportName} = Object.freeze(`;
  const start = src.indexOf(open);
  if (start < 0) throw new InspectorError(`missing ${exportName}`);
  const v = parseValue(src, start + open.length);
  if (!Array.isArray(v.value) || !v.value.every((x) => typeof x === 'string')) throw new InspectorError(`${exportName} must be a string array`);
  if (!src.startsWith(');', skip(src, v.end))) throw new InspectorError(`${exportName}: expected );`);
  return v.value;
}

const isStr = (x) => typeof x === 'string' && x.length > 0;
const isStrArr = (x) => Array.isArray(x) && x.every((y) => typeof y === 'string');

export function registryHash(roles, taxonomyRevision) {
  return digest({ schema: REGISTRY_HASH_SCHEMA, taxonomy_revision: taxonomyRevision, roles });
}

export function snapshotHash(snapshot) {
  const { snapshot_sha256: _omit, ...rest } = snapshot;
  return digest(rest);
}

export function inspectRegistry(text, { appId, ref, path = REGISTRY_PATH }) {
  if (typeof text !== 'string' || !text.length) throw new InspectorError('registry text missing');
  if (!text.includes(ROLE_FACTORY)) throw new InspectorError('role() factory signature changed; refusing to guess the argument order');
  if (!text.includes(SECTOR_FACTORY)) throw new InspectorError('sector() factory signature changed');
  const rev = /export const TAXONOMY_REVISION = (\d+);/.exec(text);
  if (!rev) throw new InspectorError('missing TAXONOMY_REVISION');
  const families = parseFrozenStringArray(text, 'ROLE_FAMILIES');
  const sectors = parseCallList(text, 'SECTORS', 'sector').map((a) => {
    if (a.length !== 2 || !a.every(isStr)) throw new InspectorError(`sector(): expected (key, label), got ${JSON.stringify(a)}`);
    return { key: a[0], label: a[1] };
  });
  const sectorKeys = new Set(sectors.map((s) => s.key));
  const seen = new Set();
  const roles = parseCallList(text, 'ROLES', 'role').map((a) => {
    if (a.length < 5 || a.length > 6) throw new InspectorError(`role(): expected 5 or 6 arguments, got ${a.length}`);
    const [key, label, legacyGroup, family, secs, synonyms = []] = a;
    if (![key, label, legacyGroup, family].every(isStr) || !isStrArr(secs) || !isStrArr(synonyms)) throw new InspectorError(`role(${JSON.stringify(key)}): wrong argument types`);
    if (!KEY.test(key)) throw new InspectorError(`role key ${JSON.stringify(key)} breaks the key pattern`);
    if (seen.has(key)) throw new InspectorError(`duplicate role key ${key}`);
    seen.add(key);
    if (!families.includes(family)) throw new InspectorError(`role ${key}: unknown family ${family}`);
    for (const s of secs) if (!sectorKeys.has(s)) throw new InspectorError(`role ${key}: unknown sector ${s}`);
    return { key, label, family, sectors: secs };
  });
  if (!roles.length) throw new InspectorError('no roles');
  const taxonomyRevision = Number(rev[1]);
  const snapshot = {
    schema: SNAPSHOT_SCHEMA,
    source: { app_id: appId, ref, path, file_sha256: sha256(text) },
    taxonomy_revision: taxonomyRevision,
    families,
    sectors,
    roles,
    role_count: roles.length,
    registry_sha256: registryHash(roles, taxonomyRevision),
  };
  snapshot.snapshot_sha256 = snapshotHash(snapshot);
  const v = validate(snapshotSchema, snapshot);
  if (!v.ok) throw new InspectorError(`snapshot fails its schema: ${v.problems.join('; ')}`);
  return snapshot;
}

// Check a snapshot handed in as data (e.g. a file): schema, both hashes, role count.
export function verifySnapshot(snapshot) {
  const problems = [];
  const v = validate(snapshotSchema, snapshot);
  if (!v.ok) return { ok: false, problems: v.problems };
  if (snapshot.role_count !== snapshot.roles.length) problems.push('role_count does not match roles');
  if (registryHash(snapshot.roles, snapshot.taxonomy_revision) !== snapshot.registry_sha256) problems.push('registry_sha256 does not match roles');
  if (snapshotHash(snapshot) !== snapshot.snapshot_sha256) problems.push('snapshot_sha256 does not match the snapshot');
  return { ok: problems.length === 0, problems };
}
