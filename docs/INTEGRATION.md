# How the pieces link: ODIR, this repository, Base44 and the contract

Four things take part. Each has one job and one boundary. They are joined by **records and a
command line**, not by shared code, so a fault or a compromise in one cannot quietly become
authority in another.

| Piece | Where | Job | May never |
|---|---|---|---|
| **Orchestrator-Swarm** (ODIR) | private repo, `<ODIR_REPO>` (the private checkout) | Turn intent into a bounded run, build in containment, verify locally, decide policy, issue permits | Trust a remote PASS as a permit; import code from this repo into its authority modules |
| **GenLayer-Integration-ODIR** (this repo) | public, `thesharkfxandfutures-dev/GenLayer-Integration-ODIR` | Hold the contract, the shared schemas and fixtures, and the `genlayer-odir` adapter | Hold a key, sign, submit, write a permit, read the private tree |
| **Mission Control** (Base44) | hosted | Project records for a human; accept proposals (button presses) | Create authority by changing a field; hold a wallet; run host commands |
| **ODIR Review Gate contract** | GenLayer Studionet `0xFE76…C646` | Consensus-backed semantic review of approved public text; role-separated approve and one-time consume | Decide local permissions, see private material, extend its own criteria |

## 1. The join is a record, not a dependency

ODIR is zero-dependency Node and must stay that way, so it does not `import` anything from this
repo. The two repositories meet on three JSON records whose shapes live here under `schema/`:

1. **Review package** (`odir-review-package/1`) — written by ODIR's exporter, read by everyone.
   Its `package_sha256` is the one identifier that ODIR's slice ledger, this adapter, Mission
   Control and the human approval all refer to.
2. **Observation** (`odir-genlayer-observation/1`) — produced by `genlayer-odir observe` from one
   `get_slice` reply. It records chain, contract, code identity, time, source and the contract's
   state. No evidence text, no authority.
3. **Reconciliation** (`odir-genlayer-reconciliation/1`) — produced by `genlayer-odir reconcile`.
   One decision word, reasons, an exit code, and `authority: none`.

The contract stores only what it is given: the criteria texts in order and the inline evidence.
Everything the contract does not know (candidate manifest, run contract, policy version, export
approval, lifetime) is bound to those two values locally by `package_sha256`. The adapter proves
the link both ways: `criteriaSha256(package)` must equal the contract's `criteria_sha256`, and
`evidence.sha256` must equal the attempt's `evidence_sha256`. Both sides use the same canonical
encoding (sorted keys, no whitespace, ASCII-escaped, integers only); `fixtures/d1/canon-vectors.json`
holds CPython-computed bytes the Node side must reproduce, and the test suite checks it.

## 2. The command line, end to end

Each arrow is a process boundary. Nothing below the exporter can reach back into ODIR.

```
human objective
   │
   ▼
odir run … (bounded run contract, worktree, local checks)           [ODIR, private]
   │  exporter writes  <ODIR_HOME>/review/<run>/<slice>/<attempt>/package.json
   ▼
genlayer-odir package verify package.json                             [this repo]
   │  → package_sha256, criteria_sha256, evidence_sha256; ODIR records them on the slice
   ▼
register_slice / submit_evidence / review_submission                  [wallets, Studio or GenLayer CLI]
   │  v0.1: done by the owner, builder and reviewer accounts by hand; the adapter never signs
   ▼
genlayer-odir observe --slice D1 --config studionet.json --from-file reply.json
   │  → observation.json  (v0.1 reads a saved reply; --rpc exits 3 BLOCKED_ENVIRONMENT)
   ▼
genlayer-odir reconcile --package package.json --observation observation.json --config studionet.json
   │  → CONSISTENT | PENDING_REVIEW | NOT_SUBMITTED | SUPERSEDED | EXPIRED | CONFIG_MISMATCH | INTEGRITY_MISMATCH
   ▼
odir review import … (planned)                                        [ODIR, private]
   │  stores observation + reconciliation beside the slice; advisory mode: display only
   │  signed sync to Base44 carries them as a NEW record type (additive)
   ▼
Mission Control shows a separate "remote review" column              [Base44]
   │  human presses "Approve reviewed attempt 1" → ControlRequest{action:approve, artefact_digest: package_sha256}
   ▼
Governor decides locally                                              [ODIR, private]
      run contract valid · candidate unchanged · local verification present ·
      reconciliation CONSISTENT and fresh · human disposition recorded
      → permit for ONE narrow action, or nothing
```

Exit codes are the contract between the adapter and whatever calls it:

| Code | Meaning | Caller's rule |
|---|---|---|
| 0 | consistent / valid | may record the result; still no authority |
| 2 | pending or not yet submitted | wait and observe again; never resubmit from here |
| 3 | superseded, expired, or environment blocked | the result is stale or unavailable; mandatory gates stay closed |
| 4 | integrity mismatch | stop, alert the owner, do not retry |
| 5 | configuration mismatch (chain, contract, code identity) | stop; fix deployment config before trusting any read |
| 6 | bad input | fix the package or reply |
| 7 | usage | fix the command |

