// Test helpers for the release (slice A4). Every repository here is a throwaway one in the OS temp
// folder, made from this repository's committed HEAD; nothing is tagged or pushed in the real one.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildRelease } from '../src/build.js';
import { gitSource } from '../src/gitsource.js';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

// Fixed identity and dates, so two repositories made from the same tree get the same commit sha.
const FIXED = {
  GIT_AUTHOR_NAME: 'ODIR release test', GIT_AUTHOR_EMAIL: 'release-test@example.invalid', GIT_AUTHOR_DATE: '2026-01-01T00:00:00Z',
  GIT_COMMITTER_NAME: 'ODIR release test', GIT_COMMITTER_EMAIL: 'release-test@example.invalid', GIT_COMMITTER_DATE: '2026-01-01T00:00:00Z',
};
export const git = (cwd, args, input) => execFileSync('git', args, { cwd, input, env: { ...process.env, ...FIXED }, stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 64 * 1024 * 1024 });

let archive = null;
const tmpDirs = [];
export const tmp = (prefix = 'odir-release-') => { const d = fs.mkdtempSync(path.join(os.tmpdir(), prefix)); tmpDirs.push(d); return d; };
process.on('exit', () => { for (const d of tmpDirs) fs.rmSync(d, { recursive: true, force: true }); });

// A new repository holding this repository's committed HEAD tree as one commit.
export function makeRepo() {
  archive ??= execFileSync('git', ['archive', '--format=tar', 'HEAD'], { cwd: ROOT, maxBuffer: 256 * 1024 * 1024 });
  const dir = tmp();
  git(dir, ['init', '-q', '-b', 'main']);
  execFileSync('tar', ['-x', '-C', dir], { input: archive });
  git(dir, ['add', '-A']);
  git(dir, ['commit', '-q', '-m', 'release test tree']);
  return { dir, commit: git(dir, ['rev-parse', 'HEAD']).toString().trim() };
}

export function commitChange(dir, file, change, message = 'change') {
  const p = path.join(dir, file);
  fs.writeFileSync(p, change(fs.readFileSync(p, 'utf8')));
  git(dir, ['add', '-A']);
  git(dir, ['commit', '-q', '-m', message]);
  return git(dir, ['rev-parse', 'HEAD']).toString().trim();
}

export const tag = (dir, name, rev = 'HEAD') => git(dir, ['tag', name, rev]);
export const build = (dir, opts) => buildRelease(gitSource(dir, opts));

export function runNode(args, { cwd = ROOT } = {}) {
  try {
    return { code: 0, stdout: execFileSync(process.execPath, args, { cwd, stdio: ['ignore', 'pipe', 'pipe'] }).toString() };
  } catch (e) {
    return { code: e.status, stdout: String(e.stdout), stderr: String(e.stderr) };
  }
}

export const writeOutputs = (outputs) => {
  const dir = tmp('odir-dist-');
  for (const [name, text] of Object.entries(outputs)) fs.writeFileSync(path.join(dir, name), text);
  return dir;
};
