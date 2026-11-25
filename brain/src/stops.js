// The four stop checks, in this order:
//   1. registry_hash_changed — the SnapLink role registry's hash (from the Inspector snapshot) is not
//      the one pinned in brain/QUEUE.md (also: not pinned, snapshot unusable, QUEUE.md unreadable);
//   2. bases_not_merged      — the phase 1 bases and schemas are not on main yet;
//   3. queue_empty           — no role is left at stage `queued`;
//   4. genskill_missing      — the genskill tools are not available (stops on-chain steps only).
// Every check is evaluated each run so the brain-blocked issue can close cleared reasons.
// open: true | false | null (null = could not be evaluated this run; the issue keeps it as it is).
export const STOP_REASONS = ['registry_hash_changed', 'bases_not_merged', 'queue_empty', 'genskill_missing'];

export function evaluateStops({ snapshot, snapshotProblem, state, genskillAvailable }) {
  const stops = [];
  let reg;
  if (snapshotProblem) reg = { open: true, detail: `Inspector snapshot unusable: ${snapshotProblem}` };
  else if (state.queue_error) reg = { open: true, detail: `brain/QUEUE.md unreadable: ${state.queue_error}` };
  else if (!state.queue.pinned_registry_sha256) reg = { open: true, detail: `registry not pinned in brain/QUEUE.md; Inspector observed ${snapshot.registry_sha256}` };
  else if (state.queue.pinned_registry_sha256 !== snapshot.registry_sha256) reg = { open: true, detail: `pinned ${state.queue.pinned_registry_sha256}, Inspector observed ${snapshot.registry_sha256}; the owner re-plans brain/QUEUE.md` };
  else reg = { open: false, detail: `registry ${snapshot.registry_sha256} matches the pin` };
  stops.push({ reason: 'registry_hash_changed', scope: 'run', ...reg });

  stops.push({
    reason: 'bases_not_merged', scope: 'run',
    open: !state.bases.merged,
    detail: state.bases.merged ? 'phase 1 bases and schemas are on main' : `missing on main: ${state.bases.missing.join(', ')}`,
  });

  const canCount = Boolean(snapshot) && !snapshotProblem && Boolean(state.queue) && typeof state.counts.queued === 'number';
  stops.push({
    reason: 'queue_empty', scope: 'run',
    open: canCount ? state.counts.queued === 0 : null,
    detail: canCount ? `${state.counts.queued} queued of ${state.queue.length}` : 'not evaluated (no usable snapshot or queue)',
  });

  stops.push({
    reason: 'genskill_missing', scope: 'onchain',
    open: !genskillAvailable,
    detail: genskillAvailable ? 'genskill tools available' : 'genskill tools missing: on-chain steps stop; template work carries on',
  });
  return stops;
}

export const firstRunStop = (stops) => stops.find((s) => s.scope === 'run' && s.open === true) || null;

// The action the run would take. A2 is a dry run: nothing is executed. Later slices add, highest
// first: verify a deployment, turn a `promote` issue into a PR, answer review comments, re-draft a
// STALE item, draft the next on-chain contract, re-inspect SnapLink.
export function pickAction({ stops, state }) {
  const stop = firstRunStop(stops);
  if (stop) return { would_do: 'none', item: null, because: `stopped: ${stop.reason}` };
  if (state.next_queued) return { would_do: 'draft_role', item: state.next_queued, because: 'next queued role' };
  return { would_do: 'none', item: null, because: 'nothing queued' };
}
