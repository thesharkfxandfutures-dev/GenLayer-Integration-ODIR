# Factory record — champion_seat_award — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #7 of the owner's page (main table, row 7, an award
contract; `factory/BACKLOG.md` item 7). Cloud workspace, genskill MCP server as the owner's claude.ai
connector. Branch `factory/champion_seat_award-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator (draft).

Owner's row, as given to the builder:

| # | Contract | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|
| 7 | champion_seat_award (award contract) | Does this entrant's seat hold under the published allocation rules: only work in the named role counted, one seat per winner (highest wins), published tie-breaks, county minimum of 3 credited jobs? | role key, scope + area code, season year, seat number, standings snapshot hash, allocation rules version + text, entrant's evidence summary + hash | `CONFIRMED` / `NOT_CONFIRMED` + the rule relied on (quoted from the allocation rules text) | unknown rules version; season not finished; a second verdict for the same role, area, season and seat |

Award type: Champion trophies and places — World (SnapLink Trophy + World Plaque, places 2–10),
Continental Plaque (10), National Cup (11), County Shield (1). Row 7 replaces the earlier
`league_placement_review` proposal; it covers the same World #1 case and every other seat.

Award-contract rules (rows 7–12) applied here: one universal contract serves every role (role key is an
input); a deterministic `FORBIDDEN_SIGNAL` refusal when a text input relies on likes, followers, votes,
a paid plan / subscription / premium / membership tier, or a boost (paid membership must never improve
anyone's chance of an award); role key validated by shape only; scope and seat validated against the
award's places.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/champion_seat_award.py` | `d3b656c058bc5d094b0d82d92ce56e2a39e8bc47eaca249cd23716c1f1e6063b` |
| `tests/factory/test_champion_seat_award.py` | `60846242cc88cbad23cc44ee116e4f31918e18da5da2ebdb0575ad623d4be1c3` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the doc block documenting the constructor and saying
calldata is public data only. Class `ChampionSeatAward`, constructor `ChampionSeatAward()` takes no
arguments; the deploying address becomes the owner.

Methods (all writes owner only):
- `register_rules(rules_version, rules_text)` → `{rules_version, rules_sha256}`; the text is stored and
  checked for forbidden signals; versions are immutable.
- `finish_season(season_year)` → `{season_year, finished}`.
- `review_seat(role_key, scope, area_code, season_year, seat, standings_sha256, rules_version, rules_text,
  evidence_summary, evidence_sha256)` → `{seat_key, award, verdict, rule_quote, reason, rules_version}`.
- Views: `get_owner`, `get_rules(rules_version)`, `get_rules_count`, `get_rules_version(i)`,
  `is_season_finished(season_year)`, `get_finished_seasons`, `get_forbidden_signals`,
  `get_verdict(role_key, scope, area_code, season_year, seat)`, `get_verdict_by_key(seat_key)`,
  `get_verdict_count`, `get_verdict_key(i)`.

