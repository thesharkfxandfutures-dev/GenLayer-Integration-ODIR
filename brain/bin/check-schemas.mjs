#!/usr/bin/env node
// CI gate: every schema in schema/ parses as JSON, and the Brain's own schemas use only keywords
// brain/src/jsonschema.js enforces (so no rule is silently ignored).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertSupported } from '../src/jsonschema.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'schema');
const BRAIN = new Set(['inspector-snapshot.v1.json', 'brain-run.v1.json']);
let bad = 0;
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json')).sort()) {
  try {
    const s = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    if (BRAIN.has(f)) assertSupported(s);
    process.stdout.write(`ok   ${f}\n`);
  } catch (e) { bad++; process.stdout.write(`FAIL ${f}: ${e.message}\n`); }
}
for (const f of BRAIN) if (!fs.existsSync(path.join(dir, f))) { bad++; process.stdout.write(`FAIL missing ${f}\n`); }
process.exit(bad ? 1 : 0);
