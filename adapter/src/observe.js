// Turn one `get_slice` reply from the contract into an observation record
// (schema odir-genlayer-observation/1). An observation says what the configured contract
// reported at one instant, from one source. It carries no authority and never includes the
// evidence text (only its digest): the text already lives in the local package.
import { sha256 } from './canon.js';

export const OBSERVATION_SCHEMA = 'odir-genlayer-observation/1';
export const SLICE_STATUSES = ['REGISTERED', 'SUBMITTED', 'REVIEWED_PASS', 'REJECTED', 'INSUFFICIENT', 'APPROVED', 'CONSUMED', 'CANCELLED'];
export const ATTEMPT_STATUSES = ['SUBMITTED', 'REVIEWED_PASS', 'REJECTED', 'INSUFFICIENT', 'APPROVED', 'CONSUMED'];
export const VERDICTS = ['PASS', 'FAIL', 'INSUFFICIENT_EVIDENCE'];
const HEX40 = /^0x[0-9a-fA-F]{40}$/, HEX64 = /^[0-9a-f]{64}$/;

export class ObservationError extends Error {
  constructor(problems) { super(`malformed contract reply: ${problems.join('; ')}`); this.problems = problems; }
}

// `raw` is the string the view returned (the contract returns canonical JSON as text).
export function observe(raw, { source, now = new Date() }) {
  const bad = [];
  const need = (c, m) => { if (!c) bad.push(m); };
  need(source && Number.isInteger(source.chain_id), 'source.chain_id');
  need(source && HEX40.test(source.contract_address || ''), 'source.contract_address');
  need(source && ['file', 'rpc'].includes(source.kind), 'source.kind must be file|rpc');
  need(typeof raw === 'string' && raw.length <= 200_000, 'reply must be text under 200 kB');
  if (bad.length) throw new ObservationError(bad);
  let r;
  try { r = JSON.parse(raw); } catch { throw new ObservationError(['reply is not JSON']); }
  const t = r?.task;
  need(t && typeof t === 'object', 'reply.task missing');
  if (bad.length) throw new ObservationError(bad);
  need(typeof t.slice_id === 'string', 'task.slice_id');
  need(SLICE_STATUSES.includes(t.status), `task.status not one of ${SLICE_STATUSES.join('|')}`);
  need(Number.isInteger(t.attempt) && t.attempt >= 0, 'task.attempt');
  need(Array.isArray(t.criteria) && t.criteria.every((c) => typeof c === 'string'), 'task.criteria must be string[]');
  need(HEX64.test(t.criteria_sha256 || ''), 'task.criteria_sha256');
  need(HEX64.test(t.task_sha256 || ''), 'task.task_sha256');
  for (const role of ['builder', 'reviewer', 'executor']) need(HEX40.test(t[role] || ''), `task.${role} address`);
  need(typeof r.paused === 'boolean', 'reply.paused');
  need(typeof r.predecessor_approved === 'boolean', 'reply.predecessor_approved');
  let attempt = null;
  if (t.attempt > 0) {
    const a = r.latest_attempt;
    need(a && typeof a === 'object', 'latest_attempt missing although task.attempt > 0');
    if (a && typeof a === 'object') {
      need(a.attempt === t.attempt, 'latest_attempt.attempt differs from task.attempt');
      need(a.slice_id === t.slice_id, 'latest_attempt.slice_id differs from task.slice_id');
      need(HEX64.test(a.evidence_sha256 || ''), 'latest_attempt.evidence_sha256');
      need(typeof a.evidence === 'string' && sha256(a.evidence) === a.evidence_sha256, 'latest_attempt.evidence does not hash to evidence_sha256');
      need(ATTEMPT_STATUSES.includes(a.status), 'latest_attempt.status');
      need(a.task_sha256 === t.task_sha256, 'latest_attempt.task_sha256 differs from task');
      need(a.criteria_sha256 === t.criteria_sha256, 'latest_attempt.criteria_sha256 differs from task');
      let review = null;
      if (a.review !== null && a.review !== undefined) {
        need(a.review && VERDICTS.includes(a.review.verdict), 'latest_attempt.review.verdict');
        need(Array.isArray(a.review?.checks) && a.review.checks.length === t.criteria.length, 'review.checks count differs from criteria count');
        review = a.review && {
          verdict: a.review.verdict,
          checks: (a.review.checks || []).map((c) => ({ index: c.index, status: c.status, quote: c.quote, reason: c.reason })),
        };
      } else {
        need(a.status === 'SUBMITTED', 'attempt past SUBMITTED must carry a review');
      }
      attempt = {
        attempt: a.attempt, status: a.status, evidence_sha256: a.evidence_sha256,
        review, approved_by: a.approved_by || '', consumed_by: a.consumed_by || '',
      };
    }
  }
  if (bad.length) throw new ObservationError(bad);
  return {
    schema: OBSERVATION_SCHEMA,
    observed_at: now.toISOString(),
    source: {
      kind: source.kind, rpc_url: source.rpc_url || null, chain_id: source.chain_id,
      contract_address: source.contract_address, contract_code_sha256: source.contract_code_sha256 || null,
      method: 'get_slice', network_label: source.network_label || null,
      state_selection: source.state_selection || null, client_version: source.client_version || null,
    },
    raw_sha256: sha256(raw),
    paused: r.paused,
    predecessor_approved: r.predecessor_approved,
    task: {
      slice_id: t.slice_id, status: t.status, attempt: t.attempt, scope: t.scope,
      criteria: t.criteria, criteria_sha256: t.criteria_sha256, task_sha256: t.task_sha256,
      builder: t.builder, reviewer: t.reviewer, executor: t.executor, predecessor_id: t.predecessor_id ?? '',
    },
    latest_attempt: attempt,
    // Stated on every record so no consumer can mistake an observation for a permit.
    authority: 'none',
    assurance: source.kind === 'rpc' ? 'single_endpoint_unverified' : 'supplied_file_unverified',
  };
}
