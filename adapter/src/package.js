// The candidate-bound review package (R06, schema odir-review-package/1).
// It is the one record the ODIR exporter, this adapter, the contract and Mission Control all
// refer to. The contract itself stores only the subset it was given (criteria texts and the
// inline evidence); the rest is bound locally through package_sha256.
import { canonical, digest, sha256 } from './canon.js';

export const PACKAGE_SCHEMA = 'odir-review-package/1';
export const EVIDENCE_CLASSES = ['text', 'observed', 'human'];
export const ASSURANCE_LEVELS = ['builder_claim', 'collector_observed', 'independently_rerun', 'protected_test', 'host_enforcement'];
const HEX40 = /^0x[0-9a-fA-F]{40}$/, HEX64 = /^[0-9a-f]{64}$/, SLICE_ID = /^[A-Za-z0-9_-]{1,64}$/;

export class PackageError extends Error {
  constructor(problems) { super(`invalid review package: ${problems.join('; ')}`); this.problems = problems; }
}

const isStr = (v, max = Infinity) => typeof v === 'string' && v.length > 0 && v.length <= max;
const isInt = (v) => Number.isInteger(v) && v >= 0;

export function validatePackage(p) {
  const bad = [];
  const need = (cond, msg) => { if (!cond) bad.push(msg); };
  need(p && typeof p === 'object', 'package must be an object');
  if (bad.length) throw new PackageError(bad);
  need(p.schema === PACKAGE_SCHEMA, `schema must be ${PACKAGE_SCHEMA}`);
  const id = p.identity || {};
  need(isStr(id.run_id, 128), 'identity.run_id');
  need(isStr(id.slice_id) && SLICE_ID.test(id.slice_id), 'identity.slice_id must match the contract rule (letters, digits, _ -, max 64)');
  need(isInt(id.attempt) && id.attempt >= 1 && id.attempt <= 3, 'identity.attempt must be 1..3 (contract limit)');
  need(id.parent_attempt === null || isInt(id.parent_attempt), 'identity.parent_attempt must be null or an integer');
  const c = p.candidate || {};
  need(isStr(c.repo, 256), 'candidate.repo');
  need(isStr(c.base_revision) && /^[0-9a-f]{7,64}$/.test(c.base_revision), 'candidate.base_revision must be a hex revision');
  need(HEX64.test(c.candidate_manifest_sha256 || ''), 'candidate.candidate_manifest_sha256 must be sha256 hex');
  const a = p.authority || {};
  need(HEX64.test(a.run_contract_sha256 || ''), 'authority.run_contract_sha256 must be sha256 hex');
  need(isStr(a.policy_version, 64), 'authority.policy_version');
  need(Array.isArray(p.criteria) && p.criteria.length >= 1 && p.criteria.length <= 8, 'criteria must hold 1..8 entries (contract limit)');
  if (Array.isArray(p.criteria)) {
    const texts = new Set();
    p.criteria.forEach((cr, i) => {
      need(isStr(cr?.id, 64), `criteria[${i}].id`);
      need(isStr(cr?.text, 600), `criteria[${i}].text (max 600, contract limit)`);
      need(EVIDENCE_CLASSES.includes(cr?.evidence_class), `criteria[${i}].evidence_class must be one of ${EVIDENCE_CLASSES.join('|')}`);
      need(isStr(cr?.version, 32), `criteria[${i}].version`);
      if (texts.has(cr?.text)) bad.push(`criteria[${i}].text duplicates an earlier criterion`);
      texts.add(cr?.text);
    });
  }
  const e = p.evidence || {};
  need(isStr(e.text, 12000) && e.text.trim().length > 0, 'evidence.text (1..12000 chars, contract limit)');
  need(HEX64.test(e.sha256 || ''), 'evidence.sha256 must be sha256 hex');
  if (isStr(e.text) && HEX64.test(e.sha256 || '')) need(sha256(e.text) === e.sha256, 'evidence.sha256 does not match evidence.text');
  need(e.raw_sha256 === null || HEX64.test(e.raw_sha256 || ''), 'evidence.raw_sha256 must be null or sha256 of the unredacted original');
  const pr = p.provenance || {};
  need(isStr(pr.collector, 128), 'provenance.collector');
  need(ASSURANCE_LEVELS.includes(pr.assurance), `provenance.assurance must be one of ${ASSURANCE_LEVELS.join('|')}`);
  need(pr.attestation_sha256 === null || HEX64.test(pr.attestation_sha256 || ''), 'provenance.attestation_sha256 must be null or sha256 hex');
  const d = p.disclosure || {};
  need(HEX64.test(d.export_manifest_sha256 || ''), 'disclosure.export_manifest_sha256 must be sha256 hex');
  need(isStr(d.release_approval, 256), 'disclosure.release_approval (who approved public release, and when)');
  const dest = p.destination || {};
  need(isInt(dest.chain_id) && dest.chain_id > 0, 'destination.chain_id');
  need(HEX40.test(dest.contract_address || ''), 'destination.contract_address must be 0x + 40 hex');
  need(HEX64.test(dest.contract_code_sha256 || ''), 'destination.contract_code_sha256 must be sha256 of the deployed source');
  const lt = p.lifetime || {};
  need(isIso(lt.submit_by), 'lifetime.submit_by must be an ISO-8601 instant');
  need(isIso(lt.accept_until), 'lifetime.accept_until must be an ISO-8601 instant');
  if (isIso(lt.submit_by) && isIso(lt.accept_until)) need(Date.parse(lt.accept_until) > Date.parse(lt.submit_by), 'lifetime.accept_until must follow submit_by');
  need(isStr(p.idempotency?.request_key, 128), 'idempotency.request_key');
  if (bad.length) throw new PackageError(bad);
  return p;
}

function isIso(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(s) && !Number.isNaN(Date.parse(s)); }

// What the contract will compute from what it is given: criteria texts in package order.
export const criteriaTexts = (p) => p.criteria.map((c) => c.text);
export const criteriaSha256 = (p) => digest(criteriaTexts(p));

// Identity of the whole package. Canonical over every field, so one changed byte anywhere
// (a criterion, the candidate manifest, the destination) is a different package.
export const packageSha256 = (p) => digest(p);

// The record ODIR keeps beside the package and shows in Mission Control.
export function bindingSummary(p) {
  validatePackage(p);
  return {
    schema: PACKAGE_SCHEMA,
    package_sha256: packageSha256(p),
    slice_id: p.identity.slice_id,
    attempt: p.identity.attempt,
    criteria_sha256: criteriaSha256(p),
    evidence_sha256: p.evidence.sha256,
    candidate_manifest_sha256: p.candidate.candidate_manifest_sha256,
    run_contract_sha256: p.authority.run_contract_sha256,
    destination: { ...p.destination },
    canonical_bytes: Buffer.byteLength(canonical(p), 'utf8'),
  };
}
