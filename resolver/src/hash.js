// Hashes for templates and resolved documents, in the adapter's canonical encoding
// (adapter/src/canon.js: sorted keys, no spaces, ASCII escapes — the same bytes as the contract's
// json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True)).
//
// Style is presentation only and is never hashed: a template's `style` block and every clause's
// `style` are left out, so paper, ink and emphasis can change without a new version, while one
// changed word changes the hash.
import { canonical, digest } from '../../adapter/src/canon.js';

export const HASH_PREFIX = 'sha256:';
const prefixed = (hex) => `${HASH_PREFIX}${hex}`;

const withoutStyle = (obj) => {
  if (!obj || typeof obj !== 'object') return obj;
  const { style, ...rest } = obj; // eslint-disable-line no-unused-vars
  return rest;
};
const clausesWithoutStyle = (clauses) => (clauses || []).map(withoutStyle);

// The words of a base or a role module: everything except style blocks.
export function templateContent(t) {
  const out = withoutStyle(t);
  if (Array.isArray(out.clauses)) out.clauses = clausesWithoutStyle(out.clauses);
  for (const slot of ['engager', 'provider']) {
    if (out[slot] && typeof out[slot] === 'object') out[slot] = { ...out[slot], clauses: clausesWithoutStyle(out[slot].clauses) };
  }
  return out;
}

export const templateHash = (t) => prefixed(digest(templateContent(t)));

// What the terms hash covers: the whole resolved document except style blocks and the hash itself.
export function termsInput(doc) {
  const { style, terms_hash, ...rest } = doc; // eslint-disable-line no-unused-vars
  return { ...rest, sections: rest.sections.map((s) => ({ ...s, clauses: clausesWithoutStyle(s.clauses) })) };
}

export const termsCanonical = (doc) => canonical(termsInput(doc));
export const termsHash = (doc) => prefixed(digest(termsInput(doc)));
export const overridesHash = (overrides) => (overrides.length ? prefixed(digest(overrides)) : null);
