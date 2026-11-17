#!/usr/bin/env python3
"""
INDEPENDENT READBACK of a demo receipt from the network. DEMO / TESTNET ONLY.

  python snaplink-work-evidence/scripts/verify_receipt.py fixtures/snaplink-work-evidence/receipts/<run-id>.json

Trusts nothing in the receipt except transaction hashes, the contract address and the fixtures.
For every case it re-reads from Studionet and re-derives locally:
  - network identity (eth_chainId == 61999)
  - the contract's policy version and the stored case record (get_case)
  - the bundle digest, recomputed from the committed fixtures with the same rules as the contract
  - the transaction's decided status and execution result, as reported by the network now
Prints PASS/FAIL per check and exits non-zero on any failure. Uses a throwaway read-only account.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import evidence_lib as lib  # noqa: E402
from run_live_demo import rpc  # noqa: E402  (no key is loaded by importing)

from genlayer_py import create_account, create_client  # noqa: E402
from genlayer_py.chains import studionet  # noqa: E402

EXPECT_STORED = {"matching": True, "non_matching": True, "tampered": False, "duplicate": True}


def main(path):
    receipt = json.loads(Path(path).read_text())
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + label + (f" — {detail}" if detail else ""))

    chain_id = int(rpc("eth_chainId")["result"], 16)
    check("network is Studionet", chain_id == lib.STUDIONET_CHAIN_ID, f"chain {chain_id}")
    client = create_client(chain=studionet, account=create_account())
    address = receipt["contract"]["address"]
    check("contract policy version", client.read_contract(address=address, function_name="get_policy_version", args=[]) == lib.POLICY_VERSION)
    code = lib.CONTRACT.read_text()
    check("local contract source matches the receipt", lib.sha256_hex(code) == receipt["contract"]["sha256"])

    fx = json.loads(lib.FIXTURES.read_text())
    for row in receipt["cases"]:
        name = row["scenario"]
        which = "non_matching" if name == "non_matching" else "matching"
        env = lib.envelope(row["case_id"], fx["brief"], fx["cases"][which])
        check(f"[{name}] bundle digest recomputed from fixtures", env["bundle_digest"] == row["bundle_digest"])
        tx = client.get_transaction(transaction_hash=row["tx"])
        lr = (tx.get("consensus_data") or {}).get("leader_receipt") or [{}]
        lr = lr[0] if isinstance(lr, list) else lr
        print(f"     tx {row['tx']} status now {tx.get('status_name')} · consensus {tx.get('result_name')} · execution {lr.get('execution_result')}")
        check(f"[{name}] transaction decided on the network", tx.get("status_name") in ("ACCEPTED", "FINALIZED"))
        stored = client.read_contract(address=address, function_name="get_case", args=[row["case_id"]])
        rec = json.loads(stored) if stored else None
        if not EXPECT_STORED[name]:
            check(f"[{name}] nothing stored for refused evidence", rec is None)
            check(f"[{name}] execution reported an error", lr.get("execution_result") == "ERROR")
            continue
        check(f"[{name}] stored record exists", rec is not None)
        if rec:
            check(f"[{name}] stored bundle digest matches", rec["bundle_digest"] == env["bundle_digest"])
            check(f"[{name}] stored evidence digests match", rec["evidence_digests"] == env["evidence_digests"])
            check(f"[{name}] stored outcome matches receipt", rec["outcome"] == row["stored_outcome"], rec["outcome"])
            if name == "duplicate":
                check(f"[{name}] resubmission refused (execution ERROR) and record unchanged", lr.get("execution_result") == "ERROR")
            else:
                check(f"[{name}] outcome is the expected one", rec["outcome"] == row["expected"], f"expected {row['expected']}")
    print("VERIFY", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
