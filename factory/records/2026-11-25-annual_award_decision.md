# Factory record — annual_award_decision — 25 Nov 2026

This is the factory run of 25 Nov 2026. The builder agent wrote contract #11 of the owner's page (the award table, row 11,
an award contract; `factory/BACKLOG.md` item 11). Cloud workspace, genskill MCP server as the owner's claude.ai
connector. Branch `factory/annual_award_decision-2026-11-25` from `main` (`f0a4525`).
Pull request: #13 (ready for review: verifier PASS and the pre-deploy Studionet check passed; the post-deploy check waits for the owner's transaction hash).

Owner's row, as given to the builder:

| # | Contract | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|
| 11 | annual_award_decision (award contract) | Which finalist best meets the published criteria, or does nobody meet them? | award code, season, published criteria text, each finalist's public evidence summary + hash | `WINNER` + finalist id, or `NO_AWARD`, with the criteria relied on | fewer than two finalists; a decision before the season reaches finalists; a second decision for the same award and season |

Award type: the annual awards. Photographer, Designer and Filmmaker of the Year; Emerging Talent; Creative
Business and Studio of the Year.

Award-contract rules (rows 7–12), as applied here:
- One universal contract serves every role, and the role key is an input.
- A deterministic `FORBIDDEN_SIGNAL` refusal applies when the criteria text or any finalist's evidence summary relies
  on likes, followers, votes, a paid plan / subscription / premium / membership tier, or a boost. Paid membership must
  never improve anyone's chance of an award.
