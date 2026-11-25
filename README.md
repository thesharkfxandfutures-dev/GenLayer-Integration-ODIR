# GenLayer Integration for ODIR

The public half of connecting ODIR (a private orchestration swarm) to a GenLayer Intelligent
Contract that gives an evidence-bound semantic review. This repository holds everything that may
be public and nothing that may not: the contract, the shared record schemas, synthetic and
live-recorded fixtures, and a read-only adapter CLI. It contains no keys, signs nothing, submits
nothing and issues no permits. The private swarm, the Base44 app source, host logs and authority
material live elsewhere.

Read `docs/INTEGRATION.md` for how the repositories, Base44 and the contract are joined, and
`docs/ARCHITECTURE-TIERS.md` for the whole system in one essay.

## Layout

```
contracts/odir_review_gate.py     the ODIR Review Gate contract (text review, roles, approve, one-time consume)
schema/review-package.v1.json     the candidate-bound package ODIR exports (odir-review-package/1)
schema/observation.v1.json        one observation of the contract's state (odir-genlayer-observation/1)
adapter/                          genlayer-odir CLI: package verify · observe (file or RPC) · reconcile · fixtures
fixtures/d1/                      synthetic D1 package and replies; the live reply recorded 2026-10-31; CPython canonical vectors
config/studionet.example.json     network, address, code identity, permitted view methods
docs/INTEGRATION.md               the linkage, the CLI flow, exit codes, Base44 records, increments
docs/DEPLOYMENTS.md               what is deployed where, the live observation, what each establishes
docs/GENVM-TESTS.md               the denial and failure cases the contract must pass on the real runtime
docs/CONTRACT-V2.md               expiry, revocation and package binding: the next contract version
docs/ARCHITECTURE-TIERS.md        developer tool → team governance → enterprise platform
factory/                          contract factory: an MCP server writes contracts, the owner signs and deploys
.mcp.json · .claude/settings.json the factory's MCP server (genskill-mcp@2.3.3) and what it may not do
```

## Quick start

```bash
cd adapter
npm install                      # optional: only --rpc needs genlayer-js@1.1.8 (pinned); file mode needs nothing
npm test                         # 36 local Node tests
npm run fixtures                 # synthetic REVIEWED_PASS and live-recorded CONSUMED cases → both CONSISTENT, authority none

node bin/genlayer-odir.mjs package verify ../fixtures/d1/package.live.json
node bin/genlayer-odir.mjs observe --slice D1 --config ../config/studionet.example.json --rpc > obs.json
node bin/genlayer-odir.mjs reconcile --package ../fixtures/d1/package.live.json --observation obs.json --config ../config/studionet.example.json
```

Node 20 or later. The adapter core has no dependencies; `genlayer-js` is an optional dependency
used only by `--rpc`, loaded on demand.

## Assurance level, stated plainly

| Claim | Level |
|---|---|
| Contract lifecycle works on Studionet | owner-demonstrated once (D1); read back live by this adapter on 2026-10-31 (`docs/DEPLOYMENTS.md`) |
| Adapter logic refuses what it should | 36 local unit tests, deterministic paths only |
| Node, CPython and the deployed contract hash the same bytes | CPython vectors checked in Node; the deployed `task_sha256` and `criteria_sha256` reproduced from the live reply |
| Network reads | one configured endpoint through the pinned client, state `latest-final`; no corroboration, no state proof |
| Deployed code identity | claimed (source hash only), not confirmed |
| Submission, signing, receipts | not implemented (R08) |
| GenVM denial tests | specified in `docs/GENVM-TESTS.md`, not yet run on the real runtime |
| Any authority over ODIR's host | none, by design |

A `PASS` from the contract is a reviewed opinion about approved public text. It becomes permission
to do anything only inside ODIR, after ODIR's own checks, under ODIR's own policy.

## Licence

Not yet chosen. Until a licence file exists, all rights reserved by the repository owner.
