# Contract factory — one run

What a factory run does, step by step. The scheduled task (every 6 hours) follows this file; you
can also run it yourself in Claude Code from this repository ("run the contract factory").
The `genskill` MCP server (`.mcp.json`, `genskill-mcp@2.3.3`) writes and checks the contracts.

**The factory never signs, deploys, holds or asks for a key, calls a write method, submits a
transaction, merges, or pushes to `main`.** `.claude/settings.json` denies the MCP server's
`genlayer_submit_raw_transaction` and `genlayer_raw_rpc` tools and the CLI's deploy and write
commands. The owner signs and deploys by hand.

## 0. Stop conditions (check first; stopping is a normal outcome)

- Two or more open pull requests labelled `contract-factory` →
  stop: "waiting for owner review". Unreviewed contracts are not stacked up.
- No item marked `todo` in `factory/BACKLOG.md` → stop: "backlog empty".
- The `genskill` MCP tools are not available in this session → stop and say so. Do not write a
  contract without them; the point of the factory is that the MCP server's rules and lint apply.

## 1. Branch

From `main`: `factory/<slug>-<YYYY-MM-DD>` for the first `todo` item.

## 2. Write the contract (MCP)

1. Read the MCP resource `genlayer://guide/contract-rules`. Use `genlayer_search_docs` /
   `genlayer_read_doc` for anything the item needs (equivalence principles, web access, storage).
2. `genlayer_scaffold_contract` with the nearest template (`llm-judge` for verdicts,
   `web-oracle` when a public URL is read, `storage` otherwise).
3. Write `contracts/factory/<slug>.py` to the item's inputs, decision and must-refuse cases.
   Pinned runner header, no comment line directly under it, constructor documented in the
   module docstring, every refusal a `gl.vm.UserError` with exact text.
4. `genlayer_lint_contract` on the full source. Fix and re-lint until it reports no errors.
   Keep the final lint output.

## 3. Tests

1. `genlayer_scaffold_test` for the template; write `tests/factory/test_<slug>.py` with one test
   per decision outcome and one per must-refuse case. Mock web and LLM calls so the tests are
   deterministic.
2. Try to run them: `pip install genlayer-test pytest` then `pytest tests/factory/test_<slug>.py`.
   Record the result honestly: `PASS`, `FAIL` (fix it, or say what fails) or `NOT_RUN` (why).

## 4. Record

1. In `factory/BACKLOG.md` set the item to `drafted (PR #n)` once the PR exists.
2. Write `factory/records/<YYYY-MM-DD>-<slug>.md`:
   - source sha256 (`sha256sum contracts/factory/<slug>.py`) and the runner id from its header;
   - MCP server and version; lint result; test result with grade OBSERVED / NOT_RUN;
   - what is **not** verified (it has not run on GenVM or a network until the owner deploys).

## 5. Pull request

Push the branch and open a PR to `main` labelled `contract-factory` (create the label if it is
missing). The body has three parts:

**What it decides** — two or three sentences from the backlog item.

**Deploy and sign (owner, by hand)**
```bash
npm install -g genlayer
genlayer network testnet-bradbury
# fund the deploying account first: https://testnet-faucet.genlayer.foundation/ (browser only)
genlayer deploy --contract contracts/factory/<slug>.py
```
Then write the address and transaction into `docs/DEPLOYMENTS.md` (source sha256 and runner id
beside it) and set the backlog item to `deployed testnet-bradbury <address>`.

**GenLayer Points submission (owner)** — Builder → *Contract Deployed*: the deployment
transaction or contract address, the testnet explorer link, and this PR's URL; one or two
sentences on what the contract decides. One submission per contract; stewards score
complexity, impact, quality and effort.

## 6. Report

End the run with one line: the PR link, or the stop condition met.
