#!/usr/bin/env python3
"""
LIVE demo run on GenLayer STUDIONET (development network, chain 61999). DEMO / TESTNET ONLY.

  python snaplink-work-evidence/scripts/run_live_demo.py [--contract 0x...] [--finality-wait 0]

1. Checks the network really is Studionet (eth_chainId == 61999).
2. Deploys contracts/snaplink_work_evidence.py (or reuses --contract).
3. Submits four cases built from FICTIONAL fixtures:
     matching      → expect MEETS_REQUIREMENTS
     non_matching  → expect DOES_NOT_MEET_REQUIREMENTS (the system can refuse a claim)
     tampered      → evidence changed after hashing → refused (EVIDENCE_HASH_MISMATCH), nothing stored
     duplicate     → same case again → refused (DUPLICATE_SUBMISSION), record unchanged
4. Waits for each transaction to be DECIDED (ACCEPTED) on the network, then reads the stored case back.
5. Optionally waits for FINALIZED. Finality is never assumed: the receipt records the status actually observed.
6. Writes fixtures/snaplink-work-evidence/receipts/<run-id>.json (public data only — never the key).

THIS SCRIPT SIGNS AND SUBMITS — the one exception to this repository's read-only rule, allowed only for
Studionet with a throwaway demo key. Key: GENLAYER_DEMO_PRIVATE_KEY, else a throwaway key generated at
~/.config/snaplink-genlayer-demo/key (outside the repository). Studionet needs no real funds.
Never use a production wallet. Refuses to run against any chain other than 61999.
"""
import argparse
import datetime as dt
import importlib.metadata
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence_lib as lib  # noqa: E402

KEY_FILE = Path.home() / ".config" / "snaplink-genlayer-demo" / "key"


