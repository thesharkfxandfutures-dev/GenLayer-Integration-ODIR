# Factory record — photo_delivery_review — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #13 of the owner's page ("Role contracts (one per role)",
row 13, Photographer; `factory/BACKLOG.md` item 13). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/photo_delivery_review-2026-11-25` from `main` (`f0a4525`).
Pull request: #15 (ready for review: verifier PASS and the pre-deploy Studionet check passed; the post-deploy check waits for the owner's transaction hash).

Owner's row, as given to the builder:

| # | Role | Contract | What it decides | Answer | Must refuse (the row's own) |
|---|---|---|---|---|---|
| 13 | Photographer | photo_delivery_review | Do the delivered photos match the shot list, image count, formats and usage licence? | `DELIVERED` / `SHORTFALL` + the missing item | a brief with no licence terms |

Shared by every role row: inputs = the agreed terms (text both parties agree to make public), what happened
(a delivery note, a log or public URLs) and `evidence_sha256` of anything private; refusals = an evidence hash
that does not match, the same case twice, empty terms. The page says most role contracts share one shape, so
this one is built as a reusable template (below) but decides exactly row 13.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/photo_delivery_review.py` | `1a9b3b4d5d5a4b30518b7544e5e50e41e411e9f4cae6933d20edb35e80b3bcf6` |
| `tests/factory/test_photo_delivery_review.py` | `f0e5369766b5e9dd0eee47bdee0b177e38b1d9a35d1995bd015844174711c872` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`; line 2
blank, line 3 `from genlayer import *`, then the doc block documenting the constructor, the public-data rule,
every method, every refusal and the consensus rule. Class `PhotoDeliveryReview`; constructor
`PhotoDeliveryReview()` takes no arguments; the deploying address becomes the owner.

Methods:
- `review_delivery(case_id, agreed_terms, what_happened, evidence_sha256)` (owner only) →
  `{case_id, role, verdict, missing_item, reason}`. `verdict` is `DELIVERED` or `SHORTFALL`; for `SHORTFALL`,
  `missing_item` is the one missing item quoted from the agreed terms or the delivery account (3..400
  characters, verbatim up to whitespace runs); for `DELIVERED` it is `""`.
- Views: `get_owner()`, `get_role()` (`"photographer"`), `has_review(case_id)`, `get_review(case_id)` (stored
  JSON text), `get_review_count()`, `get_review_id(i)`.

Template shape for later role rows (sections of the file): 1 constants and exact texts; 2 shared helpers
(case id, terms, account, evidence-hash, quoted-item and decision-shape checks, model-answer parser);
3 the judgment runner (leader and validator, agreement on the verdict word only); 4 this row: `ROLE_KEY`,
the two verdict words, the row's own terms check (`_require_licence_terms`) and the prompt (`_build_prompt`),
then the contract class (owner check, evidence-hash check, same-case check, verdict record, views). A later row
changes only section 4 and the verdict words.

Inputs, as built:
- `case_id` (added input, public): 1..64 characters from A-Z a-z 0-9 . _ -, stored lower-case; the identity
  of the dispute, so "the same case twice" has something to refuse. Nothing else was added.
- `agreed_terms`: 1..8000 characters (the brief: shot list, image count, formats, usage licence).
- `what_happened`: 1..8000 characters (delivery note, log or public URLs as text; links are not opened).
- `evidence_sha256`: must be the sha256 (hex, upper-case accepted, surrounding spaces ignored) of the UTF-8
  bytes of `what_happened` exactly as supplied. This is how "an evidence hash that does not match the supplied
  evidence text" is checkable on chain. Private files stay off chain; if they matter, their own sha256 values
  go inside the public account.

The licence check (the row's own refusal) is deterministic code, not the model: `agreed_terms` must contain a
line that starts (after list marks such as `-`, `*`, `1.`) with `Usage licence`, `Licence` or `License`
(optionally followed by `terms`) and a colon, with a clause that has at least 4 letters or digits and is not a
placeholder (none, n/a, nil, TBC, TBD, TBA, unknown, pending, none stated, not agreed, not specified, no
licence, to be agreed / confirmed / decided / negotiated / determined and a few close variants). A bare label
takes the lines under it up to the next blank line as its clause.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `DELIVERED` (missing item stored as `""`; stored record checked field by field) | `test_delivered_when_the_delivery_matches_the_brief` |
| Answer | `SHORTFALL` + the missing item quoted from the agreed terms | `test_shortfall_names_the_missing_item_quoted_from_the_terms` |
| Answer | `SHORTFALL` + the item quoted from the delivery account instead | `test_shortfall_item_may_be_quoted_from_the_delivery_account` |
| Item matched up to whitespace | stored item has whitespace runs collapsed | `test_item_quote_is_matched_up_to_whitespace` |
| `DELIVERED` never carries an item | a model item on `DELIVERED` is dropped | `test_delivered_never_stores_a_missing_item` |
| Verdict word spelling | `" shortfall "` is read as `SHORTFALL` | `test_a_lower_case_verdict_word_is_read_as_the_word` |
| Prompt carries public inputs only | no evidence hash, terms hash or case id in the prompt; the four checks and the role are | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id` |
| Must refuse (row): a brief with no licence terms | `[EXPECTED] NO_LICENCE_TERMS: the brief states no usage licence; agreed_terms needs a line starting 'Usage licence:' or 'Licence:' (or 'License:') followed by the licence terms` | `test_refuses_a_brief_with_no_licence_terms` (15 variants: no licence line, licence only in a sentence, label without colon, blank clause, none / None. / N/A / TBC / "to be agreed" / "not specified" / `-`, bare label followed by a blank line, "Licensee:", "Licensing:") and `test_a_licence_line_is_found_in_any_common_layout` (9 accepted layouts: US spelling, bullets and numbering, "terms:" labels, list under a bare label, CRLF, licence line first, "national use only") |
| Shared: empty terms | `[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty` | `test_refuses_empty_terms` ("", spaces, newlines; refused before the licence check and before the hash is looked at) |
| Shared: evidence hash does not match | `[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal characters) of the what_happened text exactly as supplied` | `test_refuses_an_evidence_hash_that_does_not_match` (another account's hash, the terms' hash, one trailing space, one changed digit, zeros, 63 / 65 characters, non-hex, empty, `0x` prefix, and the account edited after hashing; the exact hash, upper-case and padded, is accepted and stored lower-case) |
| Shared: the same case twice | `[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict` | `test_refuses_the_same_case_twice` (same inputs, id in another case, same id with other evidence, same id with other terms; first verdict unchanged; a different id with identical text is a new case) and `test_a_refused_review_does_not_lock_the_case` (a refusal or `[LLM_ERROR]` stores nothing, so the case can be retried) |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can request a delivery review` | `test_only_the_owner_requests_reviews` |
| Input shape | `[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -` | `test_refuses_bad_case_ids` ("", space, inner space, `/`, newline, 65 characters, non-ASCII, `:`, int, None; also on `has_review`) |
| Input length | `[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters`; `[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty`; `[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters` | `test_refuses_terms_over_the_limit` (8000 accepted, 8001 refused), `test_refuses_an_empty_or_overlong_account_of_what_happened` |
| Reads | `[EXPECTED] NO_REVIEW: no review is stored for this case_id`; `[EXPECTED] BAD_INDEX: nothing at this index` | `test_reads` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of DELIVERED or SHORTFALL`; `[LLM_ERROR] the model's missing item is not 3 to 400 characters quoted from the agreed terms or the delivery account`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (15 bad answers), `test_refuses_an_item_over_the_limit` (a 495-character quote refused, a 400-character one accepted) |
| Validator agree / disagree | verdict word only; the leader's item must be quoted from the supplied text; `DELIVERED` must carry no item; `[LLM_ERROR] the decision result is malformed` is internal to the validator | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_delivered` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `PhotoDeliveryReview`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment: this row says nothing about reading URLs) and its score band replaced by the verdict word |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings. Run twice: on the first source and again on the final source (after one simplification, see Attempts). The source was pasted into the tool call by hand; byte identity of the pasted text was not machine-checked |
| Tests pass: 22 passed | OBSERVED | `python3 -m pytest tests/factory/test_photo_delivery_review.py -q` → `22 passed in 0.59s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (this contract reads no web page) |
| One test per answer word, must-refuse case and shared refusal | OBSERVED | table above |
| The tests can fail | OBSERVED | 33 planted mutations on the final source, each run with `pytest -x` then reverted: all 33 caught; contract sha256 `1a9b3b4d…bcf6` unchanged afterwards. Mutations: owner check removed; licence check removed; placeholders accepted; licence minimum length removed; US spelling label dropped; colon not required; list under a bare label ignored; hash comparison removed; hash compared case-sensitively; hash not trimmed; hash compared to the wrong text; same-case check removed; case id not lower-cased; empty terms accepted; terms limit changed; empty `what_happened` accepted; validator always `True`; validator compares the whole result; validator accepts a leader error; validator skips the leader shape check; item-quote check accepts anything; item quoted from the terms only; item minimum length dropped; item limit raised; `DELIVERED` keeps the model's item; shape check lets `DELIVERED` carry an item; verdict words swapped; reason not required; evidence hash sent in the prompt; case id sent in the prompt; prompt drops the licence check; review not stored; role key changed. An earlier run on the first source caught 30 of 32 (two survivors, explained in Attempts) |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another item and reason → `True`; the other word → `False`; forged item not in the text, item under 3 characters, empty item for `SHORTFALL`, missing key, bad word, missing reason, non-dict leader → `False`; `DELIVERED` with an item → `False`; the validator's own model answer malformed → `False`; leader error → `False` |
| Hashes and the case id are not sent to the model | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id`: the only LLM mock requires the four checks, the brief, the delivery account and the role, and the absence of the evidence hash, the terms hash and the case id |
| Studionet reachable | OBSERVED | `genlayer_network_status` (25 Nov 2026 05:53:07 UTC per the health timestamp): endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b0677c3`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` answered `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`). It was sent with a 14-line probe contract, not this contract's source (the operation is refused by endpoint mode, so the 25,448-character base64 of this source was not resent); endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deploy contracts/factory/photo_delivery_review.py '[]'` (genlayer-js 0.18.4; 38,188 characters including `0x`, sha256 of the hex `d720061c47a3759e5405bc748141bb4c97a02a40b2f7e439ecb381d6eee2f833`, prefix `0xf94a92b94a8d`, suffix `0600`) → `"00"`, decoded `null` (constructor returned). The hex was pasted into the call by hand from four printed chunks; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it (two earlier pastes were cut short and the node refused them with `RLP string too short`) |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info (first source) | none needed. After mutation testing the redundant hash-format test and the unused `HEX_DIGITS` constant were removed, so the final source was linted again |
| Lint | 2 | pass | 0 errors, 0 warnings, 0 info (final source, sha256 `1a9b3b4d…bcf6`) | — |
| Tests | 1 | pass | 22 passed in 0.70s (first source) | none needed |
| Mutations | 1 | 30 of 32 caught | survivor 1, "evidence hash format not checked": an equivalent mutant (a value that is not 64 hex characters can never equal a sha256 digest, so the length and hex test was dead code); survivor 2, "validator accepts a leader error" written as deleting the guard: still returned `False`, because `leaders_res.calldata` raises inside the `try` | survivor 1: the dead code and the unused constant were removed from the contract; survivor 2: the mutation was rewritten as "the guard returns `True`" (a real fault); two mutations for the hash (case, trimming) were added |
| Tests | 2 | pass | 22 passed in 0.59s (final source) | — |
| Mutations | 2 | 33 of 33 caught | sha256 of the contract unchanged afterwards | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | — | NOT_RUN | `unsupported_contract_rpc` on a probe contract | not resent with this source (endpoint refuses the operation) |
| Studionet deploy simulation | 1 | tool error | `RLP string too short (code -32603)`: the `data` I pasted was cut short (request payload, not the contract) | same encoder output pasted again in full |
| Studionet deploy simulation | 2 | tool error | `RLP string too short (code -32603)`: the paste was cut short again | same encoder output pasted in full, checked chunk by chunk |
| Studionet deploy simulation | 3 | pass | `"00"` → `null` | — |
| Verifier | 1 | PASS | independent clone at `240b86a`: lint 0 errors / 0 warnings, `22 passed`, every answer and the four must-refuse cases have exact-text tests, safety audit clean, 7 of 7 planted mutations caught, sha256 `1a9b3b4d…bcf6` restored after each | — |

The two deploy-simulation errors are tooling (a truncated request), not the contract, so they do not count
against it.

## Open questions for the owner

- **Who may request a review.** `review_delivery` is owner only, as in `champion_seat_award`, because the first
  verdict on a case id is final: if anyone could request, anyone could lock a case with weak evidence. SnapLink's
  backend would sign with the owner address. The row does not say; opening the method is a one-line change.
- **What `evidence_sha256` binds.** The shared refusal is "an evidence hash that does not match", which can only
  be checked on chain against text the caller supplies. So the hash is the sha256 of the public `what_happened`
  text, byte for byte (no trimming). A hash of a private bundle that is never supplied cannot be checked; if you
  want both (a public account and a separate private-evidence hash), a fifth input would be added.
- **The licence rule is by form.** The brief must state the licence on a labelled line ("Usage licence: ...",
  "Licence: ...", "License: ..."); a brief that mentions a licence only in a sentence is refused as having no
  licence terms, and "Licence: none / n/a / TBC / to be agreed" is refused. Is that the strictness you want, or
  should any mention of a licence pass?
- **Same case.** The identity is a caller-supplied public `case_id`; one verdict per id, `SHORTFALL` locks it
  too, and a refusal or `[LLM_ERROR]` stores nothing so the call can be retried. I did not also refuse identical
  text under a new id, because two real disputes can share a standard brief and a short note.
- **Judgment rules the model is told** (in the prompt, not enforced by code): more images than agreed is not a
  shortfall; a delivery account that is silent about the licence is not a shortfall by itself, only a narrower
  grant is (fewer uses or channels, smaller territory, shorter term, watermarked or preview-only files);
  anything else the account does not show is a `SHORTFALL`; with several gaps the first of shot list, count,
  formats, licence is named.
- **Missing item.** A quote of 3..400 characters from the terms or the account (so a short quote such as `RAW`
  can also match inside a longer word); for `DELIVERED` it is empty. Only the verdict word must match between
  leader and validator.
- **Extra refusals beyond the row and the shared three:** `OWNER_ONLY`, `BAD_CASE_ID`, `TERMS_TOO_LONG`,
  `EMPTY_WHAT_HAPPENED`, `WHAT_HAPPENED_TOO_LONG` (8000-character limits), plus the read refusals and the
  model-answer refusals. The contract does not open links; URLs in the account are read as text.
- **On chain in the clear.** The terms, the account, the case id and the hashes are public calldata and storage.
  The contract cannot stop a caller putting a name or an email in the text; SnapLink must send public text only.

## Not verified

The real model's judgment; GenVM execution and multi-validator consensus on a network (direct mode runs the SDK
in CPython); any write method on Studionet; the Studionet schema (endpoint refuses it); byte identity of the
text pasted into the lint call and the deploy simulation.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction` and
`genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged; nothing
pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's page are left
to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/photo_delivery_review.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/photo_delivery_review.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_role` (expected
`"photographer"`); `genlayer call <address> get_review_count` (expected `0` on a fresh contract);
`genlayer call <address> get_owner` (expected the deploying address).

VERDICT: DRAFTED — lint clean, 22 direct-mode tests pass with the model mocked, 33 of 33 planted mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN (endpoint). The PR stays
a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view read) passes.

## Independent verification (verifier agent, 2026-11-25T10:03Z)

Verifier: a separate agent that did not build the contract, judging the code against the owner's row 13
(`DELIVERED` / `SHORTFALL` + the missing item; must refuse a brief with no licence terms) and the shared
role-contract refusals (an evidence hash that does not match; the same case twice; empty terms). Own clone at
`/home/claude/verify-photo_delivery_review`, branch head `240b86a`. The builder's claims above were not used as
evidence. Contract sha256 `1a9b3b4d5d5a4b30518b7544e5e50e41e411e9f4cae6933d20edb35e80b3bcf6`; test file sha256
`f0e5369766b5e9dd0eee47bdee0b177e38b1d9a35d1995bd015844174711c872`. Python 3.13.18, pytest 9.1.1,
genlayer-test 0.29.2 (direct mode). The Studionet deploy simulation was not redone.

| Check | How | Result | Grade |
|---|---|---|---|
| Lint | `mcp__genskill__genlayer_lint_contract` on the full 455-line source | `ok: true`, 0 errors, 0 warnings, 0 info, no findings. Source pasted by hand from the file; the file has no tabs, trailing whitespace, CR or non-ASCII bytes, but byte identity of the paste was not machine-checked | OBSERVED |
| Tests | `python3 -m pytest tests/factory/test_photo_delivery_review.py -q` | `22 passed` (first run 56.60s incl. warm-up; re-run on the restored source `22 passed in 0.60s`) | OBSERVED |
| Coverage: `DELIVERED` | read the tests | `test_delivered_when_the_delivery_matches_the_brief` asserts the whole result dict and the stored record | OBSERVED |
| Coverage: `SHORTFALL` + missing item | read the tests | `test_shortfall_names_the_missing_item_quoted_from_the_terms` asserts verdict and `missing_item == "40 edited images"` (also `..._quoted_from_the_delivery_account`) | OBSERVED |
| Coverage: no licence terms | read the tests | `test_refuses_a_brief_with_no_licence_terms`, full `NO_LICENCE_TERMS` text, 15 variants | OBSERVED |
| Coverage: evidence hash does not match | read the tests | `test_refuses_an_evidence_hash_that_does_not_match`, full `EVIDENCE_HASH_MISMATCH` text | OBSERVED |
| Coverage: same case twice | read the tests | `test_refuses_the_same_case_twice`, full `SAME_CASE_TWICE` text | OBSERVED |
| Coverage: empty terms | read the tests | `test_refuses_empty_terms`, full `EMPTY_TERMS` text | OBSERVED |
| Refusal form | grep of every `raise` in the source; read of gltest 0.29.2 `expect_revert` | every `raise` is `gl.vm.UserError(ERR_*)` with a fixed constant; each test passes the full fixed text to `expect_revert`, which checks that the error text contains it (it does not check the exception type; the type is established from the source) | OBSERVED |
| Safety: public data only | read of inputs, docstring and prompt | inputs are a public case id, public terms text, public account text and a sha256; no name, email, age or private-evidence field is asked for; the prompt carries neither hash nor case id | OBSERVED |
| Safety: no key, no sending | grep for emit / contract calls / transfer / submit / raw RPC / key / web | none: no key handling, no external contract call, no value transfer, no web access | OBSERVED |
| Safety: source shape | read lines 1-3 and the docstring | line 1 pinned runner `py-genlayer:1jb45aa8…z09h6`, line 2 blank (no comment under the header); constructor `PhotoDeliveryReview()` documented in the module docstring | OBSERVED |
| Safety: comparative equivalence | read `_judge` | `gl.vm.run_nondet_unsafe`; the validator checks the leader's shape, re-runs the judgment and agrees only on the same verdict word | OBSERVED |
| Safety: mocks | read the tests and gltest `wasi_mock.py` | every LLM call uses `direct_vm.mock_llm`; an unmatched prompt raises `MockNotFoundError` (no live handler in direct mode); the contract reads no web page | OBSERVED |
| Mutation M1 | removed the `_require_licence_terms(terms)` call | caught: `test_refuses_a_brief_with_no_licence_terms`, `test_a_refused_review_does_not_lock_the_case` (2 failed) | OBSERVED |
| Mutation M2 | swapped `VERDICT_OK` and `VERDICT_SHORT` | caught: 17 failed, incl. `test_delivered_when_the_delivery_matches_the_brief`, `test_shortfall_names_the_missing_item_quoted_from_the_terms` | OBSERVED |
| Mutation M3 | removed the evidence-hash comparison | caught: `test_refuses_an_evidence_hash_that_does_not_match` | OBSERVED |
| Mutation M4 | removed the same-case check | caught: `test_refuses_the_same_case_twice` | OBSERVED |
| Mutation M5 | validator always returns `True` | caught: `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_delivered` | OBSERVED |
| Mutation M6 | `_check_terms` no longer refuses empty or whitespace-only terms | caught: `test_refuses_empty_terms` | OBSERVED |
| Mutation M7 | validator compares the whole result (wording) instead of the verdict word | caught: `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_delivered` | OBSERVED |
| Restore | `git checkout -- contracts/factory/photo_delivery_review.py` after each mutation | sha256 back to `1a9b3b4d…bcf6` every time; tracked files unchanged (only untracked `__pycache__` from pytest, deleted); no mutation committed | OBSERVED |

Notes (not defects): the owner check and the case-id check run before the empty-terms check, so a non-owner
or a bad id with empty terms gets `OWNER_ONLY` / `BAD_CASE_ID` first; the row does not fix an order.
`evidence_sha256` is bound to the public `what_happened` text (the builder's open question to the owner stands).

Verifier verdict: PASS
