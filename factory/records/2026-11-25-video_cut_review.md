# Factory record — video_cut_review — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #14 of the owner's page ("Role contracts (one per role)",
row 14, Videographer; `factory/BACKLOG.md` item 14). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/video_cut_review-2026-11-25` from `main` (`f0a4525`).
Pull request: #16 (ready for review: verifier PASS and the pre-deploy Studionet check passed; the post-deploy check waits for the owner's transaction hash).

Owner's row, as given to the builder:

| # | Role | Contract | What it decides | Answer | Also refuses |
|---|---|---|---|---|---|
| 14 | Videographer | video_cut_review | Does the cut meet the brief's runtime, aspect ratios and deliverables list? | `DELIVERED` / `SHORTFALL` + the missing item | a brief with no runtime |

Shared by every role row: inputs = the agreed terms (text both parties agree to make public), what happened
(a delivery note, a log or public URLs) and `evidence_sha256` of anything private; refusals = an evidence hash
that does not match, the same case twice, empty terms. Built on the row-13 role-contract shape
(`photo_delivery_review`, branch `factory/photo_delivery_review-2026-11-25`, not yet independently verified);
sections 1 to 3 were re-read and re-tested here, not taken on trust.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/video_cut_review.py` | `4b7972d3c75ca843fe64db4122ea1dd1616f42053509c161882775f892883b7d` |
| `tests/factory/test_video_cut_review.py` | `8e1baf8e6342edd52172e42fd04d478e3de2e7521b2fbe4a74a0e801423d9174` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`; line 2
blank, line 3 `from genlayer import *`, then the doc block documenting the constructor, the public-data rule,
every method, the runtime rule, every refusal and the consensus rule. Class `VideoCutReview`; constructor
`VideoCutReview()` takes no arguments; the deploying address becomes the owner. 542 lines, 22,081 bytes,
ASCII only, no `for` loops, `sorted`, `lambda` or forbidden imports.

Methods:
- `review_cut(case_id, agreed_terms, what_happened, evidence_sha256)` (owner only) →
  `{case_id, role, verdict, missing_item, reason}`. `verdict` is `DELIVERED` or `SHORTFALL`; for `SHORTFALL`,
  `missing_item` is the one missing item quoted from the agreed terms or the delivery account (3..400
  characters, verbatim up to whitespace runs); for `DELIVERED` it is `""`.
- Views: `get_owner()`, `get_role()` (`"videographer"`), `has_review(case_id)`, `get_review(case_id)` (stored
  JSON text), `get_review_count()`, `get_review_id(i)`.

Inputs, as built:
- `case_id` (added input, public): 1..64 characters from A-Z a-z 0-9 . _ -, stored lower-case; the identity
  of the dispute, so "the same case twice" has something to refuse. Nothing else was added.
- `agreed_terms`: 1..8000 characters (the brief: runtime, aspect ratios, deliverables list).
- `what_happened`: 1..8000 characters (delivery note, log or public URLs as text; links are not opened).
- `evidence_sha256`: must be the sha256 (hex, upper-case accepted, surrounding spaces ignored) of the UTF-8
  bytes of `what_happened` exactly as supplied. Private files stay off chain; if they matter, their own
  sha256 values go inside the public account.

The runtime check (the row's own refusal) is deterministic code, not the model. `agreed_terms` must contain a
line that, after list marks such as `-`, `*`, `1.` or `1)`, starts with `Runtime`, `Run time`, `Run-time`,
`Running time` or `Duration` (each also after `Target `), then optional spaces and a colon; and the text after
the colon on that same line must:
- hold a duration above zero written in digits: a number (a decimal part with `.` or `,` is read) followed by
  optional spaces or one hyphen and a time unit (`s`, `sec`, `secs`, `second(s)`, `m`, `min`, `mins`,
  `minute(s)`, `h`, `hr`, `hrs`, `hour(s)`), or a clock `m:ss` / `h:mm:ss` (two digits after each colon, so
  `16:9` is not a clock); and
- not contain the words TBC, TBD or TBA, nor "to be agreed / confirmed / decided / determined / negotiated /
  announced" or "not yet agreed / confirmed / decided / known".

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `DELIVERED` (missing item stored as `""`; stored record checked field by field) | `test_delivered_when_the_cut_meets_the_brief` |
| Answer | `SHORTFALL` + the missing item quoted from the agreed terms (the runtime line) | `test_shortfall_names_the_missing_item_quoted_from_the_terms` |
| Answer | `SHORTFALL` + the item quoted from the delivery account instead | `test_shortfall_item_may_be_quoted_from_the_delivery_account` |
| Item matched up to whitespace | stored item has whitespace runs collapsed | `test_item_quote_is_matched_up_to_whitespace` |
| `DELIVERED` never carries an item | a model item on `DELIVERED` is dropped | `test_delivered_never_stores_a_missing_item` |
| Verdict word spelling | `" shortfall "` is read as `SHORTFALL` | `test_a_lower_case_verdict_word_is_read_as_the_word` |
| Prompt carries public inputs only | no evidence hash, terms hash or case id in the prompt; the role and the three checks in order (runtime, aspect ratios, deliverables list) are | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id` |
| Must refuse (row): a brief with no runtime | `[EXPECTED] NO_RUNTIME: the brief states no runtime; agreed_terms needs a line starting 'Runtime:' (or 'Run time:', 'Running time:', 'Duration:') with a duration in digits such as '90 seconds', '3 min' or '2:30'` | `test_refuses_a_brief_with_no_runtime` (25 variants: no runtime line; runtime only in a sentence; label without colon; blank; spaces; TBC; none; "to be agreed"; N/A; "short"; number in words; `0 seconds`; `00:00`; `90` with no unit; `16:9`; `16:9 widescreen`; `4K at 25 fps`; `90 frames`; `90 seconds TBC`; "3 min, to be confirmed"; "(not yet agreed)"; `Runtimes:`; `Shoot duration: 8 hours`; a duration under `Deliverables:`; a list under a bare `Runtime:` label; and refused before the account's hash is looked at) and `test_a_runtime_line_is_found_in_any_common_layout` (17 accepted layouts: units, `2:30`, `1:02:30`, `0:45`, upper case, bullets and numbering, `Target runtime:`, `Target duration:`, space before the colon, `1.5 min`, `2.0 minutes`, `a 90-second spot`, `60-90 seconds`, several durations on the line, CRLF and bare-CR line ends, runtime line first) |
| Shared: empty terms | `[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty` | `test_refuses_empty_terms` ("", spaces, newlines; refused before the runtime check and before the hash is looked at) |
| Shared: evidence hash does not match | `[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal characters) of the what_happened text exactly as supplied` | `test_refuses_an_evidence_hash_that_does_not_match` (12 wrong values: another account's hash, the terms' hash, one trailing space, one changed digit, zeros, 63 / 65 characters, non-hex, `not-a-hash`, empty, spaces, `0x` prefix; and the account edited after hashing; the exact hash, upper-case and padded, is accepted and stored lower-case) |
| Shared: the same case twice | `[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict` | `test_refuses_the_same_case_twice` (same inputs, id in another case, same id with other evidence, same id with other terms; first verdict unchanged; a different id with identical text is a new case) and `test_a_refused_review_does_not_lock_the_case` (a refusal or `[LLM_ERROR]` stores nothing, so the case can be retried) |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can request a cut review` | `test_only_the_owner_requests_reviews` |
| Input shape | `[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -` | `test_refuses_bad_case_ids` ("", space, inner space, `/`, newline, 65 characters, non-ASCII, `:`, int, None; also on `has_review`) |
| Input length | `[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters`; `[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty`; `[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters` | `test_refuses_terms_over_the_limit` (8000 accepted, 8001 refused), `test_refuses_an_empty_or_overlong_account_of_what_happened` |
| Reads | `[EXPECTED] NO_REVIEW: no review is stored for this case_id`; `[EXPECTED] BAD_INDEX: nothing at this index` | `test_reads` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of DELIVERED or SHORTFALL`; `[LLM_ERROR] the model's missing item is not 3 to 400 characters quoted from the agreed terms or the delivery account`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (15 bad answers), `test_refuses_an_item_over_the_limit` (a quote over 400 characters refused, a 400-character one accepted) |
| Validator agree / disagree | verdict word only; the leader's item must be quoted from the supplied text; `DELIVERED` must carry no item; `[LLM_ERROR] the decision result is malformed` is internal to the validator | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_delivered` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (its "studionet is gasless" line is out of date; see the deploy steps) |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `VideoCutReview`; `genlayer_scaffold_test` template `llm-judge`, name `VideoCutReview`. The scaffold's URL fetch was dropped (text-only judgment: the row says nothing about reading URLs) and its 0-100 score band replaced by the verdict word; the body follows the row-13 shape |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full final source: `ok: true`, 0 errors, 0 warnings, 0 info, `findings: []` ("No blocking errors. 0 warning(s), 0 info."). The source was pasted into the tool call by hand; byte identity of the pasted text was not machine-checked |
| Tests pass: 22 passed | OBSERVED | `python3 -m pytest tests/factory/test_video_cut_review.py -q` → `22 passed in 0.58s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (this contract reads no web page) |
| One test per answer word, must-refuse case and shared refusal | OBSERVED | table above |
| The tests can fail | OBSERVED | 47 planted mutations of the final contract, each run with `pytest -x` against the final test file and then reverted: all 47 caught; contract sha256 `4b7972d3…3b7d` unchanged afterwards. Mutations: owner check removed; runtime check removed; placeholder check removed; placeholder words ignored; placeholder phrases ignored; duration not required; zero duration accepted; zero clock accepted; unit not required; clock form not read; clock needs no second digit; decimal part not read; hyphen before unit not skipped; colon not required; `Target` labels dropped; `Duration` label dropped; list marks not stripped; label matched anywhere in the line; CR line ends not split; hash comparison removed; hash compared case-sensitively; hash not trimmed; hash compared to the terms; same-case check removed; case id not lower-cased; empty terms accepted; runtime checked before empty terms; terms limit changed; empty `what_happened` accepted; validator always `True`; validator compares the whole result; validator accepts a leader error; validator skips the leader shape check; item-quote check accepts anything; item quoted from the terms only; item minimum dropped; item limit raised; `DELIVERED` keeps the model's item; shape check lets `DELIVERED` carry an item; verdict words swapped; reason not required; evidence hash sent in the prompt; case id sent in the prompt; prompt drops the aspect-ratio check; review not stored; role key changed; lower-case verdict not normalised. The first run (before four test cases were added) caught 43 of 47 (see Attempts) |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another item and reason → `True`; the other word → `False`; forged item not in the text, item under 3 characters, empty item for `SHORTFALL`, missing key, bad word, missing reason, non-dict leader → `False`; `DELIVERED` with an item → `False`; the validator's own model answer malformed → `False`; leader error → `False` |
| Hashes and the case id are not sent to the model | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id`: the only LLM mock requires the role, the three checks in order, the brief and the delivery account, and the absence of the evidence hash, the terms hash and the case id |
| Studionet reachable | OBSERVED | `genlayer_network_status` (25 Nov 2026 10:08:57 UTC per the health timestamp): endpoint `https://studio.genlayer.com/api`, health `healthy` (genvm, database, consensus, llm_providers healthy), chain id `0xf22f`, block `0x6b06b3ba`, not syncing; `gen_dbg_ping` not available (method not found), as before |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` with the base64 of this source (29,444 characters, sha256 of the base64 text `4335b60e8a54c12d33bf1fd9cb2ada54eb0d00d9e62169487fdc834ad4ff23a9`) answered `unsupported_contract_rpc`: "Contract RPC operation "get_contract_schema" is not supported on this endpoint", endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`. Endpoint limitation, not a contract fault; tried once, not retried |
| Deploy simulation on Studionet loads and constructs | OBSERVED | 25 Nov 2026 about 10:14 UTC. `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deployfile contracts/factory/video_cut_review.py '[]'` (genlayer-js 0.18.4; 44,180 characters including `0x`, sha256 of the hex `5b266bc2e434170117479caea971560b7f793b51a14b4b0ed10b3a2be85a537c`, prefix `0xf95646b95641`, suffix `0600`) → `"00"`, decoded `null` (constructor returned). The hex was pasted by hand from four printed chunks; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info on the final source (sha256 `4b7972d3…3b7d`) | — |
| Tests | 1 | pass | 22 passed in 0.55s (first test file) | none needed |
| Mutations (self-check) | 1 | 43 of 47 caught | survivors, all test gaps: "clock needs no second digit" (no refused case had an aspect ratio followed by more text), "decimal part not read" (every accepted decimal also had a non-zero digit after the point), "hyphen before unit not skipped" (the only hyphenated case also held a plain `90 seconds`), "CR line ends not split" (CRLF still split on `\n`) | test-only change, contract unchanged: added `Runtime: 16:9 widescreen` to the refused cases and `Runtime: 2.0 minutes`, `Runtime: a 90-second spot` and a bare-CR brief to the accepted layouts |
| Tests | 2 | pass | 22 passed in 0.59s (final test file, sha256 `8e1baf8e…9174`); again 22 passed in 0.58s for this record | — |
| Mutations (self-check) | 2 | 47 of 47 caught | contract sha256 unchanged afterwards | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` (endpoint mode) | not retried: the endpoint refuses the operation |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |
| Verifier | 1 | PASS | own clone at `e5bcf08`: lint 0 errors; 22 passed; both answers and all 4 must-refuse cases have exact-text tests; safety clean; 6 of 6 planted mutations caught | — |

No check failed because of the contract; no retry was needed for lint, tests or the network check.

## Open questions for the owner

- **What counts as "a stated runtime".** By form, on one line: a `Runtime:` / `Run time:` / `Run-time:` /
  `Running time:` / `Duration:` label (also after `Target `) with a duration above zero in digits and a time
  unit, or a clock (`2:30`). Refused as "no runtime": a runtime only mentioned in a sentence, numbers in words
  ("ninety seconds"), a number with no unit, frames or fps, `0` or `00:00`, a list under a bare `Runtime:`
  label (put it on the label's line), and any runtime line that also says TBC / TBD / TBA / "to be agreed" /
  "not yet agreed" and the like, even next to a figure ("3 min, to be confirmed"). `Length:` is not a
  runtime label; `Duration:` is, so a bare `Duration: 8 hours` meaning the shoot day would pass the form check
  (`Shoot duration:` does not). A clock-shaped `16:10` on a runtime line is read as 16 min 10 s. Is this the
  strictness you want?
- **Who may request a review.** `review_cut` is owner only, as in rows 13 and `champion_seat_award`, because
  the first verdict on a case id is final. SnapLink's backend would sign with the owner address. Opening the
  method is a one-line change.
- **What `evidence_sha256` binds.** The sha256 of the public `what_happened` text, byte for byte (no
  trimming): the only way an on-chain contract can check "an evidence hash that does not match". A hash of a
  private bundle that is never supplied cannot be checked; a fifth input would be needed for both.
- **Same case.** A caller-supplied public `case_id`; one verdict per id, `SHORTFALL` locks it too; a refusal
  or `[LLM_ERROR]` stores nothing, so the call can be retried. Identical text under a new id is a new case.
- **Judgment rules the model is told** (prompt, not code): a runtime is met inside any range, maximum, minimum
  or tolerance the brief gives; a single figure with no tolerance is met when the cut rounds to it at the
  precision written (a 3:10 cut meets "3 minutes", a 3:40 cut does not); every named aspect ratio must be
  delivered; every listed deliverable must be shown as delivered; more than agreed is not a shortfall; an
  account that does not state the cut's runtime is a `SHORTFALL`; with several gaps the first of runtime,
  aspect ratios, deliverables is named.
- **Missing item.** A quote of 3..400 characters from the terms or the account (a short quote such as `1:1`
  can also match inside a longer string); empty for `DELIVERED`. Only the verdict word must match between
  leader and validator.
- **Extra refusals beyond the row and the shared three:** `OWNER_ONLY`, `BAD_CASE_ID`, `TERMS_TOO_LONG`,
  `EMPTY_WHAT_HAPPENED`, `WHAT_HAPPENED_TOO_LONG` (8000-character limits), the read refusals and the
  model-answer refusals. The contract does not open links; URLs in the account are read as text.
- **On chain in the clear.** The terms, the account, the case id and the hashes are public calldata and
  storage. The contract cannot stop a caller putting a name or an email in the text; SnapLink must send public
  text only.

## Not verified

The real model's judgment; GenVM execution and multi-validator consensus on a network (direct mode runs the SDK
in CPython); any write method on Studionet; the Studionet schema (endpoint refuses it); byte identity of the
text pasted into the lint call, the schema call and the deploy simulation. The row-13 shape this contract
shares has not yet been independently verified either.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction` and
`genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged; nothing
pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's page are left
to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

Studionet is not gasless: a deploy without fees reverts `FeeValueMustBeNonZero(1)`.

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/video_cut_review.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

Windows PowerShell 5.1:

```powershell
npm install -g genlayer@0.40.0
genlayer network set studionet
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/video_cut_review.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards (wait for FINALIZED before reading):
- `genlayer receipt <tx hash>` — the deploy finalized and the leader's `execution_result` is a success.
- `genlayer call <address> get_role` → `"videographer"`.
- `genlayer call <address> get_review_count` → `0` on a fresh contract.
- `genlayer call <address> get_owner` → the deploying address.

VERDICT: DRAFTED — lint clean, 22 direct-mode tests pass with the model mocked, 47 of 47 planted mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN (endpoint). The PR stays
a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view read) passes.

## Independent verification (verifier agent, 2026-11-25T10:26Z)

Independent verifier, not the builder. Own clone `/home/claude/verify-video_cut_review` of this branch at
`e5bcf08`. Judged against the owner's row 14 (answer `DELIVERED` / `SHORTFALL` + the missing item; also refuses
a brief with no runtime) and the shared role-contract inputs, refusals and rules; the builder's claims above were
not used as evidence.

| Check | How | Result | Grade |
|---|---|---|---|
| Source identity | `sha256sum` | contract `4b7972d3c75ca843fe64db4122ea1dd1616f42053509c161882775f892883b7d`, tests `8e1baf8e6342edd52172e42fd04d478e3de2e7521b2fbe4a74a0e801423d9174`; contract hash identical before and after the mutations | OBSERVED |
| Lint | `genlayer_lint_contract` on the full contract source (pasted from the file as read; byte identity of the paste not machine-checked) | `ok: true`, 0 errors, 0 warnings, 0 info, `findings: []` | OBSERVED |
| Tests | `python3 -m pytest tests/factory/test_video_cut_review.py -q` (Python 3.13, pytest 9.1.1, genlayer-test 0.29.2 direct mode) | `22 passed in 0.90s`; again `22 passed in 0.61s` after every mutation was reverted | OBSERVED |
| Coverage: answers | read the tests | `DELIVERED` → `test_delivered_when_the_cut_meets_the_brief` (whole return value and stored record asserted, item `""`); `SHORTFALL` + missing item → `test_shortfall_names_the_missing_item_quoted_from_the_terms` (item quoted from the terms asserted), also `test_shortfall_item_may_be_quoted_from_the_delivery_account`. Gaps: none | OBSERVED |
| Coverage: must-refuse | read the tests, the contract's `ERR_*` constants and gltest 0.29.2 `expect_revert` (literal substring of the exception text, not a regex) | each case has its own test asserting the full fixed text, identical to the contract constant: no runtime → `test_refuses_a_brief_with_no_runtime` (`[EXPECTED] NO_RUNTIME: ...`, 25 variants); hash mismatch → `test_refuses_an_evidence_hash_that_does_not_match` (`[EXPECTED] EVIDENCE_HASH_MISMATCH: ...`); same case twice → `test_refuses_the_same_case_twice` (`[EXPECTED] SAME_CASE_TWICE: ...`); empty terms → `test_refuses_empty_terms` (`[EXPECTED] EMPTY_TERMS: ...`). All 24 `raise` statements in the contract are `gl.vm.UserError(ERR_*)`. Gaps: none | OBSERVED |
| Safety | read the source; `ast` and `grep` | inputs are a public case id, public terms text, a public delivery account and a sha256; nothing asks for names, emails, ages or private evidence (the doc block tells callers not to send them); no key handling, signing, sending, value transfer, other-contract call or web fetch; the only non-deterministic call is `gl.nondet.exec_prompt` inside `gl.vm.run_nondet_unsafe`; runner pinned (`py-genlayer:1jb45aa8…09h6`), line 2 blank; the validator checks the leader's shape, re-runs the judgment and compares only the verdict word; every LLM call in the tests is mocked (`direct_vm.mock_llm`). Note, not a fail: the block documenting the constructor is a string after `from genlayer import *`, so it is not the real module docstring (`ast.get_docstring` → `None`), the same layout as earlier factory contracts. Findings: none | OBSERVED |
| Mutation M1 | removed `_require_runtime(terms)` from `review_cut` | caught: `test_refuses_a_brief_with_no_runtime`, `test_a_refused_review_does_not_lock_the_case` | OBSERVED |
| Mutation M2 | swapped the verdict words (`VERDICT_OK = "SHORTFALL"`, `VERDICT_SHORT = "DELIVERED"`) | caught by 17 tests, including `test_delivered_when_the_cut_meets_the_brief`, `test_shortfall_names_the_missing_item_quoted_from_the_terms`, `test_validator_agrees_on_the_verdict_word_not_the_wording` | OBSERVED |
| Mutation M3 | removed the `candidate != _sha256_hex(account)` comparison in `_check_evidence_hash` | caught: `test_refuses_an_evidence_hash_that_does_not_match` | OBSERVED |
| Mutation M4 | removed the `case in self.reviews` → `SAME_CASE_TWICE` check | caught: `test_refuses_the_same_case_twice` | OBSERVED |
| Mutation M5 | validator always returns `True` | caught: `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_delivered` | OBSERVED |
| Mutation M6 | empty-terms check reduced to the type check (blank terms fall through to the runtime check) | caught: `test_refuses_empty_terms` | OBSERVED |
| Restore | `git checkout -- contracts/factory/video_cut_review.py` after each mutation, then `sha256sum` and `git status --porcelain` | hash back to `4b7972d3…3b7d` after each; tree clean (pytest `__pycache__` removed); no mutation committed | OBSERVED |

Not re-run by the verifier (not required): Studionet reachability, schema and deploy simulation. Observation for
the owner, from reading the runtime check (not a defect against the row): a label followed by other words before
the colon, such as `Runtime (master): 90 s`, is refused as no runtime, while a bare `Duration: 8 hours` passes
the form check (the builder lists the second under Open questions).

Verifier verdict: PASS
