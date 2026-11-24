"""Direct-mode tests for contracts/factory/agreement_registry.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (storage), then written to the
owner page's row 4 (agreement_registry). The contract is deterministic (no web, no
LLM), so nothing is mocked; these tests check roles, input checks, the forward-only
state list, storage and the views, not GenVM consensus on a network.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_agreement_registry.py -v
"""
import hashlib
import json
from pathlib import Path

import pytest

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "agreement_registry.py")

AGREEMENT = hashlib.sha256(b"agreement 0001").hexdigest()
OTHER_AGREEMENT = hashlib.sha256(b"agreement 0002").hexdigest()
TERMS = hashlib.sha256(b"terms text v1").hexdigest()
ROLE_KEYS = "client:rk_7f3a91,creator:rk_0c22de"
BASE = "snaplink-uk"
TEMPLATE = "parchment-1.2"

STATES = ["PROPOSED", "ACCEPTED", "SIGNED", "ANCHORED", "CLOSED"]

ERR_UNAUTHORIZED = "[EXPECTED] UNAUTHORIZED: only the owner or the relayer may call this"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: the relayer may only append a record or move its state"
ERR_DUPLICATE_ID = "[EXPECTED] DUPLICATE_ID: an agreement with this id is already recorded"
ERR_UNKNOWN_AGREEMENT = "[EXPECTED] UNKNOWN_AGREEMENT: no agreement is recorded with this id"
ERR_UNKNOWN_STATE = "[EXPECTED] UNKNOWN_STATE: state must be one of PROPOSED, ACCEPTED, SIGNED, ANCHORED, CLOSED"
ERR_INVALID_TRANSITION = "[EXPECTED] INVALID_TRANSITION: state moves only forward"
ERR_BAD_AGREEMENT_ID = "[EXPECTED] BAD_AGREEMENT_ID: agreement id must be a sha256 hash (64 hex characters, optional 0x)"
ERR_BAD_TERMS_HASH = "[EXPECTED] BAD_TERMS_HASH: terms hash must be a sha256 hash (64 hex characters, optional 0x)"
ERR_BAD_ROLE_KEYS = "[EXPECTED] BAD_ROLE_KEYS: role keys must be 1 to 16 distinct comma-separated keys of 1 to 128 characters from A-Z a-z 0-9 _ . : -"
ERR_BAD_BASE = "[EXPECTED] BAD_BASE: base must be 1 to 128 printable ASCII characters"
ERR_BAD_TEMPLATE_VERSION = "[EXPECTED] BAD_TEMPLATE_VERSION: template version must be 1 to 32 characters from A-Z a-z 0-9 _ . -"
ERR_BAD_OUTCOME_CODE = "[EXPECTED] BAD_OUTCOME_CODE: outcome code must be 0 to 32 characters from A-Z 0-9 _"
ERR_BAD_ADDRESS = "[EXPECTED] BAD_ADDRESS: relayer must be 0x followed by 40 hex characters"
ERR_INDEX_OUT_OF_RANGE = "[EXPECTED] INDEX_OUT_OF_RANGE: no agreement at this index"


