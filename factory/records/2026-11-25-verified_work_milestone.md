# Factory record — verified_work_milestone — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #9 of the owner's page (main table, row 9; award
contract). Cloud workspace, genskill MCP server as the owner's claude.ai connector. Branch
`factory/verified_work_milestone-2026-11-25` from `main`. Pull request: left to the orchestrator.

Owner's row, as given to the builder:

| # | Contract | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|
| 9 | verified_work_milestone | Is every counted piece attested or SnapLink-verified, done in the named role, and counted once, so the milestone is reached? | role key, milestone, list of work-record hashes with evidence level and role | `MILESTONE_REACHED` / `NOT_REACHED` + the shortfall | milestone not in the catalogue; the same work hash twice in one claim; a milestone already confirmed for this entrant and role |

Award type: Verified Work trophies, Foundation (25) to Zenith (10,000).

Award-contract rule (rows 7–12), as given: "Six universal contracts cover every SnapLink award: each one
serves all 45 roles, taking the role key as an input. They are what would make 'VERIFIED ON GENLAYER' on
a trophy true. Every award contract refuses inputs that carry a forbidden selection signal (likes,
followers, votes, paid plan or boost), because paid membership must never improve anyone's chance of an
award."

## Output

| File | sha256 |
|---|---|
| `contracts/factory/verified_work_milestone.py` | `a8354c84f4d15f5821964623088d78a455c6789e26f6dc78743c814ecf571ef5` |
| `tests/factory/test_verified_work_milestone.py` | `5bb19ee80bf1762a73338ba41f5d5151c19c524b2439bc0b5b537e755f133e74` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the doc block documenting the constructor and saying
calldata is public data only.

Class `VerifiedWorkMilestone`; constructor `VerifiedWorkMilestone()` takes no arguments. The deployer
becomes the owner; the catalogue is seeded with `FOUNDATION` = 25 and `ZENITH` = 10000.

Methods:
- write (owner only): `claim_milestone(entrant_id, role_key, milestone, work_hashes, evidence_levels,
  work_roles)` returns `{claim_index, entrant_id, role_key, milestone, verdict, required, counted,
  shortfall, records, not_counted_level, not_counted_role, reason}`; `add_milestone(name, count)` returns
  `{milestone, count}`.
- view: `get_owner`, `get_rules`, `get_catalogue`, `get_milestone(name)`,
  `is_confirmed(entrant_id, role_key, milestone)`, `get_confirmation(entrant_id, role_key, milestone)`,
  `get_claim_count`, `get_claim(index)`.

Decision type: deterministic counting (template `storage`). No LLM, no web read, no equivalence
principle: every validator recomputes the same answer from the same calldata, so there is no
leader/validator comparison to test.

