// Compare a local review package with an observation of the contract. The result is a
// statement for ODIR's Governor and for Mission Control; it is never a permit. The Governor
// still needs the run contract, an unchanged candidate, local verification and (where policy
// says so) a human disposition before anything is authorised.
import { criteriaSha256, validatePackage } from './package.js';

export const DECISIONS = [
  'CONSISTENT',          // remote record matches this package; remote_status says where it is
  'PENDING_REVIEW',      // submitted, no consensus result yet
  'NOT_SUBMITTED',       // the contract has no attempt for this package yet
  'SUPERSEDED',          // a later attempt exists on the contract; this package is stale
  'EXPIRED',             // past lifetime.accept_until at observation time
  'CONFIG_MISMATCH',     // wrong chain, wrong contract or wrong code identity
  'INTEGRITY_MISMATCH',  // same slice and attempt but different criteria or evidence: investigate
];

export const EXIT = { CONSISTENT: 0, PENDING_REVIEW: 2, NOT_SUBMITTED: 2, SUPERSEDED: 3, EXPIRED: 3, CONFIG_MISMATCH: 5, INTEGRITY_MISMATCH: 4 };

export function reconcile(pkg, obs, config = null) {
  validatePackage(pkg);
  const reasons = [];
  const out = (decision, extra = {}) => ({
    schema: 'odir-genlayer-reconciliation/1',
    decision, exit_code: EXIT[decision], reasons,
    package_slice_id: pkg.identity.slice_id, package_attempt: pkg.identity.attempt,
    remote_status: obs.task?.status ?? null,
    remote_attempt: obs.task?.attempt ?? null,
    remote_verdict: obs.latest_attempt?.review?.verdict ?? null,
    remote_paused: obs.paused ?? null,
    observed_at: obs.observed_at,
    authority: 'none',
    next_action: nextAction(decision, obs),
    ...extra,
  });

  const d = pkg.destination;
  if (config) {
    if (config.chain_id !== d.chain_id) reasons.push(`config chain_id ${config.chain_id} differs from package destination ${d.chain_id}`);
    if (lower(config.contract_address) !== lower(d.contract_address)) reasons.push('config contract_address differs from package destination');
    if (config.contract_code_sha256 && config.contract_code_sha256 !== d.contract_code_sha256) reasons.push('config contract_code_sha256 differs from package destination');
  }
  if (obs.source.chain_id !== d.chain_id) reasons.push(`observation came from chain ${obs.source.chain_id}, package expects ${d.chain_id}`);
  if (lower(obs.source.contract_address) !== lower(d.contract_address)) reasons.push('observation came from a different contract address');
  if (obs.source.contract_code_sha256 && obs.source.contract_code_sha256 !== d.contract_code_sha256) reasons.push('observed contract code identity differs from package destination');
  if (reasons.length) return out('CONFIG_MISMATCH');

  if (obs.task.slice_id !== pkg.identity.slice_id) { reasons.push('observation is for a different slice'); return out('INTEGRITY_MISMATCH'); }
  const localCriteria = criteriaSha256(pkg);
  if (obs.task.criteria_sha256 !== localCriteria) { reasons.push('criteria registered on the contract differ from the package criteria'); return out('INTEGRITY_MISMATCH', { local_criteria_sha256: localCriteria }); }

  if (obs.task.attempt < pkg.identity.attempt) { reasons.push(`contract holds attempt ${obs.task.attempt}, package is attempt ${pkg.identity.attempt}`); return out('NOT_SUBMITTED'); }
  if (obs.task.attempt > pkg.identity.attempt) { reasons.push(`contract has moved on to attempt ${obs.task.attempt}`); return out('SUPERSEDED'); }

  const a = obs.latest_attempt;
  if (!a) { reasons.push('observation lacks the attempt record'); return out('INTEGRITY_MISMATCH'); }
  if (a.evidence_sha256 !== pkg.evidence.sha256) { reasons.push('evidence on the contract is not the evidence in this package'); return out('INTEGRITY_MISMATCH'); }

  if (Date.parse(obs.observed_at) > Date.parse(pkg.lifetime.accept_until)) { reasons.push(`observed after accept_until ${pkg.lifetime.accept_until}`); return out('EXPIRED'); }
  if (a.status === 'SUBMITTED') { reasons.push('review transaction not yet run or not yet final'); return out('PENDING_REVIEW'); }
  if (obs.paused) reasons.push('contract is paused: approvals cannot be consumed until the owner resumes');
  reasons.push(`contract attempt status ${a.status}, verdict ${a.review?.verdict ?? 'none'}`);
  return out('CONSISTENT');
}

function nextAction(decision, obs) {
  switch (decision) {
    case 'CONSISTENT':
      if (obs.latest_attempt?.status === 'REVIEWED_PASS') return 'reviewer wallet may approve_submission; ODIR records the verdict as advisory';
      if (obs.latest_attempt?.status === 'APPROVED') return 'Governor decides locally; a consume_approval is a separate, one-time on-chain claim';
      if (obs.latest_attempt?.status === 'CONSUMED') return 'closed on chain; nothing further to do remotely';
      if (obs.latest_attempt?.status === 'REJECTED') return 'repair creates a new candidate and a new attempt';
      if (obs.latest_attempt?.status === 'INSUFFICIENT') return 'supply the missing readable evidence in a new attempt, or mark the criterion human-decided';
      return 'inspect';
    case 'PENDING_REVIEW': return 'wait, then observe again; do not resubmit';
    case 'NOT_SUBMITTED': return 'exporter may submit after release approval; check the outbox first for an in-flight submission';
    case 'SUPERSEDED': return 'this package is stale; work from the latest attempt';
    case 'EXPIRED': return 'result is stale by policy; a new attempt needs a new package';
    case 'CONFIG_MISMATCH': return 'stop; fix the deployment configuration before trusting any read';
    case 'INTEGRITY_MISMATCH': return 'stop and investigate; do not retry';
    default: return 'inspect';
  }
}

const lower = (s) => String(s || '').toLowerCase();