## 3. How ODIR links to this repo

ODIR does not vendor this code. It points at an installed checkout and pins it:

```jsonc
// <ODIR_HOME>/genlayer.json  (proposed; not yet read by any ODIR command)
{
  "adapter_path": "<path to this repo>/adapter/bin/genlayer-odir.mjs",
  "adapter_commit": "<git commit of this repo that was reviewed>",
  "network_config": "<ODIR_HOME>/genlayer/studionet.json",   // copy of config/studionet.example.json, checked
  "mode": "advisory"                                               // advisory | mandatory (mandatory needs R03 + R09 first)
}
```

`odir doctor` should report the pinned commit against the checkout's actual `git rev-parse HEAD`
and refuse to run the adapter on a mismatch. The adapter runs as a child process with a
read-only working directory (the package directory) and no access to the ODIR tree. In the
containment model this is a worker, not a trusted service, so it gets no credentials.

ODIR-side work still to do (none of it is in Orchestrator-Swarm yet, by design, while the
security phase is frozen): the exporter (R05: classification, allowlisted fields, release
approval → `package.json`), `odir review verify|observe|import` wrappers that call this CLI,
the slice-ledger fields for `package_sha256` and the latest reconciliation, and the Governor
rule that reads them. Those changes touch `bin/odir.js`, `src/core/slices.js`, `src/core/sync.js`
and `src/core/governor.js` only; nothing under `src/security/`.

## 4. How Base44 links

Mission Control already receives signed syncs from the Director (`src/core/sync.js`: HMAC-SHA256 over
`ts.body`, replay guard by sequence). That wire format stays byte-identical. Remote review enters as
**new, additive records**, never by reinterpreting existing fields:

- New entity `GenLayerObservation` (admin-only RLS like the other Director entities) holding:
  `run_id`, `slice_id`, `attempt`, `package_sha256`, `chain_id`, `contract_address`,
  `contract_code_sha256`, `observed_at`, `source_kind`, `remote_status`, `remote_verdict`,
  `remote_paused`, `decision`, `reasons`, `freshness` (fresh | stale | unavailable | integrity_error),
  `authority` (always `"none"`).
- The sync body gains an optional `observations: []` array beside `run`, `lanes`, `nodes`, `acks`.
  The Base44 `director` function must accept and store it; until both ends are changed under one
  reviewed migration, ODIR sends nothing and the entity does not exist.
- `DirectorRun.verification_outcome` is **not** touched by any remote result. It stays decided
  from local records. The UI shows remote review in its own column with chain, contract, time,
  freshness and an explorer link, and a stale or failed read can never leave a green state behind.
- A human disposition reuses the existing `ControlRequest{action: "approve", artefact_digest}`
  with `artefact_digest = package_sha256`, so the Director can refuse an approval that names a
  different package than the one on screen.

Base44 login identifies a UI user. It is not the contract's wallet role and not the Governor's
principal; the page must show which wallet and which local principal a given action needs.

## 5. Trust statement for v0.1

- The contract has an owner-demonstrated D1 lifecycle on Studionet (`docs/DEPLOYMENTS.md`). That is
  one happy path, not denial coverage, and it has no repository candidate behind it.
- This adapter's 24 tests are **local Node tests of deterministic logic**: canonical encoding,
  package binding, reply parsing, reconciliation. They are not GenVM tests and not host tests, and
  they are unrelated to the "24 local stand-in tests" of the earlier contract prototype, which were
  not found on this machine.
- Nothing here submits, signs, or reads the network. `--rpc` fails closed. Submission, a signing
  service with payload validation, outbox/inbox durability and receipt reconciliation are R08 work
  for a later version.
- A `CONSISTENT` + `PASS` result is advisory information for a human and for the Governor. The
  Governor's own checks (run contract, unchanged candidate, local verification, human disposition,
  permit audience and expiry) are what authorise anything, and those live in the private repo
  behind the frozen security phase.

## 6. Increments (matches the requirements document §17)

| # | Increment | This repo | ODIR | Base44 |
|---|---|---|---|---|
| 1 | Design-text review, advisory (done by hand on Studionet) | contract, fixtures, adapter v0.1 ✔ | nothing yet | nothing yet |
| 2 | Read-only observation | `--rpc` read with a pinned client; second-endpoint corroboration | `odir review observe/import`, ledger fields | `GenLayerObservation` + column |
| 3 | Candidate-bound packages and shadow decisions | schema v1 frozen ✔; cross-runtime fixtures (Python, Node, Base44) | exporter, shadow Governor rule, disagreement log | provenance display |
| 4 | Mandatory gate for one low-risk category | GenVM denial tests, contract v2 (expiry, revocation) | R03 containment live, R09 permits, R10 crash tests | human disposition labels |
| 5 | Code claims, protected tests, final repo actions | observed-evidence criteria | protected test runner, signed attestations | — |
