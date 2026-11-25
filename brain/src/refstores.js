// Two real stores for the lease lock (see lock.js for the store contract).
//
// GitRefStore   — a LOCAL git repository, through git plumbing. `git update-ref <ref> <new> <old>`
//                 is git's own compare-and-swap (and an all-zero <old> means "must not exist").
//                 Used by the dry run and by the race tests. It never pushes anywhere.
// GitHubRefStore — the GitHub REST git-data API, with an injected fetch. Create is
//                 POST /git/refs (fails when the branch exists); moving is PATCH /git/refs with
//                 force: false (fails unless it is a fast-forward). It has no delete. It is wired
//                 to the CLI only after the owner switches the Brain on (A2 stops at the PR).
//
// Both write a tree holding one file, LEASE.json (the lease, for people browsing the branch);
// the commit message is the source of truth.
import { execFileSync } from 'node:child_process';

const ZERO = '0'.repeat(40);
const leaseFile = (message) => {
  const body = message.split('\n\n').slice(1).join('\n\n');
  return body.endsWith('\n') ? body : `${body}\n`;
};

export class GitRefStore {
  constructor({ dir, ref = 'refs/heads/brain/lock' }) {
    if (!ref.startsWith('refs/heads/')) throw new Error('ref must be a full refs/heads/ name');
    this.dir = dir; this.ref = ref;
    this.env = {
      ...process.env,
      GIT_AUTHOR_NAME: 'odir-brain', GIT_AUTHOR_EMAIL: 'odir-brain@invalid',
      GIT_COMMITTER_NAME: 'odir-brain', GIT_COMMITTER_EMAIL: 'odir-brain@invalid',
    };
  }
  #git(args, input) {
    return execFileSync('git', ['-C', this.dir, ...args], { env: this.env, input, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
  }
  #tryGit(args, input) {
    try { return { ok: true, out: this.#git(args, input) }; } catch (e) { return { ok: false, err: String(e.stderr || e.message) }; }
  }
  #commit(parent, message) {
    const blob = this.#git(['hash-object', '-w', '--stdin'], leaseFile(message)).trim();
    const tree = this.#git(['mktree'], `100644 blob ${blob}\tLEASE.json\n`).trim();
    const args = ['commit-tree', tree, ...(parent ? ['-p', parent] : []), '-F', '-'];
    return this.#git(args, message).trim();
  }
  async getRef() {
    const r = this.#tryGit(['rev-parse', '--verify', '-q', `${this.ref}^{commit}`]);
    if (!r.ok) return null;
    const sha = r.out.trim();
    return { sha, message: this.#git(['cat-file', 'commit', sha]).split('\n\n').slice(1).join('\n\n') };
  }
  async createRef(message) {
    const sha = this.#commit(null, message);
    const r = this.#tryGit(['update-ref', this.ref, sha, ZERO]);
    return r.ok ? { ok: true, sha } : { ok: false, reason: 'exists' };
  }
  async fastForward(expectedSha, message) {
    const sha = this.#commit(expectedSha, message);
    const r = this.#tryGit(['update-ref', this.ref, sha, expectedSha]);
    return r.ok ? { ok: true, sha } : { ok: false, reason: 'not_fast_forward' };
  }
}

export class GitHubRefStore {
  constructor({ owner, repo, token, fetch: f = globalThis.fetch, branch = 'brain/lock', api = 'https://api.github.com' }) {
    if (!owner || !repo) throw new Error('owner and repo required');
    this.base = `${api}/repos/${owner}/${repo}`; this.branch = branch; this.token = token; this.fetch = f;
  }
  async #call(method, path, body) {
    if (method === 'DELETE') throw new Error('the lock branch is never deleted');
    const res = await this.fetch(`${this.base}${path}`, {
      method,
      headers: {
        accept: 'application/vnd.github+json', 'x-github-api-version': '2022-11-28',
        ...(this.token ? { authorization: `Bearer ${this.token}` } : {}),
        ...(body ? { 'content-type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    return { status: res.status, json: text ? JSON.parse(text) : null };
  }
  async #commit(parent, message) {
    const tree = await this.#call('POST', '/git/trees', { tree: [{ path: 'LEASE.json', mode: '100644', type: 'blob', content: leaseFile(message) }] });
    if (tree.status !== 201) throw new Error(`create tree: HTTP ${tree.status}`);
    const c = await this.#call('POST', '/git/commits', { message, tree: tree.json.sha, parents: parent ? [parent] : [] });
    if (c.status !== 201) throw new Error(`create commit: HTTP ${c.status}`);
    return c.json.sha;
  }
  async getRef() {
    const r = await this.#call('GET', `/git/ref/heads/${this.branch}`);
    if (r.status === 404) return null;
    if (r.status !== 200) throw new Error(`read brain/lock: HTTP ${r.status}`);
    const sha = r.json.object.sha;
    const c = await this.#call('GET', `/git/commits/${sha}`);
    if (c.status !== 200) throw new Error(`read lock commit: HTTP ${c.status}`);
    return { sha, message: c.json.message };
  }
  async createRef(message) {
    const sha = await this.#commit(null, message);
    const r = await this.#call('POST', '/git/refs', { ref: `refs/heads/${this.branch}`, sha });
    if (r.status === 201) return { ok: true, sha };
    if (r.status === 422) return { ok: false, reason: 'exists' };
    throw new Error(`create brain/lock: HTTP ${r.status}`);
  }
  async fastForward(expectedSha, message) {
    const sha = await this.#commit(expectedSha, message);
    const r = await this.#call('PATCH', `/git/refs/heads/${this.branch}`, { sha, force: false });
    if (r.status === 200) return { ok: true, sha };
    if (r.status === 422) return { ok: false, reason: 'not_fast_forward' };
    throw new Error(`move brain/lock: HTTP ${r.status}`);
  }
}
