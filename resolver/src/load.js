// Reads the template tree (templates/bases/<base>.json, templates/roles/<role_key>/module.json),
// checks every file, and lists every combination that exists: each role × base × slot it takes,
// in every jurisdiction the base offers, with and without a consumer engager where allowed, plus
// each base on its own.
import fs from 'node:fs';
import path from 'node:path';
import { BASES, SLOTS } from './categories.js';
import { assertBase, assertModule } from './validate.js';

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));

export function loadTemplates(root) {
  const problems = [];
  const bases = new Map();
  const modules = new Map();
  const baseDir = path.join(root, 'templates', 'bases');
  const roleDir = path.join(root, 'templates', 'roles');
  for (const f of fs.existsSync(baseDir) ? fs.readdirSync(baseDir).sort() : []) {
    const file = `templates/bases/${f}`;
    if (!f.endsWith('.json')) { problems.push(`${file}: only <base>.json files belong here`); continue; }
    try {
      const b = assertBase(readJson(path.join(baseDir, f)));
      if (f !== `${b.key.toLowerCase()}.json`) problems.push(`${file}: holds base ${b.key}; name it ${b.key.toLowerCase()}.json`);
      else bases.set(b.key, b);
    } catch (e) { problems.push(`${file}: ${e.message}`); }
  }
  for (const d of fs.existsSync(roleDir) ? fs.readdirSync(roleDir).sort() : []) {
    const dir = path.join(roleDir, d);
    if (!fs.statSync(dir).isDirectory()) { problems.push(`templates/roles/${d}: only role folders belong here`); continue; }
    const extra = fs.readdirSync(dir).filter((f) => f !== 'module.json');
    if (extra.length) problems.push(`templates/roles/${d}: unexpected files ${extra.join(', ')}`);
    const file = `templates/roles/${d}/module.json`;
    if (!fs.existsSync(path.join(dir, 'module.json'))) { problems.push(`${file}: missing`); continue; }
    try {
      const m = assertModule(readJson(path.join(dir, 'module.json')));
      if (m.role_key !== d) problems.push(`${file}: role_key ${m.role_key} must equal its folder name`);
      else modules.set(m.role_key, m);
    } catch (e) { problems.push(`${file}: ${e.message}`); }
  }
  return { bases, modules, problems };
}

// Every combination to render: each base alone; each module in each slot and base it takes; and
// each engager module paired with each provider module under a base both take (a role booking a
// role, the same role included). `skipped` lists module bases whose base file does not exist yet.
export function combinations({ bases, modules }) {
  const combos = [];
  const skipped = [];
  const variants = (base, { consumerAllowed }) => {
    const out = [];
    for (const j of base.jurisdictions) {
      out.push({ jurisdiction: j, consumer: false });
      if (consumerAllowed && base.consumer_variant) out.push({ jurisdiction: j, consumer: true });
    }
    return out;
  };
  for (const key of Object.keys(BASES)) {
    const base = bases.get(key);
    if (!base) continue;
    for (const v of variants(base, { consumerAllowed: true })) combos.push({ base: key, engager: null, provider: null, ...v });
  }
  for (const [roleKey, m] of modules) {
    for (const slot of SLOTS) {
      if (!m[slot]) continue;
      for (const key of m[slot].bases) {
        const base = bases.get(key);
        if (!base) { skipped.push({ role: roleKey, slot, base: key, reason: 'base not present' }); continue; }
        // A consumer books for themselves, so only a provider-side module meets a consumer engager.
        for (const v of variants(base, { consumerAllowed: slot === 'provider' })) {
          combos.push({ base: key, engager: slot === 'engager' ? roleKey : null, provider: slot === 'provider' ? roleKey : null, ...v });
        }
      }
    }
  }
  for (const [e, me] of modules) {
    for (const [p, mp] of modules) {
      if (!me.engager || !mp.provider) continue;
      for (const key of me.engager.bases) {
        if (!mp.provider.bases.includes(key) || !bases.has(key)) continue;
        for (const v of variants(bases.get(key), { consumerAllowed: false })) combos.push({ base: key, engager: e, provider: p, ...v });
      }
    }
  }
  return { combos, skipped };
}

export function comboName(c) {
  const who = c.engager && c.provider ? [`${c.engager}+${c.provider}`, 'pair']
    : c.engager ? [c.engager, 'engager'] : c.provider ? [c.provider, 'provider'] : ['base', 'none'];
  return [...who, c.base, c.jurisdiction, c.consumer ? 'consumer' : 'business'].join('.');
}