Counting rule: a record counts if and only if its evidence level (trimmed, case-insensitive) is
`ATTESTED` or `SNAPLINK_VERIFIED` **and** its role equals `role_key`. Reached iff counted ≥ the
milestone's count; otherwise `NOT_REACHED` with shortfall = count − counted.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The pinned repo version in
`.mcp.json` is genskill-mcp@2.3.3; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `MILESTONE_REACHED` (shortfall 0; ATTESTED + SNAPLINK_VERIFIED counted, other levels and other roles not) | `test_milestone_reached_counts_attested_and_snaplink_verified`; also `test_zenith_needs_ten_thousand_counted_records` |
| Answer | `NOT_REACHED` + shortfall (18 of 25 → 7) | `test_not_reached_reports_the_shortfall`; `test_empty_list_is_not_reached_with_the_full_shortfall`; Zenith 9,999 → shortfall 1 |
| NOT_REACHED does not block | a later claim for the same entrant, role and milestone is answered | `test_not_reached_does_not_block_a_later_claim` |
| Level words | case-insensitive; `ATTESTED_BY_FRIEND`, `VERIFIED` accepted but not counted | `test_level_words_are_case_insensitive_and_other_words_do_not_count` |
| Must refuse: milestone not in the catalogue | `[EXPECTED] UNKNOWN_MILESTONE: this milestone is not in the catalogue` | `test_refuses_a_milestone_not_in_the_catalogue` |
| Must refuse: same work hash twice in one claim | `[EXPECTED] DUPLICATE_WORK_HASH: the same work hash appears more than once in this claim` | `test_refuses_the_same_work_hash_twice_in_one_claim` (copy upper-cased, with another level and role) |
| Must refuse: milestone already confirmed for this entrant and role | `[EXPECTED] ALREADY_CONFIRMED: this milestone is already confirmed for this entrant and role` | `test_refuses_a_milestone_already_confirmed_for_this_entrant_and_role` (another role, entrant or milestone still answered) |
| Award rule: forbidden selection signal | `[EXPECTED] FORBIDDEN_SIGNAL: inputs must not carry a selection signal (likes, followers, votes, paid plan or boost)` | `test_refuses_a_forbidden_selection_signal` ×10 (boosted, Boost2x, paid, PREMIUM, SUBSCRIPTION_VERIFIED, membership_tier, likes_curator, top_followers, Votes, voting_round); `test_refuses_a_forbidden_signal_in_a_new_milestone_name`; whole words only: `test_whole_words_only_for_forbidden_signals` |
| Role key shape | `[EXPECTED] BAD_ROLE_KEY: a role key must be lowercase snake_case, 2 to 48 characters` | `test_refuses_a_malformed_role_key` |
| Over-long list | `[EXPECTED] TOO_MANY_RECORDS: a claim may list at most 10000 work records` | `test_refuses_an_over_long_list` (10,001) |
| Owner only | `[EXPECTED] NOT_OWNER: only the contract owner (the deployer) can do this` | `test_refuses_claims_and_catalogue_changes_from_anyone_but_the_owner` |
| Catalogue | `[EXPECTED] MILESTONE_EXISTS: this milestone is already in the catalogue`; `[EXPECTED] BAD_MILESTONE_NAME: a milestone name must start with a letter and use only letters, digits or underscores, at most 32 characters`; `[EXPECTED] BAD_MILESTONE_COUNT: a milestone count must be a whole number from 1 to 10000` | `test_owner_adds_a_milestone_between_foundation_and_zenith` |
| Malformed inputs | `[EXPECTED] BAD_ENTRANT_ID: entrant_id must be 64 hexadecimal characters (a public hash, never a name)`; `[EXPECTED] BAD_WORK_HASH: every work-record hash must be 64 hexadecimal characters`; `[EXPECTED] BAD_EVIDENCE_LEVEL: an evidence level must be one word of letters, digits or underscores, at most 32 characters`; `[EXPECTED] BAD_WORK_RECORDS: work_hashes, evidence_levels and work_roles must be lists of text of the same length` | `test_refuses_malformed_entrant_hashes_levels_and_lists` |
| Views | `[EXPECTED] NOT_CONFIRMED: no confirmation is stored for this entrant, role and milestone`; `[EXPECTED] BAD_INDEX: no claim at this index` | `test_views_and_rules`, `test_not_reached_reports_the_shortfall` |

