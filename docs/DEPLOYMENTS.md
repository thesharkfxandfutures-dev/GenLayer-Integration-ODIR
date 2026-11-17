# Deployments and what each one establishes

| Field | Value | Status |
|---|---|---|
| Network | GenLayer Studionet | confirmed by the pinned client's chain definition (`genlayer-js@1.1.8`, `studionet.id`) |
| Chain ID | 61999 | **confirmed** against the client's definition; still cross-check https://docs.genlayer.com/developers/networks when the client is upgraded |
| RPC | `https://studio.genlayer.com/api` | confirmed by the client's definition; one endpoint, no corroboration |
| Contract | `0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646` | owner-supplied; explorer: https://explorer-studio.genlayer.com/address/0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646 |
| Source candidate | `contracts/odir_review_gate.py`, sha256 `f27688d0bf79f65900e4c7145909ed7b90d2a220ac8b987ed2906c94ffde5341` | the newest of three local downloads (302/302/318 lines). **Claimed** code identity: whether the deployed bytes equal this file has not been confirmed |
| Runner dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (header of the source) | pinned in source; an earlier "latest" runner was rejected during the prototype |

## Live observation, 2026-10-31 (adapter, read-only)

Read through `genlayer-odir observe --slice D1 --config config/studionet.example.json --rpc`
with `genlayer-js@1.1.8`, state selection `latest-final`, in under two seconds. Recorded as
`fixtures/d1/get_slice.live.2026-10-31.json` (raw reply) and
`fixtures/d1/observation.live.2026-10-31.json` (observation record).

| What the contract reported | Value |
|---|---|
| slice / attempt / status | `D1` / 1 / `CONSUMED` |
| scope | "Check my inventory design" |
| criterion | "Explain who owns inventory" |
| review | `PASS`, criterion 0 `MET`, quote "Each inventory record has one owner, identified by a unique account ID." |
| builder / reviewer / executor | `0x72B1…daEd` / `0x53f7…c1Eb` / `0x1A73…616C` (full values in the fixture) |
| approved_by / consumed_by | the reviewer address / the executor address |
| evidence_sha256 | `b2f9fb94bfb5ca90b193e3f193fd4688d1afce24dd5b40af2fcd79be3ae5809c` |
| task_sha256 | `bf341710c4e1aee13fd3b3c14db26a1d8f2db71206bee5317f6c6dcde12853b2` |
| raw reply sha256 | `c983dfc13b17b9e3dcffb817e11d4b8cb52dfc756d64c54591f636fdfd3f0daa` |
| paused / predecessor_approved | false / true |

What this establishes:
- The recorded D1 lifecycle (register, submit, review PASS, approve, consume) is what the contract
  holds at `latest-final`, read by this adapter rather than supplied by hand.
- The adapter's canonical encoding reproduces the `task_sha256` and `criteria_sha256` the deployed
  contract computed, and `sha256(evidence)` equals the stored `evidence_sha256`
  (`adapter/test/live-fixture.test.js`). So Node and the deployed Python agree byte for byte on
  the shared hashes, not only Node and a local CPython.
- A reconstructed package with the real evidence text reconciles `CONSISTENT` (status `CONSUMED`);
  the synthetic fixture package reconciles `INTEGRITY_MISMATCH` against the same state.

What it does not establish: the deployed code identity (only the source candidate's hash is
known), denial coverage, behaviour under malformed model output, any repository candidate, any
local execution, any host containment. One endpoint was read; nothing corroborated it.

Negative paths exercised live the same day: a config naming chain 4221 is refused before any
request (exit 5, `configuration_failure`); an unknown slice returns the contract's execution
failure (exit 3, `execution_error`), classified apart from an outage.

## Owner-demonstrated D1 lifecycle (prototype evidence, not production assurance)

Supplied transaction and state outputs showed, in order: `register_slice('D1', …)` with one
criterion "Explain who owns inventory"; `submit_evidence` (attempt 1); `review_submission` returning
PASS with a source quote; `approve_submission` by the reviewer account; `consume_approval` by the
executor account; `can_consume('D1')` afterwards returning `false`. The live observation above is
consistent with every step.

Known events from the same session worth keeping as test cases:
- a review returned malformed JSON before a later successful consensus (format-failure path);
- registration attempts whose transactions finalised **with an execution error** (finality is not success);
- a mock that accepted `Address` strings differently from the pinned runtime hid a deployment failure.

## Rules for the next deployment