def addr_hex(address):
    """Lowercase 0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex.lower()


def refused(direct_vm, text, call):
    """The call must raise; its message must be exactly `text` (expect_revert only checks a substring)."""
    with direct_vm.expect_revert(text):
        call()
    try:
        call()
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001 - genlayer.gl.vm.UserError in direct mode
        assert type(exc).__name__ == "UserError", repr(exc)
        assert exc.message == text, exc.message
        return
    raise AssertionError("call succeeded but should have been refused: " + text)


def deploy(direct_vm, direct_deploy, direct_owner, direct_alice):
    """Owner deploys (the default sender) and sets alice as the relayer."""
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    assert contract.set_relayer(addr_hex(direct_alice)) == {"relayer": addr_hex(direct_alice)}
    return contract


def append(contract, agreement=AGREEMENT, terms=TERMS, role_keys=ROLE_KEYS, base=BASE,
           template=TEMPLATE, state="ACCEPTED", outcome=""):
    return contract.append_agreement(agreement, terms, role_keys, base, template, state, outcome)


def record(contract, agreement=AGREEMENT):
    return json.loads(contract.get_agreement(agreement))


def snapshot(contract):
    """Everything the views expose, to prove a refused call wrote nothing."""
    out = {"count": contract.get_count(), "owner": contract.get_owner(), "relayer": contract.get_relayer()}
    i = 0
    while i < out["count"]:
        agreement = contract.get_agreement_id(i)
        out[agreement] = contract.get_agreement(agreement)
        i += 1
    return out


# --- answers: stored record and forward moves ------------------------------------------

def test_deployer_is_owner_and_no_relayer_at_deploy(direct_vm, direct_deploy, direct_owner):
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    assert contract.get_owner() == addr_hex(direct_owner)
    assert contract.get_relayer() == ""
    assert contract.get_count() == 0
    assert contract.get_states() == STATES


def test_relayer_appends_a_record_and_the_views_return_it(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        result = append(contract, agreement="0x" + AGREEMENT.upper(), terms="0x" + TERMS)

    assert result == {"agreement_id": AGREEMENT, "state": "ACCEPTED", "index": 0}
    assert contract.get_count() == 1
    assert contract.get_agreement_id(0) == AGREEMENT
    assert record(contract) == {
        "agreement_id": AGREEMENT,
        "terms_hash": TERMS,
        "role_keys": ["client:rk_7f3a91", "creator:rk_0c22de"],
        "base": BASE,
        "template_version": TEMPLATE,
        "state": "ACCEPTED",
        "outcome_code": "",
        "index": 0,
    }
    # 0x / bare / upper-case spellings of one id read the same record.
    assert record(contract, "0x" + AGREEMENT) == record(contract, AGREEMENT.upper())


def test_owner_may_append_and_move_too(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    assert append(contract, state="PROPOSED")["index"] == 0
    assert append(contract, agreement=OTHER_AGREEMENT, state="SIGNED")["index"] == 1
    assert contract.move_state(AGREEMENT, "ACCEPTED", "") == {
        "agreement_id": AGREEMENT, "from_state": "PROPOSED", "state": "ACCEPTED", "outcome_code": ""}
    assert contract.get_count() == 2
    assert contract.get_agreement_id(1) == OTHER_AGREEMENT
    assert record(contract, OTHER_AGREEMENT)["state"] == "SIGNED"


def test_accepted_to_anchored_is_a_valid_forward_move(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="ACCEPTED")
        result = contract.move_state(AGREEMENT, "ANCHORED", "")
    assert result == {"agreement_id": AGREEMENT, "from_state": "ACCEPTED", "state": "ANCHORED", "outcome_code": ""}
    assert record(contract)["state"] == "ANCHORED"


def test_every_state_is_reachable_one_step_at_a_time(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="PROPOSED")
        i = 1
        while i < len(STATES):
            assert contract.move_state(AGREEMENT, STATES[i], "")["from_state"] == STATES[i - 1]
            assert record(contract)["state"] == STATES[i]
            i += 1


def test_closing_sets_the_outcome_code_and_empty_code_keeps_it(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="PROPOSED", outcome="PENDING_SIGNATURE")
        contract.move_state(AGREEMENT, "SIGNED", "")
        assert record(contract)["outcome_code"] == "PENDING_SIGNATURE"
        result = contract.move_state(AGREEMENT, "CLOSED", "FULFILLED")
    assert result["outcome_code"] == "FULFILLED"
    stored = record(contract)
    assert stored["state"] == "CLOSED"
    assert stored["outcome_code"] == "FULFILLED"


def test_owner_can_change_and_remove_the_relayer(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    assert contract.set_relayer(addr_hex(direct_bob).upper().replace("0X", "0x")) == {"relayer": addr_hex(direct_bob)}
    assert contract.get_relayer() == addr_hex(direct_bob)
    # The old relayer is now just another caller.
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: append(contract))
    with direct_vm.prank(direct_bob):
        append(contract)
    assert contract.remove_relayer() == {"relayer": ""}
    assert contract.get_relayer() == ""
    with direct_vm.prank(direct_bob):
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: contract.move_state(AGREEMENT, "SIGNED", ""))


# --- refusals ---------------------------------------------------------------------------

def test_refuses_a_duplicate_id(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract)
        before = snapshot(contract)
        refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract))
        # Another spelling of the same id is the same id; other fields do not matter.
        refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract, agreement="0x" + AGREEMENT.upper(),
                                                           terms=hashlib.sha256(b"x").hexdigest(), state="PROPOSED"))
    refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract))  # the owner too
    assert snapshot(contract) == before


def test_refuses_any_other_caller_on_every_write(direct_vm, direct_deploy, direct_owner, direct_alice, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    append(contract)
    before = snapshot(contract)
    with direct_vm.prank(direct_charlie):
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: append(contract, agreement=OTHER_AGREEMENT))
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: contract.move_state(AGREEMENT, "SIGNED", ""))
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: contract.set_relayer(addr_hex(direct_charlie)))
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: contract.remove_relayer())
        # Views stay open to everyone.
        assert contract.get_count() == 1
    assert snapshot(contract) == before


def test_refuses_writes_from_anyone_but_the_owner_before_a_relayer_is_set(direct_vm, direct_deploy, direct_owner, direct_alice):
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: append(contract))
    assert contract.get_count() == 0


def test_refuses_the_relayer_doing_an_owner_only_action(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    before = snapshot(contract)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_OWNER_ONLY, lambda: contract.set_relayer(addr_hex(direct_bob)))
        refused(direct_vm, ERR_OWNER_ONLY, lambda: contract.set_relayer(addr_hex(direct_alice)))
        refused(direct_vm, ERR_OWNER_ONLY, lambda: contract.remove_relayer())
    assert snapshot(contract) == before
    assert contract.get_relayer() == addr_hex(direct_alice)


@pytest.mark.parametrize("frm,to", [
    ("ACCEPTED", "ACCEPTED"),   # same state
    ("ANCHORED", "ACCEPTED"),   # backward
    ("SIGNED", "PROPOSED"),     # backward to the start
    ("CLOSED", "CLOSED"),       # terminal: nothing follows CLOSED
    ("CLOSED", "ANCHORED"),
])
def test_refuses_a_same_or_backward_state_change(direct_vm, direct_deploy, direct_owner, direct_alice, frm, to):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state=frm, outcome="X1")
        before = snapshot(contract)
        refused(direct_vm, ERR_INVALID_TRANSITION, lambda: contract.move_state(AGREEMENT, to, "CHANGED"))
    refused(direct_vm, ERR_INVALID_TRANSITION, lambda: contract.move_state(AGREEMENT, to, ""))  # owner too
    assert snapshot(contract) == before


@pytest.mark.parametrize("state", ["DONE", "accepted", "", " ACCEPTED", "ANCHOR"])
def test_refuses_an_unknown_state(direct_vm, direct_deploy, direct_owner, direct_alice, state):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_UNKNOWN_STATE, lambda: append(contract, state=state))
        assert contract.get_count() == 0
        append(contract, state="PROPOSED")
        before = snapshot(contract)
        refused(direct_vm, ERR_UNKNOWN_STATE, lambda: contract.move_state(AGREEMENT, state, ""))
    assert snapshot(contract) == before


def test_refuses_a_move_on_an_unknown_agreement_id(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract)
        refused(direct_vm, ERR_UNKNOWN_AGREEMENT, lambda: contract.move_state(OTHER_AGREEMENT, "SIGNED", ""))
    refused(direct_vm, ERR_UNKNOWN_AGREEMENT, lambda: contract.get_agreement(OTHER_AGREEMENT))
    assert contract.get_count() == 1


@pytest.mark.parametrize("bad", ["", "abc", AGREEMENT[:63], AGREEMENT + "0", "0x" + AGREEMENT[:62],
                                 "g" + AGREEMENT[1:], "0x0x" + AGREEMENT[4:], "sha256:" + AGREEMENT])
def test_refuses_a_bad_agreement_id(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: append(contract, agreement=bad))
        refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: contract.move_state(bad, "SIGNED", ""))
    refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: contract.get_agreement(bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["", TERMS[:63], TERMS + "a", "z" * 64, "0x" + TERMS[2:]])
def test_refuses_a_bad_terms_hash(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_TERMS_HASH, lambda: append(contract, terms=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["", "client:rk_1,", "client:rk_1,client:rk_1", "a b", "client@rk",
                                 "k" * 129, ",".join(["k%d" % n for n in range(17)])])
def test_refuses_bad_role_keys(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_ROLE_KEYS, lambda: append(contract, role_keys=bad))
    assert contract.get_count() == 0


def test_accepts_role_keys_at_the_limits(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    keys = ",".join(["k%d" % n for n in range(16)])
    append(contract, role_keys=keys)
    append(contract, agreement=OTHER_AGREEMENT, role_keys="k" * 128)
    assert len(record(contract)["role_keys"]) == 16


@pytest.mark.parametrize("bad", ["", "b" * 129, "line\nbreak", "café"])
def test_refuses_a_bad_base(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_BASE, lambda: append(contract, base=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["", "v" * 33, "1.2 beta", "v1/2"])
def test_refuses_a_bad_template_version(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_TEMPLATE_VERSION, lambda: append(contract, template=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["fulfilled", "A" * 33, "OK-1", "OK 1"])
def test_refuses_a_bad_outcome_code(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_OUTCOME_CODE, lambda: append(contract, outcome=bad))
        assert contract.get_count() == 0
        append(contract, state="PROPOSED")
        before = snapshot(contract)
        refused(direct_vm, ERR_BAD_OUTCOME_CODE, lambda: contract.move_state(AGREEMENT, "SIGNED", bad))
    assert snapshot(contract) == before


@pytest.mark.parametrize("bad", ["", "0x1234", "1234567890123456789012345678901234567890",
                                 "0x" + "g" * 40, "0x" + "a" * 41])
def test_refuses_a_bad_relayer_address(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    refused(direct_vm, ERR_BAD_ADDRESS, lambda: contract.set_relayer(bad))
    assert contract.get_relayer() == addr_hex(direct_alice)


def test_refuses_an_index_out_of_range(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    refused(direct_vm, ERR_INDEX_OUT_OF_RANGE, lambda: contract.get_agreement_id(0))
    append(contract)
    assert contract.get_agreement_id(0) == AGREEMENT
    refused(direct_vm, ERR_INDEX_OUT_OF_RANGE, lambda: contract.get_agreement_id(1))
    refused(direct_vm, ERR_INDEX_OUT_OF_RANGE, lambda: contract.get_agreement_id(-1))
