# Contract factory — one run

What a factory run does, step by step. The scheduled task (every hour) follows this file; you
can also run it yourself in Claude Code from this repository ("run the contract factory").
The `genskill` MCP server (`.mcp.json`, `genskill-mcp@2.3.3`) writes and checks the contracts.

**The factory never signs, deploys, holds or asks for a key, calls a write method, submits a
transaction, merges, or pushes to `main`.** `.claude/settings.json` denies the MCP server's
`genlayer_submit_raw_transaction` and `genlayer_raw_rpc` tools and the CLI's deploy and write
commands. The owner signs and deploys by hand. Read-only RPC through the MCP server is allowed
(network status, transaction status and receipts, `gen_call` reads and deploy *simulations*):
nothing is signed or sent.

**Network: Studionet** (`studionet`, `https://studio.genlayer.com/api`, chain 61999, gasless),
the owner's choice on 24 Nov 2026 while Bradbury is out of reach (until 27 Nov). To go back,
change this paragraph and §6 to `testnet-bradbury` and restore the faucet line there.

## Owner's rules (24 Nov 2026)

- **No cap** on open `contract-factory` pull requests: a run drafts the next item even while
  earlier ones wait for review.
- **Every contract gets a Studionet check** through the MCP server (§4). A pull request whose
  check has not passed stays a **draft**.
- **Three attempts.** Lint, tests and the Studionet check each get at most three attempts. A
  retry follows a change backed by the failed attempt's evidence (the lint finding, the failing
  assertion, the error text or receipt), and the record lists every attempt with its result,
  evidence and change. After the third failed attempt caused by the contract, the contract
  **fails** (§5). Failures of the network or the tooling (`fetch failed`, HTTP 5xx, timeouts, a
  broken test package) are retried without a contract change and never fail a contract: the
  check is graded NOT_RUN and the pull request stays a draft.

## 0. Start of run (check first; stopping is a normal outcome)

1. The `genskill` MCP tools are not available in this session → stop and say so. Do not write a
   contract without them; the point of the factory is that the MCP server's rules and lint apply.
2. **Follow-ups.** For each open `contract-factory` pull request whose record does not show a
   passed Studionet check, run §4 (three attempts). Passed → add the result to that pull
   request's record on its branch and mark a draft ready for review. Failed because of the
   contract → fix on its branch with evidence, re-lint, re-test, up to the three attempts, then §5
   if it still fails. Network still unreachable → leave it as it is, one line in the report.
3. **Next item.** The first item marked `todo` in `factory/BACKLOG.md` that has no open
   `contract-factory` pull request. An item's status changes on its pull request's branch, so
   `main` shows `todo` until that pull request is merged; an item with an open pull request is
   already drafted. None → stop: "backlog empty" (after the follow-ups).

## 1. Branch

From `main`: `factory/<slug>-<YYYY-MM-DD>` for the item chosen in §0.3.

## 2. Write the contract (MCP)

1. Read the MCP resource `genlayer://guide/contract-rules`. Use `genlayer_search_docs` /
   `genlayer_read_doc` for anything the item needs (equivalence principles, web access, storage).
2. `genlayer_scaffold_contract` with the nearest template (`llm-judge` for verdicts,
   `web-oracle` when a public URL is read, `storage` otherwise).
3. Write `contracts/factory/<slug>.py` to the item's inputs, decision and must-refuse cases.
   Pinned runner header, no comment line directly under it, constructor documented in the
   module docstring, every refusal a `gl.vm.UserError` with exact text.
4. `genlayer_lint_contract` on the full source. Fix and re-lint until it reports no errors,
   within the three attempts. Keep the final lint output.

## 3. Tests

1. `genlayer_scaffold_test` for the template; write `tests/factory/test_<slug>.py` with one test
   per decision outcome and one per must-refuse case. Mock web and LLM calls so the tests are
   deterministic.
