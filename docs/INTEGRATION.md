# How the pieces link: ODIR, this repository, Base44 and the contract

Four things take part. Each has one job and one boundary. They are joined by **records and a
command line**, not by shared code, so a fault or a compromise in one cannot quietly become
authority in another.

| Piece | Where | Job | May never |
|---|---|---|---|
| **Orchestrator-Swarm** (ODIR) | private repo, `<ODIR_REPO>` | Turn intent into a bounded run, build in containment, verify locally, decide policy, issue permits | Trust a remote PASS as a permit; import code from this repo into its authority modules |
| **GenLayer-Integration-ODIR** (this repo) | public, `thesharkfxandfutures-dev/GenLayer-Integration-ODIR` | Hold the contract, the shared schemas and fixtures, and the `genlayer-odir` adapter | Hold a key, sign, submit, write a permit, read the private tree |
| **Mission Control** (Base44) | hosted | Project records for a human; accept proposals (button presses); read the contract for display | Create authority by changing a field; hold a wallet; run host commands |
| **ODIR Review Gate contract** | GenLayer Studionet `0xFE76…C646` | Consensus-backed semantic review of approved public text; role-separated approve and one-time consume | Decide local permissions, see private material, extend its own criteria |

## 1. The join is a record, not a dependency

ODIR is zero-dependency Node and must stay that way, so it does not `import` anything from this
repo. The two repositories meet on three JSON records whose shapes live here under `schema/`:

1. **Review package** (`odir-review-package/1`) — written by ODIR's exporter, read by everyone.
   Its `package_sha256` is the one identifier that ODIR's review store, this adapter, Mission
   Control and the human approval all refer to.
2. **Observation** (`odir-genlayer-observation/1`) — produced by `genlayer-odir observe` from one
   `get_slice` reply, read from a saved file or through the pinned client. It records chain,
   contract, claimed code identity, state selection, client version, time, source and the
   contract's state. No evidence text, no authority.
3. **Reconciliation** (`odir-genlayer-reconciliation/1`) — produced by `genlayer-odir reconcile`.
   One decision word, reasons, an exit code, and `authority: none`.

The contract stores only what it is given: the criteria texts in order and the inline evidence.
Everything the contract does not know (candidate manifest, run contract, policy version, export
approval, lifetime) is bound to those two values locally by `package_sha256`. The adapter proves
the link both ways: `criteriaSha256(package)` must equal the contract's `criteria_sha256`, and
`evidence.sha256` must equal the attempt's `evidence_sha256`. All sides use the same canonical
encoding (sorted keys, no whitespace, non-ASCII escaped, integers only). `fixtures/d1/canon-vectors.json`
holds CPython-computed bytes; the live fixture proves the same encoding reproduces the
`task_sha256` the deployed contract computed; the Base44 lib must pass the same vectors.

**What a match means, exactly.** `CONSISTENT` + `PASS` says: the text ODIR holds in this package
is the text the validators reviewed, and they agreed it meets the criteria. It says nothing about
whether that text describes a candidate that exists, builds, or passed any test. Candidate
verification is a separate, local observation; the package carries its digest so the two can be
tied together, but agreement on the text never substitutes for it.

**What is a claim in the package.** `destination.contract_code_sha256` is the hash of the source
candidate in this repo; whether those bytes are what runs at the address is not confirmed.
`disclosure.release_approval` is a free-text statement of who approved release; v1 has no
signature on it, so it is attributable only through ODIR's own journal. Signed statements are
deferred to a versioned package v2 (`signatures: []` is not added to the closed v1 schema).

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
   │  → package_sha256, criteria_sha256, evidence_sha256; ODIR records them beside the slice
   ▼
register_slice / submit_evidence / review_submission                  [wallets, Studio or GenLayer CLI]
   │  done by the owner, builder and reviewer accounts by hand; the adapter never signs
   ▼
