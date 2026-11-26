# Factory record — agreement_registry — 24 Nov 2026

Factory run of 24 Nov 2026 (run start 21:44:45 UTC), builder agent in a cloud session. Branch
`factory/agreement_registry-2026-11-24` from `main` `f0a4525`. Owner's page, main table, row 4
(ODIR Brain slice B2). Owner's note: SnapLink's agreement flow (parchment seal block, e-sign) is
waiting on it; until it exists every signed agreement says "Not recorded on chain".
Pull request: opened by the orchestrator (draft).

## Output

| File | sha256 |
|---|---|
| `contracts/factory/agreement_registry.py` | `5d805a0530207180f583292bfb18f2f77113dce0b7c84ec91142fbcda133936d` |
| `tests/factory/test_agreement_registry.py` | `e2fe70957fefa952ff5ddd013d68380514d36659faa190b949b4346fec7e9e46` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
(line 2 blank, line 3 `from genlayer import *`, then the module docstring).
Class `AgreementRegistry`; constructor `AgreementRegistry()` takes no arguments. The deploying
address becomes the owner (admin); no relayer at deploy; the owner sets one with `set_relayer`.

MCP server: `genskill`, used as the owner's claude.ai connector (tool names `mcp__genskill__genlayer_*`).
The repository's `.mcp.json` pins `genskill-mcp@2.3.3`; the connector does not report its own version.

## What it decides

No judgment. It records that an agreement exists (sha256 id, sha256 of the terms, public role
keys, base, template version, state, outcome code) and which state it is in. The state moves only
forward through a fixed list, and only the owner or the one relayer the owner names can write.

States (fixed, ordered, forward-only): `PROPOSED → ACCEPTED → SIGNED → ANCHORED → CLOSED`.
A move to any later state is valid (skipping is allowed, so `ACCEPTED → ANCHORED` is valid);
the same or an earlier state is refused; `CLOSED` is terminal.

| Method | Who | Answer |
|---|---|---|
| `set_relayer(relayer)` | owner | `{"relayer": <lowercase hex>}` |
| `remove_relayer()` | owner | `{"relayer": ""}` |
| `append_agreement(agreement_id, terms_hash, role_keys, base, template_version, state, outcome_code)` | owner or relayer | `{"agreement_id", "state", "index"}`; stored record |
| `move_state(agreement_id, new_state, outcome_code)` | owner or relayer | `{"agreement_id", "from_state", "state", "outcome_code"}` |
| `get_agreement(agreement_id)` / `get_count()` / `get_agreement_id(index)` / `get_owner()` / `get_relayer()` / `get_states()` | anyone (views) | record as JSON text / count / id / addresses / state list |

## Refusals (exact text) and the test that covers each

