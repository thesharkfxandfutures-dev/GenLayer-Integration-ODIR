#!/usr/bin/env node
// genlayer-odir: the narrow adapter between an ODIR review package and the ODIR Review Gate
// contract. Read-only. It never signs, never submits and never issues a permit.
//
//   genlayer-odir package verify <package.json>
//   genlayer-odir observe --slice <id> --config <cfg.json> (--from-file <reply.json> | --rpc) [--save-raw <file>] [--timeout ms]
//   genlayer-odir reconcile --package <p.json> --observation <o.json> [--config <cfg.json>]
//   genlayer-odir fixtures            run the D1 fixtures end to end (synthetic and live-recorded)
//
// Exit codes: 0 consistent/valid · 2 pending or not submitted · 3 stale/expired/blocked/outage
//             4 integrity mismatch · 5 configuration mismatch · 6 bad input · 7 usage
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { bindingSummary, PackageError } from '../src/package.js';
import { observe, ObservationError } from '../src/observe.js';
import { reconcile } from '../src/reconcile.js';
import { CanonError } from '../src/canon.js';
import { readView, RpcError } from '../src/rpc.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const flags = {};
const words = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a.startsWith('--')) { const [k, v] = a.slice(2).split('='); flags[k] = v ?? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true); }
  else words.push(a);
}
const emit = (obj) => process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
const fail = (code, message) => { process.stderr.write(`genlayer-odir: ${message}\n`); process.exit(code); };
const readJson = (p) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { fail(6, `cannot read ${p}: ${e.message}`); } };
const readText = (p) => { try { return fs.readFileSync(p, 'utf8'); } catch (e) { fail(6, `cannot read ${p}: ${e.message}`); } };

function loadConfig(p) {
  const c = readJson(p);
  for (const k of ['network_label', 'chain_id', 'rpc_url', 'contract_address', 'contract_code_sha256']) if (c[k] === undefined) fail(5, `config lacks ${k}`);
  return c;
}

try {
  const [cmd, sub] = words;
  if (cmd === 'package' && sub === 'verify') {
    const pkg = readJson(words[2] || fail(7, 'package verify <package.json>'));
    emit({ ok: true, ...bindingSummary(pkg), authority: 'none' });
  } else if (cmd === 'observe') {
    const config = loadConfig(flags.config || fail(7, '--config is required'));
    const slice = flags.slice || fail(7, '--slice is required');
    let raw, kind, read = {};
    if (flags['from-file']) { raw = readText(flags['from-file']); kind = 'file'; }
    else if (flags.rpc) {
      // One permitted view, on the configured chain and address, through the pinned client.
      read = await readView(config, 'get_slice', [slice], { timeoutMs: Number(flags.timeout || 20_000) });
      raw = read.raw; kind = 'rpc';
    } else fail(7, 'give --from-file <reply.json> or --rpc');
    const obs = observe(raw, { source: { kind, chain_id: config.chain_id, contract_address: config.contract_address, contract_code_sha256: config.contract_code_sha256, rpc_url: kind === 'rpc' ? read.rpc_url : null, network_label: config.network_label, state_selection: read.state_selection || null, client_version: read.client_version || null } });
    if (flags['save-raw']) fs.writeFileSync(flags['save-raw'], raw);
    if (obs.task.slice_id !== slice) fail(4, `reply is for slice ${obs.task.slice_id}, asked for ${slice}`);
    emit(obs);
  } else if (cmd === 'reconcile') {
    const pkg = readJson(flags.package || fail(7, '--package is required'));
    const obs = readJson(flags.observation || fail(7, '--observation is required'));
    const config = flags.config ? loadConfig(flags.config) : null;
    const r = reconcile(pkg, obs, config);
    emit(r);
    process.exit(r.exit_code);
  } else if (cmd === 'fixtures') {
    const dir = path.join(here, '..', '..', 'fixtures', 'd1');
    const config = readJson(path.join(dir, 'config.json'));
    const synthetic = (() => {
      const pkg = readJson(path.join(dir, 'package.json'));
      const obs = observe(readText(path.join(dir, 'get_slice.reviewed_pass.json')), { source: { kind: 'file', ...config }, now: new Date('2026-10-31T12:00:00Z') });
      return { package: bindingSummary(pkg), reconciliation: reconcile(pkg, obs, config) };
    })();
    const live = (() => {
      const pkg = readJson(path.join(dir, 'package.live.json'));
      const obs = readJson(path.join(dir, 'observation.live.2026-10-31.json'));
      return { package: bindingSummary(pkg), reconciliation: reconcile(pkg, obs, config) };
    })();
    emit({ synthetic_reviewed_pass: synthetic, live_recorded_2026_10_31: live, authority: 'none' });
    process.exit(Math.max(synthetic.reconciliation.exit_code, live.reconciliation.exit_code));
  } else {
    process.stdout.write(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 12).map((l) => l.replace(/^\/\/ ?/, '')).join('\n') + '\n');
    process.exit(words.length ? 7 : 0);
  }
} catch (e) {
  if (e instanceof RpcError) fail(e.exit, `${e.category}: ${e.message}`);
  if (e instanceof PackageError || e instanceof CanonError) fail(6, e.message);
  if (e instanceof ObservationError) fail(4, e.message);
  fail(6, e.message);
}