Seats and awards: world 1 = SnapLink Trophy, world 2–10 = World Plaque, continental 1–10 = Continental
Plaque, national 1–11 = National Cup, county 1 = County Shield. `seat_key` =
`role_key|scope|AREA|season_year|seat` (scope lower-case, area upper-case; world area is always `WORLD`).

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `CONFIRMED` (World seat 1 = SnapLink Trophy, rule quoted) | `test_confirmed_world_seat_one_is_the_snaplink_trophy` |
| Answer | `NOT_CONFIRMED` (County Shield, county-minimum rule quoted) | `test_not_confirmed_county_seat_quotes_the_minimum_rule` |
| Award per scope and seat | World Plaque, Continental Plaque, National Cup at both edges | `test_award_names_follow_scope_and_seat` |
| Must refuse: unknown rules version | `[EXPECTED] UNKNOWN_RULES_VERSION: no allocation rules are registered under this version` | `test_refuses_an_unknown_rules_version` |
| Rules text is not the registered text | `[EXPECTED] RULES_TEXT_MISMATCH: rules_text is not the text registered for this rules version` | `test_refuses_rules_text_that_is_not_the_registered_text` |
| Must refuse: season not finished | `[EXPECTED] SEASON_NOT_FINISHED: this season is not finished; seats are reviewed only after the owner marks the season finished` (and `[EXPECTED] SEASON_ALREADY_FINISHED: this season is already marked finished`) | `test_refuses_a_season_that_is_not_finished` |
| Must refuse: second verdict, same role, area, season and seat | `[EXPECTED] SEAT_ALREADY_DECIDED: this role, area, season and seat already has a verdict` | `test_refuses_a_second_verdict_for_the_same_role_area_season_and_seat` (a `NOT_CONFIRMED` locks the seat; case variants of scope/area hit the same key; other role/seat/season/area pass) |
| Award rule: forbidden signal in the evidence summary | `[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid plan, subscription, premium or membership tier, or a boost` | `test_refuses_an_evidence_summary_that_relies_on_a_forbidden_signal` (likes, FOLLOWERS, votes, voting, paid plan, subscription, Premium, membership tier, #Boosted, boost; whole words only: "devoted", "likeness" pass) |
| Award rule: forbidden signal in the rules text | same text | `test_refuses_rules_text_that_relies_on_a_forbidden_signal` (likes, follower count, votes, paid plan, Premium, membership tier, Boosted, Subscribers) |
| Award rule: seat out of range | `[EXPECTED] SEAT_OUT_OF_RANGE: seat must be 1-10 for world, 1-10 for continental, 1-11 for national and 1 for county` | `test_refuses_seats_out_of_range` (0, 11, -1, `True` for world; 0/11 continental; 0/12 national; 0/2 county; edges 10/10/11/1 accepted) |
| Award rule: role key shape | `[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters from a-z 0-9 _` | `test_refuses_malformed_role_keys` |
| Scope / area | `[EXPECTED] BAD_SCOPE: scope must be world, continental, national or county`; `[EXPECTED] BAD_AREA_CODE: area_code must be WORLD for the world scope, otherwise 2 to 16 characters from A-Z 0-9 -` | `test_refuses_bad_scopes_and_area_codes` |
| Season year | `[EXPECTED] BAD_SEASON_YEAR: season_year must be a whole year from 2000 to 2199` | `test_refuses_bad_season_years` |
| Hashes | `[EXPECTED] BAD_STANDINGS_HASH: standings_sha256 must be 64 hexadecimal characters`; `[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_hashes` |
| Evidence summary | `[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty`; `[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters` | `test_refuses_empty_or_long_evidence_summaries` |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can register rules, finish a season or request a seat review` | `test_only_the_owner_writes` |
| Registry | `[EXPECTED] RULES_VERSION_EXISTS: a registered rules version cannot be changed`; `[EXPECTED] BAD_RULES_VERSION: rules_version must be 1 to 32 characters from A-Z a-z 0-9 . _ -`; `[EXPECTED] BAD_RULES_TEXT: rules_text must be 1 to 8000 characters and not blank`; `[EXPECTED] BAD_INDEX: nothing at this index`; `[EXPECTED] NO_VERDICT: no verdict is stored for this seat` | `test_rules_registry` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of CONFIRMED or NOT_CONFIRMED`; `[LLM_ERROR] the model's rule quote is not 10 to 400 characters quoted from the allocation rules text`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` |
| Quote matched up to whitespace | stored quote has whitespace runs collapsed | `test_quote_is_matched_up_to_whitespace` |
| Prompt carries public inputs only | no hashes in the prompt; no-forbidden-signal instruction present | `test_prompt_carries_the_public_inputs_and_no_hashes` |
| Validator agree / disagree | verdict word only; leader quote must be in the rules text | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_not_confirmed` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `ChampionSeatAward`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by the verdict word |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the written file; byte identity of the pasted text was not machine-checked |
| Tests pass: 22 passed | OBSERVED | `python3 -m pytest tests/factory/test_champion_seat_award.py -q` → `22 passed in 0.41s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (no web read in this contract) |
| One test per answer word, must-refuse case and award rule | OBSERVED | table above |
| The tests can fail | OBSERVED | 8 mutations, each caught then reverted: `SEAT_ALREADY_DECIDED` check removed → 1 failed; validator always `True` → 2 failed; `FORBIDDEN_SIGNAL` check on the summary removed → 1 failed; `SEASON_NOT_FINISHED` check removed → 1 failed; validator stops checking the quote → 1 failed; national seats 1–12 → 1 failed; `votes`/`voting` dropped from the terms → 2 failed; word split on spaces only (not whole-word) → 2 failed. Contract sha256 `d3b656c0…063b` unchanged afterwards |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another quote and reason → `True`; `NOT_CONFIRMED` vs `CONFIRMED` → `False`; forged leader quote not in the rules → `False`; quote under 10 characters → `False`; bad word → `False`; missing reason → `False`; non-dict leader → `False`; validator's own model answer malformed → `False`; leader error → `False`; `NOT_CONFIRMED` vs `NOT_CONFIRMED` with different quotes → `True` |
| Hashes are not sent to the model; the prompt forbids weighing paid or popularity signals | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hashes`: the only LLM mock requires the instruction "Never weigh likes, followers, votes", the rules text, award, role, season, seat and summary, and the absence of both hashes |
| Studionet reachable | OBSERVED | `genlayer_network_status` (25 Nov 00:13:35 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b06282f`, not syncing |
| Schema on Studionet | NOT_RUN | not resent: orchestrator probe 25 Nov ~00:01 UTC answered `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`) for every contract; endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deploy contracts/factory/champion_seat_award.py '[]'` (genlayer-js 0.18.4; 53,506 hex chars, sha256 of the hex `89ad08e0af72364d74e987721de2c2f5eea63a0db2f21c2223b6c768ffb43421`, prefix `0xf9687db96878`, suffix `0600`) → `"00"`, decoded `null` (constructor returned). The hex was pasted into the call by hand in three read chunks; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | 1 failed, 21 passed | `test_quote_is_matched_up_to_whitespace`: `assert quote not in RULES_V1` failed — the test's quote sat inside rule A2, which has no line break (Python string concatenation), so the test's precondition was wrong | test re-written to quote across the real line break between A2 and A3 (test file only; contract unchanged) |
| Tests | 2 | 22 passed | — | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | — | NOT_RUN | orchestrator probe 25 Nov ~00:01 UTC: `unsupported_contract_rpc` on hosted Studionet | not resent (per brief) |
| Studionet deploy simulation | 1 | tool error | `'to' (code -32603)`: the call was sent without a `to` field (request shape, not the contract) | same hex resent with `to` = zero address |
| Studionet deploy simulation | 2 | pass | `"00"` → `null` | — |

## Open questions for the owner

- **Unknown rules version (registry).** Consistent with PR #3 (`listing_compliance_check`, deployer =
  owner publishes rulebooks): the owner registers each allocation rules version with its full text; the
  contract stores the text and its sha256 and refuses to change a version. A review must name a registered
  version and pass the text byte for byte (sha256 must match, else `RULES_TEXT_MISMATCH`). Registering only
  a hash would make calldata smaller but the rules would then not be readable from the contract.
- **Season not finished.** Deterministic, no wall-clock: the owner calls `finish_season(year)` once the
  season closes; reviews for any other year are refused. A finished season cannot be reopened. Seasons are
  global (not per role or scope).
- **Who may request a review.** All writes are owner only, including `review_seat`, because the row makes
  the first verdict on a seat final: if anyone could request, anyone could lock a seat with weak evidence.
  SnapLink's backend would therefore sign reviews with the owner address (or a later version could add an
  operator list).
