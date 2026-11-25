// The one open `brain-blocked` issue, keyed by reason. Notify only on change:
//   * a reason already in the issue is not reported again (no edit, no comment);
//   * a new reason is added (one edit + one comment naming it);
//   * a reason whose check now passes is removed; when none is left the issue closes;
//   * a reason that could not be evaluated this run (open: null) is left exactly as it is;
//   * if more than one open brain-blocked issue exists, the oldest is kept and the rest are closed.
// Each reason is one line carrying a marker `<!-- brain-blocked:<reason> -->`.
export const LABEL = 'brain-blocked';
const MARK = /<!-- brain-blocked:([a-z_]+) -->/;

export function parseIssueReasons(body) {
  const out = new Map();
  for (const line of String(body || '').split('\n')) {
    const m = MARK.exec(line);
    if (m && !out.has(m[1])) out.set(m[1], line);
  }
  return out;
}

const line = (stop, runId, at) => `- <!-- brain-blocked:${stop.reason} --> **${stop.reason}** — since ${at} (run ${runId}): ${stop.detail}`;

export function renderBody(lines) {
  return [
    'The ODIR Brain is stopped or limited by the conditions below. It reports each reason once,',
    'removes it when the check passes and closes this issue when none is left.',
    '',
    ...lines,
    '',
  ].join('\n');
}

// issues: the open issues labelled brain-blocked, [{ number, body }].
// -> { action: 'none'|'create'|'update'|'close', number?, body?, added: [], cleared: [], kept: [], close_duplicates: [], comment? }
export function planBlockedIssue({ issues = [], stops, runId, at }) {
  const sorted = [...issues].sort((a, b) => a.number - b.number);
  const keep = sorted[0] || null;
  const close_duplicates = sorted.slice(1).map((i) => i.number);
  const existing = keep ? parseIssueReasons(keep.body) : new Map();
  const byReason = new Map(stops.map((s) => [s.reason, s]));
  const lines = [], added = [], cleared = [], kept = [];
  // Keep existing reasons in their original order and wording unless their check now passes.
  for (const [reason, text] of existing) {
    const s = byReason.get(reason);
    if (s && s.open === false) { cleared.push(reason); continue; }
    lines.push(text); kept.push(reason);
  }
  for (const s of stops) {
    if (s.open === true && !existing.has(s.reason)) { lines.push(line(s, runId, at)); added.push(s.reason); }
  }
  const base = { added, cleared, kept, close_duplicates };
  if (!keep) {
    if (!added.length) return { action: 'none', ...base };
    return { action: 'create', title: `Brain blocked: ${added.join(', ')}`, labels: [LABEL], body: renderBody(lines), ...base };
  }
  if (!lines.length) return { action: 'close', number: keep.number, comment: `Cleared: ${cleared.join(', ')}. Closing.`, ...base };
  if (!added.length && !cleared.length) return { action: 'none', number: keep.number, ...base };
  const parts = [added.length && `New: ${added.join(', ')}.`, cleared.length && `Cleared: ${cleared.join(', ')}.`].filter(Boolean);
  return { action: 'update', number: keep.number, body: renderBody(lines), comment: parts.join(' '), ...base };
}