| Refusal | Exact text | Test |
|---|---|---|
| duplicate id | `[EXPECTED] DUPLICATE_ID: an agreement with this id is already recorded` | `test_refuses_a_duplicate_id` |
| any caller except owner or relayer | `[EXPECTED] UNAUTHORIZED: only the owner or the relayer may call this` | `test_refuses_any_other_caller_on_every_write`, `test_refuses_writes_from_anyone_but_the_owner_before_a_relayer_is_set`, `test_owner_can_change_and_remove_the_relayer` |
| relayer doing an owner-only action | `[EXPECTED] OWNER_ONLY: the relayer may only append a record or move its state` | `test_refuses_the_relayer_doing_an_owner_only_action` |
| same / backward / after-CLOSED state change | `[EXPECTED] INVALID_TRANSITION: state moves only forward` | `test_refuses_a_same_or_backward_state_change` (5 cases) |
| unknown state | `[EXPECTED] UNKNOWN_STATE: state must be one of PROPOSED, ACCEPTED, SIGNED, ANCHORED, CLOSED` | `test_refuses_an_unknown_state` (5 cases, append and move) |
| unknown agreement id on move | `[EXPECTED] UNKNOWN_AGREEMENT: no agreement is recorded with this id` | `test_refuses_a_move_on_an_unknown_agreement_id` |
| bad agreement id format | `[EXPECTED] BAD_AGREEMENT_ID: agreement id must be a sha256 hash (64 hex characters, optional 0x)` | `test_refuses_a_bad_agreement_id` (8 cases) |
| bad terms hash format | `[EXPECTED] BAD_TERMS_HASH: terms hash must be a sha256 hash (64 hex characters, optional 0x)` | `test_refuses_a_bad_terms_hash` (5 cases) |
| bad role keys | `[EXPECTED] BAD_ROLE_KEYS: role keys must be 1 to 16 distinct comma-separated keys of 1 to 128 characters from A-Z a-z 0-9 _ . : -` | `test_refuses_bad_role_keys` (7 cases) |
| bad base | `[EXPECTED] BAD_BASE: base must be 1 to 128 printable ASCII characters` | `test_refuses_a_bad_base` (4 cases) |
| bad template version | `[EXPECTED] BAD_TEMPLATE_VERSION: template version must be 1 to 32 characters from A-Z a-z 0-9 _ . -` | `test_refuses_a_bad_template_version` (4 cases) |
| bad outcome code | `[EXPECTED] BAD_OUTCOME_CODE: outcome code must be 0 to 32 characters from A-Z 0-9 _` | `test_refuses_a_bad_outcome_code` (4 cases, append and move) |
| bad relayer address | `[EXPECTED] BAD_ADDRESS: relayer must be 0x followed by 40 hex characters` | `test_refuses_a_bad_relayer_address` (5 cases) |
| index out of range | `[EXPECTED] INDEX_OUT_OF_RANGE: no agreement at this index` | `test_refuses_an_index_out_of_range` |

Every refusal test asserts the exact text twice: `direct_vm.expect_revert(text)` (substring) and
a second call whose `UserError.message` must equal the text exactly. Refusal tests also compare a
snapshot of every view before and after, so a refused call is shown to write nothing.

Answer paths: `test_deployer_is_owner_and_no_relayer_at_deploy`,
`test_relayer_appends_a_record_and_the_views_return_it` (0x/bare/upper-case spellings of one id),
`test_owner_may_append_and_move_too`, `test_accepted_to_anchored_is_a_valid_forward_move`,
`test_every_state_is_reachable_one_step_at_a_time`,
`test_closing_sets_the_outcome_code_and_empty_code_keeps_it`,
`test_owner_can_change_and_remove_the_relayer`, `test_accepts_role_keys_at_the_limits`.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (pinned runner, no comment under the header, `while` not `for`, no `sorted`/`lambda`, GenLayer storage types, `[EXPECTED]` error prefix) |
| Started from the MCP scaffold | OBSERVED | `genlayer_scaffold_contract` template `storage`, name `AgreementRegistry`; rewritten to the row (roles, state list, validation, views) |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the text written to the file; byte identity of the pasted text was not machine-checked |
| Tests started from the MCP test scaffold | OBSERVED | `genlayer_scaffold_test` template `storage` (`direct_deploy`, `direct_vm`, `direct_alice`); rewritten to the row. Nothing to mock: the contract makes no web or LLM call |
| Tests pass: 61 passed, 0 failed | OBSERVED | `python3 -m pytest tests/factory/test_agreement_registry.py -q` → `61 passed in 1.14s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode |
| The tests can fail | OBSERVED | mutations planted in the contract, run, then the file restored (sha256 `5d805a05…936d` before and after): (A) duplicate-id check removed and (B) `target <= current` changed to `target < current`, run together → 3 failed (`test_refuses_a_duplicate_id`, `…same_or_backward_state_change[ACCEPTED-ACCEPTED]`, `…[CLOSED-CLOSED]`); (C) `ERR_OWNER_ONLY` text given an `X` prefix → 1 failed (`test_refuses_the_relayer_doing_an_owner_only_action`; `expect_revert` alone would have passed, the exact-text check caught it) |
| One test per answer and per must-refuse case | OBSERVED | tables above |
| Studionet reachable through the MCP server | OBSERVED | `genlayer_network_status` at ~21:57 UTC: endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b060825`, not syncing |
| Schema from Studionet | NOT_RUN | `genlayer_get_contract_schema` with base64 of the file → `unsupported_contract_rpc`: "Contract RPC operation \"get_contract_schema\" is not supported on this endpoint", endpoint mode `studionet-hosted`, upstream "Internal database error (code -32603)". Endpoint limitation, not the contract; tried once |
| Deploy simulation on Studionet: constructor ran | OBSERVED | `genlayer_call_contract` type `deploy` (`gen_call`, a simulation: nothing signed or sent), `from`/`to` zero address, `data` from the orchestrator's encoder (genlayer-js 0.18.4 `deployContract`) with constructor args `[]` (calldata file sha256 `c0f392f3…25a2`, 25,782 characters including `0x`) → raw result `"00"`, decoded `null` = constructor returned. Pasted into the tool call from the encoder output; byte identity not machine-checked |
| Runs on GenVM; deploys and finalizes; a write and a view answer on a network | NOT_RUN | not until the owner deploys. Direct mode runs the SDK in CPython; the deploy simulation ran only the constructor |
| GenVM consensus on writes | NOT_RUN | deterministic code, so validators should agree, but no write has run on a network |

