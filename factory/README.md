# Contract factory

An MCP server writes GenLayer Intelligent Contracts; the owner reviews, signs and deploys them.

| Who | Does |
|---|---|
| `genskill` MCP server (`genskill-mcp@2.3.3`, community, MIT) | scaffolds, lints and scaffolds tests for each contract; GenLayer docs search |
| The factory run (Claude, every hour, or on request) | re-checks open factory PRs on Studionet, takes the next `todo` in `BACKLOG.md` without an open PR, writes the contract and tests through the MCP server, checks it on Studionet through the MCP server (three attempts per check), opens a PR labelled `contract-factory` (a draft until the Studionet check passes) |
| **The owner** | reviews the PR, deploys to Studionet (Bradbury again once there is access) and **signs** with their own account, records the address, submits it to the GenLayer Points Portal |

Files: `BACKLOG.md` (the queue), `RUN.md` (what a run does), `records/` (one record per contract),
`../contracts/factory/` and `../tests/factory/` (the output).

## Boundaries

This repository keeps its rule: it holds no key, signs nothing and submits nothing. The factory
adds code for a person to review; nothing it produces runs anywhere until the owner deploys it.

- `.claude/settings.json` denies the MCP server's two sending tools
  (`genlayer_submit_raw_transaction`, `genlayer_raw_rpc`), the CLI's `deploy`, `write`, `account`
  and `keygen` commands, pushes to `main` and PR merges.
- No cap on open factory PRs (owner's decision, 24 Nov 2026): each run drafts the next item.
  A PR whose Studionet check has not passed stays a draft; a contract that fails a check three
  times, each retry after an evidence-backed change, is marked `failed` and the run moves on.
- The backlog holds contracts with a real decision to make. GenLayer Points are judged by stewards
  on complexity, impact, quality and effort, one contribution at a time, so near-duplicates are
  not worth generating.

## The MCP server, reviewed

Read statically on 2026-11-23 (`genskill-mcp@2.3.3`, `dist/`): no private-key handling, no
child processes; network use is the GenLayer docs bundle (`docs.genlayer.com`) and GenLayer RPC
endpoints (localnet, Studionet, Asimov, Bradbury). It can forward an already-signed transaction
(`genlayer_submit_raw_transaction`) and send any RPC method (`genlayer_raw_rpc`); both are denied
here. Not executed in the review environment. Re-review before raising the pinned version.

Seen in use on 2026-11-23 and 2026-11-24 (on the owner's computer, configured for Studionet
`https://studio.genlayer.com/api`): rules resource, scaffolds and lint work; every network call
fails with `fetch failed` (docs bundle, network status, capability probes, deploy simulation),
and it reports schema reads (`gen_getContractSchema`) as unsupported on hosted Studionet.
