import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MemoryRepoView } from '../src/repoview.js';
import { inspectRegistry } from '../src/inspector.js';
import { PHASE1_FILES } from '../src/state.js';

export const here = path.dirname(fileURLToPath(import.meta.url));
export const T0 = Date.parse('2026-11-25T12:00:00.000Z');
export const MIN = 60 * 1000;
export const APP = '6aa3925dbd278e2d7e71b43f';

export const registryText = () => fs.readFileSync(path.join(here, 'fixtures', 'registry.synthetic.js'), 'utf8');
export const snapshotOf = (text = registryText()) => inspectRegistry(text, { appId: APP, ref: 'fixture' });

export function clock(start = T0) {
  const c = { t: start, now: () => c.t, advance: (ms) => { c.t += ms; return c.t; } };
  return c;
}

// Wraps a store so that the first `n` getRef() calls wait for each other: every racing run reads
// the same head before any of them writes. This forces the interleaving the race tests need.
export function barrier(store, n = 2) {
  let waiting = 0, release;
  const gate = new Promise((r) => { release = r; });
  let reads = 0;
  return new Proxy(store, {
    get(target, prop) {
      if (prop === 'getRef') {
        return async (...a) => {
          const v = await target.getRef(...a);
          if (reads++ < n) { waiting++; if (waiting === n) release(); await gate; }
          return v;
        };
      }
      const v = target[prop];
      return typeof v === 'function' ? v.bind(target) : v;
    },
  });
}

export function queueMd({ pin = null, order = 'registry', listed = ['photographer'] } = {}) {
  return [
    '# Brain queue', '',
    `registry_sha256: ${pin || 'unpinned'}`,
    `order: ${order}`, '',
    '## Queue',
    ...listed.map((k) => `- ${k}`), '',
  ].join('\n');
}

export function repoWith({ pin = null, bases = true, approved = [], holding = null, listed, order, queue = true } = {}) {
  const main = { 'README.md': 'x' };
  if (queue) main['brain/QUEUE.md'] = queueMd({ pin, listed, order });
  if (bases) for (const p of PHASE1_FILES) main[p] = '{}';
  for (const k of approved) main[`templates/roles/${k}/module.json`] = '{}';
  const trees = { main };
  if (holding) trees['brain/holding'] = Object.fromEntries(holding.map((p) => [p, '{}']));
  return new MemoryRepoView(trees);
}

// A fake issue store that records every call.
export function fakeIssues(initial = []) {
  const s = { issues: initial.map((i) => ({ state: 'open', comments: [], ...i })), calls: [], next: 100 };
  s.open = () => s.issues.filter((i) => i.state === 'open').map(({ number, body }) => ({ number, body }));
  s.create = async ({ title, body, labels }) => { const n = s.next++; s.issues.push({ number: n, title, body, labels, state: 'open', comments: [] }); s.calls.push(`create:${n}`); return { number: n }; };
  s.update = async (n, { body }) => { s.issues.find((i) => i.number === n).body = body; s.calls.push(`update:${n}`); };
  s.comment = async (n, text) => { s.issues.find((i) => i.number === n).comments.push(text); s.calls.push(`comment:${n}`); };
  s.close = async (n) => { s.issues.find((i) => i.number === n).state = 'closed'; s.calls.push(`close:${n}`); };
  return s;
}
