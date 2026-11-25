# Factory record — recognition_plaque_award — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #8 of the owner's page (main table, row 8, an
award contract; `factory/BACKLOG.md` item 8). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/recognition_plaque_award-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator (draft until the Studionet check passes).

Owner's row, as given to the builder:

| # | Contract | Award type | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|---|
| 8 | recognition_plaque_award | Percentage plaques: Top 1%, 3%, 5%, 10% | Does the band hold by actual rank ÷ eligible entrants (decided by rank, never by a rounded percentage), with each person counted once? | role key, scope + area code, season, rank, eligible entrants, band, snapshot hash | `BAND_CONFIRMED` / `NOT_ELIGIBLE` + the actual percentage | band outside the four; cohort below the minimum; a second verdict for the same entrant, role, area and season |

Award-contract rule (rows 7–12): "Six universal contracts cover every SnapLink award: each one
serves all 45 roles, taking the role key as an input. They are what would make 'VERIFIED ON
GENLAYER' on a trophy true. Every award contract refuses inputs that carry a forbidden selection
signal (likes, followers, votes, paid plan or boost), because paid membership must never improve
anyone's chance of an award."

## Output

| File | sha256 |
|---|---|
| `contracts/factory/recognition_plaque_award.py` | `b6987dc6e30eb529ebafe1213a9cc20420390cdbe04db9c2bc4322d169474d90` |
| `tests/factory/test_recognition_plaque_award.py` | `f4e9ef812637db0163877005010ac778156c6a5272622fa4e81822a0d5970558` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the doc block documenting the constructor and
saying calldata is public data only. Class `RecognitionPlaqueAward`; constructor
`RecognitionPlaqueAward()` takes no arguments and records the deploying address as the issuer.

Methods: write `decide_band(entrant_id, role_key, scope, area_code, season, ranking_basis, rank,
eligible_entrants, band, snapshot_sha256)` returns `{verdict, band, actual_percentage, rank,
eligible_entrants, reason}`; views `get_verdict(entrant_id, role_key, scope, area_code, season)`,
`get_cohort(role_key, scope, area_code, season)`, `get_verdict_count()`, `get_verdict_key(i)`,
`get_rules()`.

