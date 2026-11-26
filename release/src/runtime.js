// The release bundle's own API (slice A4), bundled with the resolver. `makeRelease(data, deps)` is
// called once inside the bundle with the embedded files; it is a factory so it can be tested here
// on its own.
//
// Every template is carried as the exact text of its file, with two hashes recorded at build time:
//   file_sha256 — sha256 of the whole file (UTF-8). Catches any change at all, style included.
//   sha256      — the template hash (resolver/src/hash.js: canonical JSON, style left out). This is
//                 the value a resolved document cites in sources.*.sha256.
// getBase / getModule check both before they hand a template out, and refuse on any mismatch, so
// a tampered template never reaches resolve(). verifyRelease() checks every file at once.

export class ReleaseError extends Error {
  constructor(message, problems = []) {
    super(problems.length ? `${message}:\n  - ${problems.join('\n  - ')}` : message);
    this.problems = problems;
  }
}

const deepFreeze = (v) => {
  if (v && typeof v === 'object' && !Object.isFrozen(v)) {
    Object.freeze(v);
    for (const k of Object.keys(v)) deepFreeze(v[k]);
  }
  return v;
};

// The bundle's replacement for resolver/src/validate.js loadSchema (which reads schema/ from disk):
// the same three schema files, embedded, checked against their whole-file sha256 before first use.
export function makeSchemaLoader(files, sha256Hex) {
  deepFreeze(files);
  const cache = new Map();
  return function loadSchema(name) {
    if (cache.has(name)) return cache.get(name);
    const f = files.find((x) => x.kind === 'schema' && x.path === `schema/${name}.v1.json`);
    if (!f) throw new ReleaseError(`schema ${JSON.stringify(name)} is not in this release`);
    if (sha256Hex(f.text) !== f.file_sha256) throw new ReleaseError(`release is not intact`, [`${f.path}: whole-file sha256 does not match the release`]);
    cache.set(name, deepFreeze(JSON.parse(f.text)));
    return cache.get(name);
  };
}

export function makeRelease(data, { sha256Hex, templateHash, assertBase, assertModule, SCHEMA_IDS }) {
  deepFreeze(data);
  const files = data.files;
  const byPath = new Map(files.map((f) => [f.path, f]));
  const checked = new Map(); // path → frozen parsed value, once its checks pass

  function fileProblems(f) {
    const out = [];
    if (sha256Hex(f.text) !== f.file_sha256) out.push(`${f.path}: whole-file sha256 does not match the release`);
    let value;
    try { value = JSON.parse(f.text); } catch (e) { out.push(`${f.path}: not JSON (${e.message})`); return { out }; }
    if (f.kind === 'schema') return { out, value };
    try {
      if (f.kind === 'base') assertBase(value);
      else if (f.kind === 'module') assertModule(value);
      else out.push(`${f.path}: unknown kind ${JSON.stringify(f.kind)}`);
    } catch (e) { out.push(`${f.path}: ${e.message}`); return { out }; }
    if (templateHash(value) !== f.sha256) out.push(`${f.path}: template hash does not match the release`);
    const key = f.kind === 'base' ? value.key : value.role_key;
    if (key !== f.key) out.push(`${f.path}: holds ${key}, the release lists ${f.key}`);
    if (value.version !== f.version) out.push(`${f.path}: version ${value.version}, the release lists ${f.version}`);
    const wantSchema = f.kind === 'base' ? SCHEMA_IDS.base : SCHEMA_IDS.module;
    if (value.schema !== wantSchema) out.push(`${f.path}: schema ${value.schema}, expected ${wantSchema}`);
    return { out, value };
  }

  function load(path) {
    if (checked.has(path)) return checked.get(path);
    const f = byPath.get(path);
    if (!f) throw new ReleaseError(`no file ${path} in release ${data.release.tag ?? data.release.commit}`);
    const { out, value } = fileProblems(f);
    if (out.length) throw new ReleaseError(`release ${data.release.tag ?? data.release.commit} is not intact`, out);
    checked.set(path, deepFreeze(value));
    return checked.get(path);
  }

  const find = (kind, key) => files.find((f) => f.kind === kind && f.key === key);

  return Object.freeze({
    RELEASE: data.release,
    // Every template in the release with its hashes (no text).
    // The embedded schema files with their whole-file sha256.
    listSchemas: () => files.filter((f) => f.kind === 'schema').map(({ path, file_sha256 }) => ({ path, file_sha256 })),
    listTemplates: () => files.filter((f) => f.kind !== 'schema')
      .map(({ path, kind, key, version, sha256, file_sha256 }) => ({ path, kind, key, version, sha256, file_sha256 })),
    // The exact file text, for an importer that writes it out or hashes it again.
    templateText(path) {
      const f = byPath.get(path);
      if (!f || f.kind === 'schema') throw new ReleaseError(`no template ${path} in this release`);
      load(path);
      return f.text;
    },
    getBase(key) {
      const f = find('base', key);
      if (!f) throw new ReleaseError(`no base ${JSON.stringify(key)} in this release`);
      return load(f.path);
    },
    getModule(roleKey) {
      const f = find('module', roleKey);
      if (!f) throw new ReleaseError(`no role module ${JSON.stringify(roleKey)} in this release`);
      return load(f.path);
    },
    // Check every file: whole-file sha256, template rules, template hash, key, version, schema id.
    verifyRelease() {
      const problems = [];
      const seen = new Set();
      for (const f of files) {
        if (seen.has(f.path)) problems.push(`${f.path}: listed twice`);
        seen.add(f.path);
        problems.push(...fileProblems(f).out);
      }
      for (const kind of ['base', 'module']) {
        const keys = files.filter((f) => f.kind === kind).map((f) => f.key);
        if (new Set(keys).size !== keys.length) problems.push(`two ${kind} files share a key`);
      }
      return { ok: problems.length === 0, problems };
    },
  });
}