- **A `NOT_CONFIRMED` locks the seat too.** The row says "a second verdict for the same role, area, season
  and seat" is refused, so after `NOT_CONFIRMED` no other entrant can be reviewed for that seat. If the
  owner wants only `CONFIRMED` to lock (so the next entrant can be reviewed), that is a one-line change.
  An `[LLM_ERROR]` refusal stores nothing, so the review can be retried.
- **Forbidden-signal filter is whole-word and literal.** Terms (also returned by `get_forbidden_signals`):
  likes, like count(s), follower(s), follower count, vote(s), voted, voting, voter(s), paid plan(s), paid
  tier, paid membership, subscription(s), subscriber(s), premium, membership tier(s), boost(s), boosted,
  boosting. Case-insensitive; words are runs of letters and digits, so punctuation, hashtags and hyphens
  separate words ("#Boosted" and "paid-plan" match; "devoted", "likeness" do not). It also refuses text that
  only *mentions* a term, e.g. rules saying "votes never count" or a summary "premium wedding package", so
  rules and summaries should be worded without these words. The role key, scope and area are not scanned.
  The rules text cited by a review is the registered text, which was scanned at registration.
- **Role key** is validated by shape only (lowercase snake_case, 2–40 characters, no leading/trailing or
  double underscore); the 45 SnapLink role keys are not listed on the page, so the list is not checked on
  chain.