genlayer-odir observe --slice D1 --config studionet.json --rpc        (or --from-file reply.json)
   │  → observation.json  (pinned genlayer-js@1.1.8, state latest-final, one endpoint)
   ▼
genlayer-odir reconcile --package package.json --observation observation.json --config studionet.json
   │  → CONSISTENT | PENDING_REVIEW | NOT_SUBMITTED | SUPERSEDED | EXPIRED | CONFIG_MISMATCH | INTEGRITY_MISMATCH
   ▼
odir review import …                                                  [ODIR, private]
   │  appends observation + reconciliation to the review store; computes a SHADOW decision (logged, never consulted)
   │  the Director's signed sync carries `observations` as a NEW optional key (additive)
   ▼
Mission Control: GenLayerObservation rows and the /genlayer page     [Base44]
   │  human presses the run's existing approve control; the review's package_sha256 is shown beside it
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
| 3 | superseded, expired, environment blocked, outage, or the contract refused the call | the result is stale or unavailable; mandatory gates stay closed |
| 4 | integrity mismatch | stop, alert the owner, do not retry |
| 5 | configuration mismatch (chain, URL, contract, code identity, method) | stop; fix deployment config before trusting any read |
| 6 | bad input | fix the package or reply |
| 7 | usage | fix the command |

RPC failure categories inside exit 3: `transport_outage`, `rate_limit`, `execution_error`
(the contract raised, for example an unknown slice), `configuration_failure` (client missing).

Chain selection (`adapter/src/rpc.js selectChain`). The config's `chain_id` picks the pinned
client's chains with that id; the optional `chain_name` (`bradbury`, `testnetBradbury` or the
client's display name, case and punctuation ignored) and `rpc_url` narrow them further, and
exactly one must remain. `genlayer-js@1.1.8` defines `testnetAsimov` and `testnetBradbury` both as
chain 4221, so a testnet config must give `rpc_url` or `chain_name` (the CLI already requires
`rpc_url`): a bare 4221 is refused with exit 5, never resolved to whichever chain the client lists
first. A name and URL that point at
different chains are refused the same way. `reconcile` still compares `chain_id` and the contract
address only, so a package cannot yet say which of the two testnets it means.

## 3. How ODIR links to this repo

ODIR does not vendor this code. It points at an installed checkout and pins it:

```jsonc
// <ODIR_HOME>/genlayer.json
{
  "adapter_path": "<path to this repo>/adapter/bin/genlayer-odir.mjs",
  "adapter_commit": "<git commit of this repo that was reviewed>",
  "network_config": "<ODIR_HOME>/genlayer/studionet.json",   // copy of config/studionet.example.json, checked
  "mode": "advisory"                                         // advisory | off; mandatory is refused by this version
}
```

ODIR's `src/core/genlayer.js` checks the pinned commit against the checkout's `git rev-parse HEAD`
and refuses to run the adapter on a mismatch. The adapter runs as a child process with a minimal
environment, cwd set to the package directory, and no access to the ODIR tree. In the containment
model this is a worker, not a trusted service, so it gets no credentials.

The `odir review` commands (`verify`, `observe`, `import`, `status`) wrap the adapter and keep an
append-only review store under `<ODIR_HOME>/review/`. The **shadow decision** computed on import
states what a mandatory gate would have said; it is logged and projected, and nothing that
authorises reads it. Those changes touch `bin/odir.js`, `src/core/sync.js`, `src/core/director.js`
and the new `src/core/genlayer.js` only; nothing under `src/security/`, nothing in the Governor's
permit logic.

## 4. How Base44 links

Mission Control already receives signed syncs from the Director (`src/core/sync.js`: HMAC-SHA256 over
`ts.body`, replay guard by sequence). That wire format stays byte-identical. Remote review enters as
**new, additive records**, never by reinterpreting existing fields:

