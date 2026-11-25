// A small JSON Schema validator for the subset the Brain's schemas use. No dependencies.
// Supported: type, const, enum, pattern, minLength, maxLength, minimum, maximum, required,
// properties, additionalProperties (boolean), items, minItems, maxItems, uniqueItems,
// $ref to "#/$defs/<name>". Anything else in a schema is refused, so a schema can never
// silently ask for a rule this validator does not enforce.

const KNOWN = new Set([
  '$schema', '$id', '$defs', 'title', 'description', '$comment',
  'type', 'const', 'enum', 'pattern', 'minLength', 'maxLength', 'minimum', 'maximum',
  'required', 'properties', 'additionalProperties', 'items', 'minItems', 'maxItems', 'uniqueItems', '$ref',
]);

const typeOf = (v) => {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  if (typeof v === 'number') return Number.isInteger(v) ? 'integer' : 'number';
  return typeof v;
};

const typeMatches = (want, got) => want === got || (want === 'number' && got === 'integer');
const ANNOTATIONS = new Set(['title', 'description', '$comment']);
const stable = (v) => (v && typeof v === 'object' && !Array.isArray(v)
  ? `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${stable(v[k])}`).join(',')}}`
  : Array.isArray(v) ? `[${v.map(stable).join(',')}]` : JSON.stringify(v));
const refSiblings = (s) => Object.keys(s).filter((k) => k !== '$ref' && !ANNOTATIONS.has(k));

// Walk a whole schema and refuse any keyword this validator does not enforce.
export function assertSupported(schema, at = '$') {
  if (typeof schema !== 'object' || schema === null || Array.isArray(schema)) throw new Error(`schema at ${at} must be an object`);
  for (const k of Object.keys(schema)) if (!KNOWN.has(k)) throw new Error(`unsupported schema keyword "${k}" at ${at}`);
  if (schema.$ref !== undefined && refSiblings(schema).length) throw new Error(`keywords beside $ref are ignored, refusing at ${at}`);
  for (const [k, v] of Object.entries(schema.properties || {})) assertSupported(v, `${at}.properties.${k}`);
  for (const [k, v] of Object.entries(schema.$defs || {})) assertSupported(v, `${at}.$defs.${k}`);
  if (schema.items !== undefined) assertSupported(schema.items, `${at}.items`);
  return true;
}

export function validate(schema, value) {
  const problems = [];
  const root = schema;
  const walk = (s, v, at) => {
    if (s.$ref !== undefined) {
      const m = /^#\/\$defs\/([A-Za-z0-9_-]+)$/.exec(s.$ref);
      if (!m || !root.$defs || !root.$defs[m[1]]) throw new Error(`unsupported $ref ${s.$ref}`);
      if (refSiblings(s).length) throw new Error(`keywords beside $ref are ignored, refusing at ${at}`);
      return walk(root.$defs[m[1]], v, at);
    }
    for (const k of Object.keys(s)) if (!KNOWN.has(k)) throw new Error(`unsupported schema keyword "${k}" at ${at}`);
    const t = typeOf(v);
    if (s.type !== undefined) {
      const types = Array.isArray(s.type) ? s.type : [s.type];
      if (!types.some((x) => typeMatches(x, t))) { problems.push(`${at}: expected ${types.join('|')}, got ${t}`); return; }
    }
    if (s.const !== undefined && JSON.stringify(v) !== JSON.stringify(s.const)) problems.push(`${at}: must equal ${JSON.stringify(s.const)}`);
    if (s.enum !== undefined && !s.enum.some((e) => JSON.stringify(e) === JSON.stringify(v))) problems.push(`${at}: must be one of ${JSON.stringify(s.enum)}`);
    if (t === 'string') {
      if (s.pattern !== undefined && !new RegExp(s.pattern, 'u').test(v)) problems.push(`${at}: does not match ${s.pattern}`);
      if (s.minLength !== undefined && [...v].length < s.minLength) problems.push(`${at}: shorter than ${s.minLength}`);
      if (s.maxLength !== undefined && [...v].length > s.maxLength) problems.push(`${at}: longer than ${s.maxLength}`);
    }
    if (t === 'integer' || t === 'number') {
      if (s.minimum !== undefined && v < s.minimum) problems.push(`${at}: below ${s.minimum}`);
      if (s.maximum !== undefined && v > s.maximum) problems.push(`${at}: above ${s.maximum}`);
    }
    if (t === 'array') {
      if (s.minItems !== undefined && v.length < s.minItems) problems.push(`${at}: fewer than ${s.minItems} items`);
      if (s.maxItems !== undefined && v.length > s.maxItems) problems.push(`${at}: more than ${s.maxItems} items`);
      if (s.uniqueItems) {
        const seen = new Set(v.map(stable));
        if (seen.size !== v.length) problems.push(`${at}: items are not unique`);
      }
      if (s.items !== undefined) v.forEach((x, i) => walk(s.items, x, `${at}[${i}]`));
    }
    if (t === 'object') {
      for (const r of s.required || []) if (!Object.prototype.hasOwnProperty.call(v, r)) problems.push(`${at}: missing ${r}`);
      const props = s.properties || {};
      for (const [k, x] of Object.entries(v)) {
        if (props[k]) walk(props[k], x, `${at}.${k}`);
        else if (s.additionalProperties === false) problems.push(`${at}: unexpected property ${k}`);
      }
    }
  };
  walk(schema, value, '$');
  return { ok: problems.length === 0, problems };
}
