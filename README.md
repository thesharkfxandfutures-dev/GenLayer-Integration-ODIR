# GenLayer Integration for ODIR

The public half of connecting ODIR (a private orchestration swarm) to a GenLayer Intelligent
Contract that gives an evidence-bound semantic review. This repository holds everything that may
be public and nothing that may not: the contract, the shared record schemas, synthetic fixtures,
and a read-only adapter CLI. It contains no keys, signs nothing, submits nothing and issues no
permits. The private swarm, the Base44 app source, host logs and authority material live elsewhere.

Read `docs/INTEGRATION.md` for how the repositories, Base44 and the contract are joined.

## Layout

```
contracts/odir_review_gate.py     the ODIR Review Gate contract (text review, roles, approve, one-time consume)
schema/review-package.v1.json     the candidate-bound package ODIR exports (odir-review-package/1)
schema/observation.v1.json        one observation of the contract's state (odir-genlayer-observation/1)
adapter/                          genlayer-odir CLI: package verify · observe · reconcile · fixtures
fixtures/d1/                      synthetic D1 package, contract replies, CPython canonical-encoding vectors
config/studionet.example.json     network, address, code identity, permitted view methods
docs/INTEGRATION.md               the linkage, the CLI flow, exit codes, Base44 records, increments
docs/DEPLOYMENTS.md               what is deployed where and what each deployment establishes
```

## Quick start

```bash
cd adapter
npm test                         # 24 local Node tests: canonical bytes, package binding, parsing, reconciliation
npm run fixtures                 # D1 fixture end to end → CONSISTENT, verdict PASS, authority none

node bin/genlayer-odir.mjs package verify ../fixtures/d1/package.json
node bin/genlayer-odir.mjs observe --slice D1 --config ../fixtures/d1/config.json --from-file ../fixtures/d1/get_slice.reviewed_pass.json > obs.json
node bin/genlayer-odir.mjs reconcile --package ../fixtures/d1/package.json --observation obs.json --config ../fixtures/d1/config.json
```

Node 20 or later, no dependencies.

## Assurance level, stated plainly

| Claim | Level |
|---|---|
| Contract lifecycle works on Studionet | owner-demonstrated once (D1); see `docs/DEPLOYMENTS.md` |
| Adapter logic refuses what it should | 24 local unit tests, deterministic paths only |
| Node and Python hash the same bytes | fixture vectors computed in CPython, checked in Node |
| Network reads | not implemented; `--rpc` exits 3 BLOCKED_ENVIRONMENT |
| Submission, signing, receipts | not implemented (R08) |
| GenVM denial tests | not written |
| Any authority over ODIR's host | none, by design |

A `PASS` from the contract is a reviewed opinion about approved public text. It becomes permission
to do anything only inside ODIR, after ODIR's own checks, under ODIR's own policy.

## Licence

Not yet chosen. Until a licence file exists, all rights reserved by the repository owner.
