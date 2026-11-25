// The resolver (slice A3): one base, the engager's and the provider's role modules, the parties'
// own overrides, a jurisdiction and the consumer flag → one resolved document (odir.agreement.v1).
//
// Merge order is fixed: base < engager module < provider module < overrides. A later layer adds
// clauses, or replaces an earlier clause in place by naming it in `replaces`; it never overwrites by
// accident (ids are prefixed per layer and must be unique). Every replacement is marked on the
// clause (`replaces: { id, source }`). A `locked` clause cannot be replaced. Conditions (`when`)
// pick the consumer, base and jurisdiction variants. Blanks stay as {{field_key}} in template mode
// and are filled from the parties' values (or the field's default) in agreement mode, in one pass,
// so a value can never introduce another blank.
import {
  BASES, CATEGORIES, CATEGORY_INDEX, CATEGORY_KEYS, JURISDICTIONS, SCHEMA_IDS, SECTIONS,
} from './categories.js';
import { overridesHash, templateHash, termsHash } from './hash.js';
import {
  PLACEHOLDER, TemplateError, agreementProblems, assertBase, assertModule, lintText, placeholdersIn,
} from './validate.js';

export class ResolveError extends TemplateError {}

const SOURCES = ['base', 'engager_module', 'provider_module', 'override'];
const OVERRIDE_ID = /^o\.[a-z0-9_]+$/;
const OVERRIDE_KEYS = new Set(['id', 'category', 'text', 'replaces', 'section']);
const VALUE_MAX = 300;
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function applies(when, ctx) {
  if (!when) return true;
  if (when.consumer !== undefined && when.consumer !== ctx.consumer) return false;
  if (when.bases && !when.bases.includes(ctx.base)) return false;
  if (when.jurisdictions && !when.jurisdictions.includes(ctx.jurisdiction)) return false;
  return true;
}

function checkOverrides(overrides) {
  const out = [];
  if (!Array.isArray(overrides)) return ['overrides must be a list'];
  overrides.forEach((o, i) => {
    const at = `overrides[${i}]`;
    if (!o || typeof o !== 'object' || Array.isArray(o)) { out.push(`${at}: must be an object`); return; }
    for (const k of Object.keys(o)) if (!OVERRIDE_KEYS.has(k)) out.push(`${at}: unexpected property ${k}`);
    if (typeof o.id !== 'string' || !OVERRIDE_ID.test(o.id)) out.push(`${at}: id must look like o.<name>`);
    if (!CATEGORY_KEYS.includes(o.category)) out.push(`${at}: unknown category ${JSON.stringify(o.category)}`);
    if (typeof o.text !== 'string' || !o.text || o.text.length > 1200 || /[\u0000-\u001f\u007f]/.test(o.text)) out.push(`${at}: text must be 1 to 1200 plain characters`);
    else {
      out.push(...lintText(o.text, at));
      if (/\{\{|\}\}|\[\[|\]\]/.test(o.text)) out.push(`${at}: an override is plain text — no blanks or terms`);
    }
    if (o.replaces !== undefined && typeof o.replaces !== 'string') out.push(`${at}: replaces must be a clause id`);
    if (o.section !== undefined && o.section !== 'acceptance') out.push(`${at}: section may only be "acceptance"`);
    if (o.section === 'acceptance' && !['parties_authority', 'disputes_record'].includes(o.category)) out.push(`${at}: only parties_authority or disputes_record clauses may sit under Acceptance and seal`);
  });
  return out;
}

function checkValue(field, value, at) {
  if (typeof value !== 'string') return `${at}: value must be a string`;
  if (!value.length || value.length > VALUE_MAX) return `${at}: value must be 1 to ${VALUE_MAX} characters`;
  if (value !== value.trim()) return `${at}: value has leading or trailing whitespace`;
  if (/[\u0000-\u001f\u007f\u2028\u2029]/.test(value)) return `${at}: value holds a control or line-break character`;
  if (/\{|\}|\[\[|\]\]/.test(value)) return `${at}: value cannot hold braces or [[ ]]`;
  if (field.type === 'number' && !/^\d{1,9}$/.test(value)) return `${at}: value must be a whole number`;
  return null;
}

/**
 * resolve({ base, engager?, provider?, overrides?, jurisdiction, consumer?, mode?, values?, title? })
 * Throws ResolveError (with .problems) on anything it will not resolve.
 */
