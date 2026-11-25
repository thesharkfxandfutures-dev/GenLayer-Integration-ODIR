// Template checks: the JSON schema (through the Brain's subset validator, which refuses any keyword
// it does not enforce) and then the rules a schema cannot say — id prefixes, unique keys, category
// coverage, checkable-duty counts, well-formed blanks and terms, base kinds.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validate as validateSchema } from '../../brain/src/jsonschema.js';
import {
  ACCEPTANCE_CATEGORIES, BASES, CATEGORY_KEYS, CHECKABLE_MAX, CHECKABLE_MIN, SCHEMA_IDS, SLOTS,
} from './categories.js';

const SCHEMA_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'schema');
const cache = new Map();
export function loadSchema(name) {
  if (!cache.has(name)) cache.set(name, JSON.parse(fs.readFileSync(path.join(SCHEMA_DIR, `${name}.v1.json`), 'utf8')));
  return cache.get(name);
}

export class TemplateError extends Error {
  constructor(message, problems = []) {
    super(problems.length ? `${message}:\n  - ${problems.join('\n  - ')}` : message);
    this.problems = problems;
  }
}

export const PLACEHOLDER = /\{\{([a-z][a-z0-9_]{0,63})\}\}/g;
export const TERMS = Object.freeze(['engager', 'Engager', 'provider', 'Provider', 'jurisdiction', 'courts']);
const TERM = /\[\[([A-Za-z]+)\]\]/g;

// Problems with one clause text: stray or malformed {{ }} / [[ ]], unknown terms, untrimmed text.
export function lintText(text, at) {
  const out = [];
  if (typeof text !== 'string') return [`${at}: text must be a string`];
  if (text !== text.trim()) out.push(`${at}: leading or trailing whitespace`);
  if (/\s{2,}/.test(text)) out.push(`${at}: repeated whitespace`);
  const rest = text.replace(PLACEHOLDER, '').replace(TERM, (m, t) => {
    if (!TERMS.includes(t)) out.push(`${at}: unknown term [[${t}]]`);
    return '';
  });
  if (/\{\{|\}\}|\{|\}/.test(rest)) out.push(`${at}: malformed blank (only {{field_key}} in lower case)`);
  if (/\[\[|\]\]/.test(rest)) out.push(`${at}: malformed term (only [[engager]], [[Provider]], [[jurisdiction]], [[courts]] …)`);
  return out;
}

export const placeholdersIn = (text) => [...String(text).matchAll(PLACEHOLDER)].map((m) => m[1]);

function schemaProblems(name, value) {
  const { problems } = validateSchema(loadSchema(name), value);
  return problems;
}

function clauseProblems(clauses, { prefix, at, allowReplaces, allowCheckable, allowConsumerWhen, allowedBases, jurisdictions }) {
  const out = [];
  const ids = new Set();
  for (const [i, c] of clauses.entries()) {
    const where = `${at}.clauses[${i}] (${c.id})`;
    if (!c.id.startsWith(prefix)) out.push(`${where}: id must start with "${prefix}"`);
    if (ids.has(c.id)) out.push(`${where}: duplicate clause id`);
    ids.add(c.id);
    out.push(...lintText(c.text, where));
    if (c.section === 'acceptance' && !ACCEPTANCE_CATEGORIES.includes(c.category)) out.push(`${where}: only ${ACCEPTANCE_CATEGORIES.join(' or ')} clauses may sit under Acceptance and seal`);
    if (c.replaces !== undefined && !allowReplaces) out.push(`${where}: a base clause cannot replace another clause`);
    if (c.replaces !== undefined && c.replaces === c.id) out.push(`${where}: a clause cannot replace itself`);
    if (c.checkable !== undefined && !allowCheckable) out.push(`${where}: checkable duty statements belong in role modules`);
    if (c.when) {
      if (c.when.consumer !== undefined && !allowConsumerWhen) out.push(`${where}: a consumer condition is not allowed here`);
      for (const b of c.when.bases || []) if (!allowedBases.includes(b)) out.push(`${where}: condition names base ${b}, which this layer does not take`);
      for (const j of c.when.jurisdictions || []) if (!jurisdictions.includes(j)) out.push(`${where}: condition names jurisdiction ${j}, which is not offered`);
    }
  }
  return out;
}