- **Area codes** are shape only (2–16 of A-Z 0-9 -, stored upper-case); world must be `WORLD`, and `WORLD`
  is refused for other scopes. Continent, country and county code lists are not checked on chain, so
  SnapLink must use one spelling per area (e.g. `GB` not `UK`).
- **Rule quote** must be 10–400 characters and appear in the rules text after collapsing runs of whitespace
  (so a quote across a line break matches); only the verdict word must match between leader and validator.
- **What the model sees.** Rules text, evidence summary, role key, scope, area, season, seat and award name.
  It does not see the standings snapshot or the private evidence; their hashes are stored only. "Highest
  wins" and "county minimum of 3 credited jobs" are judged from the evidence summary, not computed on chain.
- **Limits.** Rules text ≤ 8000 characters, evidence summary ≤ 2000 (trimmed), season years 2000–2199.
- **On chain in the clear.** The rules text, evidence summary, codes and hashes are public calldata and
  storage. Summaries must not carry names, emails or private evidence; the contract cannot stop that.

## Not verified

The real model's judgment; GenVM execution and multi-validator consensus on a network (direct mode runs
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
genlayer deploy --contract contracts/factory/champion_seat_award.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/champion_seat_award.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_owner`;
`genlayer call <address> get_rules_count`.

VERDICT: DRAFTED — lint clean, 22 direct-mode tests pass with the model mocked, 8 of 8 planted mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN (endpoint). The PR
stays a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view
read) passes.

## Independent verification — 25 Nov 2026 (same scheduled run, separate verifier agent)

A verifier agent that did not build this contract checked out `052a5e0ca2ef987026b8313bfd1f8a61e8d17205` and judged it
from the code, the tests and page row 7 (plus the award rules) before reading this record. **Verdict: PASS.**

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Hashes | 1 | contract `d3b656c0…6063b`, tests `60846242…be1c3` match this record | OBSERVED | unchanged after mutations |
| genskill lint (full source) | 1 | 0 errors, 0 warnings, 0 info | OBSERVED | source pasted by hand; byte identity not machine-checked |
| pytest | 1 | `22 passed in 0.51s` | OBSERVED | verifier's own clone |
| Row + award-rule coverage, exact texts | 1 | every item has a full-text test | OBSERVED | UNKNOWN_RULES_VERSION, SEASON_NOT_FINISHED, SEAT_ALREADY_DECIDED, FORBIDDEN_SIGNAL (all five families, summary and rules text), BAD_ROLE_KEY, SEAT_OUT_OF_RANGE (edges 10/10/11/1) |
| Mutations caught | 1 | 19 of 19 | OBSERVED | each refusal removed, validator always true / whole-result compare / accepts leader error, verdict flipped, seat limits changed, quote checks dropped, seat key without area; reverted, tree clean |

Verifier notes (design choices, not defects): owner-managed rules registry, owner marks seasons finished, owner-only
writes, NOT_CONFIRMED also locks the seat; the forbidden-signal filter refuses mere mentions ("votes never count") and
misses some variants ("liked", "upvotes", "Gold membership", "Pro plan", "subscribed"); "highest wins" and the county
minimum are judged by the model from the summary, not computed on chain. `ERR_DECISION_SHAPE` is reached only inside the
validator (tested there). Not reproduced by the verifier: the Studionet checks (outside its brief).
