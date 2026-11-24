# Factory record — credit_claim_verdict — 24 Nov 2026

Factory run on the owner's request in the scheduled session (cloud workspace, genskill MCP through
the owner's computer link). Branch `factory/credit_claim_verdict-2026-11-24` from `main` `f0a4525`.
Backlog item 3.
Pull request: https://github.com/thesharkfxandfutures-dev/GenLayer-Integration-ODIR/pull/4 (draft, label `contract-factory`, created by this run)

The scheduled run stopped first on the two-PR cap (#2, #3 open). The owner then wrote in the
session: "use studio net for testing and mpc as i cant acsess bradbury test net till 27th i want to
keep the process rolling", and on being asked about the cap: "no cap continue but you must do the
check on stdio net also". This run follows that; the matching `RUN.md` change is a separate pull
request.

## Output

| File | sha256 |
|---|---|
| `contracts/factory/credit_claim_verdict.py` | `d5154998faa345ae7b95a8963e92113baf6675243f41b564148ebe064bad3611` |
| `tests/factory/test_credit_claim_verdict.py` | `58a7ecf84d796daa2190b2237c29d5268a3edd6c21cdae133d927fc4e68c6a79` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
Class `CreditClaimVerdict`, constructor takes no arguments; no owner or admin role.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Stop conditions: no cap on open factory PRs (owner's instruction above), a `todo` item without a pull request, `genlayer_*` tools loaded | OBSERVED | GitHub `list_pull_requests` (state open) returned #2 and #3, both `contract-factory`; tool search listed the genskill tools. `main`'s `RUN.md` still states the two-PR stop until the owner merges the process change |
| Items 1 and 2 are already drafted, so item 3 is next | OBSERVED | `main` shows both as `todo` because PRs #2 and #3 are unmerged; their branches set them to `drafted`. This run took the first `todo` item without a pull request |
| MCP server is `genskill-mcp@2.3.3` | CLAIMED | pinned in `.mcp.json` and named in the run prompt; the tool responses do not report a version |
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (pinned runner, no comment under the header, `while` not `for`, no `sorted`/`lambda`, GenLayer storage types, web pages that change go through a custom validator agreeing on a stable field, error prefixes) |
| GenLayer docs consulted | NOT_RUN | `genlayer_search_docs`: "Unable to load GenLayer documentation from https://docs.genlayer.com/full-documentation.txt: fetch failed" |
| Started from the MCP scaffold | OBSERVED | `genlayer_scaffold_contract` template `web-oracle`, name `CreditClaimVerdict`. Its `strict_eq` JSON read was replaced by `run_nondet_unsafe` with a custom validator, because a post page is not byte-stable between fetches |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call; that the pasted text and the file are byte-identical was not machine-checked |
| Tests started from the MCP test scaffold | OBSERVED | `genlayer_scaffold_test` template `web-oracle` (`direct_vm.mock_web`, `direct_deploy`, `direct_alice`); written to `tests/factory/` as `RUN.md` asks, with `mock_llm` added |
| Tests pass: 16 passed, 0 failed | OBSERVED | `pytest tests/factory/test_credit_claim_verdict.py -v` in the cloud workspace: Python 3.13.18, pytest 9.1.1, genlayer-test **0.29.2** direct mode, GenVM `v0.2.12` extract (runner `py-genlayer:1jb45aa8…`, `py-lib-genlayer-std:11rhn002…`) |
| genlayer-test 0.30.0 cannot load these contracts here | OBSERVED | with 0.30.0 (what `pip install genlayer-test` gave on 24 Nov) all 16 tests here, and all 10 of PR #2's previously passing tests, failed at contract load: `DecodingError: unexpected end of memory` in `genlayer/_internal/msg.py`, after "could not resolve latest GenVM version (HTTP Error 403: Forbidden)" and a GenVM `v0.6.0-rc16` bundle. Pinned back to 0.29.2: PR #2 10 passed, this file 16 passed. Cause not isolated beyond that |
| The tests can fail | OBSERVED | seven mutations of the contract, each run then reverted (file sha256 unchanged afterwards): creator check removed from `confirm_claim` → 1 failed; media hash never reserved → 2 failed; verdict ignores confirmation → 2 failed; validator ignores `names_handle` → 2 failed; whole-handle boundary removed → 1 failed; `<script>` text kept → 1 failed; leader's quote need not be on the validator's page → 1 failed |
| One test per decision outcome and per must-refuse case | OBSERVED | `VERIFIED`; `NOT_VERIFIED` with `CREATOR_NOT_CONFIRMED` (then re-decided to `VERIFIED` after confirmation), `POST_DOES_NOT_NAME_HANDLE` (handle absent, no model call; handle only mentioned, model says false), `POST_UNAVAILABLE` + `CREATOR_NOT_CONFIRMED` together; `NOT_THE_CREATOR` (the claimant and a third party); `MEDIA_ALREADY_VERIFIED` (new claims for another creator or handle, and a rival claim opened earlier refused at confirm and decide); plus `ALREADY_VERIFIED`, `DUPLICATE_CLAIM`, `ALREADY_CONFIRMED`, HTTP 5xx refusal, malformed inputs and model answers, entity and meta-tag reading, the claim id formula |
| Validators agree on `post_available` and `names_handle` | OBSERVED (direct mode) | `direct_vm.run_validator()`: same answers with another quote and reason → `True`; validator's model says false → `False`; validator gets 404 → `False`; forged leader quote not on the page → `False`; leader quote that does not name the handle → `False`; malformed leader result → `False`; leader error → `False`; no handle on either copy → `True`; validator's copy now credits the handle → `False`. Real multi-validator consensus: NOT_RUN |
| **Studionet check through the MCP server** | **NOT_RUN** | the server is configured for `https://studio.genlayer.com/api` (`genlayer_probe_endpoint_capabilities`), but from the owner's computer every request failed: `genlayer_network_status` "fetch failed" (three tries across the session), every capability probe "fetch failed"; `genlayer_get_contract_schema` on a 12-line probe contract → `unsupported_contract_rpc`, "Hosted Studionet does not currently provide reliable contract RPC methods like gen_getContractState/gen_getContractCode/gen_getContractSchema", upstream error "fetch failed"; `genlayer_call_contract` type `deploy` (simulation: nothing signed or sent) → "fetch failed". This workspace cannot reach Studionet either: the egress proxy refused `studio.genlayer.com` (403, policy). **The pull request stays a draft until the Studionet check has passed** |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked; no real model has read a post |
| Real post pages read as expected | NOT_RUN | only hand-written HTML was used. Pages that build the post with JavaScript (several large social sites) may serve little or no post text to `gl.nondet.web.get` |
| Runs on GenVM; loads, deploys and finalizes on a network | NOT_RUN | not until the owner deploys. Direct mode runs the SDK in CPython, not the GenVM interpreter, and has no consensus, gas or storage encoding |
| `genlayer network set studionet` selects Studionet | OBSERVED (static) | `genlayer@0.40.0` package unpacked and read, not run: `network set [network]` accepts built-in aliases; `BUILT_IN_NETWORKS` includes `studionet` (`https://studio.genlayer.com/api`, chain 61999). The old `RUN.md` form `genlayer network <name>` is not a command in this version |
| Studionet is gasless (no faucet) | **CONTRADICTED** | the MCP rules resource says "studionet is gasless", but the owner's first deploy reverted `FeeValueMustBeNonZero(1)`: Studio now refuses transactions sent with zero fees (genlayer-js PR #237, closed unmerged, describes it). Deploys need a fee estimate, see below |
| Deploy steps in the pull request | OBSERVED (owner) | the steps without fees failed; with `genlayer estimate-fees --fee-preset standard --json` passed to `--fees`, the owner's deploy succeeded (below). The PR body and `RUN.md` now carry the working steps |
| **Deployed on Studionet; constructor ran** | **OBSERVED (owner's terminal)** | owner's `genlayer deploy` (genlayer@0.40.0, Windows PowerShell 5.1) printed transaction `0xb364980e4883bf1625c40227d593372ebc4ede750ed0bcc8e68a8f7727d5763b`, contract `0xd32E01eF391E4e4faC394e0EC8aCdC242C0E5e9a`, consensus `ACCEPTED`, "Contract deployed successfully". The CLI prints that only after `assertSuccessfulExecution` accepts the receipt, which otherwise raises "decided as …; leader execution result …" (read in the package source). Source deployed: the file on this branch, by the owner's checkout; its sha256 on the owner's disk was asked for but not seen here |
| Finalized; view read answers on Studionet | NOT_RUN | status was `ACCEPTED` at the time of the paste; `genlayer receipt` and `genlayer call … get_claim_count` not yet run |
| Studionet check through the MCP server (after deploy) | NOT_RUN | `genlayer_get_transaction_status`, `genlayer_get_transaction_receipt` and `genlayer_run_transaction_report` on the deploy hash: all "fetch failed". The owner's own CLI on the same computer reached Studionet, so the failure is specific to the MCP server process |

## Attempts (owner's rule: up to three, each retry after a change backed by the failed attempt's evidence)

| Check | Attempt | Result | Evidence | Change before the next attempt |
|---|---|---|---|---|
| Lint | 1 | pass | 0 errors, 0 warnings | — |
| Tests | 1 | 16 failed | `DecodingError: unexpected end of memory` at contract load under genlayer-test 0.30.0; PR #2's 10 previously passing tests failed the same way | pin genlayer-test 0.29.2 (tooling, not the contract); PR #2's tests then 10 passed |
| Tests | 2 | 16 failed | `AttributeError: 'bytes' object has no attribute 'as_hex'`: the 0.29.2 fixtures hand back raw bytes for test addresses | test helper `creator_hex` accepts bytes (test file only; contract unchanged) |
| Tests | 3 | 16 passed | — | — |
| Owner's deploy | 1 | reverted `FeeValueMustBeNonZero(1)`, tx `0x7c30f936d82d837c1514f55b53bd452935ad3ea80ece1297895673e244d189fb` | CLI 0.40.0 sends zero fees when none are given; Studio refuses that before the contract runs | tooling, not the contract: pass a Studio fee estimate (`estimate-fees --fee-preset standard --json` → `--fees`) |
| Owner's deploy | 2 | `ACCEPTED`, execution successful | tx `0xb364980e…5763b`, contract `0xd32E01eF…5e9a` | — |
| MCP after deploy | 1–3 | `fetch failed` | status, receipt, transaction report on the deploy hash | none: server-side network problem, not the contract |
| Studionet (before deploy) | 1–3 | `fetch failed` | `genlayer_network_status` three times across the session, plus capability probes, schema and deploy simulation | none: the cause is the network path from the owner's computer, not the contract, so the contract is not failed; NOT_RUN and the PR stays a draft |

## Choices the owner may want to change

- **Who does what.** Anyone opens a claim naming the media hash, the credited handle, the
  creator's address and a post URL. Only that creator address can confirm it. Anyone can ask
  for a decision.
- **Re-deciding.** `NOT_VERIFIED` is not final: once the missing condition is met (the creator
  confirms, the post is edited), anyone can call `decide_claim` again. `VERIFIED` is final and
  reserves the media hash for that creator and handle.
- **No admin.** There is no owner role, so a wrong `VERIFIED` cannot be revoked. If revocation
  is wanted, it needs an owner and a revoke method.
- **Handle matching.** Case is ignored and a leading `@` is optional; the handle must appear as a
  whole handle (`@alice_shoots` does not match `@alice_shoots2` or `@alice_shoots.studio`, but does
  match `@alice_shoots.` at the end of a sentence). If it does not appear at all, no model is asked.
- **Reading the post.** `gl.nondet.web.get` plus a small HTML reducer (tags and scripts out,
  `<meta content>` kept, entities decoded). `gl.nondet.web.render` would read pages built in the
  browser, but it is not in the MCP rules sheet, so this draft does not use it.
- **HTTP outcomes.** 3xx/4xx is `POST_UNAVAILABLE` (stored, can be re-decided); 5xx refuses with
  `POST_FETCH_FAILED` and stores nothing.
- **What is not checked.** The contract never sees the media, so it cannot tell whether the post
  shows this file. Handles, creator addresses and URLs are stored on-chain in the clear.

## Not done in this run

No key held, generated or asked for; nothing signed, deployed or submitted;
`genlayer_submit_raw_transaction` and `genlayer_raw_rpc` not called; no `genlayer` CLI command
run (the package was unpacked and read only); nothing merged; nothing pushed to `main`; nothing in
Base44. The one deploy simulation (`gen_call`, read-only) failed before reaching the network. The
pull request was opened and labelled with the GitHub MCP tools (REST), because this workspace's
`gh` CLI is limited to search.

VERDICT: DRAFTED (draft PR) — lint clean and 16 direct-mode tests pass with mocked web and model;
deployed by the owner on Studionet with a successful constructor (`ACCEPTED`); finality, a view
read and the MCP server's own Studionet check are still outstanding.

## Follow-up Studionet check — 24 Nov 2026, 21:46–21:50 UTC (scheduled factory run)

Through the genskill MCP server as the owner's claude.ai connector (cloud session; not the
computer link). Read-only RPC only: nothing signed or sent.

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Reachability | 1 | pass | OBSERVED | `genlayer_network_status`: endpoint `https://studio.genlayer.com/api`, health `healthy`, chain id `0xf22f` (61999), block `0x6b06059e`, not syncing |
| Transaction report | 1 | tool error | NOT_RUN | `genlayer_run_transaction_report` (with the contract address): `Internal database error (code -32603)`; `genlayer_get_transaction_receipt`: `Method not found: gen_getTransactionReceipt` on hosted Studionet. Tooling, not the contract |
| Transaction report | 2 | pass | OBSERVED | `genlayer_get_transaction_status` → `FINALIZED` (code 7). `genlayer_inspect_transaction` on `0xb364980e4883bf1625c40227d593372ebc4ede750ed0bcc8e68a8f7727d5763b`: status `FINALIZED`, `result_name` `MAJORITY_AGREE`, `txExecutionResultName` `FINISHED_WITH_RETURN`, leader `SUCCESS`, five initial validators, votes 4 `agree` + 1 `idle` (cancelled after quorum), `isAppealable` false, finality phase `final`; `contract_address` `0xd32E01eF391E4e4faC394e0EC8aCdC242C0E5e9a` |
| Deployed code = this branch | 1 | match | OBSERVED | the transaction's `contract_code` (base64) decoded to 24,550 bytes with sha256 `d5154998faa345ae7b95a8963e92113baf6675243f41b564148ebe064bad3611`, identical to `contracts/factory/credit_claim_verdict.py` on this branch |
| View read | 1 | pass | OBSERVED | `genlayer_call_contract` type `read`, `to` `0xd32E01eF…5e9a`, method `get_claim_count`, no args (calldata encoded as genlayer-js 0.18.4 `readContract` does) → `01`, which decodes to `0`: the deployed contract answers and holds no claims yet |
| Schema | 1 | not supported | NOT_RUN | `genlayer_get_contract_snapshot` / `genlayer_get_contract_interface`: "not supported on studionet-hosted"; hosted Studionet has no `gen_getContractSchema`. Superseded here by the finalized deploy and the view read |

Studionet check: **passed** (deploy finalized with majority agreement, deployed code matches this
branch, a view method answers). Not covered: any write method on Studionet, and the model's
judgment on a real post.
