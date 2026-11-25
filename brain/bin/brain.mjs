#!/usr/bin/env node
// odir-brain — the Brain loop skeleton (slice A2). DRY RUN ONLY.
//
//   odir-brain dry-run --repo <odir checkout> (--registry <registry.js> --registry-ref <label> | --snapshot <file>)
//                      [--app-id <24 hex>] [--lock-store memory|git] [--lock-dir <git dir>]
//                      [--pulls <json>] [--blocked-issues <json>] [--genskill yes|no] [--out <dir>] [--run-id <id>]
//   odir-brain inspect --registry <registry.js> --registry-ref <label> [--app-id <24 hex>]
//
// The git lock store writes refs/heads/brain/lock in a LOCAL repository only; nothing is pushed.
// The GitHub lock store, issue writes and the schedule are switched on by the owner after merge.
// Exit: 0 record written · 3 lock not taken · 4 lease lost mid-run · 5 configuration · 6 lock unreadable.
import fs from 'node:fs';
import path from 'node:path';
import { runOnce } from '../src/run.js';
import { newRunId, MemoryRefStore } from '../src/lock.js';
import { GitRefStore } from '../src/refstores.js';
import { LocalRepoView } from '../src/repoview.js';
import { DirSink } from '../src/recorder.js';
import { inspectRegistry } from '../src/inspector.js';

const SNAPLINK_APP = '6aa3925dbd278e2d7e71b43f';

function args(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const v = argv[i + 1]; if (v === undefined || v.startsWith('--')) out[a.slice(2)] = true; else { out[a.slice(2)] = v; i++; } }
    else out._.push(a);
  }
  return out;
}
const fail = (code, msg) => { process.stderr.write(`odir-brain: ${msg}\n`); process.exit(code); };
const readJson = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));

async function main() {
  const a = args(process.argv.slice(2));
  const cmd = a._[0];
  for (const k of ['live', 'apply', 'merge', 'deploy', 'sign', 'write-issue']) if (a[k]) fail(5, `--${k} is not available: A2 is a dry run; switching on is the owner's step after merge`);
  const appId = a['app-id'] || SNAPLINK_APP;

  if (cmd === 'inspect') {
    if (!a.registry || !a['registry-ref']) fail(5, 'inspect needs --registry and --registry-ref');
    const snap = inspectRegistry(fs.readFileSync(a.registry, 'utf8'), { appId, ref: a['registry-ref'] });
    process.stdout.write(`${JSON.stringify(snap, null, 2)}\n`);
    return;
  }
  if (cmd !== 'dry-run') fail(5, 'usage: odir-brain dry-run … | odir-brain inspect …');
  if (!a.repo) fail(5, '--repo is required');
  const storeName = a['lock-store'] || 'memory';
  if (storeName === 'github') fail(5, 'the GitHub lock store is switched on by the owner after merge (A2 stops at the PR)');
  if (!['memory', 'git'].includes(storeName)) fail(5, `unknown --lock-store ${storeName}`);
  const store = storeName === 'git' ? new GitRefStore({ dir: path.resolve(a['lock-dir'] || a.repo) }) : new MemoryRefStore();
  let registry = null, snapshot = null;
  if (a.registry) {
    if (!a['registry-ref']) fail(5, '--registry-ref is required with --registry');
    registry = { text: fs.readFileSync(a.registry, 'utf8'), appId, ref: a['registry-ref'] };
  } else if (a.snapshot) snapshot = readJson(a.snapshot);
  const pulls = a.pulls ? readJson(a.pulls) : [];
  const runId = a['run-id'] || newRunId(Date.now());
  const res = await runOnce({
    runId, store, storeName,
    repo: new LocalRepoView({ dir: path.resolve(a.repo) }),
    registry, snapshot,
    pulls, pullsSource: a.pulls ? `file ${path.basename(a.pulls)}` : null,
    openBlockedIssues: a['blocked-issues'] ? readJson(a['blocked-issues']) : [],
    genskillAvailable: a.genskill === 'yes',
    sink: new DirSink(path.resolve(a.out || 'out/brain-runs')),
    dryRun: true,
  });
  const { record, ...summary } = res;
  process.stdout.write(`${JSON.stringify({ ...summary, stopped_at: record?.stopped_at ?? null, would_do: record?.action ?? null }, null, 2)}\n`);
  if (res.outcome === 'LEASE_LOST') process.exit(4);
  if (res.outcome === 'LOCK_UNREADABLE') process.exit(6);
  if (!res.acquired) process.exit(3);
}

main().catch((e) => fail(5, e.message));
