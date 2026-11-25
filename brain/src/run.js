// One Brain run, dry-run mode (slice A2): take the lock, work out state, run the four stop checks,
// plan the brain-blocked issue, write a run record, release the lock. It drafts nothing, signs
// nothing, deploys nothing and merges nothing.
//
// A run that cannot take the lock writes nothing and exits. A run that loses its lease mid-run
// stops at its next write (LeaseLostError) and writes nothing more; its lease is not released
// because it is no longer its own.
import { LeaseLock, LeaseLostError } from './lock.js';
import { inspectRegistry, verifySnapshot } from './inspector.js';
import { deriveState } from './state.js';
import { evaluateStops, firstRunStop, pickAction } from './stops.js';
import { planBlockedIssue } from './blocked.js';
import { Recorder, RUN_SCHEMA } from './recorder.js';

const iso = (ms) => new Date(ms).toISOString();

export async function runOnce({
  runId, clock = () => Date.now(), store, storeName = 'memory',
  repo, registry = null, snapshot: givenSnapshot = null,
  pulls = [], pullsSource = null, openBlockedIssues = [], genskillAvailable = false,
  sink, issues = null, dryRun = true, hooks = {},
}) {
  const startedAt = iso(clock());
  const lock = new LeaseLock({ store, runId, clock });
  const acq = await lock.acquire();
  if (!acq.ok) return { outcome: `LOCK_${acq.reason.toUpperCase()}`, acquired: false, ...acq, writes: [] };

  const recorder = new Recorder({ lock, sink, issues, dryRun });
  try {
    let snapshot = null, snapshotProblem = null;
    try {
      if (registry) snapshot = inspectRegistry(registry.text, { appId: registry.appId, ref: registry.ref });
      else if (givenSnapshot) {
        const v = verifySnapshot(givenSnapshot);
        if (v.ok) snapshot = givenSnapshot; else snapshotProblem = v.problems.join('; ');
      } else snapshotProblem = 'no registry text or snapshot supplied';
    } catch (e) { snapshotProblem = e.message; }

    const state = await deriveState({ repo, snapshot: snapshotProblem ? null : snapshot, pulls });
    const stops = evaluateStops({ snapshot, snapshotProblem, state, genskillAvailable });
    const action = pickAction({ stops, state });
    const stop = firstRunStop(stops);
    const plan = planBlockedIssue({ issues: openBlockedIssues, stops, runId, at: startedAt });
    if (hooks.beforeWrites) await hooks.beforeWrites();

    const claims = [
      { claim: `lock taken on ${storeName} store (${acq.mode})`, grade: 'OBSERVED', evidence: `brain/lock head ${acq.sha}` },
      snapshot && !snapshotProblem
        ? { claim: 'Inspector snapshot passes its schema and both hashes', grade: 'OBSERVED', evidence: `snapshot ${snapshot.snapshot_sha256}` }
        : { claim: 'Inspector snapshot', grade: 'NOT_RUN', evidence: snapshotProblem || 'none' },
      pullsSource
        ? { claim: `open pull requests read (${pulls.length})`, grade: 'OBSERVED', evidence: pullsSource }
        : { claim: 'open pull requests', grade: 'NOT_RUN', evidence: 'no pull-request list supplied to this run' },
      { claim: 'brain-blocked issue updated', grade: 'NOT_RUN', evidence: dryRun ? 'dry run: plan recorded, not applied' : 'applied after this record' },
      { claim: 'action executed', grade: 'NOT_RUN', evidence: 'dry run drafts nothing' },
    ];
    const record = {
      schema: RUN_SCHEMA,
      run_id: runId,
      mode: 'dry-run',
      started_at: startedAt,
      finished_at: iso(clock()),
      lock: { store: storeName, acquired: acq.mode, sha: acq.sha, took_over_from: lock.lease.took_over_from || null },
      inspector: {
        snapshot_sha256: snapshot && !snapshotProblem ? snapshot.snapshot_sha256 : null,
        registry_sha256: snapshot && !snapshotProblem ? snapshot.registry_sha256 : null,
        role_count: snapshot && !snapshotProblem ? snapshot.role_count : null,
        source_ref: snapshot && !snapshotProblem ? snapshot.source.ref : null,
        problem: snapshotProblem,
      },
      state: {
        queue_source: state.queue?.source || null,
        pinned_registry_sha256: state.queue?.pinned_registry_sha256 || null,
        queue_error: state.queue_error,
        counts: state.counts,
        next_queued: state.next_queued,
        bases_merged: state.bases.merged,
        bases_missing: state.bases.missing,
        holding_exists: state.holding_exists,
        unknown_queue_keys: state.unknown_queue_keys,
        pulls_source: pullsSource,
      },
      stops: stops.map(({ reason, scope, open, detail }) => ({ reason, scope, open, detail })),
      stopped_at: stop ? stop.reason : null,
      action: { ...action, executed: false },
      issue_plan: { action: plan.action, added: plan.added, cleared: plan.cleared, kept: plan.kept, close_duplicates: plan.close_duplicates },
      claims,
      outcome: stop ? 'STOPPED' : action.would_do === 'none' ? 'IDLE' : 'WOULD_ACT',
    };
    const recordName = await recorder.writeRunRecord(record);
    const issueResult = await recorder.applyIssuePlan(plan);
    if (hooks.beforeRelease) await hooks.beforeRelease();
    const releasedSha = await lock.release();
    return { outcome: record.outcome, acquired: true, record, recordName, plan, issueResult, released: true, releasedSha, writes: recorder.writes };
  } catch (e) {
    if (e instanceof LeaseLostError) return { outcome: 'LEASE_LOST', acquired: true, reason: e.reason, detail: e.message, released: false, writes: recorder.writes };
    // Any other failure: give the lock back (still behind the lease check) so one transient error
    // does not block every run for 40 minutes, then surface the error.
    if (lock.held) { try { await lock.release(); } catch { /* lease already lost: nothing to give back */ } }
    throw e;
  }
}
