"""
Off-chain twin of the contract's binding rules (contracts/snaplink_work_evidence.py).
Same canonical JSON, same SHA-256, same clean shapes — tests pin that both produce identical digests.
Runs in your dev/server environment, never inside GenVM.
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "contracts" / "snaplink_work_evidence.py"
FIXTURES = REPO / "fixtures" / "snaplink-work-evidence" / "demo_cases.json"
RECEIPTS = REPO / "fixtures" / "snaplink-work-evidence" / "receipts"

POLICY_VERSION = "snaplink-work-evidence/1"
OUTCOMES = ("MEETS_REQUIREMENTS", "DOES_NOT_MEET_REQUIREMENTS", "INSUFFICIENT_EVIDENCE")
STUDIONET_RPC = "https://studio.genlayer.com/api"
STUDIONET_CHAIN_ID = 61999


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_brief(brief: dict) -> dict:
    return {"title": brief["title"], "requirements": [{"id": r["id"], "text": r["text"]} for r in brief["requirements"]]}


def clean_evidence(items: list) -> dict:
    """items: [{id, label, content}] → adds kind and sha256 of the exact content bytes (UTF-8)."""
    return {"items": [{"id": it["id"], "kind": "text", "label": it["label"], "content": it["content"], "sha256": sha256_hex(it["content"])} for it in items]}


def bundle_digest_of(brief: dict, evidence: dict) -> str:
    return sha256_hex(canonical({"policy": POLICY_VERSION, "brief": brief, "evidence": evidence}))


def envelope(case_id: str, brief: dict, evidence_items: list) -> dict:
    b = clean_brief(brief)
    e = clean_evidence(evidence_items)
    return {
        "case_id": case_id,
        "policy_version": POLICY_VERSION,
        "brief_json": canonical(b),
        "evidence_json": canonical(e),
        "bundle_digest": bundle_digest_of(b, e),
        "evidence_digests": [it["sha256"] for it in e["items"]],
    }
