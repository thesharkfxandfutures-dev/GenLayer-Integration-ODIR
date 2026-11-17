"""
LIVE round trip on Studionet — opt-in, kept apart from the mocked tests.

  GENLAYER_LIVE=1 python -m pytest snaplink-work-evidence/tests/test_live_roundtrip.py -q

Deploys a fresh contract, runs the four demo scenarios through real validators and LLMs, then
independently reads everything back. Model outcomes are real, so a FAIL here can be the network,
the model or the brief; the receipt and verifier output say which.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.environ.get("GENLAYER_LIVE") != "1", reason="live network test; set GENLAYER_LIVE=1")


def test_live_round_trip(tmp_path):
    run_id = "pytest-live"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_live_demo.py"), "--run-id", run_id], check=True, timeout=900)
    receipt = ROOT.parent / "fixtures" / "snaplink-work-evidence" / "receipts" / f"{run_id}.json"
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_receipt.py"), str(receipt)], capture_output=True, text=True, timeout=300)
    print(out.stdout)
    assert out.returncode == 0, out.stdout + out.stderr
