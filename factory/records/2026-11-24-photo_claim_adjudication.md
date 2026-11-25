# Factory record — photo_claim_adjudication — 24 Nov 2026

Factory run of 24 Nov 2026 (run start 21:44:45 UTC), builder for contract #6 of the owner's page
(main table, row 6; `factory/BACKLOG.md` item 5). Cloud workspace, genskill MCP server as the
owner's claude.ai connector. Branch `factory/photo_claim_adjudication-2026-11-24` from `main`.
Pull request: opened by the orchestrator (draft).

Owner's row, verbatim:

| # | Contract | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|
| 6 | photo_claim_adjudication | Two people claim one photograph: whose claim does the public evidence support? | each party's statement, first-publication URL and date, evidence hash | CLAIMANT_A / CLAIMANT_B / UNDECIDED + the deciding fact quoted | a third claimant; a statement edited after both are in; a decision before both exist |

## Output

| File | sha256 |
|---|---|
| `contracts/factory/photo_claim_adjudication.py` | `4b2ca45f4f98eebcdbf62b362e6091068d05abdc62142d60fad70d834d2e9277` |
| `tests/factory/test_photo_claim_adjudication.py` | `98500ce234abed376b36fc78b4437fa4e5f606f268a2e1a211022de008c9e44f` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the docstring documenting the constructor.
Class `PhotoClaimAdjudication`, constructor `PhotoClaimAdjudication()` takes no arguments; no owner
or admin role.

