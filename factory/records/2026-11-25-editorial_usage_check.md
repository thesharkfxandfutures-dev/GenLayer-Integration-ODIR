# Factory record — editorial_usage_check — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #15 of the owner's page ("Role contracts (one per role)",
row 15, Fashion Model; `factory/BACKLOG.md` item 15). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/editorial_usage_check-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator.

Owner's row, as given to the builder:

| # | Role | Contract | What it decides | Answer | Also refuses |
|---|---|---|---|---|---|
| 15 | Fashion Model | editorial_usage_check | Is a published use editorial, as agreed, or advertising that needs a new fee? | `EDITORIAL` / `COMMERCIAL_USE` + the placement quoted | usage terms missing from the booking |

Role key `model_fashion` (the booking table's row 60 is `model_fashion_booking`; this review contract uses
`model_fashion`). Shared by every role row: inputs = the agreed terms (text both parties agree to make public),
what happened (a delivery note, a log or public URLs) and `evidence_sha256` of anything private; refusals = an
evidence hash that does not match, the same case twice, empty terms.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/editorial_usage_check.py` | `9d4c2dac9c2caa8b78326443ba95c78562872e63d63f4a487dd7f5c0c33dbc4b` |
| `tests/factory/test_editorial_usage_check.py` | `19ff36ebcb7af806d453348ed6f54ebb2cf5aa3d30fe95a8b7ef13a82c2fd0c0` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`; line 2
blank, line 3 opens the module docstring, then `from genlayer import *`. The docstring is the real module
docstring (`ast.get_docstring` returns it; a test checks this) and documents the constructor, the public-data
rule, every method, every refusal and the consensus rule. Class `EditorialUsageCheck`; constructor
`EditorialUsageCheck()` takes no arguments; the deploying address becomes the owner.

Note on the template: in the row-13 contract the doc block sits after `from genlayer import *`, so Python does
not treat it as the module docstring (`__doc__` is `None`). This contract puts it first, directly after the
blank line under the header (no comment line under the header). The genskill lint accepts this layout and the
Studionet deploy simulation loads and constructs it (below).

Methods:
- `review_usage(case_id, agreed_terms, what_happened, evidence_sha256)` (owner only) →
  `{case_id, role, verdict, placement, reason}`. `verdict` is `EDITORIAL` or `COMMERCIAL_USE`. `placement` is
  required for both words: the placement decided on, quoted from `what_happened` (3..400 characters, verbatim up
  to whitespace runs, which are collapsed); for `COMMERCIAL_USE` the first advertising or commercial placement.
- Views: `get_owner()`, `get_role()` (`"model_fashion"`), `has_review(case_id)`, `get_review(case_id)` (stored
  JSON text), `get_review_count()`, `get_review_id(i)`. The view names are the same as the row-13 contract's, so
  SnapLink can read every role contract the same way.

Shape: the row-13 template's sections 1–3 (constants and texts, shared helpers, judgment runner) and the class
(owner check, evidence-hash check, same-case check, record, views), with section 4 written for this row
(`ROLE_KEY`, the verdict words, the usage-terms check `_require_usage_terms`, the prompt `_build_prompt`). Two
deliberate changes from the template: the quote is a placement from the published use only (not from the
terms), and it is required for both words; squashing the quote and trimming the reason happen once, in
`_check_shape`, which every stored result passes through (the template did it in two places).

Inputs, as built:
- `case_id` (added input, public): 1..64 characters from A-Z a-z 0-9 . _ -, stored lower-case; the identity of
  the dispute, so "the same case twice" has something to refuse. Nothing else was added.
- `agreed_terms`: 1..8000 characters — the booking's terms, including its usage terms.
- `what_happened`: 1..8000 characters — the published use: where and how the images appeared (a placement
  description and/or public URLs, as text). Links are not opened (no web read; see Open questions).
- `evidence_sha256`: must be the sha256 (hex, upper-case accepted, surrounding spaces ignored) of the UTF-8 bytes
  of `what_happened` exactly as supplied.

