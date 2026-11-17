#!/usr/bin/env python3
"""
Build the exact submission envelope for a case and print it as JSON (no network).

  python snaplink-work-evidence/scripts/prepare_evidence.py <case-id> matching|non_matching [--tamper]

Fingerprints every evidence item (SHA-256 of its UTF-8 text) and the whole case
(sha256 of canonical {policy, brief, evidence}) with the same rules as the contract.
--tamper changes one evidence item AFTER hashing, to show the contract refusing it.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence_lib as lib  # noqa: E402


def main(argv):
    if len(argv) < 2 or argv[1] not in ("matching", "non_matching"):
        sys.exit(__doc__)
    fx = json.loads(lib.FIXTURES.read_text())
    env = lib.envelope(argv[0], fx["brief"], fx["cases"][argv[1]])
    if "--tamper" in argv:
        ev = json.loads(env["evidence_json"])
        ev["items"][0]["content"] += " (edited after hashing)"
        env["evidence_json"] = lib.canonical(ev)
        env["tampered"] = True
    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