Every refusal test asserts the full text with `direct_vm.expect_revert(<full text>)`, and the refusal
tests also check that nothing was written (`get_claim_count()` unchanged, no confirmation).

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `storage`, name `VerifiedWorkMilestone`; `genlayer_scaffold_test` template `storage`. The scaffold's key/value methods were replaced by the row's claim, catalogue and views |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full final source: `ok: true`, 0 errors, 1 warning, 0 info. The warning is `L346 [python-container] Use DynArray[T] / TreeMap[K, V] for storage, not list / dict`; line 346 is the continuation line of the `claim_milestone` signature (`evidence_levels: list[str], work_roles: list[str]) -> typing.Any:`), a method parameter carried in calldata, not storage; all storage fields are `Address`, `TreeMap`, `DynArray`. Kept as a false positive. The source was pasted into the tool call from the written file; byte identity was not machine-checked, but the finding's line number matches the file |
| Tests pass: 27 passed | OBSERVED | `python3 -m pytest tests/factory/test_verified_work_milestone.py -q` → `27 passed in 0.80s` (re-run before commit: `27 passed in 0.78s`); Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode (arguments round-trip through calldata encode/decode); no LLM or web call exists to mock |
| One test per answer word and per must-refuse case | OBSERVED | table above |
| The tests can fail | OBSERVED | 10 planted mutations, each caught, each reverted (contract sha256 `a8354c84…71ef5` before and after): DUPLICATE_WORK_HASH check removed → 1 failed; FORBIDDEN_SIGNAL scan removed from `claim_milestone` → 10 failed; ALREADY_CONFIRMED check removed → 1; catalogue lookup removed → 1; `>=` changed to `>` → 7; every level counted → 5; role not compared → 2; owner check removed → 1; TOO_MANY_RECORDS removed → 1; NOT_REACHED also stored as a confirmation → 3 |
| Calldata is public data only | OBSERVED (by construction and test) | inputs are 64-hex hashes, level words, role keys and milestone names; a name or email as `entrant_id` is refused (`BAD_ENTRANT_ID`, tested with `Alice Smith` and an email) |
| Studionet reachable | OBSERVED | `genlayer_network_status` 25 Nov 00:15 UTC: endpoint `https://studio.genlayer.com/api`, health `healthy` (genvm, database, consensus, redis healthy), chain id `0xf22f`, block `0x6b06289d`, not syncing |
| Schema on Studionet | NOT_RUN | not sent: hosted Studionet answers `unsupported_contract_rpc` for `genlayer_get_contract_schema` on every contract (orchestrator probe 25 Nov ~00:01 UTC: endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`); endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deploy contracts/factory/verified_work_milestone.py '[]'` (genlayer-js 0.18.4): 37,232 hex chars, sha256 of the hex `e5cb53190ba8f8ae213cdcccb409e7b5ae4b4616775e90203ce7d08877033886`, prefix `0xf948b4b948af`, suffix `0600` → `"00"`, which decodes to `null` (constructor returned). The hex was pasted by hand in one line; byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| Calldata size of a claim | OBSERVED (encoder only) | `glcall.mjs read claim_milestone` with 25 records → 5,160 hex chars (~2.6 KB); 1,000 records → 196,264 hex chars (~98 KB); so a full 10,000-record Zenith claim is ~1 MB of calldata (extrapolated, not encoded: the argument exceeded the shell's limit) |
| Runs on GenVM; deploys and finalizes; a claim on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 1 warning (L346 python-container, false positive on a parameter annotation) | not a lint fix: two forbidden words (`liking`, `upvoted`) added to the list as a design change, so the final source was linted again |
| Lint | 2 | pass | final source: 0 errors, same 1 warning at L346 | — |
| Tests | 1 | 27 passed | — | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | — | NOT_RUN | orchestrator probe 25 Nov ~00:01 UTC (`unsupported_contract_rpc`); not resent per the builder guide | — |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |

## Open questions for the owner (choices made in this draft)

1. **Input encoding.** Three parallel lists `work_hashes: list[str]`, `evidence_levels: list[str]`,
   `work_roles: list[str]` (record *i* is the *i*-th item of each). Native GenLayer calldata arrays,
   supported by genlayer-test 0.29.2 and the schema; no JSON parsing on chain. Mismatched lengths or a
   non-text item → `BAD_WORK_RECORDS`.
2. **Accepted level words.** Exactly `ATTESTED` and `SNAPLINK_VERIFIED`, matched after trimming and ASCII
   upper-casing (so `attested` counts). Any other well-formed word (letters, digits, `_`, ≤ 32) is
   **accepted and not counted** (reported as `not_counted_level`) rather than refused, so SnapLink can send
   its other levels (e.g. `SELF_REPORTED`, `PENDING`) without a contract change. A malformed level is
   refused (`BAD_EVIDENCE_LEVEL`). Confirm SnapLink's exact level names.
3. **Role keys.** The page does not list the 45 keys, so only the shape is checked: lowercase snake_case,
   2–48 characters, letter first, no leading/trailing/double underscore (`BAD_ROLE_KEY`). Role keys are
   case-sensitive (not lower-cased for the caller). The list of 45 keys is **not** checked on chain; if
   it should be, it could be added as an owner-managed list like the catalogue.
4. **Forbidden selection signals.** Every text input (entrant id, role key, milestone, every hash, level
   and record role; and a new milestone name) is split into runs of ASCII letters, case-insensitive, and
   refused if any word is one of: like, likes, liked, liking, follower, followers, vote, votes, voted,
   voting, upvote, upvotes, upvoted, paid, subscription(s), subscriber(s), premium, membership(s), boost,
   boosts, boosted, boosting (`get_rules()` lists them). Underscores, digits and punctuation separate
   words, so `PAID_PLAN`, `membership_tier` and `Boost2x` are refused, while `lifelike` and `unpaid` are
   not. Consequence: a real role key containing one of these words (e.g. a `premium_…` role) would be
   refused; check the 45 keys against the list. A camelCase `paidPlan` level is one word (`paidplan`),
   not refused, but it is not a counting word so it cannot help an award.
5. **Catalogue.** The page names only Foundation = 25 and Zenith = 10,000; both are seeded. **The levels in
   between are missing from the page**: the owner adds them with `add_milestone(name, count)` (owner only;
   name upper-cased; count 1–10,000; an existing name is refused, so a count cannot be changed or a level
   removed once added). Milestones are independent: Zenith does not require Foundation to be confirmed
   first.
6. **Who may claim.** `claim_milestone` is owner-only (the deployer, i.e. SnapLink's account). Reason: the
   entrant is a hash, not an address, and the levels are asserted by the caller; if anyone could claim,
   a stranger could confirm (entrant, role, milestone) first with a made-up list and so block the real
   claim with `ALREADY_CONFIRMED`. There is no ownership transfer; if the owner wants a separate
   operator account or a transfer method, that is a change.
7. **Confirmations.** Keyed by (entrant_id, role_key, milestone). Only `MILESTONE_REACHED` stores a
   confirmation; `NOT_REACHED` is logged (`get_claim`) but confirms nothing and does not block a later
   claim. A confirmation cannot be revoked.
8. **List size.** At most 10,000 records per claim (= Zenith's count; `TOO_MANY_RECORDS` above that), and
   milestone counts are capped at 10,000 so every milestone is reachable in one claim. A full Zenith claim
   is ~1 MB of calldata (measured ~98 bytes per record), which may exceed a network's transaction size
   limit, especially on Bradbury. If it does, the alternative is a batched design (records submitted in
   several calls and accumulated per entrant and role, with cross-batch duplicate checks), which changes
   the row's single-claim shape.
9. **Counted once.** Duplicates are refused within a claim (hash compared case-insensitively, whatever its
   level or role). The work list is not stored, so a hash already used in another claim, for another role
   or another entrant is not detected on chain; that is SnapLink's off-chain check, like the truth of each
   level and role.
10. **Entrant id.** Must be a 64-hex public hash, never a name or email. If it is a plain sha256 of a
    guessable value (an email, a handle) it can be linked back to the person; a salted hash or random id is
    safer.

## Not verified

GenVM execution of this file on a network (direct mode runs the SDK in CPython); multi-validator
consensus; deploy and finality; a `claim_milestone` write on Studionet; the gas/size limits a 10,000-record
claim meets on Studionet or Bradbury; that SnapLink's work records, levels and roles are true.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged;
nothing pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's
page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/verified_work_milestone.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/verified_work_milestone.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_catalogue`
(expect `[{"count":25,"milestone":"FOUNDATION"},{"count":10000,"milestone":"ZENITH"}]`) and
`genlayer call <address> get_owner` (expect the deploying address).

VERDICT: DRAFTED — lint 0 errors (1 false-positive warning), 27 direct-mode tests pass, 10/10 mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN (endpoint). The PR
stays a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view
read) passes.

## Independent verification — 25 Nov 2026 (same scheduled run, separate verifier agent)

A verifier agent that did not build this contract checked out `70037747a2c48aa1485d33739a91eae8d21a02fe` and judged it
from the code, the tests and page row 9 (plus the award rules) before reading this record. **Verdict: PASS.**

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Hashes | 1 | contract `a8354c84…71ef5`, tests `5bb19ee8…33e74` match this record | OBSERVED | unchanged after mutations |
| genskill lint (full source) | 1 | 0 errors, 1 warning (`L346 python-container` on the `list[str]` calldata parameter: false positive, storage is Address/TreeMap/DynArray) | OBSERVED | source pasted by hand |
| pytest | 1 | `27 passed in 0.81s` | OBSERVED | verifier's own clone |
| Boundary | 1 | exactly the count → reached; one short → shortfall 1 | OBSERVED | Foundation 24/25, Zenith 9999/10000, added level 99/100 |
| Row + award-rule coverage, exact texts | 1 | every item has a full-text test | OBSERVED | UNKNOWN_MILESTONE, DUPLICATE_WORK_HASH (case/whitespace variants), ALREADY_CONFIRMED, FORBIDDEN_SIGNAL (10 cases, five families), BAD_ROLE_KEY; 16 ERR constants AST-compared |
| Mutations caught | 1 | 10 of 10 | OBSERVED | `>=`→`>`, each refusal removed, every level counted, role not compared, shortfall off by one, verdicts flipped, role-key check removed; reverted, tree clean |

Verifier notes (not defects): forbidden-word matching works on letter runs, so joined forms (`PAIDPLAN`, `likeCount`,
`BoostLevel`) pass but can never count; "following" is not listed; a full Zenith claim is ~1 MB of calldata; reuse of a
hash across claims is not detected on chain. Not reproduced by the verifier: the Studionet checks (outside its brief).