export function resolve({
  base, engager = null, provider = null, overrides = [], jurisdiction, consumer = false, mode = 'template', values = {}, title = null,
} = {}) {
  assertBase(base);
  if (engager) assertModule(engager);
  if (provider) assertModule(provider);
  const problems = [];
  if (!['template', 'agreement'].includes(mode)) problems.push(`mode must be template or agreement, not ${JSON.stringify(mode)}`);
  if (!Object.hasOwn(JURISDICTIONS, jurisdiction) || !base.jurisdictions.includes(jurisdiction)) problems.push(`base ${base.key} is not offered in jurisdiction ${JSON.stringify(jurisdiction)}`);
  if (typeof consumer !== 'boolean') problems.push('consumer must be true or false');
  if (consumer && !base.consumer_variant) problems.push(`base ${base.key} has no consumer variant`);
  if (consumer && engager) problems.push('a consumer engager books for themselves, not as a role: no engager module');
  if (engager && !engager.engager?.bases.includes(base.key)) problems.push(`role ${engager.role_key} does not take the engager slot under ${base.key}`);
  if (provider && !provider.provider?.bases.includes(base.key)) problems.push(`role ${provider.role_key} does not take the provider slot under ${base.key}`);
  if (title !== null && (typeof title !== 'string' || !title.trim() || title.length > 160 || title !== title.trim() || /[\u0000-\u001f\u007f{}]|\[\[|\]\]/.test(title))) problems.push('title must be 1 to 160 plain characters');
  if (values === null || typeof values !== 'object' || Array.isArray(values)) problems.push('values must be an object');
  if (mode === 'template' && values && Object.keys(values).length) problems.push('template mode takes no values');
  problems.push(...checkOverrides(overrides));
  if (problems.length) throw new ResolveError('cannot resolve', problems);

  const ctx = { base: base.key, jurisdiction, consumer };
  const labels = {
    engager: engager?.engager.party_label ?? base.party_labels.engager,
    provider: provider?.provider.party_label ?? base.party_labels.provider,
  };
  const terms = {
    engager: labels.engager, Engager: cap(labels.engager), provider: labels.provider, Provider: cap(labels.provider),
    jurisdiction: JURISDICTIONS[jurisdiction].name, courts: JURISDICTIONS[jurisdiction].courts,
  };

  // Clauses, layer by layer.
  const layers = [
    { source: 'base', clauses: base.clauses },
    { source: 'engager_module', clauses: engager?.engager.clauses || [] },
    { source: 'provider_module', clauses: provider?.provider.clauses || [] },
    { source: 'override', clauses: overrides },
  ];
  const list = []; // in merge order; a replacement takes its target's place
  const seen = new Set();
  for (const layer of layers) {
    for (const c of layer.clauses) {
      if (seen.has(c.id)) { problems.push(`${layer.source} clause ${c.id}: id already used by an earlier layer`); continue; }
      seen.add(c.id);
      if (!applies(c.when, ctx)) continue;
      const entry = {
        id: c.id, category: c.category, text: c.text, source: layer.source, replaces: null,
        locked: c.locked === true, checkable: c.checkable === true, section: c.section || null,
        ...(c.style ? { style: { ...c.style } } : {}),
      };
      if (c.replaces === undefined) { list.push(entry); continue; }
      const at = list.findIndex((x) => x.id === c.replaces);
      if (at < 0) { problems.push(`${layer.source} clause ${c.id}: replaces ${c.replaces}, which is not in this variant`); continue; }
      const target = list[at];
      if (SOURCES.indexOf(target.source) >= SOURCES.indexOf(layer.source)) { problems.push(`${layer.source} clause ${c.id}: may only replace a clause from an earlier layer`); continue; }
      if (target.locked) { problems.push(`${layer.source} clause ${c.id}: ${target.id} is locked and cannot be replaced`); continue; }
      if (target.category !== c.category) { problems.push(`${layer.source} clause ${c.id}: must keep the category of ${target.id} (${target.category})`); continue; }
      list[at] = { ...entry, replaces: { id: target.id, source: target.source } };
    }
  }

  // Fields, layer by layer: a later layer may refine (label or default) but must say so.
  const fields = new Map();
  const fieldLayers = [
    { source: 'base', fields: base.fields },
    { source: 'engager_module', fields: engager?.engager.fields || [] },
    { source: 'provider_module', fields: provider?.provider.fields || [] },
  ];
  for (const { source, fields: fs } of fieldLayers) {
    for (const f of fs) {
      const prior = fields.get(f.key);
      if (!prior) {
        if (f.refines) problems.push(`${source} field ${f.key}: refines a field no earlier layer defines`);
        fields.set(f.key, { key: f.key, label: f.label, category: f.category, type: f.type, default: f.default ?? null, value: null, source });
        continue;
      }
      const same = f.label === prior.label && f.type === prior.type && f.category === prior.category && (f.default ?? null) === prior.default;
      if (!f.refines && same) continue; // the same blank, defined the same way on both sides
      if (!f.refines) { problems.push(`${source} field ${f.key}: already defined differently by ${prior.source} (mark it refines: true)`); continue; }
      if (f.type !== prior.type || f.category !== prior.category) { problems.push(`${source} field ${f.key}: a refinement keeps the type and category`); continue; }
      fields.set(f.key, { ...prior, label: f.label, default: f.default ?? prior.default, source });
    }
  }

  // Terms first ([[...]] → labels), then blanks.
  for (const e of list) e.text = e.text.replace(/\[\[([A-Za-z]+)\]\]/g, (m, t) => terms[t]);
  const used = [];
  for (const e of list) for (const k of placeholdersIn(e.text)) {
    if (!fields.has(k)) problems.push(`clause ${e.id}: blank {{${k}}} is not a field of any layer`);
    else if (!used.includes(k)) used.push(k);
  }
  for (const c of CATEGORY_KEYS) if (!list.some((e) => e.category === c)) problems.push(`category ${c} has no clause in this variant`);
  if (problems.length) throw new ResolveError(`cannot resolve ${base.key}/${jurisdiction}`, problems);

  const resolvedFields = [...fields.values()].filter((f) => used.includes(f.key));
  if (mode === 'agreement') {
    for (const k of Object.keys(values)) if (!used.includes(k)) problems.push(`values.${k}: not a blank in this document`);
    for (const f of resolvedFields) {
      const v = Object.hasOwn(values, f.key) ? values[f.key] : f.default;
      if (v === null || v === undefined) { problems.push(`values.${f.key}: missing (${f.label})`); continue; }
      const bad = checkValue(f, v, `values.${f.key}`);
      if (bad) problems.push(bad); else f.value = v;
    }
    if (problems.length) throw new ResolveError('cannot fill the blanks', problems);
    const byKey = new Map(resolvedFields.map((f) => [f.key, f.value]));
    for (const e of list) e.text = e.text.replace(PLACEHOLDER, (m, k) => byKey.get(k));
  }

  // Sections: each category's clauses, in category order, under its standard section; clauses
  // marked section "acceptance" under Acceptance and seal.
  const sectionOf = new Map(CATEGORIES.map((c) => [c.key, c.section]));
  const order = (a, b) => CATEGORY_INDEX.get(a.category) - CATEGORY_INDEX.get(b.category) || list.indexOf(a) - list.indexOf(b);
  const sections = SECTIONS.map(({ key, title: t }) => ({
    key,
    title: t,
    clauses: list
      .filter((e) => (e.section === 'acceptance' ? key === 'acceptance' : sectionOf.get(e.category) === key))
      .sort(order)
      .map(({ section, ...rest }) => rest), // eslint-disable-line no-unused-vars
  }));

  const moduleRef = (m) => (m ? { role_key: m.role_key, version: m.version, sha256: templateHash(m), stale: m.drafted_against[base.key] !== base.version } : null);
  const defaultTitle = provider ? `${provider.role_label} — ${base.title}` : engager ? `${engager.role_label} engaging — ${base.title}` : base.title;
  const style = { ...(base.style || {}), ...(engager?.style || {}), ...(provider?.style || {}) };
  const doc = {
    schema: SCHEMA_IDS.agreement,
    mode,
    title: title ?? defaultTitle,
    notice: base.notice,
    base: base.key,
    jurisdiction,
    jurisdiction_name: JURISDICTIONS[jurisdiction].name,
    consumer,
    roles: { engager: engager?.role_key ?? null, provider: provider?.role_key ?? null },
    parties: [
      { slot: 'engager', label: labels.engager, role: engager?.role_key ?? null, role_label: engager?.role_label ?? null, kind: BASES[base.key].engager },
      { slot: 'provider', label: labels.provider, role: provider?.role_key ?? null, role_label: provider?.role_label ?? null, kind: BASES[base.key].provider },
    ],
    sources: {
      base: { key: base.key, version: base.version, sha256: templateHash(base) },
      engager_module: moduleRef(engager),
      provider_module: moduleRef(provider),
      overrides: { count: overrides.length, sha256: overridesHash(overrides) },
    },
    sections,
    fields: resolvedFields,
    ...(Object.keys(style).length ? { style } : {}),
  };
  doc.terms_hash = termsHash(doc);
  const bad = agreementProblems(doc);
  if (bad.length) throw new ResolveError('resolved document fails odir.agreement.v1', bad);
  return doc;
}