1. Record the exact source sha256 and the runner id beside the new address, here, before use.
2. Treat a code change at the same address as a new trust assumption: re-run the GenVM cases in
   `docs/GENVM-TESTS.md`, decide whether earlier verdicts remain valid under policy.
3. Never update the runner or the client to clear a transient provider error.
4. When `genlayer-js` is upgraded, re-run `adapter/test/rpc.test.js` and take a fresh live
   observation; the chain definition and the read semantics are part of the trust assumption.

# SnapLink work-evidence assessment — Studionet, 2026-11-17 (demo only)

| Field | Value | Status |
|---|---|---|
| Network | GenLayer Studionet, `https://studio.genlayer.com/api` | `eth_chainId` read live = `0xf22f` (61999) before any write; the runner refuses other chains |
| Contract | `0x89253affc135Ad782ba012bB19bBd2Df5C722B3e` | deployed by the runner, tx `0x2e086426df851b2325710346dd9165d376312ea34b1aa31b7f39ca2332e661bf`, `ACCEPTED` / `MAJORITY_AGREE` / `SUCCESS` |
| Source | `contracts/snaplink_work_evidence.py`, sha256 `b89a6938c2e46abb8d1897a6d9f3e86ea675a1a059c6a00b6d3b4ffd8559d91b` | the runner deployed exactly these bytes (sha recorded at deploy time equals this file); explorer confirmation not done |
| Runner dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` | same pin as `odir_review_gate.py` |
| Client | `genlayer-py==0.16.3`, Python 3.12 | pinned in `snaplink-work-evidence/requirements.txt` |
| Fixtures | `fixtures/snaplink-work-evidence/demo_cases.json`, sha256 `132f3648b3561d4cb5f32696da3ea88067576cb54ed916bc09a1c57c8a9a5edc` | fictional; public calldata |
| Submitter | `0xCA13C54FE1F3283CA211bA4FD23252d479097F51` | throwaway Studionet key, never committed |
| Receipt | `fixtures/snaplink-work-evidence/receipts/dryrun1.json`, sha256 `3c13d317c1a52b6070370466a622f556b58752f6de67efd17694897c1cec401c` | written by the runner, byte-identical copy |

| Scenario | Transaction | Network status | Execution | Stored outcome |
|---|---|---|---|---|
| matching | `0xd0dc630cb1afa44ae223a91f531ae21e1cc9810e16c5bcc5978453837b0b1bb1` | ACCEPTED, MAJORITY_AGREE, 1 round | SUCCESS | `MEETS_REQUIREMENTS` (R1–R4 met) |
| non_matching | `0x33e3cde5ce87202a53d96b30cb460604d7ac21831e635098686a90f1356fd6cb` | ACCEPTED, MAJORITY_AGREE, 1 round | SUCCESS | `DOES_NOT_MEET_REQUIREMENTS` (R1–R4 not met) |
| tampered (evidence edited after hashing) | `0xe3cfd8ae35ad091c00c166e4599dff0df7a88353c117cd3edebeaedee7ff62ab` | ACCEPTED, MAJORITY_AGREE | ERROR | nothing stored |
| duplicate (same case again) | `0x3916fc7bd863139b10ecd1f215823e2059bba8a85684fb1c92b6b334d516e0bc` | ACCEPTED, MAJORITY_AGREE | ERROR | original record unchanged |

Independent readback, 2026-11-17T12:56Z: `verify_receipt.py` run from a fresh clone of this branch (commit `d240079`)
in a separate environment re-read chain id, policy version, all four transactions and every stored case
from Studionet and recomputed every digest from the committed fixtures: **VERIFY PASS** (28 checks).
All four transactions then reported **FINALIZED** by the network (status read, not assumed); the
deploy transaction was not re-read. Log: `fixtures/snaplink-work-evidence/receipts/dryrun1.verify.txt`.

What this establishes: a SnapLink-shaped work claim was assessed by Studionet's validators and their
LLMs, they agreed on the decision, the result is stored bound to the evidence and bundle digests,
a non-matching claim was refused, and changed or repeated submissions stored nothing new.

What it does not establish: the specific refusal
reason on-chain (the receipt shows execution `ERROR`; that the reason is `EVIDENCE_HASH_MISMATCH` /
`DUPLICATE_SUBMISSION` is established by the direct-mode tests, not read from the network); model
quality beyond these two fixtures; explorer confirmation of code identity; anything about a real
person, or production.
