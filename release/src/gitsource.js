// Reads release inputs straight from git objects at one commit (slice A4), never from the working
// tree, so uncommitted edits, line-ending settings and file order on disk cannot change the
// templates or the bundled code. (The build tooling itself must equal the commit: see build.js.)
// Every git call ignores replace refs (`git replace` can make a sha read as other bytes) and any
// GIT_* setting in the environment (GIT_DIR, GIT_NAMESPACE, …), so a commit always reads the same.
import { execFileSync } from 'node:child_process';

const cleanEnv = () => {
  const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('GIT_')));
  return { ...env, GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1' };
};
const git = (cwd, args, opts = {}) => execFileSync('git', ['--no-replace-objects', ...args], { cwd, env: cleanEnv(), maxBuffer: 64 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'], ...opts });
const utf8 = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });

export const TAG = /^templates-v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

// { tag, ref } → { tag, commit, read(path), list(prefix) }. With a tag, the ref defaults to the tag
// and must be the commit the tag points at. Without one, the build is untagged (tag null).
export function gitSource(cwd, { tag = null, ref = null } = {}) {
  if (tag !== null && !TAG.test(tag)) throw new Error(`tag ${JSON.stringify(tag)} must look like templates-v1.2.3`);
  if (tag === null && !ref) throw new Error('give a tag (templates-vX.Y.Z) or a ref');
  if (ref !== null && (typeof ref !== 'string' || ref.startsWith('-'))) throw new Error(`no commit for ${JSON.stringify(ref)}`);
  const rev = (r) => {
    try { return git(cwd, ['rev-parse', '--verify', '--end-of-options', `${r}^{commit}`]).toString().trim(); }
    catch { throw new Error(`no commit for ${JSON.stringify(r)}`); }
  };
  const commit = rev(ref ?? `refs/tags/${tag}`);
  if (tag !== null) {
    const tagged = rev(`refs/tags/${tag}`);
    if (tagged !== commit) throw new Error(`tag ${tag} points at ${tagged}, not ${commit}`);
  }
  return {
    tag,
    commit,
    read(path) {
      let buf;
      try { buf = git(cwd, ['cat-file', 'blob', `${commit}:${path}`]); } catch { throw new Error(`${path}: not in commit ${commit}`); }
      try { return utf8.decode(buf); } catch { throw new Error(`${path}: not valid UTF-8`); }
    },
    list(prefix) {
      const out = git(cwd, ['ls-tree', '-r', '-z', '--name-only', commit, '--', prefix]).toString('utf8');
      return out.split('\0').filter(Boolean).sort();
    },
  };
}