function fieldProblems(fields = [], { at, allowRefines }) {
  const out = [];
  const keys = new Set();
  for (const [i, f] of fields.entries()) {
    const where = `${at}.fields[${i}] (${f.key})`;
    if (keys.has(f.key)) out.push(`${where}: duplicate field key`);
    keys.add(f.key);
    if (f.refines !== undefined && !allowRefines) out.push(`${where}: a base field cannot refine another`);
    if (f.default !== undefined) out.push(...lintText(f.default, `${where}.default`).filter((p) => !p.includes('repeated whitespace')));
    if (f.default !== undefined && /\{\{|\}\}|\[\[|\]\]/.test(f.default)) out.push(`${where}: a default cannot hold a blank or a term`);
  }
  return out;
}

export function baseProblems(base) {
  const out = schemaProblems('base-template', base);
  if (out.length) return out;
  const kinds = BASES[base.key];
  if (base.engager_kind !== kinds.engager || base.provider_kind !== kinds.provider) out.push(`$: ${base.key} is ${kinds.engager} → ${kinds.provider}`);
  if (base.consumer_variant && base.engager_kind !== 'person') out.push('$: only a base whose engager is a person can have a consumer variant');
  out.push(...clauseProblems(base.clauses, {
    prefix: `${base.key.toLowerCase()}.`, at: '$', allowReplaces: false, allowCheckable: false,
    allowConsumerWhen: base.consumer_variant, allowedBases: [base.key], jurisdictions: base.jurisdictions,
  }));
  for (const c of base.clauses) if (c.when?.bases) out.push(`$.clauses (${c.id}): a base clause cannot be conditional on the base`);
  out.push(...fieldProblems(base.fields, { at: '$', allowRefines: false }));
  const fieldKeys = new Set(base.fields.map((f) => f.key));
  for (const c of base.clauses) for (const k of placeholdersIn(c.text)) if (!fieldKeys.has(k)) out.push(`$.clauses (${c.id}): blank {{${k}}} is not a field of this base`);
  const covered = new Set(base.clauses.filter((c) => !c.when).map((c) => c.category));
  for (const k of CATEGORY_KEYS) if (!covered.has(k)) out.push(`$: no unconditional clause in category ${k}`);
  return out;
}

export function moduleProblems(mod) {
  const out = schemaProblems('role-template', mod);
  if (out.length) return out;
  if (!mod.engager && !mod.provider) out.push('$: a module needs an engager or a provider slot');
  const allIds = new Set();
  for (const slot of SLOTS) {
    const s = mod[slot];
    if (!s) continue;
    const at = `$.${slot}`;
    for (const b of s.bases) if (mod.drafted_against[b] === undefined) out.push(`${at}: takes base ${b} but drafted_against has no version for it`);
    out.push(...clauseProblems(s.clauses, {
      prefix: `${mod.role_key}.${slot}.`, at, allowReplaces: true, allowCheckable: true,
      allowConsumerWhen: slot === 'provider', allowedBases: s.bases, jurisdictions: ['EW', 'SC', 'NI'],
    }));
    for (const c of s.clauses) { if (allIds.has(c.id)) out.push(`${at} (${c.id}): duplicate clause id`); allIds.add(c.id); }
    out.push(...fieldProblems(s.fields, { at, allowRefines: true }));
    const covered = new Set(s.clauses.map((c) => c.category));
    for (const k of CATEGORY_KEYS) if (!covered.has(k)) out.push(`${at}: no clause in category ${k}`);
    const checkable = s.clauses.filter((c) => c.checkable).length;
    if (slot === 'provider' && (checkable < CHECKABLE_MIN || checkable > CHECKABLE_MAX)) out.push(`${at}: ${checkable} checkable duty statements (need ${CHECKABLE_MIN} to ${CHECKABLE_MAX})`);
    if (slot === 'engager' && checkable > CHECKABLE_MAX) out.push(`${at}: ${checkable} checkable duty statements (at most ${CHECKABLE_MAX})`);
  }
  return out;
}

export function assertBase(base) {
  if (base?.schema !== SCHEMA_IDS.base) throw new TemplateError(`not a base template (schema ${JSON.stringify(base?.schema)})`);
  const p = baseProblems(base);
  if (p.length) throw new TemplateError(`base ${base.key} is invalid`, p);
  return base;
}

export function assertModule(mod) {
  if (mod?.schema !== SCHEMA_IDS.module) throw new TemplateError(`not a role module (schema ${JSON.stringify(mod?.schema)})`);
  const p = moduleProblems(mod);
  if (p.length) throw new TemplateError(`module ${mod.role_key} is invalid`, p);
  return mod;
}

export function agreementProblems(doc) {
  return schemaProblems('agreement', doc);
}
