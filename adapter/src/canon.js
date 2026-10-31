// Canonical JSON identical to the contract's `_dump`:
//   json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
// Every hash shared between ODIR, this adapter and the contract is a sha256 of this encoding.
// Only strings, integers, booleans, null, arrays and plain objects are allowed; floats are
// refused because Python and JavaScript print them differently.
import crypto from 'node:crypto';

export class CanonError extends Error {}

function sortValue(v, path) {
  if (v === null) return null;
  if (Array.isArray(v)) return v.map((x, i) => sortValue(x, `${path}[${i}]`));
  switch (typeof v) {
    case 'string': case 'boolean': return v;
    case 'number':
      if (!Number.isInteger(v) || !Number.isSafeInteger(v)) throw new CanonError(`non-integer number at ${path}`);
      return v;
    case 'object': {
      const out = {};
      for (const k of Object.keys(v).sort()) {
        if (v[k] === undefined) continue;
        out[k] = sortValue(v[k], `${path}.${k}`);
      }
      return out;
    }
    default: throw new CanonError(`unsupported value (${typeof v}) at ${path}`);
  }
}

// Python's ensure_ascii escapes every code point above 0x7F as \uXXXX (astral ones as a
// surrogate pair, which is what JavaScript strings already hold).
const escapeNonAscii = (s) => s.replace(/[\u0080-￿]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);

export function canonical(value) {
  return escapeNonAscii(JSON.stringify(sortValue(value, '$')));
}

export const sha256 = (text) => crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
export const digest = (value) => sha256(canonical(value));
