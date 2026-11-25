# Factory record — campaign_buyout_check — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #16 of the owner's page ("Role contracts (one per role)",
row 16, Commercial Model; `factory/BACKLOG.md` item 16). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/campaign_buyout_check-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator.

Owner's row, as given to the builder:

| # | Role | Contract | What it decides | Answer | Also refuses |
|---|---|---|---|---|---|
| 16 | Commercial Model | campaign_buyout_check | Is a campaign use inside the buyout's channels, territory and term? | `WITHIN_BUYOUT` / `BUYOUT_EXCEEDED` + the term exceeded | a use dated before the booking |

Role key `model_commercial` (the booking table's row 61 is `model_commercial_booking`; this review contract uses
`model_commercial`). Shared by every role row: inputs = the agreed terms (text both parties agree to make
public), what happened (a delivery note, a log or public URLs) and `evidence_sha256` of anything private;
refusals = an evidence hash that does not match, the same case twice, empty terms.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/campaign_buyout_check.py` | `4f23a3d2336fade5d398c0922a231f8d08f423406e8b310b8a8bd1a29100f62a` |
| `tests/factory/test_campaign_buyout_check.py` | `bdb2f2f0d52655fbb264149c18995aa17c1b0860776f63c6d2690c322cd23156` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`; line 2
blank, line 3 opens the module docstring, then `from genlayer import *` (the row-15 layout). The docstring is the
real module docstring (`ast.get_docstring` returns it; a test checks this) and documents the constructor, the
public-data rule, the method and its inputs, the date rule, every refusal and the consensus rule. Class
`CampaignBuyoutCheck`; constructor `CampaignBuyoutCheck()` takes no arguments; the deploying address becomes the
owner.

Methods:
- `review_campaign_use(case_id, agreed_terms, what_happened, evidence_sha256)` (owner only) →
  `{case_id, role, verdict, exceeded_term, reason, booking_date, first_use_date}`. `verdict` is `WITHIN_BUYOUT`
  or `BUYOUT_EXCEEDED`. For `BUYOUT_EXCEEDED`, `exceeded_term` is the buyout term the use exceeds, quoted from
  `agreed_terms` (3..400 characters, verbatim up to whitespace runs, which are collapsed); for `WITHIN_BUYOUT` it
  is `""`. `booking_date` and `first_use_date` are the dates the contract read (`YYYY-MM-DD`).
- Views: `get_owner()`, `get_role()` (`"model_commercial"`), `has_review(case_id)`, `get_review(case_id)`
  (stored JSON text), `get_review_count()`, `get_review_id(i)` — the same view names as rows 13–15.

