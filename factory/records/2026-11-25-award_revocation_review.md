# Factory record — award_revocation_review — 25 Nov 2026

Factory run of 25 Nov 2026, builder for contract #12 of the owner's page (table "Award contracts (one per
award type)", row 12; `factory/BACKLOG.md` item 12). Cloud workspace, genskill MCP server as the owner's
claude.ai connector. Branch `factory/award_revocation_review-2026-11-25` from `main` (`f0a4525`).
Pull request: left to the orchestrator (draft).

Owner's row, as given to the builder:

| # | Contract | Award type | What it decides | Inputs | Answer | Must refuse |
|---|---|---|---|---|---|---|
| 12 | award_revocation_review | Any award (champion seats, percentage plaques, Verified Work milestones, service medals, annual awards) | Does the stated reason justify revoking an issued award (evidence withdrawn, fraud found, work not in the role)? | award reference hash, the reason, evidence summary + hash, the award's rules version | `REVOKE` / `KEEP` + the rule relied on | a revocation of an award never issued; a second decision on the same reason |

Award-contract rules (rows 7–12) applied here: one universal contract serves every award type and every role
(the role key is an input, given when the issued award is recorded); a deterministic `FORBIDDEN_SIGNAL`
refusal when a text input carries likes, followers, votes, a paid plan / subscription / premium / membership,
or a boost (paid membership must never improve anyone's chance of an award, or of keeping one).

"An award never issued" is checked against an owner-only registry of issued award reference hashes
(`record_issued_award`). "The same reason" is the same award reference plus the same reason hash
(sha256 of the reason after ASCII lower-casing and collapsing whitespace).

## Output

| File | sha256 |
|---|---|
| `contracts/factory/award_revocation_review.py` | `8db424e99e5ffc2840c887cd4b4d30d13cd3ff335d1be0500ed880132cdc22d4` |
| `tests/factory/test_award_revocation_review.py` | `a69536fabb92215a115a9ca52ba7c77c52f7b3c6ba7ad436e32d7e28675e2d2e` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`;
line 2 blank, line 3 `from genlayer import *`, then the doc block that documents the constructor and says
calldata is public data only. Class `AwardRevocationReview`, constructor `AwardRevocationReview()` takes no
arguments; the deploying address becomes the owner (SnapLink's issuer account).

Methods (all writes owner only):
- `register_rules(rules_version, rules_text)` → `{rules_version, rules_sha256}`. The contract stores the text,
  checks it for forbidden signals and does not allow a version to change.
- `record_issued_award(award_ref_sha256, role_key, award_type, rules_version)` →
  `{award_ref_sha256, role_key, award_type, rules_version, status}`. `award_type` is one of `CHAMPION_SEAT`,
  `RECOGNITION_PLAQUE`, `VERIFIED_WORK_MILESTONE`, `SERVICE_MEDAL` or `ANNUAL_AWARD`. The status starts as
  `ISSUED`.
- `review_revocation(award_ref_sha256, rules_version, reason, evidence_summary, evidence_sha256)` →
  `{decision_key, award_ref_sha256, verdict, rule_quote, explanation, rules_version, reason_sha256,
  award_status}`. The rules text comes from the registry (only the version is an input, as the row says), and
  `rules_version` must be the version the award was issued under. A `REVOKE` sets the award to `REVOKED`; a
  `KEEP` leaves it `ISSUED`.
- Views: `get_owner`, `get_rules(rules_version)`, `get_rules_count`, `get_rules_version(i)`,
  `get_award_status(award_ref_sha256)` (`NOT_ISSUED` / `ISSUED` / `REVOKED`), `get_award(award_ref_sha256)`,
  `get_award_count`, `get_award_ref(i)`, `get_decision(award_ref_sha256, reason)`,
  `get_decision_by_key(decision_key)`, `get_decision_count`, `get_decision_key(i)`, `get_forbidden_signals`.

`decision_key` = `award_ref_sha256|reason_sha256`. The model sees the rules text, the reason, the evidence
summary, the role key and the award type. It does not see the award reference hash or the evidence hash.

MCP server: `genskill` claude.ai connector; tools `mcp__genskill__genlayer_*`, resource
`genlayer://guide/contract-rules`. The repo pins `genskill-mcp@2.3.3` in `.mcp.json`; the connector did not
report its own version.

## Answers and refusals (exact text) and the test for each

| Case | Exact text / word | Test |
|---|---|---|
| Answer | `REVOKE` (fraud found, rule R2 quoted; award status becomes `REVOKED`) | `test_revoke_when_fraud_is_found` |
| Answer | `KEEP` (complaint about taste, rule R4 quoted; award stays `ISSUED`) | `test_keep_when_the_reason_is_a_complaint_about_taste` |
| One contract for every award type and role | all five award types, five roles | `test_one_contract_serves_every_award_type_and_role` |
| **Must refuse: revocation of an award never issued** | `[EXPECTED] AWARD_NOT_ISSUED: no issued award is recorded under this award reference` | `test_refuses_a_revocation_of_an_award_never_issued` (empty registry; another award recorded; upper-case hash; `get_award` refuses, `get_award_status` = `NOT_ISSUED`; accepted once recorded) |
| **Must refuse: a second decision on the same reason** | `[EXPECTED] REASON_ALREADY_DECIDED: this award already has a decision on the same reason` | `test_refuses_a_second_decision_on_the_same_reason` (after `KEEP`; same reason with other case, spacing, summary and evidence hash; after `REVOKE` too; another reason or another award passes) |
| Award rule: forbidden signal in the reason or summary | `[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid plan, subscription, premium or membership, or a boost` | `test_refuses_a_reason_or_summary_that_carries_a_forbidden_signal` (13 texts, each as reason and as summary: likes, LIKED, Followers, votes, voting, Upvotes, paid plan, Subscription, premium, membership, Pro plan, #Boosted, boost; whole words only: "devoted", "likeness" pass) |
| Award rule: forbidden signal in the rules text | same text | `test_refuses_rules_text_that_carries_a_forbidden_signal` (likes, follower count, vote, paid plan, Premium, Membership, Boosted, Subscribers) |
| New reason on a revoked award | `[EXPECTED] AWARD_ALREADY_REVOKED: this award is already revoked` | `test_refuses_a_new_reason_on_a_revoked_award` |
| Rules version | `[EXPECTED] UNKNOWN_RULES_VERSION: no award rules are registered under this version`; `[EXPECTED] RULES_VERSION_MISMATCH: rules_version is not the rules version this award was issued under` | `test_refuses_an_unknown_or_mismatched_rules_version` (and the model gets the v2 text for a v2 award) |
| Hashes | `[EXPECTED] BAD_AWARD_REF: award_ref_sha256 must be 64 hexadecimal characters`; `[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters` | `test_refuses_malformed_hashes` (upper-case accepted, stored lower-case) |
| Issued-award registry | `[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters from a-z 0-9 _`; `[EXPECTED] BAD_AWARD_TYPE: award_type must be CHAMPION_SEAT, RECOGNITION_PLAQUE, VERIFIED_WORK_MILESTONE, SERVICE_MEDAL or ANNUAL_AWARD`; `[EXPECTED] AWARD_ALREADY_RECORDED: this award reference is already recorded as issued` | `test_record_issued_award_refusals` |
| Reason / summary | `[EXPECTED] EMPTY_REASON: reason must not be empty`; `[EXPECTED] REASON_TOO_LONG: reason must be at most 1000 characters`; `[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty`; `[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters` | `test_refuses_empty_or_long_reasons_and_summaries` (limits 1000 / 2000 accepted) |
| Owner only | `[EXPECTED] OWNER_ONLY: only the contract owner can register rules, record an issued award or request a revocation review` | `test_only_the_owner_writes` |
| Rules registry and reads | `[EXPECTED] RULES_VERSION_EXISTS: a registered rules version cannot be changed`; `[EXPECTED] BAD_RULES_VERSION: rules_version must be 1 to 32 characters from A-Z a-z 0-9 . _ -`; `[EXPECTED] BAD_RULES_TEXT: rules_text must be 1 to 8000 characters and not blank`; `[EXPECTED] BAD_INDEX: nothing at this index`; `[EXPECTED] NO_DECISION: no decision is stored for this award and reason` | `test_rules_registry` |
| Malformed model answer | `[LLM_ERROR] the model did not return a JSON object`; `[LLM_ERROR] the model returned no verdict of REVOKE or KEEP`; `[LLM_ERROR] the model's rule quote is not 10 to 400 characters quoted from the award rules text`; `[LLM_ERROR] the model returned no explanation` | `test_refuses_malformed_model_answers` (nothing stored; the same reason can then be retried) |
| Quote matched up to whitespace | stored quote has whitespace runs collapsed | `test_quote_is_matched_up_to_whitespace` |
| Prompt carries public inputs only | no award reference or evidence hash in the prompt; no-forbidden-signal instruction present | `test_prompt_carries_the_public_inputs_and_no_hashes` |
| Fresh contract | `get_rules_count` / `get_award_count` / `get_decision_count` = 0, `get_award_status(any)` = `NOT_ISSUED` | `test_fresh_contract_is_empty` |
| Validator agree / disagree | verdict word only; leader quote must be in the rules text | `test_validator_agrees_on_the_verdict_word_not_the_wording`, `test_validator_agrees_on_keep` |

`[LLM_ERROR] the decision result is malformed` (`ERR_DECISION_SHAPE`) is reached only inside the validator
and is tested there.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` |
| Started from the MCP scaffolds | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `AwardRevocationReview`; `genlayer_scaffold_test` template `llm-judge`. The scaffold's URL fetch was dropped (text-only judgment) and its score band replaced by the verdict word |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call from the written file; byte identity of the pasted text was not machine-checked. The contract was not changed afterwards (sha256 above) |
| Tests pass: 20 passed | OBSERVED | `python3 -m pytest tests/factory/test_award_revocation_review.py -q` → `20 passed in 0.58s`; Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; LLM mocked (no web read in this contract) |
| One test per answer word, must-refuse case and award rule | OBSERVED | table above |
| The tests can fail | OBSERVED | 13 mutations, each caught and then reverted: `AWARD_NOT_ISSUED` check removed → 1 failed; `REASON_ALREADY_DECIDED` check removed → 1 failed; reason hash not case-folded → 2 failed; `FORBIDDEN_SIGNAL` not checked on the reason → 1 failed; not checked on the rules text → 1 failed; validator always agrees → 2 failed; validator stops checking the leader's quote → 1 failed; `AWARD_ALREADY_REVOKED` check removed → 1 failed; `KEEP` also revokes → 2 failed; `RULES_VERSION_MISMATCH` check removed → 1 failed; `liked` dropped from the terms → 1 failed; whole-word match replaced by substring match → 1 failed; evidence hash sent to the model → 1 failed. The script restored the original bytes after each run; the contract sha256 was `8db424e9…dc22d4` before and after |
| Validators agree on the verdict word, not the wording | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with another quote and explanation → `True`; `KEEP` vs `REVOKE` → `False`; forged leader quote not in the rules → `False`; quote under 10 characters → `False`; bad word → `False`; missing explanation → `False`; non-dict leader → `False`; validator's own model answer malformed → `False`; leader error → `False`; `KEEP` vs `KEEP` with different quotes → `True` |
| Hashes are not sent to the model; the prompt forbids weighing paid or popularity signals | OBSERVED (direct mode) | `test_prompt_carries_the_public_inputs_and_no_hashes`: the only LLM mock requires the instruction "Never weigh likes, followers, votes", the rules text, award type, summary, reason and role, and requires that neither the award reference hash nor the evidence hash appears |
| Studionet reachable | OBSERVED | `genlayer_network_status` (25 Nov ~05:37 UTC): endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f`, block `0x6b06740e`, not syncing |
| Schema on Studionet | NOT_RUN | `genlayer_get_contract_schema` (25 Nov ~05:38 UTC) answered `unsupported_contract_rpc` (`endpoint_mode` `studionet-hosted`, upstream `Internal database error (code -32603)`). The probe sent a 12-line minimal contract (sha256 `b2e4a015…2d97`), not this contract's source; the refusal is endpoint-wide (same answer as earlier probes for every contract). This is an endpoint limitation, not a contract fault |
| Deploy simulation on Studionet loads and constructs | OBSERVED | `genlayer_call_contract` type `deploy` (gen_call simulation; nothing signed or sent), `from`/`to` zero address, `data` from `glcall.mjs deploy contracts/factory/award_revocation_review.py '[]'` (genlayer-js 0.18.4; 54,886 hex chars, sha256 of the hex `59c4113316fc75be401c4c5e632c3d5e6d5021bef46e01cfcc5a5d7d5f4e0560`, prefix `0xf96b2fb96b2a`, suffix `0600`) → `"00"`, decoded `null` (the constructor returned). The hex was pasted into the call by hand from three read chunks. Byte identity was not machine-checked, but the RLP lengths had to match for the node to decode it |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked |
| Runs on GenVM; deploys and finalizes; consensus on a network | NOT_RUN | not until the owner deploys |

## Attempts

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings, 0 info | — |
| Tests | — | NOT_RUN (tooling) | the session's permission classifier gave no verdict on 8 calls in a row (Bash and the MCP network status), so pytest could not be started. Under rule 5d this is a tooling failure and does not count as an attempt | none (retried after the classifier recovered; contract and tests unchanged) |
| Tests | 1 | pass | `20 passed in 0.58s` | — |
| Mutations | 1 | 13 of 13 caught | listed above | — |
| Studionet reachability | 1 | pass | `genlayer_network_status` above | — |
| Studionet schema | 1 | NOT_RUN | `unsupported_contract_rpc` on hosted Studionet (minimal probe contract) | not resent |
| Studionet deploy simulation | 1 | pass | `"00"` → `null` | — |

## Open questions for the owner

- **Who records issued awards.** The row needs "an award never issued" to be refusable, so the contract keeps
  an owner-only registry: SnapLink calls `record_issued_award(award_ref_sha256, role_key, award_type,
  rules_version)` when it issues an award. The award reference is a sha256 of SnapLink's award record id,
  not the id itself. The other award contracts (rows 7–11) are separate deployments, and this contract does
  not read them. Should a later version accept an operator list besides the owner?
- **Rules version is the award's version.** Only the version is passed, as the row lists, and the text is read
  from the registry. A review must use the version the award was issued under (`RULES_VERSION_MISMATCH`
  otherwise). If the owner wants revocations judged under the newest rules, that is a one-line change.
- **Same reason.** The same award reference plus sha256 of the reason after ASCII lower-casing and collapsing
  whitespace. A reworded reason is a new reason and can be decided once. A `KEEP` locks that reason too. After
  a `REVOKE`, any further reason gets `AWARD_ALREADY_REVOKED` (an extra refusal the row did not ask for).
  An `[LLM_ERROR]` stores nothing, so it can be retried.
- **Forbidden-signal filter vs fraud reasons.** The filter is whole-word and literal. Terms (also returned by
  `get_forbidden_signals`): likes, liked, like count(s), follower(s), follower count, vote(s), voted, voting,
  voter(s), upvote(s), upvoted, downvote(s), paid plan(s), paid tier, paid account, pro plan, subscription(s),
  subscribed, subscriber(s), premium, membership(s), boost(s), boosted, boosting. Because of this, a genuine
  fraud reason such as "bought fake followers" or "vote rigging" is refused, and must be worded without those
  words (e.g. "bought fake audience accounts"). Rules text cannot say "votes never count" either. The list
  is wider than row 7's: it adds `liked`, `upvote`, `pro plan`, `subscribed` and bare `membership`, which the
  row 7 verifier noted as gaps. Bare "like" and "paid" are not terms, so "did not like the colours" and
  "paid on time" pass.
- **Role key** is checked by shape only (lowercase snake_case, 2–40 characters), because the 45 SnapLink role
  keys are not on the page.
- **What the model sees.** The rules text, the reason, the evidence summary, the role key and the award type.
  It cannot check that the summary is true, and the private evidence stays off chain (hash only).
- **Limits.** Rules text ≤ 8000 characters, reason ≤ 1000 (whitespace collapsed), evidence summary ≤ 2000
  (trimmed).
- **On chain in the clear.** The rules text, reason, evidence summary, role key and hashes are public calldata
  and storage. Reasons and summaries must not carry names, emails or private evidence; the contract cannot
  stop that.

## Not verified

The real model's judgment; GenVM execution and multi-validator consensus on a network (direct mode runs
the SDK in CPython); any write method on Studionet; the Studionet schema (the endpoint refuses it).

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or sent; `genlayer_submit_raw_transaction`
and `genlayer_raw_rpc` not called; no `genlayer deploy`, `write`, `account` or `keygen`; nothing merged;
nothing pushed to `main`; no other repository touched; nothing in Base44. The pull request and the owner's
page are left to the orchestrator.

## Deploy steps for the owner (Studionet, by hand, from a checkout of this branch)

```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
genlayer deploy --contract contracts/factory/award_revocation_review.py --fees "$(genlayer estimate-fees --fee-preset standard --json)"
```

PowerShell 5.1:

```powershell
$fees = genlayer estimate-fees --fee-preset standard --json
genlayer deploy --contract contracts/factory/award_revocation_review.py --fees ($fees -replace '"','\"')
```

Read-only checks afterwards: `genlayer receipt <tx hash>`; `genlayer call <address> get_owner`;
`genlayer call <address> get_award_count` (expected `0` on a fresh contract).

VERDICT: DRAFTED — lint clean (first attempt), 20 direct-mode tests pass with the model mocked, 13 of 13
planted mutations caught, Studionet reachable and the deploy simulation constructs (`00`); schema NOT_RUN
(endpoint). The PR stays a draft until the owner deploys and the post-deploy Studionet check (transaction
report and a view read) passes.