- New entity `GenLayerObservation` (admin-only RLS like the other Director entities): `observation_id`,
  `run_id`, `slice_id`, `attempt`, `package_sha256`, `chain_id`, `contract_address`,
  `contract_code_sha256`, `observed_at`, `source_kind`, `remote_status`, `remote_verdict`,
  `remote_paused`, `decision`, `reasons`, `freshness` (fresh | stale | unavailable | integrity_error),
  `shadow_would_permit`, `authority` (always `"none"`), `sync_seq`.
- The sync body gains an optional `observations: []` array beside `run`, `lanes`, `nodes`, `acks`,
  sent only when non-empty. The Base44 `director` function upserts them by `observation_id` and
  forces `authority: "none"`; a bad record never fails the sync.
- `DirectorRun.verification_outcome` is **not** touched by any remote result. It stays decided
  from local records. The `/genlayer` page reads the contract live (its own `genlayer-review-state`
  function, read methods only) and lists ODIR's observations beside it, with chain, contract,
  time, freshness and an explorer link; a stale or failed read never leaves a green state behind.
- **Approval binding.** The Director's approve handler compares the request's `artefact_digest`
  with the run's own artefact digest (`this.digest()` in `director.js`) and refuses a mismatch.
  That digest is the run's, not the package's, and it must stay so. The review's `package_sha256`
  is therefore shown next to the approval and recorded in the journal when the approval is
  handled; it does not replace `artefact_digest`.

Base44 login identifies a UI user. It is not the contract's wallet role and not the Governor's
principal; the page must show which wallet and which local principal a given action needs.

## 5. Trust statement

- The contract has an owner-demonstrated D1 lifecycle on Studionet, read back live by this
  adapter (`docs/DEPLOYMENTS.md`). That is one happy path, not denial coverage, and it has no
  repository candidate behind it.
- This adapter's 31 tests are **local Node tests of deterministic logic**: canonical encoding,
  package binding, reply parsing, reconciliation, RPC guard rails, and the recorded live reply.
  They are not GenVM tests and not host tests, and they are unrelated to the "24 local stand-in
  tests" of the earlier contract prototype, which were not found on this machine.
- `--rpc` reads one configured endpoint through the pinned client. A TLS connection to that
  endpoint is not a state proof; nothing corroborates the read. Submission, a signing service with
  payload validation, outbox/inbox durability and receipt reconciliation are R08 work.
- A `CONSISTENT` + `PASS` result is advisory information for a human and for the Governor. The
  Governor's own checks (run contract, unchanged candidate, local verification, human disposition,
  permit audience and expiry) are what authorise anything, and those live in the private repo
  behind the frozen security phase. The shadow decision is a prediction of that gate, not the gate.

## 6. Increments (matches the requirements document §17)

| # | Increment | This repo | ODIR | Base44 |
|---|---|---|---|---|
| 1 | Design-text review, advisory (done by hand on Studionet) | contract, fixtures, adapter ✔ | — | live read page ✔ |
| 2 | Read-only observation | `--rpc` with pinned client ✔; second-endpoint corroboration ✗ | `odir review observe/import`, review store ✔ | `GenLayerObservation` + sync key ✔ |
| 3 | Candidate-bound packages and shadow decisions | schema v1 frozen ✔; cross-runtime fixtures (CPython, Node, deployed contract, Base44) ✔ | shadow rule ✔; exporter (R05 classification, allowlists, release approval) ✗ | provenance display ✔ |
| 4 | Mandatory gate for one low-risk category | GenVM denial tests run on the real runtime ✗ (`docs/GENVM-TESTS.md`), contract v2 ✗ (`docs/CONTRACT-V2.md`) | R03 containment live, R09 permits, R10 crash tests ✗ | disposition labels per action ✗ |
| 5 | Code claims, protected tests, final repo actions | observed-evidence criteria ✗ | protected test runner, signed attestations ✗ | — |

✔ built in this repository state; ✗ not built. See the private repo's `docs/genlayer/` for the ODIR
side and `docs/ARCHITECTURE-TIERS.md` §3 for what each later tier requires.