## Attempts (owner's rule: up to three, each retry after a change backed by the failed attempt's evidence)

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | 61 passed | `61 passed in 1.24s` | not a retry: after a probe showed direct mode raises `genlayer.gl.vm.UserError` with `.message` equal to the text, the test helper `refused` was tightened from "ends with the text" to "`.message` equals the text" (test file only), then re-run: `61 passed in 1.14s` (the hash above is of this file) |
| Studionet reachability | 1 | pass | `healthy`, chain `0xf22f` | — |
| Studionet schema | 1 | not supported | `unsupported_contract_rpc` (hosted Studionet) | none: endpoint limitation, graded NOT_RUN |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |

## Choices the owner may want to change

- **State list.** `PROPOSED → ACCEPTED → SIGNED → ANCHORED → CLOSED`, forward-only with skipping
  allowed. `CLOSED` is the single terminal state; how the agreement ended goes in the outcome code
  (e.g. `FULFILLED`, `CANCELLED`). If SnapLink's flow uses other names or needs separate terminal
  states (e.g. `VOIDED`), change `STATES` and the `UNKNOWN_STATE` text together.
- **Starting state.** `append_agreement` accepts any known state, so a record can be appended
  already `ACCEPTED` (the row's example) or even `CLOSED`.
- **Outcome code on a move.** An empty outcome code keeps the stored one; a non-empty one
  replaces it. Codes are `A-Z 0-9 _`, at most 32 characters.
- **Role keys.** One string, comma-separated, 1–16 distinct keys of 1–128 characters from
  `A-Z a-z 0-9 _ . : -`, stored as a list. A JSON list argument would also work if preferred.
- **`base`.** Treated as a public string of 1–128 printable ASCII characters (meaning not fixed by
  the row). Template version: 1–32 characters from `A-Z a-z 0-9 _ . -`.
- **Hash spelling.** 0x-prefixed or bare, any case; stored lowercase bare, so all spellings of one
  id are the same id (duplicate check included).
- **Relayer.** No relayer at deploy; the owner sets one with `set_relayer`, can replace it, and can
  remove it with `remove_relayer`. The owner can also append and move. Ownership cannot be
  transferred (no method); add one if needed.
- **Nothing is ever deleted or rewritten** except a record's state (forward) and outcome code.
  No history of past states is stored; the chain's transaction log has it.

## Not verified

GenVM execution of any write method; deploy, finality and a view read on Studionet (until the
owner deploys); GenVM consensus on writes. There is no model judgment or web read in this contract.

## Deploy steps for the owner (Studionet, by hand, from a checkout of the PR branch)

```
npm install -g genlayer@0.40.0
genlayer network set studionet
```
bash:
```
genlayer deploy --contract contracts/factory/agreement_registry.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```
PowerShell 5.1:
```
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/agreement_registry.py --fees ($fees -replace '"','\"')
```
Read-only checks: `genlayer receipt <tx hash>`; `genlayer call <address> get_count` (expect `0`),
`genlayer call <address> get_states`, `genlayer call <address> get_owner` (expect the deploying address).
Then, by the owner: `set_relayer` with SnapLink's relayer address.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen` run; nothing
merged; nothing pushed to `main`; no other repository touched; nothing in Base44. Only read-only RPC
through the MCP server (network status, schema request, one deploy simulation). No pull request
opened by this builder (the orchestrator opens it).

VERDICT: DRAFTED — lint clean, 61 direct-mode tests pass, Studionet reachable and the deploy
simulation's constructor returned; schema NOT_RUN (hosted Studionet); post-deploy transaction
report and view read pending the owner's deploy.

## Independent verification — 25 Nov 2026 (scheduled factory run)

A separate verifier agent (not the builder) checked out this branch at `68cfec38d6a7a137b8a7302af357fa43e433d531`
and judged it from the code, the tests and page row 4, without this record. **Verdict: PASS.**

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Contract sha256 | 1 | `5d805a0530207180f583292bfb18f2f77113dce0b7c84ec91142fbcda133936d` | OBSERVED | unchanged after all mutations were reverted |
| genskill lint (full source) | 1 | `ok: true`, 0 errors, 0 warnings, 0 info | OBSERVED | source pasted into the tool call; byte identity not machine-checked |
| pytest (genlayer-test 0.29.2 direct mode) | 1 | `61 passed in 1.17s` | OBSERVED | re-run in the verifier's own clone |
| Every row item has a test; refusals exact | 1 | yes | OBSERVED | duplicate id, other caller (all 4 writes), invalid/unknown state, relayer owner-only actions; helper checks `exc.message == text` |
| Mutations caught | 1 | 5 of 5 | OBSERVED | duplicate check removed → 1 failed; backward moves allowed → 5 failed; relayer allowed owner-only → 1 failed; any caller allowed → 3 failed; refusal text suffixed → 5 failed; each reverted, tree clean |
| Studionet schema (endpoint re-probe) | 1 | `unsupported_contract_rpc` (`studionet-hosted`, upstream `Internal database error (code -32603)`) | NOT_RUN | orchestrator probe with a 15-line contract, 25 Nov ~00:01 UTC; endpoint limitation, not this contract |
| Studionet reachability | 1 | healthy, chain `0xf22f`, block `0x6b062555` | OBSERVED | orchestrator `genlayer_network_status`, 25 Nov ~00:01 UTC |

Notes from the verifier (not defects): the doc block sits after `from genlayer import *`, so Python does not see it
as `__doc__` (the constructor is still documented at the top of the file; lint accepts it). `base` is free printable
text, so "public data only" for it is enforced by callers. Not reproduced by the verifier: the Studionet deploy
simulation above (not in its brief).

## Slice B2 alignment — 26 Nov 2026 (ODIR contracts autopilot, run 9)

A separate builder (the ODIR contracts autopilot, not the factory) reviewed this draft against what the
other slices now produce, before the first deploy, on branch `odir/b2-agreement-registry-review-2026-11-26`
(stacked on this PR's head `ddb95c4`). The draft above stays as it was verified; this section records what
changed and why. Nothing was signed, deployed or sent.

### Why it changed

| Gap in the draft | Where the other slice stands | Change |
|---|---|---|
| A terms hash written `sha256:<hex>` was refused (`BAD_TERMS_HASH`) | A3's resolver and SnapLink's C4 evidence both write `sha256:<hex>` | hashes accept one `sha256:` or `0x` prefix (or none), any case, no spaces; `terms_hash` is stored as `sha256:<hex>`, the seal and the id as bare hex, so SnapLink compares with plain equality |
| No place for the e-sign seal | C4: `agreementSealHash` "is what slice D4 writes to GenLayer" | new `seal_hash`: given at append, or recorded once on a forward `move_state`; never changed after (`SEAL_ALREADY_SET`, `BAD_SEAL_HASH`) |
| `base` was any printable text, so names could reach the chain (verifier note above) | A3 base keys `P2P P2B B2P B2B STAFF` | `base` must be one of them |
| Role keys were up to 16 × 128 free characters | A3 `roles`: engager and provider, role key `^[a-z][a-z0-9_]{1,40}$`, either may be null | `""` or 1–2 `slot:role` keys, each slot once, stored engager first |
| Template version was any 32 characters | A4 release tag `templates-vX.Y.Z` | must be that tag (no leading zeros, ≤ 32 characters) |

Interface change: `append_agreement(…, outcome_code, seal_hash)` and `move_state(agreement_id, new_state,
outcome_code, seal_hash)` each gained a last argument (`""` = no seal / keep the seal). `move_state` also
returns `seal_hash`; the stored record has a `seal_hash` key.

### Output

| File | sha256 |
|---|---|
| `contracts/factory/agreement_registry.py` | `aa6528e9465d080db50c2a0d927ee67ca891e3c3f76c73fa05cb47d144fc6bf6` |
| `tests/factory/test_agreement_registry.py` | `baaba845d89958ed9ed92397f729cdd20b310e26adf7033cef05ab6e0be3f536` |

### Claims

| Claim | Grade | Evidence |
|---|---|---|
| Lint: no errors | OBSERVED | `genlayer_lint_contract` (genskill connector) on the full final source: `ok: true`, 0 errors, 0 warnings, 0 info. Source pasted into the tool call; byte identity not machine-checked |
| Tests pass: 137 passed | OBSERVED | `python3 -m pytest tests/factory/test_agreement_registry.py -q` → `137 passed in 2.99s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode. Baseline on `ddb95c4` before the change: `61 passed` |
| A real A3 terms hash is accepted and read back equal | OBSERVED | test uses `terms_hash` of A3's golden `agreement.photographer.provider.B2P.EW.json` at `dcb91be` (`sha256:780d49e0…33d5`) |
| The test seal equals SnapLink's own `agreementSealHash` | OBSERVED | SnapLink `base44/shared/esign/esignEvidence.js` (file sha256 `f7eb54a4…dd45`) run with node on the integration branch for evidence hashes of `"evidence engager"` / `"evidence provider"` → `3cad22ef…bf9b`, the test's `SEAL` |
| The tests can fail | OBSERVED | 30 mutants planted one at a time, file restored after (sha256 above): 29 caught; 1 survivor equivalent (`MAX_ROLE_KEYS = 3`: a third key must repeat a slot, which is refused anyway) |
| Independent verifier | OBSERVED | a separate agent, fresh clone, judged from code + tests + spec without this record: **PASS WITH FINDINGS**, no blockers; `129 passed`; 24 own mutants, 22 caught, 2 equivalent. Should-fix: stored bare `terms_hash` never string-equals SnapLink's `sha256:<hex>` → **fixed** (stored with the prefix, test + mutant). Nit: surrounding whitespace was trimmed → **fixed** (refused, tests + mutant). Nits kept: no seal required at SIGNED/ANCHORED (D4 decides); no owner transfer; docstring after the import |
| Verifier re-check of the two fixes | OBSERVED | same agent, fresh checkout of `5716d89`: **PASS**; `137 passed in 3.02s`; 6 mutants against the fixes (strip back, lstrip, terms bare, seal or id prefixed, terms upper case), 6 caught; clone clean |
| Constructor unchanged | OBSERVED | `__init__` identical to `ddb95c4` (`git diff`), so the earlier Studionet deploy simulation still covers it; not re-run |
| Runs on GenVM; deploy, finality, a write on a network | NOT_RUN | until the owner deploys (testnet only) |

### How SnapLink is expected to use it (for D2/D4; their slices decide)

| SnapLink (D2 state) | Call |
|---|---|
| Both parties have signed (ACCEPTED → PENDING_ANCHOR) | `append_agreement(id, terms_hash, roles, base, tag, "SIGNED", "", seal)`; the receipt moves SnapLink to ANCHORED |
| ACTIVE | optional `move_state(id, "ANCHORED", "", "")` |
| COMPLETED / CANCELLED / TERMINATED | `move_state(id, "CLOSED", "<that word>", "")` |
| VARIED | the old version: `move_state(id, "CLOSED", "VARIED", "")`; the new version is a new record with its own id |

Open for D2: how the agreement id is derived (it must differ per version, since terms change on a
variation); D4 may want a rule that SIGNED or later carries a seal.

VERDICT: ALIGNED ON BRANCH — lint clean, 137 direct-mode tests, 29/30 own mutants (1 equivalent),
independent verifier's should-fix fixed; not merged, not deployed.
