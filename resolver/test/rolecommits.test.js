import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkRoleCommits, commitsInRange, roleFolder } from '../src/rolecommits.js';

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'check-role-commits.mjs');

test('roleFolder finds the role folder on main and in the holding bay', () => {
  assert.deepEqual(roleFolder('templates/roles/photographer/module.json'), { key: 'photographer', folder: 'templates/roles/photographer/' });
  assert.deepEqual(roleFolder('holding/templates/maker/photographer/module.json'), { key: 'photographer', folder: 'holding/templates/maker/photographer/' });
  assert.deepEqual(roleFolder('holding/templates/dj/dj/module.json'), { key: 'dj', folder: 'holding/templates/dj/dj/' });
  assert.equal(roleFolder('templates/bases/p2p.json'), null);
  assert.equal(roleFolder('templates/roles/README.md'), null);
  assert.equal(roleFolder('holding/templates/maker/README.md'), null);
});

test('a role commit that keeps to its folder passes; other commits are not role commits', () => {
  assert.deepEqual(checkRoleCommits([
    { sha: 'a1', files: ['templates/roles/photographer/module.json'] },
    { sha: 'a2', files: ['holding/templates/craft/makeup_artist/module.json', 'holding/templates/craft/makeup_artist/notes.md'] },
    { sha: 'a3', files: ['templates/bases/p2p.json', 'schema/agreement.v1.json', 'resolver/src/resolve.js'] },
  ]), []);
});

test('a role commit that touches anything else, or two roles, fails', () => {
  const p = checkRoleCommits([
    { sha: 'b1', files: ['templates/roles/photographer/module.json', 'templates/bases/p2p.json'] },
    { sha: 'b2', files: ['templates/roles/photographer/module.json', 'templates/roles/videographer/module.json'] },
    { sha: 'b3', files: ['templates/roles/photographer/module.json', 'holding/templates/maker/photographer/module.json'] },
    { sha: 'b4', files: ['templates/roles/README.md'] },
  ]);
  assert.equal(p.length, 4);
  assert.match(p[0], /^b1: a role commit also touches templates\/bases\/p2p\.json/);
  assert.match(p[1], /^b2: a role commit touches 2 role folders/);
  assert.match(p[2], /^b3: a role commit touches 2 role folders/);
  assert.match(p[3], /^b4: templates\/roles\/README\.md sits directly in a role tree/);
});

function tempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'odir-rolecommits-'));
  const git = (...a) => execFileSync('git', a, { cwd: dir, encoding: 'utf8' }).trim();
  git('init', '-q', '-b', 'main');
  git('config', 'user.email', 'test@example.invalid');
  git('config', 'user.name', 'test');
  const commit = (files, msg) => {
    for (const [f, body] of Object.entries(files)) {
      const p = path.join(dir, f);
      if (body === null) { fs.rmSync(p); continue; }
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, body);
    }
    git('add', '-A');
    git('commit', '-q', '-m', msg);
    return git('rev-parse', 'HEAD');
  };
  return { dir, git, commit };
}

test('real git history: the range is read per commit, renames count on both sides, merges are listed not checked', () => {
  const { dir, git, commit } = tempRepo();
  const base = commit({ 'README.md': 'x\n' }, 'root');
  commit({ 'templates/roles/photographer/module.json': '{}\n' }, 'role ok');
  git('checkout', '-q', '-b', 'side');
  commit({ 'side.txt': 's\n' }, 'side');
  git('checkout', '-q', 'main');
  commit({ 'schema/a.json': '{}\n' }, 'schema');
  git('merge', '-q', '--no-ff', '-m', 'merge side', 'side');
  // a rename out of a role folder touches the role folder and somewhere else
  fs.mkdirSync(path.join(dir, 'templates', 'bases'), { recursive: true });
  git('mv', 'templates/roles/photographer/module.json', 'templates/bases/p2p.json');
  git('commit', '-q', '-m', 'rename');
  const { commits, merges } = commitsInRange(dir, base, 'HEAD');
  assert.equal(commits.length, 4);
  assert.equal(merges.length, 1);
  const p = checkRoleCommits(commits);
  assert.equal(p.length, 1);
  assert.match(p[0], /also touches templates\/bases\/p2p\.json/);
  const cli = spawnSync('node', [BIN, '--base', base, '--repo', dir], { encoding: 'utf8' });
  assert.equal(cli.status, 1);
  assert.match(cli.stdout, /4 commit\(s\) checked .*1 merge commit\(s\) not checked/);
  assert.match(cli.stdout, /FAIL .*also touches templates\/bases\/p2p\.json/);
});

test('the CLI passes a clean range and refuses bad arguments', () => {
  const { dir, commit } = tempRepo();
  const base = commit({ 'README.md': 'x\n' }, 'root');
  commit({ 'templates/roles/photographer/module.json': '{}\n' }, 'role');
  commit({ 'templates/bases/p2p.json': '{}\n', 'resolver/x.js': '\n' }, 'code');
  const ok = spawnSync('node', [BIN, '--base', base, '--repo', dir], { encoding: 'utf8' });
  assert.equal(ok.status, 0, ok.stdout + ok.stderr);
  assert.match(ok.stdout, /2 commit\(s\) checked/);
  assert.equal(spawnSync('node', [BIN, '--repo', dir], { encoding: 'utf8' }).status, 2);
  assert.equal(spawnSync('node', [BIN, '--base', 'nope', '--repo', dir], { encoding: 'utf8' }).status, 2);
});