def rpc(method, params=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(lib.STUDIONET_RPC, data=body, headers={"content-type": "application/json", "user-agent": "snaplink-genlayer-demo/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def demo_account():
    from genlayer_py import create_account
    key = os.environ.get("GENLAYER_DEMO_PRIVATE_KEY")
    if not key:
        if KEY_FILE.exists():
            key = KEY_FILE.read_text().strip()
        else:
            from genlayer_py.accounts.account import generate_private_key
            key = "0x" + bytes(generate_private_key()).hex()
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            KEY_FILE.write_text(key)
            os.chmod(KEY_FILE, 0o600)
    return create_account(key)


def summarise(tx: dict) -> dict:
    leader = ((tx.get("consensus_data") or {}).get("leader_receipt") or [])
    leader = leader[0] if isinstance(leader, list) and leader else leader if isinstance(leader, dict) else {}
    return {
        "status": tx.get("status_name"),
        "consensus_result": tx.get("result_name"),
        "execution_result": leader.get("execution_result"),
        "leader_error": (leader.get("genvm_result") or {}).get("stderr") if isinstance(leader.get("genvm_result"), dict) else None,
        "rounds": tx.get("num_of_rounds"),
    }


def wait(client, tx_hash, status, retries):
    try:
        return client.wait_for_transaction_receipt(transaction_hash=tx_hash, status=status, interval=3000, retries=retries), None
    except Exception as e:  # report what was actually seen; never fake a status
        return client.get_transaction(transaction_hash=tx_hash), str(e).splitlines()[0][:300]


def main():
    from genlayer_py import create_client
    from genlayer_py.chains import studionet
    from genlayer_py.types import TransactionStatus

    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", help="reuse an already deployed contract address")
    ap.add_argument("--finality-wait", type=int, default=0, help="extra polls (3 s each) to observe FINALIZED; 0 = record decided status only")
    ap.add_argument("--run-id", default=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = ap.parse_args()

    chain_id = int(rpc("eth_chainId")["result"], 16)
    if chain_id != lib.STUDIONET_CHAIN_ID:
        sys.exit(f"Refusing: chain id {chain_id} is not Studionet {lib.STUDIONET_CHAIN_ID}")

    acct = demo_account()
    client = create_client(chain=studionet, account=acct)
    code = lib.CONTRACT.read_text()
    out = {
        "run_id": args.run_id,
        "network": {"name": "GenLayer Studionet (development network)", "rpc": lib.STUDIONET_RPC, "chain_id": chain_id},
        "environment": "DEMO / TESTNET ONLY — not production, not a verification of any real person",
        "submitter": acct.address,
        "contract": {"path": str(lib.CONTRACT.relative_to(lib.REPO)), "sha256": lib.sha256_hex(code), "policy_version": lib.POLICY_VERSION},
        "fixtures_sha256": lib.sha256_hex(lib.FIXTURES.read_text()),
        "sdk": {"genlayer_py": importlib.metadata.version("genlayer-py"), "py_genlayer_runner": code.split("py-genlayer:")[1].split('"')[0]},
        "cases": [],
    }

    if args.contract:
        address = args.contract
        out["deploy"] = {"reused": True}
    else:
        t0 = time.time()
        tx = client.deploy_contract(code=code, args=[])
        rec, err = wait(client, tx, TransactionStatus.ACCEPTED, 60)
        address = rec.get("recipient") or (rec.get("data") or {}).get("contract_address")
        out["deploy"] = {"tx": tx, **summarise(rec), "seconds": round(time.time() - t0, 1), "wait_error": err}
    out["contract"]["address"] = address
    print("contract", address)

    fx = json.loads(lib.FIXTURES.read_text())
    rid = args.run_id.lower()
    plan = [
        ("matching", lib.envelope(f"{rid}-match", fx["brief"], fx["cases"]["matching"]), None, "MEETS_REQUIREMENTS"),
        ("non_matching", lib.envelope(f"{rid}-miss", fx["brief"], fx["cases"]["non_matching"]), None, "DOES_NOT_MEET_REQUIREMENTS"),
    ]
    tampered = lib.envelope(f"{rid}-tamper", fx["brief"], fx["cases"]["matching"])
    ev = json.loads(tampered["evidence_json"])
    ev["items"][0]["content"] = ev["items"][0]["content"].replace("3000x2000", "1200x800")  # changed after hashing
    plan.append(("tampered", tampered, lib.canonical(ev), "EVIDENCE_HASH_MISMATCH"))
    plan.append(("duplicate", plan[0][1], None, "DUPLICATE_SUBMISSION"))

    for name, e, evidence_override, expected in plan:
        t0 = time.time()
        tx = client.write_contract(address=address, function_name="submit_case",
                                   args=[e["case_id"], e["brief_json"], evidence_override or e["evidence_json"], e["bundle_digest"]])
        rec, err = wait(client, tx, TransactionStatus.ACCEPTED, 100)
        stored = client.read_contract(address=address, function_name="get_case", args=[e["case_id"]])
        stored_obj = json.loads(stored) if stored else None
        row = {
            "scenario": name, "case_id": e["case_id"], "tx": tx, **summarise(rec), "seconds": round(time.time() - t0, 1), "wait_error": err,
            "bundle_digest": e["bundle_digest"], "evidence_digests": e["evidence_digests"],
            "expected": expected,
            "stored_outcome": stored_obj and stored_obj.get("outcome"),
            "stored_bundle_digest": stored_obj and stored_obj.get("bundle_digest"),
            "stored_record": stored_obj,
        }
        print(name, row["status"], row["consensus_result"], row["execution_result"], "stored:", row["stored_outcome"])
        out["cases"].append(row)

    if args.finality_wait:
        for row in out["cases"]:
            rec, err = wait(client, row["tx"], TransactionStatus.FINALIZED, args.finality_wait)
            row["later_status"] = rec.get("status_name")
            row["finality_wait_error"] = err

    out["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    lib.RECEIPTS.mkdir(parents=True, exist_ok=True)
    path = lib.RECEIPTS / f"{args.run_id}.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print("receipt", path, "sha256", lib.sha256_hex(path.read_text()))


if __name__ == "__main__":
    main()