- Comparative equivalence: validators agree on `WINNER` with the same finalist id, or on `NO_AWARD`.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/annual_award_decision.py` | `5d46d92cb5b3a3da400e3db836259710bbc59474748c1a198da20dd0a54631ac` |
| `tests/factory/test_annual_award_decision.py` | `935f305c85fad670c3503cca61d02c27c0480ffbbce22ffebe091203015cf8e3` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.
Line 2 is blank and line 3 is `from genlayer import *`. The doc block follows: it documents the constructor and says
calldata carries public data only. The class is `AnnualAwardDecision`. The constructor `AnnualAwardDecision()` takes
no arguments, and the deploying address becomes the owner.

Methods (all writes are owner only):
- `open_finalists(season_year)` returns `{season_year, finalists_open}`. It marks a season (2000–2199) as having
  reached the finalist stage, once.
- `decide_award(role_key, award_code, season_year, criteria_text, finalists_json)` returns `{award_key, award_name,
  decision, winner_id, criteria_quote, reason}`. `decision` is `WINNER` (with `winner_id` one of the finalist ids) or
  `NO_AWARD` (with `winner_id` `""`). `criteria_quote` is the criterion relied on, quoted from `criteria_text`
  (10–400 characters, matched up to runs of whitespace).
  - `finalists_json` is a JSON array of 2–10 objects. Each object has exactly `finalist_id` (public id, 2–64 of
    a-z 0-9 _ -, stored lower-case), `evidence_summary` (1–2000 characters, public) and `evidence_sha256`.
  - The criteria text, its sha256, every finalist's id, summary and hash, the decision, the quote and the reason are
    stored.
  - The prompt carries no hashes.
- Views: `get_owner`, `is_finalists_open(season_year)`, `get_finalist_seasons`, `get_award_codes`,
  `get_forbidden_signals`, `get_decision(role_key, award_code, season_year)`, `get_decision_by_key(award_key)`,
  `get_decision_count`, `get_decision_key(i)`.

Award codes and names:

| Code | Name |
|---|---|
| `PHOTOGRAPHER_OF_THE_YEAR` | Photographer of the Year |
| `DESIGNER_OF_THE_YEAR` | Designer of the Year |
| `FILMMAKER_OF_THE_YEAR` | Filmmaker of the Year |
| `EMERGING_TALENT` | Emerging Talent |
| `CREATIVE_BUSINESS_OF_THE_YEAR` | Creative Business of the Year |
| `STUDIO_OF_THE_YEAR` | Studio of the Year |

Codes are accepted in any case and stored upper-case. `award_key` is `role_key|AWARD_CODE|season_year`.

MCP server: the `genskill` claude.ai connector, tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `WINNER` + finalist id (`fin-b2`), criterion quoted, full record stored | `test_winner_names_one_finalist_and_quotes_the_criteria` |
| Answer | `NO_AWARD`, `winner_id` `""` (an id sent with NO_AWARD is ignored) | `test_no_award_when_no_finalist_meets_the_criteria` |
| Every annual award code served | six codes and names, one decision each | `test_every_annual_award_code_is_served` |
| **Must refuse: fewer than two finalists** | `[EXPECTED] TOO_FEW_FINALISTS: an award decision needs at least two finalists` | `test_refuses_fewer_than_two_finalists`: 0 or 1 finalist refused; the same id twice gives `[EXPECTED] DUPLICATE_FINALIST: each finalist_id may appear only once`; two finalists pass |
| **Must refuse: decision before the season reaches finalists** | `[EXPECTED] SEASON_NOT_AT_FINALISTS: this season has not reached the finalist stage; awards are decided only after the owner opens the season's finalist stage` (and `[EXPECTED] SEASON_ALREADY_AT_FINALISTS: this season has already reached the finalist stage`) | `test_refuses_a_decision_before_the_season_reaches_finalists`: another season's stage does not open this one; 2027 is refused after 2026 is open |
| **Must refuse: second decision, same award and season** | `[EXPECTED] AWARD_ALREADY_DECIDED: this role, award and season already has a decision` | `test_refuses_a_second_decision_for_the_same_award_and_season`: a `NO_AWARD` locks the award; case or space variants of the code, other finalists or other criteria hit the same key; another role, award or season passes |
| Award rule: forbidden signal in an evidence summary | `[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid plan, subscription, premium or membership tier, or a boost` | `test_refuses_an_evidence_summary_that_carries_a_forbidden_signal`: likes, FOLLOWERS, votes, voting, paid plan, subscription, Premium, membership tier, #Boosted, boost, each in the first or second finalist; whole words only, so "devoted" and "likeness" pass |
| Award rule: forbidden signal in the criteria text | same text | `test_refuses_criteria_text_that_carries_a_forbidden_signal`: likes, follower count, votes, paid plan, Premium, membership tier, Boosted, Subscribers |
| Too many finalists | `[EXPECTED] TOO_MANY_FINALISTS: an award decision takes at most 10 finalists` | `test_refuses_more_than_ten_finalists` (11 refused, 10 pass) |
| Malformed finalists JSON | `[EXPECTED] BAD_FINALISTS: finalists_json must be a JSON array of at most 40000 characters whose items are objects with exactly finalist_id, evidence_summary and evidence_sha256` | `test_refuses_malformed_finalists_json`: not JSON, empty, object, string item, list item, missing key, extra `name` key, wrong key, over 40000 characters |
| Finalist id | `[EXPECTED] BAD_FINALIST_ID: finalist_id must be a public id of 2 to 64 characters from a-z 0-9 _ - (never a name or email)` | `test_refuses_bad_finalist_ids`: an email, spaces, dots, leading `_`/`-`, 65 characters, non-strings; 64 characters accepted; ` FIN-B2 ` stored as `fin-b2` |
| Evidence hash | `[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_evidence_hashes` (upper-case accepted, stored lower-case) |
| Evidence summary | `[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty`; `[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters` | `test_refuses_empty_or_long_evidence_summaries` |
| Role key shape | `[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters from a-z 0-9 _` | `test_refuses_malformed_role_keys` |
| Award code | `[EXPECTED] UNKNOWN_AWARD_CODE: award_code must be PHOTOGRAPHER_OF_THE_YEAR, DESIGNER_OF_THE_YEAR, FILMMAKER_OF_THE_YEAR, EMERGING_TALENT, CREATIVE_BUSINESS_OF_THE_YEAR or STUDIO_OF_THE_YEAR` | `test_refuses_unknown_award_codes` (writes and reads) |
| Season year | `[EXPECTED] BAD_SEASON_YEAR: season_year must be a whole year from 2000 to 2199` | `test_refuses_bad_season_years` |
| Criteria text | `[EXPECTED] BAD_CRITERIA_TEXT: criteria_text must be 1 to 8000 characters and not blank` | `test_refuses_bad_criteria_text` (8000 characters accepted) |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can open a season's finalist stage or request an award decision` | `test_only_the_owner_writes` |
| Reads | `[EXPECTED] NO_DECISION: no decision is stored for this award and season`; `[EXPECTED] BAD_INDEX: nothing at this index` | `test_reads_refuse_missing_decisions_and_indexes` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no decision of WINNER or NO_AWARD`; `[LLM_ERROR] the model's WINNER does not name one of the finalist ids`; `[LLM_ERROR] the model's criteria quote is not 10 to 400 characters quoted from the criteria text`; `[LLM_ERROR] the model returned no reason` | `test_refuses_malformed_model_answers` (unknown or empty winner id, quote not in criteria, short or long quote, etc.; `no award` and ` Fin-C3 ` are normalised) |
| Quote matched up to whitespace | stored quote has whitespace runs collapsed | `test_quote_is_matched_up_to_whitespace` |
| Prompt carries public inputs only | no evidence hashes in the prompt; no-forbidden-signal and list-order instructions present; finalists in input order | `test_prompt_carries_the_public_inputs_and_no_hashes` |
| Validator agree / disagree | WINNER with the same id, or NO_AWARD; the leader's id must be a finalist; the quote must be in the criteria | `test_validator_agrees_on_the_same_winner_not_the_wording`, `test_validator_agrees_on_no_award` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `AnnualAwardDecision`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment), and its score band was replaced by WINNER + id / NO_AWARD |
| GenLayer docs search | NOT_RUN | `genlayer_search_docs` answered `Unable to load GenLayer documentation ... ENOENT: mkdir '/var/task/.cache'` (connector tooling); the contract-rules resource and the previous award contracts were enough |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the written file; byte identity of the pasted text was not machine-checked |
| Tests pass: 24 passed | OBSERVED | `python3 -m pytest tests/factory/test_annual_award_decision.py -q` gave `24 passed in 0.63s`. Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode. The LLM was mocked (this contract makes no web read) |
| One test per answer word, must-refuse case and award rule | OBSERVED | table above |
| The tests can fail | OBSERVED | 12 mutations planted one at a time by a script that restores the original bytes; 11 caught, 1 equivalent. Contract sha256 `5d46d92c…31ac` was unchanged afterwards. Details in **Mutations** below |
| Validators agree on WINNER + the same id, or on NO_AWARD, not on the wording | OBSERVED (direct mode) | `direct_vm.run_validator()` agrees (`True`) on: the same winner with another quote, reason and id case; NO_AWARD against NO_AWARD with different quotes. It disagrees (`False`) on: another finalist; NO_AWARD against WINNER; a leader id that is not a finalist or not normalised; WINNER without an id; NO_AWARD naming an id; a bad word; a quote not in the criteria; a quote under 10 characters; no reason; a non-dict leader; the validator's own model answer malformed or naming an unknown id; a leader error |
| Hashes are not sent to the model; the prompt forbids weighing paid or popularity signals and list order | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hashes`: the only LLM mock requires the instructions, the award, the criteria, every finalist's id and summary in input order, the role and season, and the absence of all three hashes |
| Studionet reachable | OBSERVED | `genlayer_network_status` (25 Nov 05:27:40 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b0671cc`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` on the base64 source (35,628 characters) answered `unsupported_contract_rpc` (endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`). This is an endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` with `from`/`to` both the zero address (a gen_call simulation; nothing is signed or sent) answered `"00"`, which `glcall.mjs decode` reads as `null` (the constructor returned), at about 05:30 UTC. `data` came from `glcall.mjs deploy contracts/factory/annual_award_decision.py '[]'` (genlayer-js 0.18.4): 53,456 hex characters, sha256 of the hex `6fdd47947143a002be79c45e9ee48d50a9550f3bd860dde41d2bea656d32956f`, prefix `0xf96864b9685f`, suffix `0600`. The hex was pasted into the call by hand from three read chunks. Byte identity was not machine-checked, but the RLP lengths (`f96864`, `b9685f`) had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Mutations

Each mutation was planted alone, the tests were run, and the original bytes were restored
(`/tmp/.../scratchpad/mutate_annual_award.py`, outside the repository).

| Mutation | Result | Failing tests |
|---|---|---|
| `TOO_FEW_FINALISTS` check removed | caught (1 failed) | `test_refuses_fewer_than_two_finalists` |
| `SEASON_NOT_AT_FINALISTS` check removed | caught (1) | `test_refuses_a_decision_before_the_season_reaches_finalists` |
| `AWARD_ALREADY_DECIDED` check removed | caught (1) | `test_refuses_a_second_decision_for_the_same_award_and_season` |
| `FORBIDDEN_SIGNAL` on evidence summaries removed | caught (1) | `test_refuses_an_evidence_summary_that_carries_a_forbidden_signal` |
| `FORBIDDEN_SIGNAL` on criteria text removed | caught (1) | `test_refuses_criteria_text_that_carries_a_forbidden_signal` |
| Validator compares the decision word only, not the winner id | caught (1) | `test_validator_agrees_on_the_same_winner_not_the_wording` |
| Validator always agrees | caught (2) | both validator tests |
| Model's WINNER not checked against the finalist ids | caught (1) | `test_refuses_malformed_model_answers` |
| Leader-result quote check dropped | caught (1) | `test_validator_agrees_on_the_same_winner_not_the_wording` |
| Award key without the role key | caught (8) | answer, code, quote, second-decision, id, hash and role tests |
| `DUPLICATE_FINALIST` check removed | caught (1) | `test_refuses_fewer_than_two_finalists` |
| A leader `NO_AWARD` may name a winner id (shape check removed) | not caught: **equivalent mutant** | none. The validator's own `NO_AWARD` always has `winner_id ""`, so a leader `NO_AWARD` naming an id already fails the id comparison. The contract's own leader result comes from `_parse_model`, which never names an id for `NO_AWARD`. The check is defence in depth with no observable effect |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint (first try) | — | NOT_RUN (tooling) | the permission check gave no verdict ("classifier gave no verdict"), so the tool did not run | none; retried after the orchestrator reported the classifier had recovered (rule 5d: tooling, not an attempt) |
| Tests (first tries) | — | NOT_RUN (tooling) | 7 Bash calls to pytest were blocked the same way and never ran | none; retried as above |
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | 24 passed | `24 passed in 0.63s` | — |
| Mutations | 1 | 11 of 12 caught, 1 equivalent | table above | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` on hosted Studionet | none (endpoint limitation) |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |

## Open questions for the owner

- **"Creative Business and Studio of the Year": one award or two?** The contract reads the row as two awards,
  `CREATIVE_BUSINESS_OF_THE_YEAR` and `STUDIO_OF_THE_YEAR`, following the row's pattern of "Photographer, Designer,
  Filmmaker of the Year". If it is one award, one code changes (`CREATIVE_BUSINESS_AND_STUDIO_OF_THE_YEAR` is
  refused today).
- **What "the same award" means.** The award-table rule says each universal contract takes the role key as an input,
  so the award is (role key, award code). A second decision is refused for the same role, award code and season
  (`role|CODE|season`). If one award code per season should serve all roles together, drop the role from the key:
  a one-line change. The builder's mutation "award key without the role" shows the tests pin the current choice.
- **What "the season reaches finalists" means.** The owner calls `open_finalists(year)` once a season's finalists
  are announced. The stage is per season, not per award code, and a season cannot be reopened. Decisions are refused
  for a season whose stage is not open. Opening per award (or per role and award) would be a small change.
- **Criteria are an input, not a registry.** The criteria text is passed with the decision, scanned for forbidden
  signals, and stored with its sha256 in the decision record, so the basis of every decision is readable on chain.
  It is not pinned before the finalists are known. If the owner wants the criteria published on chain before the
  finalist stage (so they cannot be tailored to a finalist), a registry like `champion_seat_award`'s rules versions
  can be added.
- **Who may request a decision.** All writes are owner only, because the first decision is final; an open method
  would let anyone lock an award with weak evidence. SnapLink's backend would sign with the owner address.
- **A `NO_AWARD` locks the award too.** The row refuses "a second decision", so after `NO_AWARD` the award stays
  unawarded for that role and season. An `[LLM_ERROR]` refusal stores nothing and can be retried.
- **Finalist ids are public ids.** An id is 2–64 characters of a-z 0-9 _ -, so an email or a spaced name is refused.
  A snake_case name could still pass, so SnapLink must send opaque public ids.
- **Forbidden-signal filter is whole-word and literal**, the same terms as rows 7–10. They are listed by
  `get_forbidden_signals`. Mentions alone are refused too (e.g. criteria saying "votes never count"). Finalist ids,
  role keys and award codes are not scanned.
- **Close calls may not reach consensus.** Validators must name the same winner. If two finalists are near level and
  the criteria publish no tie-break, validators may disagree and the transaction may not finalise. Publishing a
  tie-break in the criteria (as in the test fixture's C4) helps.
- **What the model sees.** It sees the criteria text, each finalist's id and summary in input order, the role,
  season, award code and name. It does not see the evidence or the hashes. The prompt tells it that list position and
  summary length count for nothing.
- **Limits.** Criteria up to 8000 characters, summaries up to 2000 (trimmed), 2–10 finalists, finalists JSON up to
  40000 characters, season years 2000–2199.
- **On chain in the clear.** The criteria, summaries, ids and hashes are public calldata and storage. Summaries
  must not carry names, emails or private evidence; the contract cannot stop that.

## Not verified

- The real model's judgment.
- GenVM execution and multi-validator consensus on a network (direct mode runs the SDK in CPython).
- Any write method on Studionet.
- The Studionet schema (the endpoint refuses it).

## Not done in this run

- No key was held, generated or asked for; nothing was signed, deployed or sent.
- `genlayer_submit_raw_transaction` and `genlayer_raw_rpc` were not called; no `genlayer deploy`, `write`, `account`
  or `keygen` was run.
- Nothing was merged or pushed to `main`; no other repository was touched; nothing was done in Base44.
- The pull request and the owner's page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/annual_award_decision.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/annual_award_decision.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_decision_count` (a fresh
contract answers `0`); `genlayer call <address> get_owner`.

VERDICT: DRAFTED — lint clean (attempt 1); 24 direct-mode tests pass (attempt 1) with the model mocked; 11 of 12
planted mutations caught and the twelfth is equivalent; Studionet is reachable and the deploy simulation constructs
(`00`); the schema is NOT_RUN (endpoint). The PR stays a draft until the owner deploys and the post-deploy Studionet
check (transaction report and a view read) passes.

## Independent verification (verifier agent, 2026-11-25 05:47 UTC)

Fresh clone of branch `factory/annual_award_decision-2026-11-25`, HEAD checked `b56fbac941187d118758b2f7470c732a504ac350`.
The builder's record was read only after the verdict below was reached.

- `contracts/factory/annual_award_decision.py` sha256 `5d46d92cb5b3a3da400e3db836259710bbc59474748c1a198da20dd0a54631ac` (matches the build)
- `tests/factory/test_annual_award_decision.py` sha256 `935f305c85fad670c3503cca61d02c27c0480ffbbce22ffebe091203015cf8e3`

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| genskill lint | `genlayer_lint_contract` on the full source, attempt 1 | 0 errors, 0 warnings, 0 infos | OBSERVED | "Looks deployable" |
| Tests | `python3 -m pytest tests/factory/test_annual_award_decision.py -q`, attempt 1 | `24 passed in 0.67s` | OBSERVED | genlayer-test 0.29.2, GenVM direct mode |
| Source shape | read the contract | pinned runner on line 1, blank line 2, no comment under the header; constructor `AnnualAwardDecision()` documented in the module docstring | OBSERVED | lines 1-3, 22-25 |
| Answer words | read contract and tests | `WINNER` + finalist id (`test_winner_names_one_finalist_and_quotes_the_criteria`, all six award codes in `test_every_annual_award_code_is_served`) and `NO_AWARD` (`test_no_award_when_no_finalist_meets_the_criteria`) each have a test with the exact result object; criteria quote is returned and checked against the criteria text | OBSERVED | tests lines 113-191 |
| Row refusal: fewer than two finalists | read | `TOO_FEW_FINALISTS` asserted with exact text for 0 and 1 finalists (and a duplicate id, which is not two finalists); two is accepted | OBSERVED | `test_refuses_fewer_than_two_finalists` |
| Row refusal: season not at finalists | read | `SEASON_NOT_AT_FINALISTS` exact text; another season's stage does not open this one; `SEASON_ALREADY_AT_FINALISTS` also tested | OBSERVED | `test_refuses_a_decision_before_the_season_reaches_finalists` |
| Row refusal: second decision | read | `AWARD_ALREADY_DECIDED` exact text, including after a NO_AWARD and with other finalists, criteria and a differently written award code; a different role, award or season is a separate award | OBSERVED | `test_refuses_a_second_decision_for_the_same_award_and_season` |
| Award-table rule: forbidden signals | read | `FORBIDDEN_SIGNAL` exact text for likes, followers, votes/voting, paid plan, subscription, premium, membership tier, boost/boosted in evidence summaries (first and second finalist) and in the criteria text; whole-word matching proven by a clean "likeness" summary | OBSERVED | two tests, lines 264-308 |
| Award-table rule: one universal contract for all roles | read | role key is an input (shape-checked, `BAD_ROLE_KEY` tested); award key is role + code + season | OBSERVED | `test_refuses_malformed_role_keys` |
| Other refusals | read | owner-only, bad season, bad criteria, too many, bad finalists JSON (incl. an extra `name` key), bad id, bad hash, empty/long summary, unknown code, no decision, bad index, six malformed-model-answer cases: each has a test with exact text | OBSERVED | tests lines 313-497 |
| Validator compares the verdict word | read + mutation | `mine["decision"] == theirs["decision"] and mine["winner_id"] == theirs["winner_id"]`; tests: same winner with different quote and reason agrees; other finalist or NO_AWARD disagrees; NO_AWARD agrees with NO_AWARD; forged or malformed leader results and a leader error disagree | OBSERVED | tests lines 501-558 |
| Safety: calldata | read | arguments are role key, award code, year, criteria text, finalists JSON (id, public summary, sha256); the finalist id rejects `@` and spaces; no name/email field (an extra key is refused as `BAD_FINALISTS`); the prompt carries no evidence hash (asserted in `test_prompt_carries_the_public_inputs_and_no_hashes`) | OBSERVED | contract lines 292-357, 541-548 |
| Safety: no key, no sending | grep for private, key, sign, raw_rpc, submit, eth_send, send_, secret, mnemonic, wallet, web calls | only docstring words ("private evidence", "signals", "Designer"); no web call, no signing or sending call, no key handling; the only external call is `gl.nondet.exec_prompt`, mocked with `direct_vm.mock_llm` in every test | OBSERVED | grep output |
| Mutations | 10 planted one at a time, see below | all 10 caught | OBSERVED | below |
| Clean after mutations | `git checkout -- <file>`, `sha256sum`, `git status` | sha256 unchanged (`5d46d92c...631ac`), working tree clean (only untracked `__pycache__` from pytest, removed) | OBSERVED | |
| Deploy simulation | not run | the optional step needs the 53,456-character hex payload passed by hand into `genlayer_call_contract`; not attempted rather than risk a transcription error | NOT_RUN | the builder's record states `00`; this verifier did not reproduce it |

### Mutations (each reverted with `git checkout -- contracts/factory/annual_award_decision.py`)

| # | Mutation | Caught by |
|---|---|---|
| M1 | `MIN_FINALISTS = 2` to `1` | `test_refuses_fewer_than_two_finalists` |
| M2 | season gate `if str(season) not in self.finalist_seasons` to `if False` | `test_refuses_a_decision_before_the_season_reaches_finalists` |
| M3 | already-decided check to `if False` | `test_refuses_a_second_decision_for_the_same_award_and_season` |
| M4 | validator returns `True` always | `test_validator_agrees_on_the_same_winner_not_the_wording` |
| M5 | validator ignores the winner id | `test_validator_agrees_on_the_same_winner_not_the_wording` |
| M6 | no forbidden-signal check on evidence summaries | `test_refuses_an_evidence_summary_that_carries_a_forbidden_signal` |
| M7 | no forbidden-signal check on criteria text | `test_refuses_criteria_text_that_carries_a_forbidden_signal` |
| M8 | model's WINNER need not name a finalist | `test_refuses_malformed_model_answers` |
| M9 | owner check removed | `test_only_the_owner_writes` |
| M10 | the "boost" terms removed from the forbidden list | `test_refuses_an_evidence_summary_that_carries_a_forbidden_signal` |

### Observations (not defects)

- An extra key such as `likes` on a finalist object is refused with `BAD_FINALISTS` (exact-keys rule), not `FORBIDDEN_SIGNAL`; the input is still refused. Probed with a scratch test outside the repository.
- `finalist_id` and `role_key` are shape-checked but not scanned for forbidden words (a finalist id such as `top-voted-boosted` is accepted); only the criteria text and evidence summaries are scanned. The ids are meant to be opaque.
- Matching is ASCII-lowercased whole words; Unicode look-alike spellings would not match.
- Refusal order: `TOO_FEW_FINALISTS` is reported before `SEASON_NOT_AT_FINALISTS` when both apply.

**Verdict: PASS**
