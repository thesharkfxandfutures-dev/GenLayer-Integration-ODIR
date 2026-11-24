# Factory record — work_evidence_review — 23 Nov 2026

Scheduled factory run (cloud workspace, genskill MCP through the owner's computer link).
Branch `factory/work_evidence_review-2026-11-23` from `main` `f0a4525`. Backlog item 1.
Pull request: https://github.com/thesharkfxandfutures-dev/GenLayer-Integration-ODIR/pull/2 (label `contract-factory`, created by this run)

## Output

| File | sha256 |
|---|---|
| `contracts/factory/work_evidence_review.py` | `8781026144624fe15ed2d6026fa87ddfce2f950c100de1398dfd910cd9f4ebf4` |
| `tests/factory/test_work_evidence_review.py` | `9a7d3cc1aa74a1fd45fd68cb0c3907c4df9bede56d86692689023c59ba2ade62` |

Runner (line 1 of the contract): `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
Class `WorkEvidenceReview`, constructor takes no arguments.

## Claims

| Claim | Grade | Evidence |
|---|---|---|
| Stop conditions clear: 0 open pull requests, item 1 is `todo`, `genlayer_*` tools loaded | OBSERVED | GitHub `list_pull_requests` (state open) returned `[]`; `factory/BACKLOG.md`; tool search listed the genskill tools |
| MCP server is `genskill-mcp@2.3.3` | CLAIMED | pinned in `.mcp.json` and named in the run prompt; the tool responses do not report a version |
| Contract rules read from the MCP server | OBSERVED | resource `genlayer://guide/contract-rules` (pinned runner, no comment under the header, `while` not `for`, `run_nondet_unsafe` validators agree on a stable field, `[EXPECTED]`/`[LLM_ERROR]` prefixes) |
| GenLayer docs consulted | NOT_RUN | `genlayer_search_docs` and `genlayer_read_doc` both failed: "Unable to load GenLayer documentation from https://docs.genlayer.com/full-documentation.txt: fetch failed". The contract follows the rules resource and the scaffold only |
| Started from the MCP scaffold | OBSERVED | `genlayer_scaffold_contract` template `llm-judge`, name `WorkEvidenceReview`; its web fetch and 0–100 score were replaced by the backlog item's text inputs and verdict word |
| Lint: no errors | OBSERVED | `genlayer_lint_contract` on the full source: `ok: true`, 0 errors, 0 warnings, 0 info, no findings, first attempt. The source was pasted into the tool call; that the pasted text and the file are byte-identical was not machine-checked |
| Tests pass: 10 passed, 0 failed | OBSERVED | `pytest tests/factory/test_work_evidence_review.py -v` in the cloud workspace: Python 3.13.18, pytest 9.1.1, genlayer-test 0.29.2 direct mode, SDK from the genvm `v0.2.12` release with the pinned runner `py-genlayer:1jb45aa8…` extracted |
| The tests can fail | OBSERVED | three mutations of the contract, each run then reverted (file sha256 unchanged afterwards): validator always `True`, no brief-and-delivery duplicate check, `check_evidence` never refusing — each gave 1 failed, 9 passed |
| One test per decision outcome and per must-refuse case | OBSERVED | `MEETS_REQUIREMENTS`, `DOES_NOT_MEET_REQUIREMENTS`; `EVIDENCE_HASH_MISMATCH`, `DUPLICATE_SUBMISSION` (same hash; same brief and delivery), `EMPTY_BRIEF`; plus malformed hash, empty delivery, a model quote not in the delivery, a model answer with no verdict word, and the validator's verdict comparison |
| Validators agree on the verdict word only | OBSERVED (direct mode) | `direct_vm.run_validator()`: same word with a different quote → `True`; other word → `False`; forged leader quote → `False`; leader error → `False`. Real multi-validator consensus: NOT_RUN |
| The model's judgment is sound | NOT_RUN | every LLM call in the tests is mocked; no real model has read a brief |
| Runs on GenVM; loads, deploys and finalizes on a network | NOT_RUN | not until the owner deploys. Direct mode runs the SDK in CPython, not the GenVM interpreter, and has no consensus, gas or storage encoding |
| `check_evidence` keeps the evidence text out of transactions and state | CLAIMED | it is a `@gl.public.view` (a `gen_call` read) and writes nothing; the RPC node queried still receives the text |
| Deploy steps in the pull request | CLAIMED | `factory/RUN.md` §5 |

## Choices the owner may want to change

- **Hash check.** The private evidence stays off-chain, so `review_work` takes only its
  sha256. "Refuse a hash that does not match the supplied evidence text" is the view
  `check_evidence(case_id, evidence)`: it refuses with `EVIDENCE_HASH_MISMATCH` and writes
  nothing. If the evidence should be checked inside the reviewing transaction instead, it
  would have to be sent on-chain, which makes it public.
- **Same case twice.** `DUPLICATE_SUBMISSION` covers an evidence hash already decided and the
  same brief-and-delivery pair already decided (so a fresh hash does not buy a second verdict).
- **Open access.** No owner, no roles, no pause; anyone can submit a case.
- **Limits.** Brief 4000 characters, delivery 8000, quote 300, reason 400 (truncated).

## Not done in this run

No key held, nothing signed, deployed or submitted; `genlayer_submit_raw_transaction` and
`genlayer_raw_rpc` not called; no `genlayer` CLI command run; nothing merged; nothing pushed to
`main`.

VERDICT: DRAFTED — lint clean and direct-mode tests pass with a mocked model; unproven on GenVM
and on any network until the owner deploys.

## Follow-up Studionet check — 24 Nov 2026 (scheduled factory run)

Pre-deploy check: no deploy transaction hash has been posted on PR #2 yet. Contract on this
branch: `contracts/factory/work_evidence_review.py`, sha256
`8781026144624fe15ed2d6026fa87ddfce2f950c100de1398dfd910cd9f4ebf4` (unchanged; contract and
tests not touched). Read-only RPC through the genskill MCP server only; nothing signed or sent.

| Check | Attempt | Result | Grade | Evidence |
|---|---|---|---|---|
| Reachability (`genlayer_network_status`) | 1 | Studionet reachable, 21:52 UTC | OBSERVED | endpoint `https://studio.genlayer.com/api`, chainId `0xf22f`, blockNumber `0x6b060734`, `syncing: false`, health `healthy` (genvm, database, consensus, llm_providers healthy) |
| Schema (`genlayer_get_contract_schema`, `base64 -w0` of the contract) | 1 | refused by the endpoint, 21:57 UTC | NOT_RUN (endpoint limitation; not retried, no contract change) | `kind: unsupported_contract_rpc`, "Contract RPC operation \"get_contract_schema\" is not supported on this endpoint.", `endpoint_mode: studionet-hosted`, `upstream_error: Internal database error (code -32603)` |
| Deploy simulation (`genlayer_call_contract`, type `deploy`, from/to `0x0000000000000000000000000000000000000000`, constructor args `[]`) | 1 | constructor ran and returned, 21:53 UTC | OBSERVED | raw returned value `"00"`, decoded `null` (constructor returned, no error). Data: genlayer-js 0.18.4 deployContract encoding of this branch file, 21,160 hex chars incl. `0x`, regenerated from the branch file and byte-identical to the orchestrator's precomputed hex |

Result: passed — reachability and deploy simulation OBSERVED; schema NOT_RUN because hosted
Studionet does not provide it. The post-deploy part (transaction report and a view read) waits
for the owner to deploy and post the transaction hash on the PR.
