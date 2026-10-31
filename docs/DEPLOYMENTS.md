# Deployments and what each one establishes

| Field | Value | Status |
|---|---|---|
| Network | GenLayer Studionet | owner-supplied |
| Chain ID | 61999 | **UNVERIFIED** against https://docs.genlayer.com/developers/networks |
| Contract | `0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646` | owner-supplied; explorer: https://explorer-studio.genlayer.com/address/0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646 |
| Source candidate | `contracts/odir_review_gate.py`, sha256 `f27688d0bf79f65900e4c7145909ed7b90d2a220ac8b987ed2906c94ffde5341` | the newest of three local downloads (`odir_review_gate.py`, `(1)`, `(2)`, 302/302/318 lines). Which one is deployed has **not** been confirmed byte-for-byte |
| Runner dependency | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (header of the source) | pinned in source; an earlier "latest" runner was rejected during the prototype |

## Owner-demonstrated D1 lifecycle (prototype evidence, not production assurance)

Supplied transaction and state outputs showed, in order: `register_slice('D1', …)` with one
criterion "Explain who owns inventory"; `submit_evidence` (attempt 1); `review_submission` returning
PASS with a source quote; `approve_submission` by the reviewer account; `consume_approval` by the
executor account; `can_consume('D1')` afterwards returning `false`.

What this establishes: the happy path works on Studionet with role-separated accounts and the
one-time consume.

What it does not establish: denial coverage (wrong roles, duplicate consume, dependency blocks,
pause), behaviour under malformed model output in every path, any repository candidate, any local
execution, any host containment.

Known events from the same session worth keeping as test cases:
- a review returned malformed JSON before a later successful consensus (format-failure path);
- registration attempts whose transactions finalised **with an execution error** (finality is not success);
- a mock that accepted `Address` strings differently from the pinned runtime hid a deployment failure.

## Rules for the next deployment

1. Record the exact source sha256 and the runner id beside the new address, here, before use.
2. Treat a code change at the same address as a new trust assumption: re-run GenVM tests, decide
   whether earlier verdicts remain valid under policy.
3. Never update the runner to clear a transient provider error.
