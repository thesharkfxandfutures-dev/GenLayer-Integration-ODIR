"""Direct-mode tests for contracts/factory/agreement_registry.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (storage), then written to the
owner page's row 4 (agreement_registry) and aligned on 26 Nov 2026 with ODIR slices
A3 (terms hash spelling, base keys, role keys), A4 (release tag) and SnapLink's C4
(e-sign seal hash). The contract is deterministic (no web, no LLM), so nothing is
mocked; these tests check roles, input checks, the forward-only state list, the
one-time seal, storage and the views, not GenVM consensus on a network.

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
ROLE_KEYS = "provider:photographer"
BASE = "B2P"
TEMPLATE = "templates-v1.0.0"

# A real A3 output: terms_hash of resolver/test/golden/agreement.photographer.provider.B2P.EW.json
# (ODIR branch odir/a3-schemas-templates-2026-11-25 at dcb91be), written the way A3 and SnapLink write it.
A3_GOLDEN_TERMS = "sha256:780d49e0f38f0ca491d733c127726cc1273e99501768b91f1b68efb70f2233d5"

# SnapLink C4 agreementSealHash: sha256("snaplink-esign-evidence/1|" + evidence hashes in slot order joined by "|").
EVIDENCE_ENGAGER = hashlib.sha256(b"evidence engager").hexdigest()
EVIDENCE_PROVIDER = hashlib.sha256(b"evidence provider").hexdigest()
SEAL = hashlib.sha256(("snaplink-esign-evidence/1|" + EVIDENCE_ENGAGER + "|" + EVIDENCE_PROVIDER).encode()).hexdigest()
OTHER_SEAL = hashlib.sha256(b"another seal").hexdigest()

STATES = ["PROPOSED", "ACCEPTED", "SIGNED", "ANCHORED", "CLOSED"]
BASES = ["P2P", "P2B", "B2P", "B2B", "STAFF"]

ERR_UNAUTHORIZED = "[EXPECTED] UNAUTHORIZED: only the owner or the relayer may call this"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: the relayer may only append a record or move its state"
ERR_DUPLICATE_ID = "[EXPECTED] DUPLICATE_ID: an agreement with this id is already recorded"
ERR_UNKNOWN_AGREEMENT = "[EXPECTED] UNKNOWN_AGREEMENT: no agreement is recorded with this id"
ERR_UNKNOWN_STATE = "[EXPECTED] UNKNOWN_STATE: state must be one of PROPOSED, ACCEPTED, SIGNED, ANCHORED, CLOSED"
ERR_INVALID_TRANSITION = "[EXPECTED] INVALID_TRANSITION: state moves only forward"
ERR_BAD_AGREEMENT_ID = "[EXPECTED] BAD_AGREEMENT_ID: agreement id must be a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_BAD_TERMS_HASH = "[EXPECTED] BAD_TERMS_HASH: terms hash must be a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_BAD_SEAL_HASH = "[EXPECTED] BAD_SEAL_HASH: seal hash must be empty or a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_SEAL_ALREADY_SET = "[EXPECTED] SEAL_ALREADY_SET: the seal hash is already recorded and cannot change"
ERR_BAD_ROLE_KEYS = "[EXPECTED] BAD_ROLE_KEYS: role keys must be empty or 1 to 2 comma-separated slot:role keys (slot engager or provider, each once; role a-z then 1 to 40 of a-z 0-9 _)"
ERR_BAD_BASE = "[EXPECTED] BAD_BASE: base must be one of P2P, P2B, B2P, B2B, STAFF"
ERR_BAD_TEMPLATE_VERSION = "[EXPECTED] BAD_TEMPLATE_VERSION: template version must be a release tag templates-vX.Y.Z (no leading zeros, at most 32 characters)"
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
           template=TEMPLATE, state="ACCEPTED", outcome="", seal=""):
    return contract.append_agreement(agreement, terms, role_keys, base, template, state, outcome, seal)


def move(contract, state, outcome="", seal="", agreement=AGREEMENT):
    return contract.move_state(agreement, state, outcome, seal)


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
        "terms_hash": "sha256:" + TERMS,   # stored the way A3 and SnapLink write a terms hash
        "role_keys": ["provider:photographer"],
        "base": BASE,
        "template_version": TEMPLATE,
        "state": "ACCEPTED",
        "outcome_code": "",
        "seal_hash": "",
        "index": 0,
    }
    # 0x / sha256: / bare / upper-case spellings of one id read the same record.
    assert record(contract, "0x" + AGREEMENT) == record(contract, AGREEMENT.upper())
    assert record(contract, "sha256:" + AGREEMENT) == record(contract, "SHA256:" + AGREEMENT.upper())


def test_takes_the_a3_terms_hash_and_the_c4_seal_as_snaplink_writes_them(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, agreement="sha256:" + AGREEMENT, terms=A3_GOLDEN_TERMS, seal=SEAL)
    stored = record(contract)
    # Each hash is stored in the spelling its SnapLink source writes, so D4 compares with plain equality:
    assert stored["terms_hash"] == A3_GOLDEN_TERMS          # A3 / C4 evidence: sha256:<hex>
    assert stored["seal_hash"] == SEAL                      # C4 agreementSealHash: bare <hex>
    assert stored["agreement_id"] == AGREEMENT              # bare <hex>, like C4's agreement_ref
    # One hash, every spelling: a later append of the same id in another spelling is a duplicate.
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract, agreement="0x" + AGREEMENT))


def test_owner_may_append_and_move_too(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    assert append(contract, state="PROPOSED")["index"] == 0
    assert append(contract, agreement=OTHER_AGREEMENT, state="SIGNED")["index"] == 1
    assert move(contract, "ACCEPTED") == {
        "agreement_id": AGREEMENT, "from_state": "PROPOSED", "state": "ACCEPTED", "outcome_code": "", "seal_hash": ""}
    assert contract.get_count() == 2
    assert contract.get_agreement_id(1) == OTHER_AGREEMENT
    assert record(contract, OTHER_AGREEMENT)["state"] == "SIGNED"


def test_accepted_to_anchored_is_a_valid_forward_move(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="ACCEPTED")
        result = move(contract, "ANCHORED")
    assert result == {"agreement_id": AGREEMENT, "from_state": "ACCEPTED", "state": "ANCHORED",
                      "outcome_code": "", "seal_hash": ""}
    assert record(contract)["state"] == "ANCHORED"


def test_every_state_is_reachable_one_step_at_a_time(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="PROPOSED")
        i = 1
        while i < len(STATES):
            assert move(contract, STATES[i])["from_state"] == STATES[i - 1]
            assert record(contract)["state"] == STATES[i]
            i += 1


def test_closing_sets_the_outcome_code_and_empty_code_keeps_it(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="PROPOSED", outcome="PENDING_SIGNATURE")
        move(contract, "SIGNED")
        assert record(contract)["outcome_code"] == "PENDING_SIGNATURE"
        result = move(contract, "CLOSED", "COMPLETED")
    assert result["outcome_code"] == "COMPLETED"
    stored = record(contract)
    assert stored["state"] == "CLOSED"
    assert stored["outcome_code"] == "COMPLETED"


def test_the_seal_is_recorded_once_on_a_move_and_an_empty_seal_keeps_it(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="PROPOSED")
        assert record(contract)["seal_hash"] == ""
        result = move(contract, "SIGNED", seal="sha256:" + SEAL.upper())
        assert result == {"agreement_id": AGREEMENT, "from_state": "PROPOSED", "state": "SIGNED",
                          "outcome_code": "", "seal_hash": SEAL}
        assert move(contract, "ANCHORED")["seal_hash"] == SEAL  # "" keeps it
        before = snapshot(contract)
        # Once recorded it never changes: not to another value, not even to the same value again.
        refused(direct_vm, ERR_SEAL_ALREADY_SET, lambda: move(contract, "CLOSED", "COMPLETED", OTHER_SEAL))
        refused(direct_vm, ERR_SEAL_ALREADY_SET, lambda: move(contract, "CLOSED", "COMPLETED", SEAL))
        assert snapshot(contract) == before
        assert move(contract, "CLOSED", "COMPLETED")["seal_hash"] == SEAL
    refused(direct_vm, ERR_INVALID_TRANSITION, lambda: move(contract, "CLOSED", "", OTHER_SEAL))  # owner, terminal
    assert record(contract)["seal_hash"] == SEAL


def test_a_seal_given_at_append_cannot_be_replaced_by_the_owner_either(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, state="ACCEPTED", seal="0x" + SEAL)
    assert record(contract)["seal_hash"] == SEAL
    before = snapshot(contract)
    refused(direct_vm, ERR_SEAL_ALREADY_SET, lambda: move(contract, "ANCHORED", "", OTHER_SEAL))
    assert snapshot(contract) == before


@pytest.mark.parametrize("keys,stored", [
    ("", []),                                                    # a base-only agreement (A3: both roles null)
    ("provider:photographer", ["provider:photographer"]),
    ("engager:photographer", ["engager:photographer"]),
    ("engager:event_planner,provider:photographer", ["engager:event_planner", "provider:photographer"]),
    ("provider:photographer,engager:event_planner", ["engager:event_planner", "provider:photographer"]),  # engager first
    ("provider:ab", ["provider:ab"]),                            # shortest A3 role key (2)
    ("provider:a" + "b" * 40, ["provider:a" + "b" * 40]),        # longest A3 role key (41)
])
def test_role_keys_follow_the_agreement_roles(direct_vm, direct_deploy, direct_owner, direct_alice, keys, stored):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract, role_keys=keys)
    assert record(contract)["role_keys"] == stored


@pytest.mark.parametrize("base", BASES)
def test_accepts_every_a3_base_key(direct_vm, direct_deploy, direct_owner, direct_alice, base):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    append(contract, base=base)
    assert record(contract)["base"] == base


@pytest.mark.parametrize("tag", ["templates-v0.0.0", "templates-v1.0.0", "templates-v10.20.30",
                                 "templates-v1234567.1234567.12345"])  # 32 characters
def test_accepts_a_release_tag_as_the_template_version(direct_vm, direct_deploy, direct_owner, direct_alice, tag):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    append(contract, template=tag)
    assert record(contract)["template_version"] == tag


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
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: move(contract, "SIGNED"))


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
        refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract, agreement="sha256:" + AGREEMENT, seal=SEAL))
    refused(direct_vm, ERR_DUPLICATE_ID, lambda: append(contract))  # the owner too
    assert snapshot(contract) == before


def test_refuses_any_other_caller_on_every_write(direct_vm, direct_deploy, direct_owner, direct_alice, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    append(contract)
    before = snapshot(contract)
    with direct_vm.prank(direct_charlie):
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: append(contract, agreement=OTHER_AGREEMENT))
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: move(contract, "SIGNED"))
        refused(direct_vm, ERR_UNAUTHORIZED, lambda: move(contract, "SIGNED", "", SEAL))
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
        refused(direct_vm, ERR_INVALID_TRANSITION, lambda: move(contract, to, "CHANGED"))
        # A refused move records no seal either.
        refused(direct_vm, ERR_INVALID_TRANSITION, lambda: move(contract, to, "", SEAL))
    refused(direct_vm, ERR_INVALID_TRANSITION, lambda: move(contract, to))  # owner too
    assert snapshot(contract) == before


@pytest.mark.parametrize("state", ["DONE", "accepted", "", " ACCEPTED", "ANCHOR"])
def test_refuses_an_unknown_state(direct_vm, direct_deploy, direct_owner, direct_alice, state):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_UNKNOWN_STATE, lambda: append(contract, state=state))
        assert contract.get_count() == 0
        append(contract, state="PROPOSED")
        before = snapshot(contract)
        refused(direct_vm, ERR_UNKNOWN_STATE, lambda: move(contract, state))
    assert snapshot(contract) == before


def test_refuses_a_move_on_an_unknown_agreement_id(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        append(contract)
        refused(direct_vm, ERR_UNKNOWN_AGREEMENT, lambda: move(contract, "SIGNED", agreement=OTHER_AGREEMENT))
    refused(direct_vm, ERR_UNKNOWN_AGREEMENT, lambda: contract.get_agreement(OTHER_AGREEMENT))
    assert contract.get_count() == 1


BAD_HASHES = ["", "abc", AGREEMENT[:63], AGREEMENT + "0", "0x" + AGREEMENT[:62], "g" + AGREEMENT[1:],
              "0x0x" + AGREEMENT[4:], "sha256:0x" + AGREEMENT, "0xsha256:" + AGREEMENT, "sha256" + AGREEMENT,
              "sha256:" + AGREEMENT[:63], "sha-256:" + AGREEMENT, "sha256:sha256:" + AGREEMENT,
              " " + AGREEMENT, AGREEMENT + "\n", "sha256: " + AGREEMENT, "0x " + AGREEMENT]  # no spaces (A3/C4 regexes)


@pytest.mark.parametrize("bad", BAD_HASHES)
def test_refuses_a_bad_agreement_id(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: append(contract, agreement=bad))
        refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: move(contract, "SIGNED", agreement=bad))
    refused(direct_vm, ERR_BAD_AGREEMENT_ID, lambda: contract.get_agreement(bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["", TERMS[:63], TERMS + "a", "z" * 64, "0x" + TERMS[2:],
                                 "sha256:" + TERMS[:63], "sha256:0x" + TERMS, "sha256: " + TERMS,
                                 " sha256:" + TERMS, "sha256:" + TERMS + " "])
def test_refuses_a_bad_terms_hash(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_TERMS_HASH, lambda: append(contract, terms=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", [" ", "abc", SEAL[:63], SEAL + "0", "z" * 64, "sha256:0x" + SEAL,
                                 "sha256:" + SEAL[:63], "0x" + SEAL[:62], " " + SEAL, SEAL + "\t"])
def test_refuses_a_bad_seal_hash(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_SEAL_HASH, lambda: append(contract, seal=bad))
        assert contract.get_count() == 0
        append(contract, state="PROPOSED")
        before = snapshot(contract)
        refused(direct_vm, ERR_BAD_SEAL_HASH, lambda: move(contract, "SIGNED", "", bad))
    assert snapshot(contract) == before


@pytest.mark.parametrize("bad", [
    "client:rk_1",                                   # not a slot
    "creator:photographer",                          # not a slot
    "photographer",                                  # no slot
    ":photographer",                                 # empty slot
    "provider:",                                     # empty role
    "provider:p",                                    # role too short (A3: 2 to 41)
    "provider:a" + "b" * 41,                         # role too long (42)
    "provider:Photographer",                         # upper case
    "provider:1photographer",                        # must start with a letter
    "provider:_photographer",                        # must start with a letter
    "provider:photo-grapher",                        # '-' is not in an A3 role key
    "provider:photo.grapher",                        # '.' is not in an A3 role key
    "provider:photographer:x",                       # one colon only
    "provider:photographer,provider:videographer",   # a slot twice
    "engager:a1,engager:b2",                         # a slot twice
    "engager:planner,provider:photographer,engager:x1",  # more than 2 keys
    "provider:photographer,",                        # trailing comma
    ",provider:photographer",                        # leading comma
    " provider:photographer",                        # spaces are not trimmed
    "provider:photographer ",
    "provider: photographer",
    "Provider:photographer",                         # slot is lower case
])
def test_refuses_bad_role_keys(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_ROLE_KEYS, lambda: append(contract, role_keys=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", ["", "p2p", "P2P ", " P2P", "snaplink-uk", "STAFF2", "B2C", "café", "P2P,B2P"])
def test_refuses_a_bad_base(direct_vm, direct_deploy, direct_owner, direct_alice, bad):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    with direct_vm.prank(direct_alice):
        refused(direct_vm, ERR_BAD_BASE, lambda: append(contract, base=bad))
    assert contract.get_count() == 0


@pytest.mark.parametrize("bad", [
    "", "1.0.0", "v1.0.0", "parchment-1.2", "templates-v1.0", "templates-v1.0.0.0", "templates-v01.0.0",
    "templates-v1.00.0", "templates-v1.0.0-rc1", "templates-V1.0.0", "Templates-v1.0.0", "templates-v1..0",
    "templates-v.1.0", "templates-v1.0.", "templates-v 1.0.0", "templates-v1.0.0 ", "templates-v-1.0.0",
    "templates-v12345678.1234567.12345",  # 33 characters
])
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
        refused(direct_vm, ERR_BAD_OUTCOME_CODE, lambda: move(contract, "SIGNED", bad))
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
