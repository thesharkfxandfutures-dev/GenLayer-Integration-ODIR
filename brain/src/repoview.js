// Read-only views of the ODIR repository for deriveState().
//   LocalRepoView  — a local git checkout (`git show`, `git ls-tree`); used by the dry run.
//   MemoryRepoView — fixed trees, for tests.
// Neither writes anything.
import { execFileSync } from 'node:child_process';

export class LocalRepoView {
  // refs maps a logical name ('main', 'brain/holding') to candidate git refs in `dir`; the first
  // that exists is read (remote-tracking first, so a fetched clone reads what GitHub has).
  constructor({ dir, refs = { main: ['origin/main', 'main'], 'brain/holding': ['origin/brain/holding', 'brain/holding'] } }) { this.dir = dir; this.refs = refs; }
  #git(args) { return execFileSync('git', ['-C', this.dir, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 64 << 20 }); }
  #ref(name) { return [].concat(this.refs[name] || name).find((r) => this.#exists(r)) || null; }
  #exists(ref) { try { this.#git(['rev-parse', '--verify', '-q', `${ref}^{commit}`]); return true; } catch { return false; } }
  async readFile(ref, path) {
    const r = this.#ref(ref);
    if (!r) return null;
    try { return this.#git(['show', `${r}:${path}`]); } catch { return null; }
  }
  async listTree(ref) {
    const r = this.#ref(ref);
    if (!r) return null;
    return this.#git(['ls-tree', '-r', '--name-only', r]).split('\n').filter(Boolean);
  }
}

export class MemoryRepoView {
  // trees: { main: { 'path': 'content', ... }, 'brain/holding': {...} }
  constructor(trees = {}) { this.trees = trees; }
  async readFile(ref, path) { const t = this.trees[ref]; return t && Object.prototype.hasOwnProperty.call(t, path) ? t[path] : null; }
  async listTree(ref) { const t = this.trees[ref]; return t ? Object.keys(t) : null; }
}
