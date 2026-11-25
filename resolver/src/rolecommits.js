// CI rule (slice A3): a role commit touches only its own folder.
// A commit that touches any role folder — templates/roles/<role_key>/ on main, or
// holding/templates/<family>/<role_key>/ in the holding bay — must touch nothing else: no other
// role, no base, no schema, no code. Commits that touch no role folder are not role commits and
// are not limited by this rule.
import { execFileSync } from 'node:child_process';

const ROLE_PATH = [
  /^(templates\/roles\/([^/]+)\/)[^/]/,
  /^(holding\/templates\/[^/]+\/([^/]+)\/)[^/]/,
];
const ROLE_PREFIX = [/^templates\/roles\//, /^holding\/templates\//];

// The role folder a path sits in ({ key, folder }), or null when it is not inside one.
export function roleFolder(file) {
  for (const re of ROLE_PATH) {
    const m = re.exec(file);
    if (m) return { key: m[2], folder: m[1] };
  }
  return null;
}

// commits: [{ sha, files: [path] }] → problems (empty when every role commit keeps to its folder).
export function checkRoleCommits(commits) {
  const problems = [];
  for (const { sha, files } of commits) {
    const short = String(sha).slice(0, 10);
    const roleTree = files.filter((f) => ROLE_PREFIX.some((re) => re.test(f)));
    if (!roleTree.length) continue;
    const loose = roleTree.filter((f) => !roleFolder(f));
    if (loose.length) problems.push(`${short}: ${loose.join(', ')} sits directly in a role tree, not in a role folder`);
    const folders = [...new Set(roleTree.map(roleFolder).filter(Boolean).map((r) => r.folder))];
    if (folders.length > 1) problems.push(`${short}: a role commit touches ${folders.length} role folders (${folders.join(', ')})`);
    const others = files.filter((f) => !ROLE_PREFIX.some((re) => re.test(f)));
    if (others.length) problems.push(`${short}: a role commit also touches ${others.join(', ')}`);
  }
  return problems;
}

const git = (cwd, ...a) => execFileSync('git', a, { cwd, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });

// Every commit in base..head with the paths it touches. Paths are read NUL-separated (-z), so a
// non-ASCII path is never quoted and always matches. Renames are split into a delete and an add, so
// both sides count. A merge commit is checked on what the merge itself changed (-c: the paths that
// differ from every parent — conflict resolutions and "evil merge" edits); what it brings in from
// its other parent is checked as those commits.
export function commitsInRange(cwd, base, head) {
  const list = (args) => git(cwd, ...args).split('\n').filter(Boolean);
  const nulPaths = (out) => out.split('\0').filter(Boolean);
  const shas = list(['rev-list', '--reverse', `${base}..${head}`]);
  const merges = new Set(list(['rev-list', '--merges', `${base}..${head}`]));
  const commits = shas.map((sha) => ({
    sha,
    merge: merges.has(sha),
    files: merges.has(sha)
      ? nulPaths(git(cwd, 'diff-tree', '-z', '-c', '--no-commit-id', '--name-only', '-r', sha))
      : nulPaths(git(cwd, 'diff-tree', '-z', '--root', '--no-commit-id', '--name-only', '--no-renames', '-r', sha)),
  }));
  return { commits, merges: [...merges] };
}
