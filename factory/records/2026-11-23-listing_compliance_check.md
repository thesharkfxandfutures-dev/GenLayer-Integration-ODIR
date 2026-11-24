# Factory record — listing_compliance_check — 23 Nov 2026

Scheduled factory run (cloud workspace, genskill MCP through the owner's computer link).
Branch `factory/listing_compliance_check-2026-11-23` from `main` `f0a4525`. Backlog item 2.
Pull request: https://github.com/thesharkfxandfutures-dev/GenLayer-Integration-ODIR/pull/3 (label `contract-factory`, created by this run)

## Output

| File | sha256 |
|---|---|
| `contracts/factory/listing_compliance_check.py` | `bdb6f49b931598c2015d5a593c0f06df29064ce0fa0adacb407ecc29673ed65f` |
| `tests/factory/test_listing_compliance_check.py` | `42edab86a110b84ea71e46b5023e4ba7f7b1dd4c3179c22ac6e4ffcc031da593` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
Class `ListingComplianceCheck`, constructor takes no arguments; the deployer becomes the owner.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Stop conditions clear: 1 open `contract-factory` pull request (fewer than two), a `todo` item without a pull request, `genlayer_*` tools loaded | OBSERVED | GitHub `list_pull_requests` (state open) returned only #2 (`factory/work_evidence_review-2026-11-23`, label `contract-factory`); tool search listed the genskill tools |
| Item 1 is already drafted, so item 2 is next | OBSERVED | `main` still shows item 1 as `todo` because PR #2 is unmerged; that PR's branch sets it to `drafted (PR #2)`. Drafting it again would duplicate PR #2, so this run took the first `todo` item without a pull request |
| MCP server is `genskill-mcp@2.3.3` | CLAIMED | pinned in `.mcp.json` and named in the run prompt; the tool responses do not report a version |
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (pinned runner, no comment under the header, `while` not `for`, no `sorted`/`lambda`, GenLayer storage types, validators agree on a stable field, `[EXPECTED]`/`[LLM_ERROR]` prefixes) |
| GenLayer docs consulted | NOT_RUN | `genlayer_search_docs` and `genlayer_read_doc` both failed: "Unable to load GenLayer documentation from https://docs.genlayer.com/full-documentation.txt: fetch failed". The contract follows the rules resource, the scaffold and the pattern already in PR #2 |
| Started from the MCP scaffold | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `ListingComplianceCheck`; its web fetch and 0–100 score were replaced by the item's listing inputs, published rulebooks and the `COMPLIANT`/`HOLD` verdict |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call; that the pasted text and the file are byte-identical was not machine-checked |
| Tests started from the MCP test scaffold | OBSERVED | `genlayer_scaffold_test` template `llm-judge` (fixtures `direct_vm`, `direct_deploy`, `direct_alice`, `mock_llm`); written to `tests/factory/` as `RUN.md` asks, not the scaffold's `tests/direct/` |
| Tests pass: 12 passed, 0 failed | OBSERVED | `pytest tests/factory/test_listing_compliance_check.py -v` in the cloud workspace: Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode; genlayer-test fetched the genvm `v0.2.12` release and extracted the pinned runner `py-genlayer:1jb45aa8…` and `py-lib-genlayer-std:11rhn002…` |
| The tests can fail | OBSERVED | four mutations of the contract, each run then reverted (file sha256 unchanged afterwards): validator accepts any HOLD rule → 1 failed; no duplicate-listing check → 1 failed; limit check `>=` instead of `>` → 1 failed; model's rule ids never collected → 4 failed |
| One test per decision outcome and per must-refuse case | OBSERVED | `COMPLIANT`; `HOLD` naming a baseline rule, a rulebook rule (id matched ignoring case) and `FRAUD-SIGNAL`; `UNKNOWN_RULEBOOK_VERSION`; `LISTING_TOO_LONG` (one over refused, exactly at the limit accepted); `DUPLICATE_LISTING` (same caller, other caller, newer rulebook); plus empty fields, every `publish_rulebook` refusal, seven malformed model answers and the lookups |
| Validators agree on the verdict word and, for HOLD, the named rule | OBSERVED (direct mode) | `direct_vm.run_validator()`: same verdict and the leader's rule in the validator's list → `True`; validator's list without that rule → `False`; other verdict → `False`; forged leader quote → `False`; invented rule id → `False`; leader error → `False`. Real multi-validator consensus: NOT_RUN |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked; no real model has read a listing |
| The baseline rule texts state UK law correctly | NOT_RUN | written for this draft as a screening prompt; not reviewed by anyone qualified in UK law. A `HOLD` is a reason for a person to look, not a legal finding |
| Runs on GenVM; loads, deploys and finalizes on a network | NOT_RUN | not until the owner deploys. Direct mode runs the SDK in CPython, not the GenVM interpreter, and has no consensus, gas or storage encoding |
| Deploy steps in the pull request | CLAIMED | `factory/RUN.md` §5 |

## Choices the owner may want to change

- **Rulebooks live in the contract.** The owner publishes each version once with
  `publish_rulebook(version, rules_json, max_listing_chars)`; a version cannot be changed or
  removed. `check_listing` takes the version, not the rulebook text, so every verdict points at
  a fixed, hashed rulebook (`rules_sha256` is stored with it).
- **Baseline rules.** `UK-LAW`, `PROHIBITED-CATEGORY` (adult content, drugs, offensive
  memorabilia) and `FRAUD-SIGNAL` are fixed in the source and apply to every check; a rulebook
  adds rules but cannot rename or replace these.
- **The stated limit** is the rulebook's `max_listing_chars` (100–8000), counted over title,
  description and category together, in Python characters.
- **Same listing hash.** The hash covers title, description and category only, not the rulebook
  version, so a listing with a verdict under `v1` cannot get a second one under `v2`. Any edit,
  even a trailing space, is a new listing. If re-checks under a new rulebook are wanted, the
  version would have to join the hash.
- **Consensus.** Validators must give the same verdict word; for `HOLD`, their own list of broken
  rules must include the rule the leader named. A `COMPLIANT`/`HOLD` split means no consensus and
  no stored verdict.
- **Open access.** Anyone can ask for a check against a published version; only the owner
  publishes rulebooks. Listing text is stored on-chain in the clear.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or submitted;
`genlayer_submit_raw_transaction` and `genlayer_raw_rpc` not called; no `genlayer` CLI command
run; nothing merged; nothing pushed to `main`; nothing in Base44. The pull request was opened
and labelled with the GitHub MCP tools (REST), because this workspace's `gh` CLI is limited to
search.

VERDICT: DRAFTED — lint clean and direct-mode tests pass with a mocked model; unproven on GenVM
and on any network until the owner deploys.

## Follow-up Studionet check — 24 Nov 2026 (scheduled factory run)

Pre-deploy check: no deploy transaction hash has been posted on PR #3 yet. Contract on this
branch: `contracts/factory/listing_compliance_check.py`, sha256
`bdb6f49b931598c2015d5a593c0f06df29064ce0fa0adacb407ecc29673ed65f` (unchanged; contract and
tests not touched). Read-only RPC through the genskill MCP server only; nothing signed or sent.

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Reachability (`genlayer_network_status`) | 1 | Studionet reachable, 21:52 UTC | OBSERVED | endpoint `https://studio.genlayer.com/api`, chainId `0xf22f`, blockNumber `0x6b060734`, `syncing: false`, health `healthy` (genvm, database, consensus, llm_providers healthy) |
| Schema (`genlayer_get_contract_schema`) | — | not sent for this contract; recorded once for the run | NOT_RUN (endpoint limitation; no contract change) | the same endpoint refused the operation itself at 21:57 UTC (PR #2 contract): `kind: unsupported_contract_rpc`, "Contract RPC operation \"get_contract_schema\" is not supported on this endpoint.", `endpoint_mode: studionet-hosted`, `upstream_error: Internal database error (code -32603)`; the refusal is per endpoint, not per contract |
| Deploy simulation (`genlayer_call_contract`, type `deploy`, from/to `0x0000000000000000000000000000000000000000`, constructor args `[]`) | 1 | constructor ran and returned, 21:55 UTC | OBSERVED | raw returned value `"00"`, decoded `null` (constructor returned, no error; in the simulation the owner is the zero sender). Data: genlayer-js 0.18.4 deployContract encoding of this branch file, 41,168 hex chars incl. `0x`, regenerated from the branch file and byte-identical to the orchestrator's precomputed hex |

Result: passed — reachability and deploy simulation OBSERVED; schema NOT_RUN because hosted
Studionet does not provide it. The post-deploy part (transaction report and a view read) waits
for the owner to deploy and post the transaction hash on the PR.
