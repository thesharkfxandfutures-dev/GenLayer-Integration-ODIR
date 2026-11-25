import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { here, registryText, snapshotOf, queueMd } from './helpers.js';
import { PHASE1_FILES } from '../src/state.js';
import { runSchema } from '../src/recorder.js';
import { validate } from '../src/jsonschema.js';

const BIN = path.join(here, '..', 'bin', 'brain.mjs');
const node = (args, cwd) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8' });
const git = (dir, ...a) => execFileSync('git', ['-C', dir, ...a], { encoding: 'utf8', env: { ...process.env, GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@t', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@t' } }).trim();

function fixtureRepo({ pin, bases }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'brain-cli-'));
  git(dir, 'init', '-q', '-b', 'main');
  fs.mkdirSync(path.join(dir, 'brain'));
  fs.writeFileSync(path.join(dir, 'brain', 'QUEUE.md'), queueMd({ pin }));
  if (bases) for (const p of PHASE1_FILES) { fs.mkdirSync(path.join(dir, path.dirname(p)), { recursive: true }); fs.writeFileSync(path.join(dir, p), '{}\n'); }
  git(dir, 'add', '-A'); git(dir, 'commit', '-q', '-m', 'fixture');
  const reg = path.join(dir, '..', `${path.basename(dir)}-registry.js`);
  fs.writeFileSync(reg, registryText());
  return { dir, reg, out: path.join(dir, '..', `${path.basename(dir)}-out`) };
}

test('CLI dry run with the local git lock store: record written, brain/lock held then released, nothing pushed', () => {
  const snap = snapshotOf();
  const { dir, reg, out } = fixtureRepo({ pin: snap.registry_sha256, bases: false });
  const r = node(['dry-run', '--repo', dir, '--registry', reg, '--registry-ref', 'fixture', '--lock-store', 'git', '--out', out, '--run-id', 'cli-run-1'], dir);
  assert.equal(r.status, 0, r.stderr);
  const summary = JSON.parse(r.stdout);
  assert.deepEqual([summary.outcome, summary.stopped_at, summary.released], ['STOPPED', 'bases_not_merged', true]);
  const rec = JSON.parse(fs.readFileSync(path.join(out, 'cli-run-1.json'), 'utf8'));
  assert.equal(validate(runSchema, rec).ok, true);
  assert.equal(rec.lock.store, 'git');
  assert.equal(git(dir, 'rev-list', '--count', 'refs/heads/brain/lock'), '2');
  assert.equal(git(dir, 'remote'), '', 'no remote, nothing pushed');
  const second = node(['dry-run', '--repo', dir, '--registry', reg, '--registry-ref', 'fixture', '--lock-store', 'git', '--out', out, '--run-id', 'cli-run-2'], dir);
  assert.equal(second.status, 0, second.stderr);
  assert.equal(git(dir, 'rev-list', '--count', 'refs/heads/brain/lock'), '4', 'the branch only grows');
});

test('CLI: a held lock exits 3 and writes no record', () => {
  const snap = snapshotOf();
  const { dir, reg, out } = fixtureRepo({ pin: snap.registry_sha256, bases: true });
  // hold the lock with a long-lived lease written by hand through git plumbing
  const lease = JSON.stringify({ at: new Date().toISOString(), expires_at: new Date(Date.now() + 30 * 60e3).toISOString(), run_id: 'other', schema: 'odir-brain-lease/1', state: 'held' });
  const tree = git(dir, 'write-tree');
  const sha = execFileSync('git', ['-C', dir, 'commit-tree', tree, '-m', `brain-lock: held\n\n${lease}`], { encoding: 'utf8', env: { ...process.env, GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@t', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@t' } }).trim();
  git(dir, 'update-ref', 'refs/heads/brain/lock', sha);
  const r = node(['dry-run', '--repo', dir, '--registry', reg, '--registry-ref', 'fixture', '--lock-store', 'git', '--out', out, '--run-id', 'cli-run-3'], dir);
  assert.equal(r.status, 3);
  assert.equal(JSON.parse(r.stdout).outcome, 'LOCK_HELD');
  assert.equal(fs.existsSync(path.join(out, 'cli-run-3.json')), false);
});

test('CLI refuses the GitHub lock store and any live flag (A2 is a dry run)', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'brain-cli-'));
  for (const args of [
    ['dry-run', '--repo', tmp, '--lock-store', 'github'],
    ['dry-run', '--repo', tmp, '--live'],
    ['dry-run', '--repo', tmp, '--merge'],
    ['dry-run', '--repo', tmp, '--write-issue'],
  ]) {
    const r = node(args, tmp);
    assert.equal(r.status, 5, args.join(' '));
    assert.match(r.stderr, /owner/);
  }
});

test('CLI inspect prints a verified snapshot', () => {
  const { reg } = fixtureRepo({ pin: null, bases: false });
  const r = node(['inspect', '--registry', reg, '--registry-ref', 'fixture'], path.dirname(reg));
  assert.equal(r.status, 0, r.stderr);
  assert.equal(JSON.parse(r.stdout).registry_sha256, snapshotOf().registry_sha256);
});