Methods: `submit_claim(media_sha256, statement, first_publication_url, first_publication_date,
evidence_sha256)` (first sender = claimant A, second different sender = claimant B);
`edit_claim(...)` same arguments (claimant A only, while B is missing); `decide(media_sha256)`
returns `{media_sha256, verdict, deciding_fact, fact_source, reason}`; views `get_dispute`,
`get_dispute_count`, `get_dispute_id`.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo
version in `.mcp.json` is genskill-mcp@2.3.3; the connector does not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `CLAIMANT_A` (fact quoted from statement A) | `test_claimant_a_with_the_deciding_fact_quoted` |
| Answer | `CLAIMANT_B` (fact = B's date as given) | `test_claimant_b_with_a_quoted_date` |
| Answer | `UNDECIDED` (fact may be empty) | `test_undecided_is_a_valid_answer` |
| Must refuse: third claimant | `[EXPECTED] THIRD_CLAIMANT: this photo already has two claimants` | `test_refuses_a_third_claimant` |
| Must refuse: edit after both are in | `[EXPECTED] STATEMENT_LOCKED: both claims are in; statements can no longer be edited` | `test_refuses_an_edit_after_both_are_in` (A and B both refused; A's edit before B joins succeeds) |
| Must refuse: decision before both exist | `[EXPECTED] BOTH_CLAIMS_REQUIRED: a decision needs both claimants' statements` (and `[EXPECTED] UNKNOWN_DISPUTE: no dispute is stored for this media hash` when no claim exists) | `test_refuses_a_decision_before_both_exist` |
| Second decision | `[EXPECTED] ALREADY_DECIDED: this dispute is already decided` | `test_refuses_a_second_decision` |
| Party claims twice / outsider edits | `[EXPECTED] ALREADY_A_CLAIMANT: this address already has a claim on this photo; use edit_claim`; `[EXPECTED] NOT_A_CLAIMANT: only a claimant can edit their own claim` | `test_refuses_a_second_claim_from_a_party_and_edits_from_others` |
| Malformed hashes | `[EXPECTED] BAD_MEDIA_HASH: media_sha256 must be 64 hexadecimal characters`; `[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_hashes` |
| Malformed date | `[EXPECTED] BAD_DATE: first_publication_date must be a real calendar date written YYYY-MM-DD` | `test_refuses_malformed_dates` |
| Empty / long statement, bad URL, bad index | `[EXPECTED] EMPTY_STATEMENT: statement must not be empty`; `[EXPECTED] STATEMENT_TOO_LONG: statement must be at most 2000 characters`; `[EXPECTED] BAD_URL: first_publication_url must be an http:// or https:// URL of at most 500 characters with no spaces`; `[EXPECTED] BAD_INDEX: no dispute at this index` | `test_refuses_empty_or_long_statements_and_bad_urls` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of CLAIMANT_A, CLAIMANT_B or UNDECIDED`; `[LLM_ERROR] the model's deciding fact is not quoted verbatim from the claims`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` |
| Validator agree / disagree | verdict word only | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_undecided` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `PhotoClaimAdjudication`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by the verdict word |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the written file; byte identity of the pasted text was not machine-checked |
| Tests pass: 16 passed | OBSERVED | `python3 -m pytest tests/factory/test_photo_claim_adjudication.py -q` → `16 passed in 0.34s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (no web read in this contract) |
| One test per answer word and per must-refuse case | OBSERVED | table above |
| The tests can fail | OBSERVED | mutation 1: `THIRD_CLAIMANT` check removed from `submit_claim` → 1 failed (`test_refuses_a_third_claimant`); mutation 2: validator always returns `True` → 2 failed (both validator tests). Each reverted; contract sha256 `4b2ca45f…9277` unchanged afterwards |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another fact and reason → `True`; `UNDECIDED` or `CLAIMANT_B` against a `CLAIMANT_A` leader → `False`; forged leader fact not in the claims → `False`; `CLAIMANT_A` with empty fact → `False`; bad verdict word → `False`; validator's own model answer malformed → `False`; leader error → `False`; `UNDECIDED` vs `UNDECIDED` with different facts → `True` |
| Evidence hashes are not sent to the model | OBSERVED (direct mode) | `test_prompt_carries_only_the_public_claims`: the only LLM mock requires both statements, URLs and dates and the absence of both evidence hashes |
| Studionet reachable | OBSERVED | `genlayer_network_status`: endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b06081b`, not syncing |
| Schema on Studionet | NOT_RUN | not attempted in this run (time budget); hosted Studionet is known to answer "not supported on studionet-hosted" for schema/interface (PR #4 follow-up record) |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from the orchestrator's encoder (`glcall.mjs deploy contracts/factory/photo_claim_adjudication.py '[]'`, 36,982 hex chars: `0xf94837b94832` + the file's bytes + `0600`) → `"00"`, which decodes to `null` (constructor returned). The hex was pasted into the call by hand; that it was byte-identical to the encoder output was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Real first-publication pages | NOT_RUN | by design the contract does not fetch the URLs |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | 1 failed, 15 passed | `test_prompt_carries_only_the_public_claims`: `MockNotFoundError: No LLM mock for prompt` — the test's regex assumed statement-URL-date order, but the prompt JSON uses sorted keys (date, url, statement) | test regex re-ordered (test file only; contract unchanged) |
| Tests | 2 | 1 failed, 15 passed | same test: `ImportError: Failed to load contract: only one contract is allowed` — a second `direct_deploy` in one test | the evidence-hash check folded into the one mock via negative lookahead (test file only) |
| Tests | 3 | 16 passed | — | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet deploy simulation | 1 | tool error | `Non-hexadecimal digit found (code -32603)`: the pasted `data` contained line breaks (transcription, not the contract) | same hex resent as one line |
| Studionet deploy simulation | 2 | pass | `"00"` → `null` | — |

## Choices the owner may want to change

- **Text only.** The contract judges the two public statements and the stated URLs and dates; it
  does not open the URLs, see the photo or the evidence files, or check that a date is true. A
  `web-oracle` version could read the first-publication pages.
- **Roles by address.** The first sender on a media hash is claimant A, the next different sender
  claimant B. Nobody else can join. There is no owner or admin, so a wrong decision cannot be
  revoked, and a squatter could open a dispute first as A.
- **Edits.** Claimant A may edit only while B is missing; once B joins, both are locked (B can never
  edit). Edits replace the whole claim (statement, URL, date, evidence hash).
- **Decision.** Anyone may call `decide` once both claims exist; it is final (`ALREADY_DECIDED`).
  An `[LLM_ERROR]` refusal stores nothing, so `decide` can be retried.
- **Deciding fact.** Must be an exact substring of statement A or B, URL A or B, or date A or B
  (`fact_source` names the first that contains it); required for `CLAIMANT_A`/`CLAIMANT_B`,
  optional for `UNDECIDED`. Only the verdict word must match between leader and validator.
- **Input limits.** Statement 1–2000 characters (trimmed); URL `http://` or `https://`, at most 500
  characters, no spaces or quotes; dates from 1826-01-01, real calendar dates only.
- **On chain in the clear.** Statements, URLs, dates and hashes are public calldata and storage.
  Parties must not put names, emails or private evidence in a statement; the contract cannot
  stop that.

## Not verified

The real model's judgment; real first-publication pages; GenVM execution and multi-validator
consensus on a network (direct mode runs the SDK in CPython); any write method on Studionet.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing
merged; nothing pushed to `main`; no other repository touched; nothing in Base44. The pull request
and the owner's Claude Docs page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/photo_claim_adjudication.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/photo_claim_adjudication.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_dispute_count`.

VERDICT: DRAFTED — lint clean, 16 direct-mode tests pass with the model mocked, Studionet reachable
and the deploy simulation constructs (`00`); schema NOT_RUN. The PR stays a draft until the owner
deploys and the post-deploy Studionet check (transaction report and a view read) passes.

## Independent verification — 25 Nov 2026 (scheduled factory run)

A separate verifier agent (not the builder) checked out this branch at `22cffed36b96681dbf628d0429e350f9e3d266c5`
and judged it from the code, the tests and page row 6, without this record. **Verdict: PASS.**

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Contract sha256 | 1 | `4b2ca45f4f98eebcdbf62b362e6091068d05abdc62142d60fad70d834d2e9277` | OBSERVED | unchanged after all mutations were reverted |
| genskill lint (full source) | 1 | `ok: true`, 0 errors, 0 warnings, 0 info | OBSERVED | source pasted into the tool call; byte identity not machine-checked |
| pytest (genlayer-test 0.29.2 direct mode, LLM mocked) | 1 | `16 passed in 0.26s` | OBSERVED | re-run in the verifier's own clone (orchestrator smoke run also `16 passed`) |
| Every answer word and refusal has a test; refusals exact | 1 | yes | OBSERVED | CLAIMANT_A, CLAIMANT_B, UNDECIDED; `THIRD_CLAIMANT`, `STATEMENT_LOCKED`, `BOTH_CLAIMS_REQUIRED` assert the full text |
| Quoted fact checked against the claims | 1 | yes | OBSERVED (direct mode) | in the leader's parse and in the validator |
| Mutations caught | 1 | 9 of 9 | OBSERVED | each refusal removed → 1 failed each; validator always agrees → 2; validator compares wording → 2; stored verdict flipped → 2; each verbatim-fact check removed → 1 each; refusal text changed → 1; each reverted, tree clean |
| Studionet schema (endpoint re-probe) | 1 | `unsupported_contract_rpc` (`studionet-hosted`, upstream `Internal database error (code -32603)`) | NOT_RUN | orchestrator probe with a 15-line contract, 25 Nov ~00:01 UTC; the refusal is per endpoint, so this file was not sent |
| Studionet reachability | 1 | healthy, chain `0xf22f`, block `0x6b062555` | OBSERVED | orchestrator `genlayer_network_status`, 25 Nov ~00:01 UTC |
| Deploy-simulation calldata reproducible | 1 | 36,982 hex chars, prefix `0xf94837b94832`, suffix `0600` | OBSERVED | orchestrator re-encoded this file with genlayer-js 0.18.4; matches the length and framing recorded above |

Notes from the verifier (not defects): the doc block sits after `from genlayer import *`, so it is not Python's
`__doc__` (lint accepts it); the test harness's `expect_revert` matches the message, so the `gl.vm.UserError` class was
confirmed by reading the source. Not reproduced by the verifier: the Studionet deploy simulation (not in its brief).