The usage-terms check (the row's own refusal) is deterministic code, not the model: `agreed_terms` must contain
a line that starts (after list marks such as `-`, `*`, `1.`, `2)`) with `Usage`, `Usage terms`, `Usage rights`,
`Usage licence` / `Usage license`, `Agreed usage`, `Permitted usage` or `Image usage` (any case, optional `*` or
`_` before the colon, so `**Usage**:` works) and a colon, with a clause of at least 3 letters or digits that is
not a placeholder (none, n/a, nil, TBC, TBD, TBA, unknown, pending, none stated / specified / agreed, not agreed
/ specified / stated / applicable, not yet agreed / decided, to be agreed / confirmed / decided / negotiated /
determined, as agreed, as discussed, see contract, see attached). A bare label takes the lines under it up to
the next blank line as its clause. `Usage fee:` is not a usage line.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

Every refusal test uses `refused(text)`, which requires a `gl.vm.UserError` whose message equals the text
exactly (stricter than gltest's `expect_revert`, which only checks that the text is contained).

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `EDITORIAL` + the editorial placement quoted (stored record checked field by field) | `test_editorial_when_the_published_use_is_editorial` |
| Answer | `COMMERCIAL_USE` + the advertising placement quoted | `test_commercial_use_quotes_the_advertising_placement` |
| Placement may be a public URL in the published use | URL quoted as the placement | `test_the_placement_may_be_a_public_url_in_the_published_use` |
| Placement only from the published use | a quote from the terms is refused with `[LLM_ERROR] the model's placement is not 3 to 400 characters quoted from the published use` | `test_the_placement_must_be_quoted_from_the_published_use_not_the_terms` |
| Placement matched up to whitespace | stored placement and reason trimmed / collapsed | `test_placement_quote_is_matched_up_to_whitespace` |
| Verdict word spelling | `" commercial use "`, `Commercial-Use`, `editorial` read as the words | `test_verdict_word_spelling_is_normalised` |
| Prompt carries public inputs only | the decision rules verbatim, terms, published use and role; no evidence hash, terms hash or case id | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id` |
| Must refuse (row): usage terms missing from the booking | `[EXPECTED] NO_USAGE_TERMS: the booking states no usage terms; agreed_terms needs a line starting 'Usage:' or 'Usage terms:' (or 'Usage rights:') followed by the agreed usage` | `test_refuses_a_booking_with_no_usage_terms` (20 variants: no usage line, usage only in a sentence, label without colon, blank clause, none / None. / N/A / TBC / `-` / "ok" / "to be agreed" / "not specified" / "as agreed" / "see contract", bare label followed by a blank line, `Usage fee:`, a fee line, `Notes: usage ...`, `Reusage:`) and `test_a_usage_line_is_found_in_any_common_layout` (13 accepted layouts) |
| Shared: empty terms | `[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty` | `test_refuses_empty_terms` ("", spaces, newlines, `None`; refused before the usage check and before the hash) |
| Shared: evidence hash does not match | `[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal characters) of the what_happened text exactly as supplied` | `test_refuses_an_evidence_hash_that_does_not_match` (another account's hash, the terms' hash, one trailing space, one changed word, zeros, 63 / 65 characters, non-hex, empty, `0x` prefix, `None`, an int, and the account edited after hashing; the exact hash, upper-case and padded, is accepted and stored lower-case) |
| Shared: the same case twice | `[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict` | `test_refuses_the_same_case_twice` (same inputs, id in another case, same id with other evidence, same id with other terms; first verdict unchanged; a different id is a new case) and `test_a_refused_review_does_not_lock_the_case` |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can request a usage review` | `test_only_the_owner_requests_reviews` |
| Input shape | `[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -` | `test_refuses_bad_case_ids` |
| Input length | `[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters`; `[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty`; `[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters` | `test_refuses_terms_over_the_limit` (8000 accepted, 8001 refused), `test_refuses_an_empty_or_overlong_account_of_what_happened` (8000 accepted, 8001 refused) |
| Reads | `[EXPECTED] NO_REVIEW: no review is stored for this case_id`; `[EXPECTED] BAD_INDEX: nothing at this index` | `test_reads` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of EDITORIAL or COMMERCIAL_USE`; `[LLM_ERROR] the model's placement is not 3 to 400 characters quoted from the published use`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (19 bad answers), `test_model_json_wrapped_in_text_is_read`, `test_refuses_a_placement_over_the_limit_and_truncates_the_reason` |
| Validator agree / disagree | verdict word only; the leader's placement must be quoted from the published use; `[LLM_ERROR] the decision result is malformed` is internal to the validator | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_editorial` |
| Source shape | header on line 1, no comment on line 2, module docstring documents the constructor | `test_source_shape_header_and_module_docstring` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `EditorialUsageCheck`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by the verdict word; the row-13 template supplied the shared shape |
| Lint: no errors (connector) | OBSERVED | `genlayer_lint_contract` on the full final source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings. The source was pasted into the tool call by hand |
| Lint: no errors (exact bytes) | OBSERVED | `lintContractSource` from genskill-mcp@2.3.3 (the version `.mcp.json` pins, installed in a scratch folder) run by node on the committed file itself (sha256 `9d4c2dac…dbc4b`): `{"ok":true,"errors":0,"warnings":0,"infos":0,"findings":[]}`. The same function flags a probe file with a comment under the header (`comment-after-header`), so it is live |
| Tests pass: 24 passed | OBSERVED | `python3 -m pytest tests/factory/test_editorial_usage_check.py -q` → `24 passed in 0.72s` (10:19 UTC); Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (the contract reads no web page) |
| One test per answer word and per must-refuse case, exact text | OBSERVED | table above |
| The tests can fail | OBSERVED | 52 planted mutations on the final source, each run with `pytest -x` then the file restored from a copy: 51 caught; contract sha256 unchanged afterwards. The one survivor, "verdict words swapped" (`VERDICT_OK` and `VERDICT_FEE` exchanged), is equivalent: the code treats the two words identically and the prompt and refusal texts spell them out literally. Caught: owner check removed; usage check removed; placeholders accepted; usage minimum removed / raised to 4; `usage rights`, `agreed usage` or bare `usage` label dropped; colon not required; `*`/`_` before the colon not stripped; bullets not stripped; list under a bare label ignored; label matched anywhere in the line; hash comparison removed; hash compared case-sensitively; hash not trimmed; hash of the terms; hash of stripped text; same-case check removed; case id not lower-cased; empty terms accepted; terms limit off by one; empty `what_happened` accepted; account limit removed; validator always `True`; validator compares the whole result; validator accepts a leader error; validator skips the leader shape check; placement check accepts anything; placement may come from the terms; placement minimum dropped; placement limit raised; placement not squashed; reason not stripped; shape check lets the placement be empty; shape check accepts a blank reason; verdict not normalised; reason not required; reason not truncated; stored reason replaced; evidence hash or case id sent in the prompt; prompt drops the "expressly grant", "not commercial by itself" or EDITORIAL rule; review not stored; id not listed; role key changed; refusal text changed; docstring moved below the import; comment under the header |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another placement and reason → `True`; the other word → `False`; forged placement, placement quoted from the terms, placement under 3 characters, empty or missing placement, bad or lower-case word, missing or blank reason, non-dict leader → `False`; the validator's own model answer malformed → `False`; leader error → `False` |
| Hashes and the case id are not sent to the model | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hash_or_case_id` |
| Studionet reachable | OBSERVED | `genlayer_network_status` (health timestamp 2026-11-25 10:14:33 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy` (genvm, database, consensus, llm_providers healthy), chain id `0xf22f`, block `0x6b06b509`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` with the base64 of this source (25,832 characters) answered `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`); endpoint limitation, not a contract fault; not retried |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deployfile contracts/factory/editorial_usage_check.py '[]'`: 38,764 characters including `0x`, sha256 of the hex string `cc5f21a705bc11721770a27f3753bfc21b329ac3b4fc8d3b27d25f6abbfd4713`, prefix `0xf94bb2b94bad`, suffix `0600` → `"00"`, decoded `null` (constructor returned), between 10:14 and 10:17 UTC. The hex was pasted into the call by hand from three printed chunks; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

No check failed. The test re-runs below followed changes made on mutation-testing evidence, not failures.

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Tests | 1 | pass | 24 passed (first source `9e751e68…6765`, first test file `c41b7cdc…1f3f`) | none needed |
| Mutations | 1 | 43 of 48 caught | survivors: "label matched anywhere in the line" (no test had a usage word after another 5-letter label); "prompt drops the expressly-grant rule" (the prompt test's regex matched the other "expressly grant"); "placement not squashed in the parser", "reason not truncated in the parser" (equivalent: squashed / truncated again later); "verdict words swapped" (equivalent) | tests: added `Notes: usage to be agreed later` to the refused terms; the prompt test now requires each decision rule verbatim; two more prompt mutations added |
| Tests | 2 | pass | 24 passed (same source, test file `6e5b0c45…5d4a`) | — |
| Mutations | 2 | 47 of 50 caught | the three equivalent mutants above | contract: squash and trim moved into `_check_shape` only (the parser returns the model's text, the class stores the decision as checked), so the duplicate code is gone and those mutants become real; mutations re-targeted, two added |
| Tests | 3 | pass | 24 passed (final source `9d4c2dac…dbc4b`) | — |
| Mutations | 3 | 50 of 52 caught | "reason not stripped" survived (no test padded the reason); "verdict words swapped" (equivalent) | tests: the whitespace test now pads the reason and checks it is stored trimmed |
| Tests | 4 | pass | 24 passed (final test file `19ff36eb…d0c0`); re-run at 10:19 UTC: `24 passed in 0.72s` | — |
| Mutations | 4 | 51 of 52 caught | only the equivalent "verdict words swapped" survives | — |
| Lint (connector) | 1 | pass | 0 errors, 0 warnings, 0 info (final source) | — |
| Lint (exact bytes, genskill-mcp@2.3.3 `lintContractSource`) | 1 | pass | 0 errors, 0 warnings, 0 info (final file, sha256 checked) | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` with this source | not retried (endpoint refuses the operation) |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |
| Verifier | 1 | PASS | own clone at 424276b, source `9d4c2dac…dbc4b`: lint 0 errors / 0 warnings; `24 passed`; 9 of 9 planted mutations caught; coverage and safety audits clean | — |

## Open questions for the owner

- **What EDITORIAL means when the booking already grants advertising.** The answer words are only `EDITORIAL`
  and `COMMERCIAL_USE`, and the row's question is "editorial, as agreed, or advertising that needs a new fee".
  The model is told: `COMMERCIAL_USE` when any placement is advertising or commercial use that the usage terms do
  not expressly grant (a new fee is due); otherwise `EDITORIAL`, which therefore means "as agreed, no new fee",
  including a use the terms expressly grant even if it advertises. If you would rather such a booking be refused
  or answered differently, that needs a third word or a refusal.
- **Editorial overruns.** An editorial use beyond the agreed medium, territory or term (for example online when
  only print was agreed) is still `EDITORIAL`: the contract decides editorial vs advertising, not every breach
  of the usage terms.
- **Unclear placements.** A placement whose kind the published use does not show is not commercial use by itself
  (so an unclear account leans `EDITORIAL`). Say if the burden should go the other way.
- **The usage-terms rule is by form.** The booking must state its usage on a labelled line (`Usage:`,
  `Usage terms:`, `Usage rights:`, `Usage licence:`, `Agreed usage:`, `Permitted usage:`, `Image usage:`) with at
  least 3 letters or digits that are not a placeholder; usage mentioned only in a sentence, `Usage: TBC`,
  `Usage: as agreed` or `Usage terms: see contract` are refused as missing. `Licence:` alone is not a usage label
  here. Is that the strictness you want?
- **The placement is quoted from the published use only** (3..400 characters, for both words), not from the
  terms. A short quote can match inside a longer word; only the verdict word must match between leader and
  validator.
- **No web read.** The published use may contain public URLs, but the contract judges the text and does not open
  them (a page can change between validators, and an ad is often an image the model cannot read as text). A
  `web-oracle` variant that fetches the URL is possible if you want it.
- **Who may request a review.** `review_usage` is owner only, as in the row-13 contract, because the first
  verdict on a case id is final.
- **What `evidence_sha256` binds.** It is the sha256 of the public `what_happened` text, byte for byte — the only
  way the contract can check "an evidence hash that does not match". A private-evidence hash would need a fifth
  input.
- **Same case.** Identity is the caller-supplied public `case_id`; a refusal or `[LLM_ERROR]` stores nothing, so
  the call can be retried.
- **Extra refusals beyond the row and the shared three:** `OWNER_ONLY`, `BAD_CASE_ID`, `TERMS_TOO_LONG`,
  `EMPTY_WHAT_HAPPENED`, `WHAT_HAPPENED_TOO_LONG`, the read refusals and the model-answer refusals.
- **On chain in the clear.** Terms, published use, case id and hashes are public calldata and storage. The
  contract cannot stop a caller putting a name or an email in the text; SnapLink must send public text only (no
  model names, agency contacts or fees that are private).

## Not verified

The real model's judgment; GenVM execution of a write and multi-validator consensus on a network (direct mode
runs the SDK in CPython); any write method on Studionet; the Studionet schema (endpoint refuses it); byte
identity of the text pasted into the connector lint call and the deploy simulation (the lint was also run on the
exact file bytes with the pinned package, see Claims).

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction` and
`genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged; nothing
pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's page are left
to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/editorial_usage_check.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
npm install -g genlayer@0.40.0
genlayer network set studionet
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/editorial_usage_check.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>` (check
`consensus_data.leader_receipt[0].execution_result`, not only the top-level status);
`genlayer call <address> get_role` (expected `"model_fashion"`); `genlayer call <address> get_review_count`
(expected `0` on a fresh contract); `genlayer call <address> get_owner` (expected the deploying address).

VERDICT: DRAFTED — lint clean (connector and exact bytes), 24 direct-mode tests pass with the model mocked, 51 of
52 planted mutations caught (the survivor is equivalent), Studionet reachable and the deploy simulation
constructs (`00`); schema NOT_RUN (endpoint). The PR stays a draft until the owner deploys and the post-deploy
Studionet check (transaction report and a view read) passes.

## Independent verification (verifier agent, 2026-11-25T10:26Z)

Done by a separate verifier agent that did not build the contract, in its own clone
(`/home/claude/verify-editorial_usage_check`, branch `factory/editorial_usage_check-2026-11-25` at `424276b`).
Judged against the owner's row 15 and the shared role-contract rules, not against the builder's claims above.
Contract sha256 `9d4c2dac9c2caa8b78326443ba95c78562872e63d63f4a487dd7f5c0c33dbc4b`; test file sha256
`19ff36ebcb7af806d453348ed6f54ebb2cf5aa3d30fe95a8b7ef13a82c2fd0c0`. Nothing was signed, sent or deployed; the
Studionet deploy simulation was not repeated.

| Check | How | Result | Grade |
|---|---|---|---|
| Lint | `genlayer_lint_contract` (genskill MCP) on the full source | `ok: true`, 0 errors, 0 warnings, 0 info, no findings | OBSERVED |
| Tests | `python3 -m pytest tests/factory/test_editorial_usage_check.py -q` (genlayer-test 0.29.2, direct mode), 10:23 UTC | `24 passed in 0.67s` | OBSERVED |
| Coverage: answers | read the tests | `EDITORIAL` + quoted placement: `test_editorial_when_the_published_use_is_editorial` (result and stored record checked field by field); `COMMERCIAL_USE` + quoted placement: `test_commercial_use_quotes_the_advertising_placement` (placement checked to be a quote from `what_happened`); a placement quoted from the terms is refused (`test_the_placement_must_be_quoted_from_the_published_use_not_the_terms`) | OBSERVED |
| Coverage: must-refuse cases | read the tests; compared each test constant with the contract's `ERR_*` constant by script (all 15 identical) | usage terms missing → `test_refuses_a_booking_with_no_usage_terms` (`NO_USAGE_TERMS`, 20 variants); evidence hash does not match → `test_refuses_an_evidence_hash_that_does_not_match`; same case twice → `test_refuses_the_same_case_twice`; empty terms → `test_refuses_empty_terms`. `refused()` requires type `UserError` and `message ==` the exact text. Gaps: none | OBSERVED |
| Refusals are fixed text | grep of every `raise` in the source | every refusal is `raise gl.vm.UserError(ERR_*)` with a module constant; no computed messages | OBSERVED |
| Safety | read the source; grep for key, sign, send, transfer, emit, contract calls, web access | inputs are a public case id, public terms text, public account text/URLs and a sha256; docstring forbids names, emails, ages and private evidence; no key handling, no sending or cross-contract call, no web access (only `gl.nondet.exec_prompt`); line 1 is the pinned runner `py-genlayer:1jb45aa8…09h6`, line 2 blank; constructor documented in the module docstring; `run_nondet_unsafe` validator re-runs the judgment and compares only the verdict word; every LLM call in the tests is mocked with `direct_vm.mock_llm`. Findings: none | OBSERVED |
| Mutation M1 | removed `_require_usage_terms(terms)` from `review_usage` | caught: `test_refuses_a_booking_with_no_usage_terms`, `test_a_refused_review_does_not_lock_the_case` (2 failed) | OBSERVED |
| Mutation M2 | `_check_shape` always returns `EDITORIAL` | caught: `test_commercial_use_quotes_the_advertising_placement` and 5 others (6 failed) | OBSERVED |
| Mutation M3 | removed the `candidate != sha256(what_happened)` comparison | caught: `test_refuses_an_evidence_hash_that_does_not_match`, `test_a_refused_review_does_not_lock_the_case` (2 failed) | OBSERVED |
| Mutation M4 | removed the `case in self.reviews` same-case check | caught: `test_refuses_the_same_case_twice` (1 failed) | OBSERVED |
| Mutation M5 | validator always returns `True` | caught: `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_editorial` (2 failed) | OBSERVED |
| Mutation M6 | parser maps the model's `EDITORIAL` to `COMMERCIAL_USE` and back | caught: `test_editorial_when_the_published_use_is_editorial`, `test_commercial_use_quotes_the_advertising_placement` and 11 others (13 failed) | OBSERVED |
| Mutation M7 | empty-terms check reduced to a type check (blank terms pass on) | caught: `test_refuses_empty_terms` (1 failed) | OBSERVED |
| Mutation M8 | `SAME_CASE_TWICE` text changed ("this case_id" → "this case") | caught: `test_refuses_the_same_case_twice` (1 failed): exact-text assertion is live | OBSERVED |
| Mutation M9 | validator skips the shape check of the leader's result | caught: `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_editorial` (2 failed) | OBSERVED |
| Restore | `git checkout -- contracts/factory/editorial_usage_check.py` after each mutation | sha256 back to `9d4c2dac…dbc4b` every time; `git status` clean apart from pytest `__pycache__`, which was deleted; no mutation committed | OBSERVED |

Note (not a defect): `review_usage` checks the owner and the case id format before empty terms, as the row-13
template does; empty terms are still refused before the usage-terms check, the evidence hash and the same-case check.

Verifier verdict: PASS
