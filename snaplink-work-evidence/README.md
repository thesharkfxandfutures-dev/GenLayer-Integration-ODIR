# SnapLink work-evidence assessment (GenLayer, Studionet demo)

**Demo and testnet only.** This runs one narrow GenLayer assessment and reads it back from the network. It is kept apart from the simulated GenLayer screens in the SnapLink app. It does not replace them, and it never reuses their token IDs.

## The question it answers

> Does this submitted deliverable meet these stated requirements?

The answer is one of `MEETS_REQUIREMENTS`, `DOES_NOT_MEET_REQUIREMENTS` or `INSUFFICIENT_EVIDENCE`. The contract also stores which requirements were met.

It does **not** say who made the work, that the work is "non-AI", or that a person is verified. Those are different claims and need different evidence.

## How a case is bound

1. Every evidence item carries the SHA-256 of its exact UTF-8 text.
2. The whole case is bound by `sha256(canonical({policy, brief, evidence}))`, with policy `snaplink-work-evidence/1`.
3. The contract recomputes both. If either fingerprint doesn't match, the case is refused before any model runs, and nothing is stored.
4. Each validator asks its own LLM. Every answer is reduced to a canonical `{met:{R1..Rn: bool}, outcome}`, and `strict_eq` requires the validators to agree on that decision. The outcome comes from the per-requirement answers, never from what the model says the outcome is. A malformed answer counts as not met (it fails closed).
5. Only the owner, or submitters the owner allows, can submit. Resubmitting the same case is refused (`DUPLICATE_SUBMISSION`). A different bundle under the same case ID is also refused (`CONFLICTING_RESUBMISSION`).
6. A decided transaction is not the same as a successful assessment. A transaction can be `ACCEPTED` with execution `ERROR` (a refused case), or `SUCCESS` with `DOES_NOT_MEET_REQUIREMENTS`.

Evidence sent to the contract is **public calldata**. Only fictional, consented fixtures may be used. Never use payslips, client contracts or personal data.

## Files

| Path | Runs where | Purpose |
|---|---|---|
| `contracts/snaplink_work_evidence.py` | GenVM | The contract |
| `snaplink-work-evidence/scripts/evidence_lib.py` | Your machine | Off-chain copy of the binding rules (same digests, tested) |
| `snaplink-work-evidence/scripts/prepare_evidence.py` | Your machine | Prints the exact envelope for a case (`--tamper` to break it) |
| `snaplink-work-evidence/scripts/run_live_demo.py` | Your machine → Studionet | Deploys, submits four scenarios, reads back, writes a receipt. **Signs** (throwaway demo key only) |
| `snaplink-work-evidence/scripts/verify_receipt.py` | Your machine → Studionet | Independent readback: re-reads every transaction and case, and recomputes digests from the fixtures |
| `snaplink-work-evidence/tests/test_work_evidence.py` | Local | 13 deterministic tests on the real SDK (`gltest` direct mode), with the LLM mocked |
| `snaplink-work-evidence/tests/test_live_roundtrip.py` | Studionet | Opt-in live round trip (`GENLAYER_LIVE=1`) |
| `fixtures/snaplink-work-evidence/demo_cases.json` | — | Fictional brief, plus matching and non-matching evidence |
| `fixtures/snaplink-work-evidence/receipts/*.json` | — | Recorded live runs (public data only) |

## Run it (meeting script)

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r snaplink-work-evidence/requirements.txt

# 1 · deterministic tests on the real SDK (LLM mocked)
python -m pytest snaplink-work-evidence/tests -q

# 2 · contract lint and validation against the GenVM SDK
genvm-lint check contracts/snaplink_work_evidence.py

# 3 · live: deploy and run the four scenarios on Studionet (about 1–2 minutes)
python snaplink-work-evidence/scripts/run_live_demo.py --run-id meeting-$(date +%H%M)

# 4 · independent readback from the network
python snaplink-work-evidence/scripts/verify_receipt.py fixtures/snaplink-work-evidence/receipts/meeting-HHMM.json
```

The four things to show:

| Scenario | Expected on the network |
|---|---|
| matching | `ACCEPTED`, execution `SUCCESS`, stored `MEETS_REQUIREMENTS` |
| non_matching | `ACCEPTED`, execution `SUCCESS`, stored `DOES_NOT_MEET_REQUIREMENTS`: the system can refuse a claim |
| tampered (evidence changed after hashing) | `ACCEPTED`, execution `ERROR`, **nothing stored** |
| duplicate (same case again) | `ACCEPTED`, execution `ERROR`, original record unchanged |

If the live network is slow or a run is still pending, say it's pending. Then show the recorded run in `fixtures/snaplink-work-evidence/receipts/` and label it as recorded. Re-run `verify_receipt.py` on it: that reads the recorded transactions back from Studionet live.

## Network and key

- **Network:** Studionet (`https://studio.genlayer.com/api`, chain 61999), GenLayer's hosted development network. Describe it as a live development-network assessment, not a production deployment. The runner refuses any other chain ID.
- **Key:**
  - If `GENLAYER_DEMO_PRIVATE_KEY` is set, the runner uses it.
  - Otherwise it generates a throwaway key at `~/.config/snaplink-genlayer-demo/key` (`chmod 600`, outside this repository). Studionet needs no real funds.
  - Never commit a key, and never use a production wallet.
- **Pinned versions:** runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`, `genlayer-py==0.16.3`, `genlayer-test==0.29.2`, `genvm-linter==0.11.0`, Python 3.12.
  - Don't mix in Studio-dev release-candidate examples.
  - Never upgrade the runner or client to clear a transient error.

## Not yet done

- **SnapLink app integration:** a server-side status adapter, a separate live-receipt record and a "Run network assessment" panel action. This repo is the evidence layer; the app shares over later.
- **Image evidence:** the runtime accepts images, but this version takes text only.
- **Finality:** runs record the *decided* status. `--finality-wait N` records whether `FINALIZED` was observed; finality is never assumed.
- **Corroboration:** one RPC endpoint, no state proof (same limit as the D1 adapter).