Shape: the row-13 template's sections 1–3 (constants and texts, shared helpers, judgment runner) and the class
(owner check, evidence-hash check, same-case check, record, views), taken in the row-15 form (squash and trim
only in `_check_shape`, which every stored result passes through). Section 4 is this row: `ROLE_KEY`, the
verdict words, the date rule (`_booking_date`, `_first_use_date`, `_iso_date`,
`_require_use_on_or_after_booking`) and the prompt (`_build_prompt`). Differences from the templates, on
purpose: the quote (`exceeded_term`) comes from the agreed terms only, because it names the buyout term that was
exceeded, and it is required for `BUYOUT_EXCEEDED` only (`WITHIN_BUYOUT` stores `""`, as row 13's `DELIVERED`);
the record and the return value carry the two dates.

Inputs, as built:
- `case_id` (added input, public): 1..64 characters from A-Z a-z 0-9 . _ -, stored lower-case; the identity of
  the dispute, so "the same case twice" has something to refuse. Nothing else was added.
- `agreed_terms`: 1..8000 characters — the buyout terms (channels, territory, term) and exactly one
  `Booking date: YYYY-MM-DD` line.
- `what_happened`: 1..8000 characters — the campaign use (channel, territory, dates, placements, public URLs as
  text) with at least one `Use date:` / `Use dates:` / `First use:` / `First use date:` line. Links are not
  opened.
- `evidence_sha256`: must be the sha256 (hex, upper-case accepted, surrounding spaces ignored) of the UTF-8 bytes
  of `what_happened` exactly as supplied.

The date rule (the row's own refusal) is deterministic code, not the model:
- A labelled line is found after list marks (`-`, `*`, `#`, `>`, `1.`, `2)`), in any letter case, with optional
  `*` or `_` before and after the colon (so `**Booking date:** 2026-03-02` and `**First use**: 2026-03-07` work).
  The label must start the line: `Notes: booking date: …`, `Rebooking date:`, `Booking dates:`,
  `Date of booking:`, `Usage date:`, `Date of use:`, `Reuse date:` are not labelled lines.
- The value must begin with a real calendar date written `YYYY-MM-DD` (ASCII digits, Gregorian leap years,
  year ≥ 0001), not followed directly by a letter or digit. A time or note may follow after a space
  (`2026-03-02 10:00 UTC`, `2026-03-08 (Instagram post)`); `2026-03-02T10:00` is refused. Only the first date on
  each line is read (`Use dates: 2026-03-16 to 2026-09-30` → 2026-03-16).
- Booking date: exactly one `Booking date:` line in `agreed_terms` (none, or two — even with the same date — is
  `NO_BOOKING_DATE`). Use date: the earliest date over all use-date lines in `what_happened` (none is
  `NO_USE_DATE`; any malformed one is `BAD_DATE`). A booking date in the account or a use date in the terms does
  not count.
- Refused when the use date is earlier than the booking date (`USE_BEFORE_BOOKING`); the same day is allowed.
- Order of checks: owner → case id → terms (empty, too long) → booking date → account (empty, too long) →
  evidence hash → use date → use before booking → same case → model. The account's dates are read only after
  its hash has matched.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

Every refusal test uses `refused(text)`, which requires a `gl.vm.UserError` whose message equals the text
exactly (stricter than gltest's `expect_revert`, which only checks that the text is contained).

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `WITHIN_BUYOUT`, `exceeded_term` `""` (stored record checked field by field, both dates) | `test_within_buyout_when_the_use_stays_inside_the_buyout` |
| Answer | `BUYOUT_EXCEEDED` + the buyout term quoted from the agreed terms | `test_buyout_exceeded_quotes_the_term_exceeded`, `test_the_exceeded_term_may_be_any_buyout_term` |
| Exceeded term only from the agreed terms | a quote from the campaign use is refused with `[LLM_ERROR] the model's exceeded term is not 3 to 400 characters quoted from the agreed terms` | `test_the_exceeded_term_must_be_quoted_from_the_agreed_terms_not_the_use` |
| Quote matched up to whitespace | stored term collapsed, reason trimmed | `test_exceeded_term_quote_is_matched_up_to_whitespace` |
| `WITHIN_BUYOUT` stores no term | whatever the model puts in `exceeded_term` (a term, "none", a forged text, `null`, a number, no key) → `""` | `test_within_buyout_stores_no_exceeded_term` |
| Verdict word spelling | `" buyout exceeded "`, `Buyout-Exceeded`, `within_buyout`, `Within Buyout` read as the words | `test_verdict_word_spelling_is_normalised` |
| Prompt carries public inputs only | the decision rules verbatim, terms, campaign use, both dates and role; no evidence hash, terms hash or case id | `test_prompt_carries_the_public_inputs_and_dates_and_no_hash_or_case_id` |
| **Must refuse (row): a use dated before the booking** | `[EXPECTED] USE_BEFORE_BOOKING: the campaign use is dated before the booking` | `test_refuses_a_use_dated_before_the_booking` (one day before; across a month end; across a year end; a range starting before; the earliest of several lines before; 1999; booking 2027-01-01 with use 2026-12-31) and `test_a_use_on_or_after_the_booking_date_is_allowed` (same day, one day after, earliest line wins, year end on the same day) |
| Row: dates the rule needs, missing | `[EXPECTED] NO_BOOKING_DATE: agreed_terms needs exactly one line starting 'Booking date:' followed by the booking date as YYYY-MM-DD` | `test_refuses_terms_without_exactly_one_booking_date` (13 variants incl. two lines, label not at the line start, booking date only in the account) |
| | `[EXPECTED] NO_USE_DATE: what_happened needs a line starting 'Use date:', 'Use dates:' or 'First use:' followed by the date of the use as YYYY-MM-DD` | `test_refuses_an_account_without_a_use_date` (10 variants incl. a use date only in the terms) |
| Row: dates malformed | `[EXPECTED] BAD_DATE: a booking date or use date line does not begin with a real calendar date written YYYY-MM-DD` | `test_refuses_malformed_dates` (24 values, each as booking and as use date: empty, `2026-3-2`, `26-03-02`, `2026/03/02`, `02-03-2026`, words, month 13 / 00, day 00 / 32, 2026-04-31, 2026-02-29, 2100-02-29, 0000-01-01, a trailing digit or letter, `T10:00`, full-width digits, `TBC`, …; plus one bad line among good ones) and `test_real_calendar_dates_and_layouts_are_read` (leap days 2028 and 2000, year 0999 padded, case, no space, list marks, bold, trailing time/note, CRLF and CR line ends) |
| Check order | the hash is checked before the account's dates; the booking date before the account | `test_the_date_checks_come_after_the_shared_input_checks` |
| Shared: empty terms | `[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty` | `test_refuses_empty_terms` ("", spaces, newlines, `None`; refused before the date rule and before the hash) |
| Shared: evidence hash does not match | `[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal characters) of the what_happened text exactly as supplied` | `test_refuses_an_evidence_hash_that_does_not_match` (another account's hash, the terms' hash, one trailing space, a changed use date, zeros, 63 / 65 characters, non-hex, empty, `0x` prefix, `None`, an int, the account edited after hashing, the hash of the trimmed text for an account with a trailing newline; the exact hash, upper-case and padded, is accepted and stored lower-case) |
| Shared: the same case twice | `[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict` | `test_refuses_the_same_case_twice` (same inputs, id in another case, same id with other evidence, same id with other terms; first verdict unchanged; a different id is a new case) and `test_a_refused_review_does_not_lock_the_case` |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can request a buyout review` | `test_only_the_owner_requests_reviews` |
| Input shape | `[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -` | `test_refuses_bad_case_ids` |
| Input length | `[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters`; `[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty`; `[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters` | `test_refuses_terms_over_the_limit` (8000 accepted, 8001 refused), `test_refuses_an_empty_or_overlong_account_of_what_happened` (8000 accepted, 8001 refused) |
| Reads | `[EXPECTED] NO_REVIEW: no review is stored for this case_id`; `[EXPECTED] BAD_INDEX: nothing at this index` | `test_reads` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of WITHIN_BUYOUT or BUYOUT_EXCEEDED`; `[LLM_ERROR] the model's exceeded term is not 3 to 400 characters quoted from the agreed terms`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (20 bad answers), `test_model_json_wrapped_in_text_is_read`, `test_refuses_a_term_over_the_limit_and_truncates_the_reason` |
| Validator agree / disagree | verdict word only; the leader's term must be quoted from the agreed terms (`BUYOUT_EXCEEDED`) or empty (`WITHIN_BUYOUT`); `[LLM_ERROR] the decision result is malformed` is internal to the validator | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_within_buyout` |
| Source shape | header on line 1, no comment on line 2, module docstring documents the constructor | `test_source_shape_header_and_module_docstring` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (its "studionet is gasless" line is out of date, see the deploy steps) |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `CampaignBuyoutCheck`; `genlayer_scaffold_test` template `llm-judge`, name `CampaignBuyoutCheck`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by the verdict word; the row-13/15 templates supplied the shared shape |
| Lint: no errors (connector) | OBSERVED | `genlayer_lint_contract` on the full final source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings ("No blocking errors. 0 warning(s), 0 info."). The source was pasted into the tool call by hand |
| Lint: no errors (exact bytes) | OBSERVED | `lintContractSource` from genskill-mcp@2.3.3 (the version `.mcp.json` pins; the copy installed in the factory's scratch folder) run by node on the committed file itself: `sha256 4f23a3d2…0f62a` → `{"ok":true,"errors":0,"warnings":0,"infos":0,"findings":[]}` |
| Tests pass: 30 passed | OBSERVED | `python3 -m pytest tests/factory/test_campaign_buyout_check.py -q` → `30 passed in 0.75s` (10:45 UTC); Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (the contract reads no web page) |
| One test per answer word and per must-refuse case, exact text | OBSERVED | table above |
| The tests can fail | OBSERVED | 80 planted mutations on the final source, each run with `pytest -x` then the file restored from a copy: 80 caught; contract sha256 unchanged afterwards and `git status` showed only the new files. The date rule alone has 37: check removed; same day refused; comparison reversed; latest or first or last use line instead of the earliest; bad use date skipped; missing use date accepted; two booking dates accepted; bad booking date accepted; booking date read from the account; use date read from the terms; date read before the hash; each use label dropped; colon not required; label matched anywhere; label case-sensitive; bullets not stripped; `*`/`_` before the colon or before the date not stripped; CR line ends not split; dash positions not checked; non-ASCII digits accepted; trailing digit/letter accepted; month range, month 0, year 0, day 0 accepted; days in month not checked; no leap years; every 4th year a leap year; 400-year rule dropped; 30-day months given 31; date text not padded; month/day swapped. The other 43 cover the owner check, hash, same case, case id, limits, validator, quote check, `WITHIN_BUYOUT` term, reason, verdict words, prompt content (hash, case id or dates sent; channel-list, term-ended or "limit not stated" rule dropped), storage, role key, refusal text, docstring position and a comment under the header |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another quoted term and reason → `True`; the other word → `False`; forged term, term quoted from the use, term under 3 characters, empty or missing term for `BUYOUT_EXCEEDED`, a term for `WITHIN_BUYOUT`, bad or lower-case word, missing or blank reason, non-dict leader → `False`; the validator's own model answer malformed → `False`; leader error → `False` |
| Hashes and the case id are not sent to the model | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_dates_and_no_hash_or_case_id` |
| Studionet reachable | OBSERVED | `genlayer_network_status` (health timestamp 2026-11-25 10:39:34 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy` (genvm, database, consensus, llm_providers, redis healthy), chain id `0xf22f`, block `0x6b06bae6`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` with the base64 of this source (29,084 characters, sha256 of the base64 text `37feea76…6b43`) answered `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`); endpoint limitation, not a contract fault; not retried |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deployfile contracts/factory/campaign_buyout_check.py '[]'`: 43,640 characters including `0x`, sha256 of the hex string `8727348c52845e8456d3cbd1fd9099793291f2fd3575c631108a246cafc21037`, prefix `0xf95538b95533`, suffix `0600` → `"00"`, decoded `null` (constructor returned), between 10:42:43 and 10:45:03 UTC. The hex was pasted into the call by hand from two printed halves; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

No check failed. The test re-runs below followed changes made on mutation-testing evidence or a prompt wording
change, not failures.

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint (exact bytes, genskill-mcp@2.3.3 `lintContractSource`) | 1 | pass | 0 errors, 0 warnings, 0 info (first source `e1a14bb0…5c5f`) | none needed |
| Tests | 1 | pass | 30 passed (first source `e1a14bb0…5c5f`, first test file, not hashed) | none needed |
| Mutations | 1 | 78 of 80 caught | survivors: "label matched anywhere in the line" (with `label in line` the slice after the label rarely starts with a colon, so no test line reached a different refusal); "hash of stripped text" (no test account had surrounding whitespace) | tests: added `Confirmation: booking date 2026-03-02` and `Comments: use date 2026-03-16` (the mutant reads them as `BAD_DATE`), and an account with a trailing newline whose trimmed-text hash is refused and exact hash accepted |
| Tests | 2 | pass | 30 passed (test file `bb14c688…bde9`) | — |
| Mutations | 2 | 80 of 80 caught | — | contract: prompt wording only, "a channel the buyout lists limits the use to the channels listed" → "when the buyout lists channels, the use is limited to the channels listed" (clearer for the model); the prompt test and the mutation updated to the new sentence |
| Tests | 3 | pass | 30 passed (final source `4f23a3d2…0f62a`, final test file `bdb2f2f0…3156`); re-run at 10:45 UTC: `30 passed in 0.75s` | — |
| Mutations | 3 | 80 of 80 caught | final source unchanged afterwards | — |
| Lint (exact bytes) | 2 | pass | 0 errors, 0 warnings, 0 info (final source, sha256 printed by the script `4f23a3d2…0f62a`) | — (a re-check of the changed source, not a retry) |
| Lint (connector) | 1 | pass | 0 errors, 0 warnings, 0 info (final source) | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` with this source | not retried (endpoint refuses the operation) |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |

## Open questions for the owner

- **The date rule is by form.** The booking date must be on exactly one `Booking date: YYYY-MM-DD` line in the
  terms and the use dated on `Use date:` / `Use dates:` / `First use:` / `First use date:` lines in the account.
  A missing date is refused (`NO_BOOKING_DATE` / `NO_USE_DATE`), a malformed one too (`BAD_DATE`); the contract
  never guesses a date from free text or reads other formats (`2 March 2026`, `02/03/2026`). Is that the
  strictness you want, and are those the labels SnapLink will write?
- **Which use date counts.** The earliest first date over all use-date lines. A use line that gives a range
  (`2026-03-16 to 2026-09-30`) counts from its first date. Someone could hide an earlier use in free text (not on
  a labelled line); the model sees it but the date rule does not.
- **Same day is allowed.** A use on the booking date itself is not "before the booking". Dates only, no times or
  time zones: `2026-03-02 23:00` and `2026-03-02 01:00` are the same day.
- **Term expiry is the model's call.** Whether the use runs past the buyout's term (for example "12 months from
  first use") is judged by the model from the text and the two dates, not computed by the contract. A
  deterministic end-of-term check would need a fixed form for the term (for example `Term end: YYYY-MM-DD`).
- **A limit the buyout does not state cannot be exceeded.** The model is told so, because `BUYOUT_EXCEEDED` must
  quote the term exceeded and an unstated limit has nothing to quote. So a booking with only a booking date and
  no channels, territory or term is always `WITHIN_BUYOUT`. If you want such a booking refused, that needs an
  extra refusal (for example `NO_BUYOUT_TERMS` with labelled `Channels:` / `Territory:` / `Term:` lines, as row
  15 does for usage terms).
- **Listed channels are exhaustive.** When the buyout lists channels, a channel not on the list exceeds it.
- **Unclear facts.** A fact the campaign use does not show is not a breach by itself (an unclear account leans
  `WITHIN_BUYOUT`). Say if the burden should go the other way.
- **The exceeded term is quoted from the agreed terms only** (3..400 characters), not from the campaign use; only
  the verdict word must match between leader and validator. Only the first exceeded term is returned.
- **No web read.** The campaign use may contain public URLs, but the contract judges the text and does not open
  them. A `web-oracle` variant is possible.
- **Who may request a review.** `review_campaign_use` is owner only, as in rows 13–15, because the first verdict
  on a case id is final.
- **What `evidence_sha256` binds.** It is the sha256 of the public `what_happened` text, byte for byte — the only
  way the contract can check "an evidence hash that does not match". It also binds the use dates, which live in
  that text. A private-evidence hash would need a fifth input.
- **Same case.** Identity is the caller-supplied public `case_id`; a refusal or `[LLM_ERROR]` stores nothing, so
  the call can be retried.
- **Extra refusals beyond the row and the shared three:** `NO_BOOKING_DATE`, `NO_USE_DATE`, `BAD_DATE` (the
  missing/malformed dates the row's refusal needs), `OWNER_ONLY`, `BAD_CASE_ID`, `TERMS_TOO_LONG`,
  `EMPTY_WHAT_HAPPENED`, `WHAT_HAPPENED_TOO_LONG`, the read refusals and the model-answer refusals.
- **On chain in the clear.** Terms, campaign use, dates, case id and hashes are public calldata and storage. The
  contract cannot stop a caller putting a name or an email in the text; SnapLink must send public text only (no
  model names, agency contacts or fees that are private).

## Not verified

The real model's judgment (including term-expiry reasoning); GenVM execution of a write and multi-validator
consensus on a network (direct mode runs the SDK in CPython); any write method on Studionet; the Studionet schema
(endpoint refuses it); byte identity of the text pasted into the connector lint call and the deploy simulation
(the lint was also run on the exact file bytes with the pinned package, see Claims). Independent verification by
the factory's verifier agent has not happened yet.

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
genlayer deploy --contract contracts/factory/campaign_buyout_check.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
npm install -g genlayer@0.40.0
genlayer network set studionet
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/campaign_buyout_check.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>` (check
`consensus_data.leader_receipt[0].execution_result`, not only the top-level status);
`genlayer call <address> get_role` (expected `"model_commercial"`); `genlayer call <address> get_review_count`
(expected `0` on a fresh contract);
`genlayer call <address> get_owner` (expected the deploying address).

VERDICT: DRAFTED — lint clean (connector and exact bytes), 30 direct-mode tests pass with the model mocked, 80 of
80 planted mutations caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN
(endpoint). The PR stays a draft until the owner deploys and the post-deploy Studionet check (transaction report
and a view read) passes.