Decision (deterministic, no LLM, no web): band X% holds iff `rank * 100 <= X * eligible_entrants`
in integers, with `1 <= rank <= eligible_entrants`. `actual_percentage` is `rank * 100 /
eligible_entrants` as a 4-place decimal string rounded up, informational only; it never decides.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`. The repo pins
genskill-mcp@2.3.3 in `.mcp.json`; the connector did not report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `BAND_CONFIRMED` + `actual_percentage` (rank 12 of 1260, Top 1%, `0.9524`; full stored record incl. snapshot hash) | `test_band_confirmed_by_rank_and_stored_with_the_snapshot` |
| Answer | `NOT_ELIGIBLE` + `actual_percentage` (rank 2 of 199: rounded percentage says 1%, the rank says no; `1.0051`) | `test_not_eligible_with_the_actual_percentage_where_rounding_would_say_one_percent` |
| Decided by rank, display rounds up | rank 100001 of 10000001 → `NOT_ELIGIBLE`, `1.0001` (truncation would read `1.0000`) | `test_displayed_percentage_rounds_up_so_it_never_reads_inside_a_band_that_fails` |
| Exact band boundaries | Top 1/3/5/10% at 1000 entrants: rank 10/30/50/100 confirmed, 11/31/51/101 not | `test_exact_boundaries_of_all_four_bands` |
| No nondeterminism | no LLM or web mock needed; `run_validator()` → "No validator captured" | `test_no_llm_or_web_call_and_no_validator_is_needed` |
| Must refuse: band outside the four | `[EXPECTED] BAD_BAND: band must be TOP_1, TOP_3, TOP_5 or TOP_10` | `test_refuses_a_band_outside_the_four` |
| Must refuse: cohort below the minimum | `[EXPECTED] COHORT_TOO_SMALL: eligible_entrants must be at least 100` (100 accepted) | `test_refuses_a_cohort_below_the_minimum` |
| Must refuse: second verdict, same entrant/role/area/season | `[EXPECTED] ALREADY_DECIDED: this entrant already has a verdict for this role, area and season` (any band; same keys in other case/padding; other season/role/area/scope/entrant allowed) | `test_refuses_a_second_verdict_for_the_same_entrant_role_area_and_season` |
| Award rule: forbidden selection signal | `[EXPECTED] FORBIDDEN_SIGNAL: likes, followers, votes, a paid plan or a boost must never select an award` (16 cases, every family, in role_key, scope, area_code, season and ranking_basis; whole words only) | `test_refuses_forbidden_selection_signals_in_any_text_input` |
| Award rule: role key shape | `[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case of 2 to 48 characters (a-z, 0-9, single '_' between words), starting with a letter` (a well-formed unknown key is accepted) | `test_refuses_a_malformed_role_key_and_does_not_check_the_role_list` |
| Cohort pinned | `[EXPECTED] COHORT_MISMATCH: this role, area and season is pinned to another snapshot_sha256 or eligible_entrants` | `test_refuses_a_cohort_that_disagrees_with_its_pinned_snapshot_or_size` |
| Issuer only | `[EXPECTED] NOT_ISSUER: only the issuer that deployed this contract can record a verdict` | `test_refuses_a_sender_other_than_the_issuer` |
| Malformed inputs | `[EXPECTED] BAD_ENTRANT_ID: entrant_id must be a public hash of 64 hexadecimal characters, never a name`; `[EXPECTED] BAD_SNAPSHOT_HASH: snapshot_sha256 must be 64 hexadecimal characters`; `[EXPECTED] BAD_SCOPE: …`, `[EXPECTED] BAD_AREA_CODE: …`, `[EXPECTED] BAD_SEASON: …` (`must be 1 to 32 characters of letters, digits, '-', '_' or '.'`); `[EXPECTED] BAD_RANKING_BASIS: ranking_basis must be 1 to 200 printable ASCII characters of public text`; `[EXPECTED] BAD_ENTRANTS: eligible_entrants must be a whole number of at most 1000000000`; `[EXPECTED] BAD_RANK: rank must be a whole number from 1 to eligible_entrants` | `test_refuses_malformed_hashes_codes_basis_and_numbers` |
| Views | `[EXPECTED] UNKNOWN_VERDICT: no verdict is stored for this entrant, role, area and season`; `[EXPECTED] UNKNOWN_COHORT: no cohort is stored for this role, area and season`; `[EXPECTED] BAD_INDEX: no verdict at this index` | `test_views` |

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `storage`, name `RecognitionPlaqueAward`; `genlayer_scaffold_test` template `storage`. The scaffold's key/value methods were replaced by the row's decision |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. Source pasted into the tool call from the written file; byte identity of the pasted text not machine-checked |
| Tests pass: 14 passed | OBSERVED | `python3 -m pytest tests/factory/test_recognition_plaque_award.py -q` → `14 passed in 0.35s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; nothing mocked (no LLM or web call in this contract) |
| One test per answer word and per must-refuse case; refusals asserted with full text | OBSERVED | table above (`expect_revert` matches the full constant text) |
| The tests can fail | OBSERVED | 6 mutations, each reverted from a backup: `ALREADY_DECIDED` check removed → 1 failed; decision by `round(rank*100/eligible) <= X` → 4 failed; `FORBIDDEN_SIGNAL` check removed → 1 failed; `<=` changed to `<` → 2 failed; `COHORT_TOO_SMALL` check removed → 1 failed; `TOP_2` added to the bands → 2 failed. Contract sha256 `b6987dc6…4d90` unchanged afterwards; 14 passed on the restored file |
| Decided by rank, never by a rounded percentage | OBSERVED (direct mode) | integer comparison in the source; the rounding mutation above fails 4 tests |
| No consensus risk from nondeterminism | OBSERVED (direct mode) | no `gl.nondet` / `run_nondet` in the source; `run_validator()` reports no validator captured |
| Studionet reachable | OBSERVED | `genlayer_network_status` 25 Nov 2026 00:14:05 UTC: endpoint `https://studio.genlayer.com/api`, health `healthy` (genvm, database, consensus healthy), chain id `0xf22f`, block `0x6b06284d`, not syncing |
| Schema on Studionet | NOT_RUN | not sent: hosted Studionet refuses `genlayer_get_contract_schema` for every contract (orchestrator probe 25 Nov ~00:01 UTC: `unsupported_contract_rpc`, endpoint_mode `studionet-hosted`, upstream `Internal database error (code -32603)`) |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from` and `to` zero address, `data` from `glcall.mjs deploy contracts/factory/recognition_plaque_award.py '[]'` (genlayer-js 0.18.4): 37,418 hex chars, sha256 of the hex `f08ade6fa694ff2528d216aa7ea22bc58784f3057156267b7356fcc59f0a3d65`, prefix `0xf94911b9490c23`, suffix `0600` → `"00"`, decoded `null` (constructor returned). The hex was pasted by hand in one line; byte identity with the file was not machine-checked, but the node had to decode the RLP lengths |
| SnapLink's real ranking data, the 45 role keys | NOT_RUN | not available to the factory; role keys are checked for shape only |
| Runs on GenVM; deploys and finalizes; a write on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | `ok: true`, 0 errors, 0 warnings, 0 info | — |
| Tests | 1 | pass | `14 passed in 0.31s` | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | — | NOT_RUN | orchestrator probe 25 Nov ~00:01 UTC (`unsupported_contract_rpc`) | not resent, per the brief |
| Studionet deploy simulation | 1 | tool error (request shape) | `'to' (code -32603)`: the node rejected the request without a `to` field (not the contract) | same hex resent with `to` = zero address; no contract change |
| Studionet deploy simulation | 2 | pass | `"00"` → `null` | — |

## Open questions for the owner

Each is a choice the builder made where the page is silent; change any of them.

1. **No LLM, no judgment.** The decision is arithmetic, so it is plain deterministic code (template
   `storage`, no equivalence principle). Its value is a public, immutable, rule-checked record of
   the verdict, like `agreement_registry`, not a judgment ordinary code cannot make.
2. **Formula.** Band X% holds iff `rank * 100 <= X * eligible_entrants` (integers), `1 <= rank <=
   eligible_entrants`. Tied ranks are accepted as given; the contract does not check that ranks
   are unique.
3. **Actual percentage.** 4 decimal places, rounded **up**, so the display never reads inside a
   band that does not hold (rank 100001 of 10000001 shows `1.0001`, not `1.0000`). Informational.
4. **Minimum cohort.** `MIN_ELIGIBLE_ENTRANTS = 100`, one global minimum for all four bands (the
   smallest cohort in which even Top 1% can hold, for rank 1). Alternative: per-band minimums
   100 / 34 / 20 / 10, which the arithmetic already implies for rank 1. A sanity cap of
   1,000,000,000 entrants (`BAD_ENTRANTS`).
5. **`entrant_id` added.** The row lists no entrant input; "each person counted once" and "a second
   verdict for the same entrant" need one. It must be a 64-hex public hash, never a name. A plain
   sha256 of an email or name can be guessed; SnapLink should use a keyed hash (e.g. HMAC of its
   internal user id) so the public cannot reverse it.
6. **One verdict per slot, whatever the band.** The slot is (entrant, role, scope + area_code,
   season). A `NOT_ELIGIBLE` verdict also uses the slot, so SnapLink should request the tightest
   band the rank qualifies for. Alternatives: key by band too, or allow an upgrade.
7. **"Area" = scope + area_code.** The same area code under another scope (city vs region) is a
   different slot and a different cohort.
8. **Cohort pinning (`COHORT_MISMATCH`, beyond the row).** The first verdict in a role / area /
   season cohort pins its `snapshot_sha256` and `eligible_entrants`; later verdicts there must
   match, so one cohort cannot be given different sizes for different entrants. A wrong first
   verdict locks the cohort; there is no admin to fix it (redeploy).
9. **Issuer only (`NOT_ISSUER`, beyond the row).** Unlike earlier factory contracts, only the
   deploying address can record verdicts. Reason: because any verdict uses the entrant's slot, an
   open contract would let anyone pre-empt an entrant with a `NOT_ELIGIBLE`. The issuer cannot be
   rotated; a new SnapLink key means a redeploy. Alternative: an open contract with a per-sender
   namespace.
10. **`ranking_basis` added.** A required public text (1–200 printable ASCII characters) naming
    what the rank counts, so the forbidden-signal refusal has something to read. The contract
    cannot check that the basis is true.
11. **Forbidden-signal terms.** Whole words, case-insensitive; a word is a run of ASCII letters and
    digits, so spaces, `_`, `-` and `.` separate words. Words: likes, liked, follower(s), vote(s),
    voted, voting, voter(s), upvote(s), upvoted, subscription(s), subscriber(s), premium, boost(s),
    boosted, boosting. Phrases: like count(s), paid plan(s), paid tier(s), paid member(s), paid
    membership(s), membership tier(s), membership plan(s). Not refused on purpose: "like",
    "following", "paid" and "membership" alone (common words; "paid bookings" is a fair basis).
    Not included: sponsored, promoted, featured, tips. The role key is scanned too, so a real role
    key containing a term (e.g. one starting `premium_`) would be refused.
12. **Role key.** Shape only: lowercase snake_case, 2–48 characters, starting with a letter, no
    double or trailing `_`. The list of 45 keys is not on the page and is not checked on chain.
13. **Codes.** scope, area_code and season: 1–32 characters of letters, digits, `-`, `_`, `.`,
    stored and compared in lowercase (`GB-LND` = `gb-lnd`).
14. **Band input.** `TOP_1`, `TOP_3`, `TOP_5`, `TOP_10`, case-insensitive and trimmed.
15. **Final.** No revocation or correction of a verdict.

## Not verified

GenVM execution, deploy and finality on a network, and any write on Studionet (direct mode runs the
SDK in CPython); SnapLink's real ranking snapshots and that each person is counted once inside
them; that a ranking's stated basis is true; the 45 role keys.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing
merged; nothing pushed to `main`; no other repository touched; nothing in Base44. The pull request
and the owner's page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/recognition_plaque_award.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/recognition_plaque_award.py --fees ($fees -replace '"','\"')
```

The deploying account becomes the only issuer of verdicts: deploy from the account SnapLink will
use. Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_rules`
(shows the issuer) and `genlayer call <address> get_verdict_count`.

VERDICT: DRAFTED — lint clean, 14 direct-mode tests pass (no mocks needed), 6 of 6 planted mutations
caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN. The PR stays
a draft until the owner deploys and the post-deploy Studionet check (transaction report and a view
read) passes.
