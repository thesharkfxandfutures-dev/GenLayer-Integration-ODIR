# Factory record — conduct_reason_review — 24 Nov 2026

Factory run (owner's scheduled factory session, run start 21:44:45 UTC; this builder 21:52–22:17 UTC,
cloud workspace, genskill MCP as the owner's claude.ai connector). Branch
`factory/conduct_reason_review-2026-11-24` from `main` `f0a4525`. Owner page main table row 5
(backlog item 4). Pull request: opened by the orchestrator (draft).

## Output

| File | sha256 |
|---|---|
| `contracts/factory/conduct_reason_review.py` | `9336ac702d921f8545d557056b89a72f2b8b5202bc9b302934de11f43e72727a` |
| `tests/factory/test_conduct_reason_review.py` | `713a4781b9a39a552202f4f8d2425ff50371059ae9bb9970822057c39dbc4ad2` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
(line 2 blank, line 3 `from genlayer import *`, then the module docstring with the constructor).
Class `ConductReasonReview`, constructor takes no arguments; no owner or admin role.

Methods: `open_case(case_id, booking_terms)`, `submit_reason(case_id, stated_reason,
evidence_summary, evidence_sha256)`, `decide_case(case_id)`, `close_case(case_id)` (opener only);
views `get_case`, `get_case_count`, `get_case_id`.

Answer: `verdict` `PENALTY_JUSTIFIED` or `PENALTY_NOT_JUSTIFIED`; `band` `MINOR` / `STANDARD` /
`SEVERE` when justified and `NONE` when not justified; `clause` an exact substring of the booking
terms (for either verdict); `reason` one sentence.

MCP server: the `genskill` claude.ai connector (tool names `mcp__genskill__genlayer_*`). The
version pinned in the repository's `.mcp.json` is `genskill-mcp@2.3.3`; the connector does not
report its own version, so that it runs 2.3.3 is not verified.

## Refusals (exact text, each asserted in a test)

| Text | Test |
|---|---|
| `[EXPECTED] CASE_CLOSED: this case is closed and accepts no reason or decision` | `test_refuses_a_reason_after_the_case_is_decided`, `test_refuses_a_reason_after_the_case_is_closed` |
| `[EXPECTED] SEVERITY_OUT_OF_BANDS: severity band must be MINOR, STANDARD or SEVERE` | `test_refuses_a_severity_outside_the_bands` |
| `[EXPECTED] ALREADY_DECIDED: this case already has a decision` | `test_refuses_a_second_decision` |
| `[EXPECTED] EMPTY_TERMS: booking_terms must not be empty` | `test_refuses_empty_terms` |
| `[EXPECTED] TERMS_TOO_LONG: booking_terms must be at most 8000 characters` | `test_refuses_empty_terms` |
| `[EXPECTED] BAD_CASE_ID: case_id must be 64 hexadecimal characters` | `test_refuses_malformed_hashes` |
| `[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_hashes` |
| `[EXPECTED] NOT_THE_OPENER: only the address that opened the case can close it` | `test_refuses_a_reason_after_the_case_is_closed` |
| `[EXPECTED] DUPLICATE_CASE: a case with this case_id already exists` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] NO_REASON: no reason has been submitted for this case` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] UNKNOWN_CASE: no case is stored for this case_id` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] BAD_STATED_REASON: stated_reason must be 1-2000 characters` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] BAD_EVIDENCE_SUMMARY: evidence_summary must be 1-4000 characters` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] REASON_ALREADY_SUBMITTED: this case already has a stated reason` | `test_refuses_other_lifecycle_and_input_errors` |
| `[EXPECTED] BAD_INDEX: no case at this index` | `test_refuses_other_lifecycle_and_input_errors` |
| `[LLM_ERROR] the model did not return a JSON object` | `test_refuses_malformed_model_answers` |
| `[LLM_ERROR] the model returned no PENALTY_JUSTIFIED or PENALTY_NOT_JUSTIFIED verdict` | `test_refuses_malformed_model_answers` |
| `[LLM_ERROR] the model's clause is not an exact substring of the booking terms` | `test_refuses_malformed_model_answers` |
| `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` |
| `[LLM_ERROR] the decision result is malformed` | used inside the validator (a malformed leader result → validator `False`, `test_validator_rejects_bad_leader_results`) |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (pinned runner, no comment under the header, `while` not `for`, no `sorted`/`lambda`, GenLayer storage types, custom validator agreeing on a stable field, error prefixes) |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `ConductReasonReview` (its web fetch and 0–100 score replaced by the case lifecycle and a verdict/band judgment); `genlayer_scaffold_test` template `llm-judge` (fixtures `direct_vm`, `direct_deploy`, `direct_alice`, `mock_llm`) |
| GenLayer docs consulted | NOT_RUN | `genlayer_search_docs` not called (the rules resource covered what was needed; it failed with "fetch failed" in earlier runs) |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the file (sha256 `9336ac70…2727a` before and after); byte identity of the pasted text was not machine-checked |
| Tests pass: 14 passed, 0 failed | OBSERVED | `python3 -m pytest tests/factory/test_conduct_reason_review.py -q` → `14 passed in 0.29s`; pytest 9.1.1, genlayer-test **0.29.2** direct mode; LLM mocked (no web call in this contract) |
| One test per answer word and band | OBSERVED | `PENALTY_JUSTIFIED` + `STANDARD` (`test_penalty_justified_standard`), + `MINOR` (`test_penalty_justified_minor`, model's lowercase `minor` normalised), + `SEVERE` (`test_penalty_justified_severe`); `PENALTY_NOT_JUSTIFIED` + `NONE` (`test_penalty_not_justified_has_band_none`, also an empty band stored as `NONE`) |
| One test per must-refuse case | OBSERVED | reason after the case closed: after a decision (`test_refuses_a_reason_after_the_case_is_decided`) and after the opener's close (`test_refuses_a_reason_after_the_case_is_closed`); severity outside the bands (`test_refuses_a_severity_outside_the_bands`: `EXTREME`, `NONE`/empty/number/missing on a justified verdict, `MINOR`/`CRITICAL` on a not-justified verdict); plus second decision, empty terms, malformed hashes, other lifecycle errors and malformed model answers. Each refusal leaves the stored case unchanged (asserted) |
| Validators agree on verdict AND band, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same verdict and band with another clause and reason → `True`; same verdict, other band → `False`; other verdict → `False`; validator's model answers out of bands → `False`; leader clause not in the terms → `False`; leader band out of bands, or a real band on a not-justified verdict → `False`; leader verdict not a known word → `False`; leader error → `False`; a well-formed matching leader result → `True`. Real multi-validator consensus: NOT_RUN |
| The tests can fail | OBSERVED | three mutations, each run then reverted (file sha256 `9336ac70…2727a` unchanged afterwards, then 14 passed): `CASE_CLOSED` check removed from `submit_reason` → 2 failed (both reason-after-close tests); any band accepted on a justified verdict → 1 failed (`test_refuses_a_severity_outside_the_bands`); validator ignores the band → 1 failed (`test_validator_agrees_on_verdict_and_band_not_the_wording`) |
| Studionet reachable through the MCP server | OBSERVED | `genlayer_network_status` 21:56 UTC: endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b060805`, not syncing |
| Schema from Studionet | NOT_RUN | `genlayer_get_contract_schema` with base64 of the file: `unsupported_contract_rpc`, "Hosted Studionet does not currently provide reliable contract RPC methods like gen_getContractState/gen_getContractCode/gen_getContractSchema", upstream `Internal database error (code -32603)`. Endpoint limitation, not retried |
| Deploy simulation on Studionet | NOT_RUN | `genlayer_call_contract` type `deploy` (simulation, nothing signed or sent) with the orchestrator's encoder output (`glcall.mjs deploy … '[]'`, 32,737 hex characters, sha256 of the hex file `1c18d744…74ce`): both attempts → `RLP string ends with 16367 superfluous bytes (code -32603)`. The calldata had to be pasted by hand into the tool call, and the builder's paste contained a transcription slip (an extra hex digit near the `close_case` definition, found on review after the second attempt), so the node received malformed RLP, not this contract. Tooling, not the contract: no contract change; the PR stays a draft until a deploy simulation or the owner's deploy passes |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked; no real model has judged a case |
| Runs on GenVM; deploys and finalizes on a network; consensus between real validators | NOT_RUN | not until the owner deploys. Direct mode runs the SDK in CPython, without consensus, gas or storage encoding |

## Attempts (owner's rule: up to three, each retry after a change backed by the failed attempt's evidence)

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | pass | `14 passed in 0.29s` | — |
| Studionet reachability | 1 | pass | `healthy`, chain `0xf22f` | — |
| Studionet schema | 1 | not supported | hosted Studionet has no `gen_getContractSchema` | none (endpoint limitation) |
| Studionet deploy simulation | 1 | tool error | `RLP string ends with 16367 superfluous bytes (code -32603)` | none to the contract: re-pasted the calldata |
| Studionet deploy simulation | 2 | tool error | same error; the hand-pasted hex still carried the same slip | none to the contract; out of time in this run (NOT_RUN). Next try: send the calldata from a file rather than by hand |

## Choices the owner may want to change

- **Band when not justified.** `PENALTY_NOT_JUSTIFIED` always stores band `NONE` (no penalty, so
  no severity). The model may send `NONE` or an empty band there; a real band (`MINOR` etc.) with a
  not-justified verdict is refused as `SEVERITY_OUT_OF_BANDS` rather than silently dropped.
- **No caller-supplied severity.** The API takes no severity from the caller; the band comes from
  the model and is checked against the three bands. If SnapLink wants to propose a band (or cap
  one), add a parameter and refuse it with the same `SEVERITY_OUT_OF_BANDS` text.
- **Clause for both verdicts.** Every decision quotes a clause from the booking terms: the one
  that sets the penalty, or the one that excuses it. A model answer whose clause is not an exact
  substring of the terms is refused (`[LLM_ERROR]`), so terms with no relevant clause cannot be
  decided; the prompt tells the model to answer not-justified when no clause covers the reason,
  but it still has to quote some clause.
- **Who does what.** Anyone opens a case (the case id is a 64-hex value such as sha256 of
  SnapLink's own booking reference), anyone submits the one reason, anyone asks for the decision;
  only the opener can close a case without a decision. Closed means status `DECIDED` or `CLOSED`.
- **One reason per case, one decision per case.** A reason cannot be replaced
  (`REASON_ALREADY_SUBMITTED`); a decision is final (`ALREADY_DECIDED`), with no appeal or
  revoke method and no admin.
- **Leader errors.** If the leader's model answer is refused (band out of bands, bad clause), the
  transaction reverts and nothing is stored; a validator never accepts a leader error.
- **Public data.** Terms, the stated reason and the evidence summary are stored on-chain in the
  clear; callers must send only public text and the hash of the private evidence. The contract
  cannot check that the hash matches the private evidence.

## Deploy steps for the owner (Studionet, by hand, from a checkout of the PR branch)

```
npm install -g genlayer@0.40.0
genlayer network set studionet
```

bash:

```
genlayer deploy --contract contracts/factory/conduct_reason_review.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/conduct_reason_review.py --fees ($fees -replace '"','\"')
```

Read-only checks: `genlayer receipt <tx hash>`; `genlayer call <address> get_case_count`.
Post the transaction hash on the pull request for the after-deploy Studionet check.

## Not verified

Real model judgment on real booking terms and reasons; GenVM consensus on a network; the
deployed contract's behaviour on Studionet (until the owner deploys and posts the hash).

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer` CLI command run; no pull request opened or merged
(the orchestrator opens it); nothing pushed to `main`; nothing in Base44. Only read-only RPC
through the MCP server (network status, schema request, deploy simulation via `gen_call`).

## Studionet pre-deploy check (through genskill MCP, read-only)

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Reachability | 1 | pass | OBSERVED | `genlayer_network_status` 21:56 UTC: `https://studio.genlayer.com/api`, `healthy`, chain `0xf22f`, block `0x6b060805`, `syncing: false` |
| Schema | 1 | not supported | NOT_RUN | `unsupported_contract_rpc` on `studionet-hosted`; upstream `Internal database error (code -32603)` |
| Deploy simulation | 1–2 | tool error | NOT_RUN | `RLP string ends with 16367 superfluous bytes (code -32603)`: hand-pasted calldata malformed (builder's transcription slip), not the contract |

Studionet check: **NOT_RUN** (reachability passed; schema unsupported on the hosted endpoint; deploy
simulation not completed). The pull request stays a draft.