2. Run them: `pip install genlayer-test==0.29.2 pytest` then
   `pytest tests/factory/test_<slug>.py`. Pinned because genlayer-test 0.30.0 failed to load any
   contract in the cloud workspace on 24 Nov 2026 (`DecodingError: unexpected end of memory`;
   PR #2's passing tests failed the same way), while 0.29.2 passed. Record the result honestly:
   `PASS`, `FAIL` (fix it within the three attempts, or say what fails) or `NOT_RUN` (why).
3. Check that the tests can fail: break a few of the contract's rules one at a time, run, revert,
   and confirm the file's sha256 is unchanged afterwards.

## 4. Studionet check (MCP, read-only)

1. Reachability: `genlayer_network_status` (chain id 61999 and a block number) or
   `genlayer_probe_endpoint_capabilities`.
2. Before the owner deploys: `genlayer_get_contract_schema` on the base64 source (Studionet's
   GenVM loads the code and lists its methods), and a deploy simulation with
   `genlayer_call_contract` type `deploy` (calldata from `genlayer_plan_contract_action`,
   action `deploy`). On 24 Nov 2026 the server reported schema reads as unsupported on hosted
   Studionet; record whatever it answers.
3. After the owner deploys and posts the transaction hash and address on the pull request:
   `genlayer_run_transaction_report` on the hash (FINALIZED, and
   `leader_receipt[0].execution_result` a success: a deploy can finalize with a failed
   constructor), then `genlayer_call_contract` type `read` of one view method.
4. Passed: the schema lists the contract's public methods and the deploy simulation succeeds,
   or step 3 passes. Grade each step OBSERVED or NOT_RUN with the exact answer or error.

## 5. Record

1. In `factory/BACKLOG.md` set the item to `drafted (PR #n)` once the pull request exists, or
   `failed (PR #n)` after the third contract-caused failure.
2. Write `factory/records/<YYYY-MM-DD>-<slug>.md`:
   - source sha256 (`sha256sum contracts/factory/<slug>.py`) and the runner id from its header;
   - MCP server and version; lint result; test result; Studionet check result;
   - an attempts table: check, attempt, result, evidence, change before the next attempt;
   - every claim graded OBSERVED / CLAIMED / NOT_RUN;
   - what is **not** verified (it has not run on GenVM or a network until the owner deploys).
3. A failed contract still gets its pull request, as a draft titled `FAILED: …`, so the owner
   can read the evidence; its record ends `VERDICT: FAILED` with the three attempts. The next
   run moves on to the next item. The owner can set it back to `todo`.

## 6. Pull request

Push the branch and open a pull request to `main` labelled `contract-factory` (create the label
if it is missing), as a **draft** unless the Studionet check has passed. The body has these
parts:

**What it decides**: two or three sentences from the backlog item.

**Studionet check**: passed, or NOT_RUN with the error, and why the pull request is a draft.

**Deploy and sign (owner, by hand)**
```bash
npm install -g genlayer@0.40.0
genlayer network set studionet
# Studionet is gasless: no faucet. Use your own CLI account; the factory never touches keys.
genlayer deploy --contract contracts/factory/<slug>.py
```
Then write the address and transaction into `docs/DEPLOYMENTS.md` (source sha256 and runner id
beside it), set the backlog item to `deployed studionet <address>`, and post the transaction
hash and address on the pull request for §4.3.

**GenLayer Points submission (owner)**: Builder → *Contract Deployed*: the deployment
transaction or contract address, the explorer link, and this pull request's URL; one or two
sentences on what the contract decides. One submission per contract; stewards score
complexity, impact, quality and effort. Whether the Portal accepts a Studionet deployment has
not been checked; if it wants a testnet one, redeploy on Bradbury
(`genlayer network set testnet-bradbury`, fund the account at
https://testnet-faucet.genlayer.foundation/ first) and submit that.

## 7. Report

End the run with one line: the pull request link (saying draft or failed), the follow-ups
done, or the stop condition met.
