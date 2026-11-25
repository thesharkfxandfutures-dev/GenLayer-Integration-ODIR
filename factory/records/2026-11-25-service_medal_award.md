# Factory record — service_medal_award — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #10 of the owner's page (table "Award contracts (one per
award type)", row 10; `factory/BACKLOG.md` item 10). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/service_medal_award-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator (draft).

Owner's row, as given to the builder:

| # | Contract | Award type | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|---|
| 10 | `service_medal_award` | Service medals: 1, 5, 10, 15, 20, 25 years | Do the dated activity records show the stated years of active service in the role? | role key, medal years, dated activity summary + hash | `MEDAL_CONFIRMED` / `NOT_YET` + the gap | years outside the six; the same medal twice |

Award-contract rules (rows 7–12) applied here: one universal contract serves all 45 roles (role key is an
input, shape checked only); a deterministic `FORBIDDEN_SIGNAL` refusal when an input carries likes,
followers, votes, a paid plan / subscription / premium / membership tier, or a boost (paid membership must
never improve anyone's chance of an award). "The same medal twice" is read, as the orchestrator's brief
says, as a second decision for the same entrant (public id hash), role and medal years.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/service_medal_award.py` | `6235a2768400ef7974997210b67a194b170aa25f90108fc55e32eda0a975fe95` |
| `tests/factory/test_service_medal_award.py` | `a7e55dfe5f3bba4d950da421d0f299f89c04fb06e2bc683904dd2baa3de6fe32` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the doc block documenting the constructor and saying
calldata is public data only. Class `ServiceMedalAward`, constructor `ServiceMedalAward()` takes no
arguments; the deploying address becomes the owner.

Methods:
- `decide_medal(entrant_id, role_key, medal_years, activity_summary, activity_sha256)` (owner only) →
  `{medal_key, medal_years, verdict, gap, reason}`; `medal_key` = `entrant_id|role_key|medal_years`
  (entrant id lower-case hex).
- Views: `get_owner`, `get_medal_years` (`[1,5,10,15,20,25]`), `get_forbidden_signals`,
  `has_decision(entrant_id, role_key, medal_years)`, `get_decision(entrant_id, role_key, medal_years)`,
  `get_decision_by_key(medal_key)`, `get_decision_count`, `get_decision_key(i)`.

How the answer is reached: the model reads only the role key and the activity summary and reports
`years_shown`, the whole years of active service in that role the dated records show (it is not told the
medal sought, so the target cannot anchor its count). The counting rule is fixed in the prompt: only dated
activity in the named role counts; the years are the successive 12-month periods from the earliest dated
activity in the role; a period counts only if it has ended by the latest dated activity in the role and at
least one dated activity in the role falls inside it. The contract then decides in plain code:
`MEDAL_CONFIRMED` (gap 0) when `years_shown >= medal_years`, otherwise `NOT_YET` with
`gap = medal_years - years_shown`.

Consensus: comparative equivalence on the verdict word. Each validator first checks that the leader's
verdict and gap follow from the leader's own count (a forged or malformed leader result is rejected),
counts itself and agrees only on the same word; for `NOT_YET` it also needs its gap within one year of the
leader's, so a leader cannot store an inflated gap. The count above the medal and the reason may differ.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `MEDAL_CONFIRMED`, gap 0 (5-year medal, 6 years counted; full stored record checked) | `test_medal_confirmed_when_the_records_show_the_years` |
| Answer | `NOT_YET` + the gap (10-year medal, 6 years counted → gap 4) | `test_not_yet_reports_the_gap` |
| Word and gap follow from the count for every medal | count 12: 1/5/10 confirmed; 15/20/25 `NOT_YET` gaps 3/8/13 | `test_verdict_and_gap_follow_from_the_count_for_every_medal` |
| Edges | count = medal → confirmed; one short → gap 1; no dated activity → gap = the medal; 1-year medal | `test_edges_exact_years_one_short_and_none` |
| Must refuse: years outside the six | `[EXPECTED] MEDAL_YEARS_NOT_OFFERED: medal_years must be 1, 5, 10, 15, 20 or 25` | `test_refuses_medal_years_outside_the_six` (0, 2, 3, 4, 6, 9, 11, 30, 50, -5, `True`, `"5"`, `None`; on the write and on `get_decision`) |
| Must refuse: the same medal twice | `[EXPECTED] MEDAL_ALREADY_DECIDED: this entrant already has a decision for this role and medal` | `test_refuses_the_same_medal_twice` (a `NOT_YET` locks the medal; upper-case / padded entrant id with a new summary and hash hits the same key; a confirmed medal is refused too; other medal, role or entrant pass) |
| Award rule: forbidden signal in the activity summary | `[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid plan, subscription, premium or membership tier, or a boost` | `test_refuses_an_activity_summary_with_a_forbidden_signal` (likes, FOLLOWERS, votes, voting, Upvoted, paid plan, Subscription, Premium, membership tier, #Boosted, boost; whole words only: "devoted", "likeness" pass) |
| Award rule: forbidden signal in the role key | same text | `test_refuses_a_role_key_with_a_forbidden_signal` (`premium_photographer`, `boosted_editor`, `paid_plan_member`, `followers_curator`, `votes_counter`) |
| Award rule: role key shape | `[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 48 characters from a-z 0-9 _` | `test_refuses_malformed_role_keys` (48 accepted, 49 refused) |
| Entrant id / activity hash | `[EXPECTED] BAD_ENTRANT_ID: entrant_id must be 64 hexadecimal characters (a public hash, never a name)`; `[EXPECTED] BAD_ACTIVITY_HASH: activity_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_entrant_ids_and_activity_hashes` (a name and an email are refused as entrant ids; upper-case hex stored lower-case) |
| Activity summary | `[EXPECTED] EMPTY_ACTIVITY_SUMMARY: activity_summary must not be empty`; `[EXPECTED] ACTIVITY_SUMMARY_TOO_LONG: activity_summary must be at most 4000 characters` | `test_refuses_empty_or_long_activity_summaries` (4000 after trimming accepted, 4001 refused) |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can request a medal decision` | `test_only_the_owner_decides` |
| Reads | `[EXPECTED] BAD_INDEX: nothing at this index`; `[EXPECTED] NO_DECISION: no decision is stored for this entrant, role and medal` | `test_reads_on_a_fresh_contract` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no whole number of years_shown from 0 to 100`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (no JSON, a list, missing, -1, 101, "4.5", "1000", "five", "6 years", `true`, `null`, blank or missing reason; " 7 " and 100 accepted) |
| Prompt carries public inputs only | no entrant id, no activity hash, no medal sought; counting rules and the no-forbidden-signal instruction present | `test_prompt_carries_the_public_inputs_only` |
| Validator agree / disagree | verdict word; `NOT_YET` gap within one year; leader result must be self-consistent | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_on_not_yet_needs_a_gap_within_one_year`, `test_validator_rejects_forged_or_malformed_leader_results` |

`[LLM_ERROR] the decision result is malformed` (`ERR_DECISION_SHAPE`) is reached only inside the validator
(a forged or malformed leader result), where it makes the validator disagree; it is tested there.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `ServiceMedalAward`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by a counted `years_shown` from which the verdict word and gap are derived |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings. The source was pasted into the tool call from the written file; byte identity of the pasted text was not machine-checked |
| Tests pass: 18 passed | OBSERVED | `python3 -m pytest tests/factory/test_service_medal_award.py -q` → `18 passed in 0.52s`; Python 3.13, genlayer-test 0.29.2 direct mode (GenVM v0.2.12 SDK); LLM mocked (no web read in this contract) |
| One test per answer word, must-refuse case and award rule | OBSERVED | table above |
| The tests can fail | OBSERVED | 19 mutations planted one at a time by a script outside the repo, 19 caught, each reverted: `MEDAL_ALREADY_DECIDED` check removed → 1 failed; medal list gains 3 → 3 failed; medal years accept `True` → 1 failed; forbidden check on the summary removed → 1 failed; on the role key removed → 1 failed; words split on spaces only → 2 failed; `voting` dropped from the terms → 1 failed; validator always agrees → 3 failed; validator ignores the `NOT_YET` gap → 1 failed; gap tolerance 2 → 1 failed; validator skips the leader shape check → 1 failed; validator accepts a leader error → 1 failed; `>` instead of `>=` → 3 failed; gap off by one → 8 failed; medal key without the entrant → 8 failed; prompt told the medal sought → 1 failed; owner check removed → 1 failed; count limit 101 → 1 failed; summary limit 4001 → 1 failed. Contract sha256 `6235a276…fe95` unchanged afterwards, tree clean |
| Validators agree on the verdict word (and, for `NOT_YET`, a gap within one year) | OBSERVED (direct mode) | `direct_vm.run_validator()`: confirmed with counts 5 and 9 vs leader 6 → `True`; count 4 (`NOT_YET`) vs `MEDAL_CONFIRMED` → `False`; leader gap 3 vs validator gaps 3/4/2 → `True`, 5/1/10/0 → `False`; nine forged or malformed leader results (verdict or gap not following the count, bool gap, string count, missing or blank reason, count 101 or -1, word `YES`), a string and `None` → `False`; validator's own model answer malformed → `False`; leader error → `False` |
| The model sees only public inputs and not the medal sought | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_only`: the only LLM mock requires the counting rules, "Never weigh likes, followers, votes", the summary and role key, and the absence of the entrant id, the activity hash and `medal_years` |
| Studionet reachable | OBSERVED | `genlayer_network_status` (health timestamp 25 Nov 2026 05:11:08 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b066dec`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` on the base64 source (24,784 characters), ~05:19 UTC → `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`); endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deploy contracts/factory/service_medal_award.py '[]'` (genlayer-js 0.18.4; 37,190 hex characters, sha256 of the hex `23341a868bcfe862cdc726a1e7150611780911bbee00bacea6aac67b85c2c895`, prefix `0xf9489fb9489a`, suffix `0a0600`) → `"00"`, decoded `null` (constructor returned), between 05:11 and 05:18 UTC. The hex was pasted by hand in one piece from a single-line read; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's counting is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info (an earlier call got no permission verdict from the session's auto-mode check and did not run; not counted) | — |
| Tests | 1 | 1 failed, 17 passed | `test_refuses_malformed_model_answers`: a mocked answer `{"years_shown": 4.5}` came back as `[LLM_ERROR] the model did not return a JSON object`, not the years error: direct mode passes mock answers through GenLayer calldata, which has no float type, so a float never reaches the contract | contract: the float branch in `_whole_years` removed (a JSON number must be a whole int, else `[LLM_ERROR]`); test: float cases replaced by `"4.5"`, `"1000"` and the edge 100 |
| Tests | 2 | 18 passed | `18 passed in 0.52s` (several re-runs in between got no permission verdict and did not run; not counted) | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` on hosted Studionet | none (endpoint limitation) |
| Studionet deploy simulation | 1 | tool error | `Non-hexadecimal digit found (code -32603)`: the hex was pasted with line breaks between read chunks (request shape, not the contract) | same hex resent without line breaks |
| Studionet deploy simulation | 2 | tool error | `RLP string ends with 1 superfluous bytes (code -32603)`: one byte too many where two read chunks were joined by hand (transcription, not the contract) | the hex re-read as one unbroken line and pasted in one piece; no contract change |
| Studionet deploy simulation | 3 | pass | `"00"` → `null` | — |

Both deploy-simulation failures were tooling or transcription faults on the request (rule 5d: no contract change, never a contract failure).

## Open questions for the owner

- **A `NOT_YET` locks the medal too.** Following the brief, "the same medal twice" is any second decision
  for the same entrant, role and medal years, so an entrant who is decided `NOT_YET` (gap 1) can never be
  decided again for that medal, even a year later. If the owner wants only `MEDAL_CONFIRMED` to lock (so a
  `NOT_YET` can be re-decided once the gap has passed), that is a one-line change. An `[LLM_ERROR]`
  refusal stores nothing, so the decision can be retried.
- **What a year of active service is.** The page does not define it, so the draft fixes one rule in the
  prompt: 12-month periods from the earliest dated activity in the role, each counted only if it has ended
  by the latest dated activity and contains at least one dated activity in the role. Years need not be
  consecutive (a year with no activity is skipped, not a reset). Changing the rule needs a new deployment.
  There is no "as of" date: the latest dated record is the end of the count, and the contract cannot tell
  whether a date is in the future.
- **Entrant id.** The row lists no entrant input, but "the same medal twice" needs one; the draft adds
  `entrant_id`, a public 64-hex hash (never a name). Higher medals do not require the lower ones, and a
  10-year decision does not imply a 5-year one.
- **Who may request a decision.** Owner only (SnapLink's backend signs), because the first decision on a
  medal is final: an open method would let anyone lock someone's medal with a weak summary.
- **Gap tolerance.** Validators agree on the verdict word; for `NOT_YET` they also need the leader's gap
  within one year of their own. This guards the stored gap; it may cause a disagreement (and a retry) when
  two counts differ by two years or more on a borderline summary.
- **Forbidden-signal filter is whole-word and literal.** Terms (also returned by `get_forbidden_signals`):
  likes, like count(s), follower(s), follower count, vote(s), voted, voting, voter(s), upvote(s), upvoted,
  paid plan(s), paid tier, paid membership, subscription(s), subscriber(s), subscribed, premium, membership
  tier(s), boost(s), boosted, boosting. Both the role key and the activity summary are scanned. It refuses
  mere mentions ("premium wedding package") and misses other wording ("liked", "Gold member").
- **Model output.** `years_shown` must be a JSON whole number 0–100 or a digit string; anything else is an
  `[LLM_ERROR]` (nothing stored, retry possible).

## Not verified

The real model's counting; GenVM execution and multi-validator consensus on a network (direct mode runs
the SDK in CPython); any write method on Studionet; the Studionet schema (endpoint refuses it).

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged;
nothing pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's
page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/service_medal_award.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/service_medal_award.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_decision_count`
(expected `0` on a fresh contract); `genlayer call <address> get_medal_years` (expected `[1,5,10,15,20,25]`).

VERDICT: DRAFTED — lint clean, 18 direct-mode tests pass with the model mocked, 19 of 19 planted mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN (endpoint). The PR
stays a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view
read) passes.

## Independent verification (verifier agent, 2026-11-25T05:30Z)

Checked in a fresh clone of branch `factory/service_medal_award-2026-11-25` at HEAD
`2433dbe8215fa26d116f0a88b7775a9b3f880377`, working from the contract, the tests and the owner's row 10 and
the award-table rule (rows 7-12) before reading this record.

- contract sha256: `6235a2768400ef7974997210b67a194b170aa25f90108fc55e32eda0a975fe95`
- test sha256: `a7e55dfe5f3bba4d950da421d0f299f89c04fb06e2bc683904dd2baa3de6fe32`

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| genskill lint | `genlayer_lint_contract` on the full source | 0 errors, 0 warnings, 0 infos | OBSERVED | `ok: true`, "Looks deployable" |
| pytest | `python3 -m pytest tests/factory/test_service_medal_award.py -q` (genlayer-test 0.29.2) | 18 passed | OBSERVED | `18 passed in 0.48s` |
| Answer words | read tests | `MEDAL_CONFIRMED` (gap 0) and `NOT_YET` (+ gap) both asserted, every medal 1/5/10/15/20/25, edges (exact, one short, zero years) | OBSERVED | `test_medal_confirmed_...`, `test_not_yet_reports_the_gap`, `test_verdict_and_gap_follow_...`, `test_edges_...` |
| Must refuse: years outside the six | read tests | 0,2,3,4,6,9,11,30,50,-5, True, "5", None refused on write and read with the exact `MEDAL_YEARS_NOT_OFFERED` text, no model mock (refusal precedes the model) | OBSERVED | `test_refuses_medal_years_outside_the_six` |
| Must refuse: same medal twice | read tests | second decision refused with exact `MEDAL_ALREADY_DECIDED` text, also with upper-case padded id, new summary and hash; also after a confirmed medal; other medal/role/entrant allowed | OBSERVED | `test_refuses_the_same_medal_twice` |
| Award rule: forbidden signals | read tests | likes, followers, votes, voting, upvoted, paid plan, subscription, premium, membership tier, boost(ed) refused in the summary; role keys with premium/boosted/paid_plan/followers/votes refused; exact `FORBIDDEN_SIGNAL` text; whole-word acceptance ("devoted", "likeness") | OBSERVED | `test_refuses_an_activity_summary_...`, `test_refuses_a_role_key_...` |
| Other refusals exact text | read tests | BAD_ROLE_KEY, BAD_ENTRANT_ID, BAD_ACTIVITY_HASH, EMPTY_ACTIVITY_SUMMARY, ACTIVITY_SUMMARY_TOO_LONG, OWNER_ONLY, NO_DECISION, BAD_INDEX, four LLM_ERROR texts each asserted | OBSERVED | tests listed in file |
| Validator compares the verdict word | read source and tests | validator re-derives the leader's verdict and gap from the leader's count, disagrees on a different verdict word, accepts a different count/reason with the same word, NOT_YET gap within 1; forged or malformed leader results and leader errors rejected | OBSERVED | `_judge` / `validator_fn`; three `test_validator_*` tests |
| Safety: calldata | read `decide_medal` signature | arguments are a sha256 entrant id, role key, medal years, a dated activity summary written for publication and a sha256; no names or emails fields; prompt excludes entrant id, activity hash and medal sought (asserted) | OBSERVED | `test_prompt_carries_the_public_inputs_only` |
| Safety: source | grep for private, key, sign, raw_rpc, submit, eth_send, web calls | only `role_key`/`medal_key`/`sort_keys` hits and docstring prose; no key, signing, sending or web call; the model call is mocked in every test | OBSERVED | grep output |
| Deploy simulation | not run by the verifier | the deploy calldata is the whole source in hex (about 36 KB), too large to pass by hand to the call tool without risk of corrupting it | NOT_RUN | tooling limit, not a contract defect |

### Mutations (one at a time, each reverted with `git checkout -- <file>`)

| # | Mutation | Caught by |
|---|---|---|
| M1 | skip the already-decided refusal | `test_refuses_the_same_medal_twice` |
| M2 | loosen the medal-years check to any positive integer | `test_refuses_medal_years_outside_the_six` |
| M3 | validator no longer compares the verdict word | `test_validator_agrees_on_the_verdict_word_not_the_wording` |
| M4 | verdict boundary `>=` changed to `>` | 3 tests (edges, malformed role keys, validator) |
| M5 | summary not scanned for forbidden signals | `test_refuses_an_activity_summary_with_a_forbidden_signal` |
| M6 | boost terms removed from the forbidden list | 3 tests (summary, role key, fresh-contract read) |
| M7 | validator gap tolerance widened from 1 to 5 | `test_validator_on_not_yet_needs_a_gap_within_one_year` |
| M8 | gap off by one | 8 tests |
| M9 | role key not scanned for forbidden signals | `test_refuses_a_role_key_with_a_forbidden_signal` |
| M10 | wording of the MEDAL_YEARS_NOT_OFFERED text changed | `test_refuses_medal_years_outside_the_six` |
| M11 | owner check removed | `test_only_the_owner_decides` |

11 of 11 caught. After the last revert the contract sha256 was again
`6235a2768400ef7974997210b67a194b170aa25f90108fc55e32eda0a975fe95` and `git status` was clean (the
`__pycache__` folders pytest wrote were deleted).

### Observations (not defects)

- The forbidden-signal filter is lexical, whole-word and ASCII-case-folded: it can be evaded by wording the
  list does not contain or by splitting a term with a non-letter character, and it refuses a summary that only
  mentions a term in negation. The model is also told never to weigh those signals; the record's own
  "Not verified" section already states the limit.
- The model's real counting, GenVM execution and multi-validator consensus were not exercised (direct mode
  only, as the brief allows).

**Verdict: PASS**
