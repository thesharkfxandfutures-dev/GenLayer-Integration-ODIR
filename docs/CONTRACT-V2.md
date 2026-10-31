# Contract v2: what the next version of `odir_review_gate.py` must add, and why

The deployed v0.1 contract stores slice, scope, criteria, roles, attempt and inline evidence. It
has a global pause and refuses to cancel approved or consumed slices. It has **no** per-approval
expiry, **no** revocation, **no** binding to a repository candidate or a local policy, and **no**
record of which package a submission came from. Those are the gaps R06, R07 and R10 name. v2
closes them without moving any authority onto the chain.

## Design rules that do not change

- The LLM judges text against criteria. Code checks caller, roles, identity, binding, attempts,
  predecessors, expiry and pause. The LLM never decides who owns the contract, never extends a
  deadline, never alters criteria, never grants scope.
- Instructions inside evidence are untrusted text.
- A consensus PASS is a reviewed opinion. Approval binds one attempt and one evidence hash.
  Consumption is a one-time on-chain claim, not a permit.
- Addresses are not people. Finality is not success. On-chain records cannot be withdrawn.

## Additions

### 1. Package binding
`submit_evidence(slice_id, evidence, package_sha256)` stores the 64-hex `package_sha256` on the
attempt. `get_attempt` returns it. The adapter's reconcile step then compares the on-chain value
to `packageSha256(package)` as a third binding beside criteria and evidence. A mismatch is an
integrity event. The contract does not interpret the package; it only remembers which one.

### 2. Candidate and policy identity on the slice
`register_slice(..., binding_json)` where `binding_json` is a canonical object
`{candidate_manifest_sha256, run_contract_sha256, policy_version}` or an empty string for text-only
design tasks. Stored verbatim and folded into `task_sha256`. Criteria whose `evidence_class` is
`observed` or `human` are listed in the same object so the contract can return
`INSUFFICIENT` for them when only prose is supplied (the prompt tells the model which criteria it
may not decide from text; the validator enforces that those criteria are never `MET`).

### 3. Per-approval expiry
`approve_submission(slice_id, attempt, evidence_sha256, expires_at_unix)` with
`expires_at_unix <= now + MAX_APPROVAL_SECONDS` (owner-set at registration, default 7 days).
`consume_approval` requires `now < expires_at`; otherwise the status becomes `EXPIRED` on the
next write and `can_consume` returns false. `get_slice` exposes `expires_at`. Block time is the
only clock; ODIR keeps its own, stricter `lifetime.accept_until`.

### 4. Revocation
`revoke_approval(slice_id, attempt, reason_code)` by the reviewer **or** the owner, allowed in
`APPROVED` only (a consumed approval cannot be un-consumed; revocation after consumption is an
ODIR-side compensating record). Status `REVOKED`; `reason_code` from a closed list:
`candidate_changed`, `evidence_error`, `key_compromised`, `policy_withdrawn`, `other`.
A revoked attempt cannot be re-approved; a new attempt is needed.

### 5. Attempt lineage
`submit_evidence` for attempt n > 1 records `parent_attempt = n-1` and the previous attempt's
`evidence_sha256`, so a repair is visibly a repair.

### 6. Version and code identity
`get_config` returns `{owner, paused, contract_version: 2, source_sha256}` where `source_sha256`
is set once by the deployer at construction from the reviewed source hash. It is a claim by the
deployer, which the owner can confirm against this repository, not a proof; but it makes a silent
redeploy at the same address detectable by every reader.

## State machine (application states)

```
REGISTERED ─submit→ SUBMITTED ─review→ REVIEWED_PASS ─approve→ APPROVED ─consume→ CONSUMED
                       │                    │                       │
                       ├─review→ REJECTED   │                       ├─revoke→ REVOKED
                       ├─review→ INSUFFICIENT                       └─(time)→ EXPIRED
                       └─(≤3 attempts; identical evidence refused)
REGISTERED | SUBMITTED | REJECTED | INSUFFICIENT ─cancel(owner)→ CANCELLED
```

Transaction states (pending, accepted, finalised, execution error) are separate from these and
are the adapter's concern.

## Validator rules carried over, plus two

- Exact JSON shape, one check per criterion in order, quotes verbatim from evidence, `MET`/`NOT_MET`
  need a quote, verdict derived in code from statuses, independent re-evaluation in `validate`.
- New: a criterion flagged `observed` or `human` in the binding may never be `MET`; the validator
  rejects such output.
- New: the response size bound and the retry budget are stated in `get_config` so ODIR's budget
  rule can read them rather than assume them.

## Migration

v1 at `0xFE76…C646` stays as the record of the D1 demonstration. v2 deploys at a new address;
`DEPLOYMENTS.md` records both. ODIR config names one destination per task category; v1 verdicts
remain valid only for the advisory design-review category and are never imported into a mandatory
gate. The GenVM cases in `GENVM-TESTS.md` gain rows for expiry, revocation, package mismatch and
the `observed`-criterion refusal before v2 is used for anything.
