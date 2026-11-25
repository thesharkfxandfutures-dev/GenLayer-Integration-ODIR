"""Direct-mode tests for contracts/factory/verified_work_milestone.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (storage), then written to the
owner's row 9 (award contract). The contract is deterministic counting: it makes no LLM
or web call, so there is nothing to mock and no validator to test. These tests check the
counting rule, the answer words, the shortfall, every refusal (full text), the owner-managed
catalogue and the storage, not GenVM execution or consensus on a network.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_verified_work_milestone.py -v
"""
import hashlib
import json
from pathlib import Path

import pytest

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "verified_work_milestone.py")

ENTRANT = hashlib.sha256(b"snaplink entrant 0001").hexdigest()
OTHER_ENTRANT = hashlib.sha256(b"snaplink entrant 0002").hexdigest()
ROLE = "photographer"
OTHER_ROLE = "videographer"

NOT_OWNER = "[EXPECTED] NOT_OWNER: only the contract owner (the deployer) can do this"
FORBIDDEN_SIGNAL = ("[EXPECTED] FORBIDDEN_SIGNAL: inputs must not carry a selection signal "
                    "(likes, followers, votes, paid plan or boost)")
BAD_ROLE_KEY = "[EXPECTED] BAD_ROLE_KEY: a role key must be lowercase snake_case, 2 to 48 characters"
BAD_ENTRANT_ID = ("[EXPECTED] BAD_ENTRANT_ID: entrant_id must be 64 hexadecimal characters "
                  "(a public hash, never a name)")
BAD_WORK_HASH = "[EXPECTED] BAD_WORK_HASH: every work-record hash must be 64 hexadecimal characters"
BAD_EVIDENCE_LEVEL = ("[EXPECTED] BAD_EVIDENCE_LEVEL: an evidence level must be one word of letters, "
                      "digits or underscores, at most 32 characters")
BAD_WORK_RECORDS = ("[EXPECTED] BAD_WORK_RECORDS: work_hashes, evidence_levels and work_roles must be "
                    "lists of text of the same length")
TOO_MANY_RECORDS = "[EXPECTED] TOO_MANY_RECORDS: a claim may list at most 10000 work records"
UNKNOWN_MILESTONE = "[EXPECTED] UNKNOWN_MILESTONE: this milestone is not in the catalogue"
DUPLICATE_WORK_HASH = "[EXPECTED] DUPLICATE_WORK_HASH: the same work hash appears more than once in this claim"
ALREADY_CONFIRMED = "[EXPECTED] ALREADY_CONFIRMED: this milestone is already confirmed for this entrant and role"
BAD_MILESTONE_NAME = ("[EXPECTED] BAD_MILESTONE_NAME: a milestone name must start with a letter and use "
                      "only letters, digits or underscores, at most 32 characters")
BAD_MILESTONE_COUNT = "[EXPECTED] BAD_MILESTONE_COUNT: a milestone count must be a whole number from 1 to 10000"
MILESTONE_EXISTS = "[EXPECTED] MILESTONE_EXISTS: this milestone is already in the catalogue"
NOT_CONFIRMED = "[EXPECTED] NOT_CONFIRMED: no confirmation is stored for this entrant, role and milestone"
BAD_INDEX = "[EXPECTED] BAD_INDEX: no claim at this index"


def work_hash(i, tag="w"):
    return hashlib.sha256(f"work-record {tag} {i}".encode()).hexdigest()


def records(count, level="ATTESTED", role=ROLE, start=0, tag="w"):
    """Parallel lists (hashes, levels, roles) for `count` distinct work records."""
    hashes = [work_hash(i, tag) for i in range(start, start + count)]
    return hashes, [level] * count, [role] * count


def join(*parts):
    hashes, levels, roles = [], [], []
    for h, lv, r in parts:
        hashes += h
        levels += lv
        roles += r
    return hashes, levels, roles


def deploy(direct_deploy):
    # The default direct-mode sender (direct_owner) deploys and so becomes the owner.
    return direct_deploy(CONTRACT)


def claim(contract, milestone, recs, entrant=ENTRANT, role=ROLE):
    hashes, levels, roles = recs
    return contract.claim_milestone(entrant, role, milestone, hashes, levels, roles)


def address_hex(address):
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


# --- answers -------------------------------------------------------------------------

def test_milestone_reached_counts_attested_and_snaplink_verified(direct_deploy):
    contract = deploy(direct_deploy)
    recs = join(
        records(15, "ATTESTED", tag="a"),
        records(10, "SNAPLINK_VERIFIED", tag="v"),
        records(4, "SELF_REPORTED", tag="s"),
        records(3, "ATTESTED", role=OTHER_ROLE, tag="o"),
    )

    result = claim(contract, "FOUNDATION", recs)

    assert result == {
        "claim_index": 0,
        "entrant_id": ENTRANT,
        "role_key": ROLE,
        "milestone": "FOUNDATION",
        "verdict": "MILESTONE_REACHED",
        "required": 25,
        "counted": 25,
        "shortfall": 0,
        "records": 32,
        "not_counted_level": 4,
        "not_counted_role": 3,
        "reason": ("25 of 25 required work records counted for role photographer "
                   "(4 not attested or SnapLink-verified, 3 in another role)"),
    }
    assert contract.is_confirmed(ENTRANT, ROLE, "FOUNDATION") is True
    assert json.loads(contract.get_confirmation(ENTRANT, ROLE, "foundation")) == result
    assert contract.get_claim_count() == 1
    assert json.loads(contract.get_claim(0)) == result


def test_not_reached_reports_the_shortfall(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    recs = join(
        records(18, "SNAPLINK_VERIFIED", tag="v"),
        records(5, "PENDING", tag="p"),
        records(2, "ATTESTED", role=OTHER_ROLE, tag="o"),
    )

    result = claim(contract, "FOUNDATION", recs)

    assert result["verdict"] == "NOT_REACHED"
    assert result["required"] == 25
    assert result["counted"] == 18
    assert result["shortfall"] == 7
    assert result["not_counted_level"] == 5
    assert result["not_counted_role"] == 2
    assert result["reason"] == ("18 of 25 required work records counted for role photographer "
                                "(5 not attested or SnapLink-verified, 2 in another role)")
    assert contract.is_confirmed(ENTRANT, ROLE, "FOUNDATION") is False
    with direct_vm.expect_revert(NOT_CONFIRMED):
        contract.get_confirmation(ENTRANT, ROLE, "FOUNDATION")
    assert json.loads(contract.get_claim(0))["verdict"] == "NOT_REACHED"


def test_not_reached_does_not_block_a_later_claim(direct_deploy):
    contract = deploy(direct_deploy)
    first = claim(contract, "FOUNDATION", records(24))
    assert first["verdict"] == "NOT_REACHED"
    assert first["shortfall"] == 1

    second = claim(contract, "FOUNDATION", records(25))

    assert second["verdict"] == "MILESTONE_REACHED"
    assert second["claim_index"] == 1
    assert contract.is_confirmed(ENTRANT, ROLE, "FOUNDATION") is True
    assert contract.get_claim_count() == 2


def test_empty_list_is_not_reached_with_the_full_shortfall(direct_deploy):
    contract = deploy(direct_deploy)
    result = claim(contract, "FOUNDATION", ([], [], []))
    assert result["verdict"] == "NOT_REACHED"
    assert result["counted"] == 0
    assert result["shortfall"] == 25


def test_zenith_needs_ten_thousand_counted_records(direct_deploy):
    contract = deploy(direct_deploy)
    short = join(records(9999, "ATTESTED", tag="z"), records(1, "UNVERIFIED", tag="u"))
    first = claim(contract, "ZENITH", short)
    assert first["verdict"] == "NOT_REACHED"
    assert first["required"] == 10000
    assert first["counted"] == 9999
    assert first["shortfall"] == 1

    second = claim(contract, "Zenith", records(10000, "SNAPLINK_VERIFIED", tag="z"))
    assert second["verdict"] == "MILESTONE_REACHED"
    assert second["counted"] == 10000
    assert second["shortfall"] == 0
    assert contract.is_confirmed(ENTRANT, ROLE, "ZENITH") is True


def test_level_words_are_case_insensitive_and_other_words_do_not_count(direct_deploy):
    contract = deploy(direct_deploy)
    recs = join(
        records(13, " attested ", tag="a"),
        records(12, "Snaplink_Verified", tag="v"),
        records(3, "ATTESTED_BY_FRIEND", tag="f"),
        records(2, "VERIFIED", tag="x"),
    )
    result = claim(contract, "FOUNDATION", recs)
    assert result["verdict"] == "MILESTONE_REACHED"
    assert result["counted"] == 25
    assert result["not_counted_level"] == 5


def test_whole_words_only_for_forbidden_signals(direct_deploy):
    contract = deploy(direct_deploy)
    # "lifelike" and "unpaid" contain forbidden letters but are not forbidden words.
    recs = join(records(25, "ATTESTED", role="lifelike_sculptor"), records(1, "UNPAID", role="lifelike_sculptor",
                                                                             tag="u"))
    result = claim(contract, "FOUNDATION", recs, role="lifelike_sculptor")
    assert result["verdict"] == "MILESTONE_REACHED"
    assert result["not_counted_level"] == 1


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_a_milestone_not_in_the_catalogue(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    for name in ["SUMMIT", "", "Foundation!", "25"]:
        with direct_vm.expect_revert(UNKNOWN_MILESTONE):
            claim(contract, name, records(25))
    with direct_vm.expect_revert(UNKNOWN_MILESTONE):
        contract.get_milestone("SUMMIT")
    with direct_vm.expect_revert(UNKNOWN_MILESTONE):
        contract.is_confirmed(ENTRANT, ROLE, "SUMMIT")
    assert contract.get_claim_count() == 0


def test_refuses_the_same_work_hash_twice_in_one_claim(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    hashes, levels, roles = records(25)
    # Same hash again, upper-cased, with another level and role: still the same work record.
    hashes.append(hashes[3].upper())
    levels.append("SELF_REPORTED")
    roles.append(OTHER_ROLE)

    with direct_vm.expect_revert(DUPLICATE_WORK_HASH):
        contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, levels, roles)
    assert contract.get_claim_count() == 0
    assert contract.is_confirmed(ENTRANT, ROLE, "FOUNDATION") is False


def test_refuses_a_milestone_already_confirmed_for_this_entrant_and_role(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    assert claim(contract, "FOUNDATION", records(25))["verdict"] == "MILESTONE_REACHED"

    with direct_vm.expect_revert(ALREADY_CONFIRMED):
        claim(contract, "FOUNDATION", records(30, tag="new"))
    with direct_vm.expect_revert(ALREADY_CONFIRMED):
        claim(contract, " foundation ", records(25))
    assert contract.get_claim_count() == 1

    # Another role, another entrant or another milestone is a separate confirmation.
    assert claim(contract, "FOUNDATION", records(25, role=OTHER_ROLE), role=OTHER_ROLE)["verdict"] == \
        "MILESTONE_REACHED"
    assert claim(contract, "FOUNDATION", records(25), entrant=OTHER_ENTRANT)["verdict"] == "MILESTONE_REACHED"
    assert claim(contract, "ZENITH", records(25))["verdict"] == "NOT_REACHED"
    assert contract.get_claim_count() == 4


# --- forbidden selection signals (award-contract rule) -------------------------------------

@pytest.mark.parametrize("field,value", [
    ("level", "boosted"),                      # boost / boosted
    ("level", "Boost2x"),                      # digits separate words
    ("level", "paid"),                         # paid plan
    ("level", "PREMIUM"),                      # premium
    ("level", "SUBSCRIPTION_VERIFIED"),        # subscription
    ("level", "membership_tier"),              # membership tier
    ("role_key", "likes_curator"),             # likes
    ("work_role", "top_followers"),            # followers
    ("milestone", "Votes"),                    # votes
    ("milestone", "voting_round"),             # voting
])
def test_refuses_a_forbidden_selection_signal(direct_vm, direct_deploy, field, value):
    contract = deploy(direct_deploy)
    hashes, levels, roles = records(25)
    role_key = ROLE
    milestone = "FOUNDATION"
    if field == "level":
        levels[7] = value
    elif field == "role_key":
        role_key = value
        roles = [value] * 25
    elif field == "work_role":
        roles[0] = value
    elif field == "milestone":
        milestone = value

    with direct_vm.expect_revert(FORBIDDEN_SIGNAL):
        contract.claim_milestone(ENTRANT, role_key, milestone, hashes, levels, roles)
    assert contract.get_claim_count() == 0


def test_refuses_a_forbidden_signal_in_a_new_milestone_name(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    with direct_vm.expect_revert(FORBIDDEN_SIGNAL):
        contract.add_milestone("BOOST_BONUS", 50)
    with direct_vm.expect_revert(FORBIDDEN_SIGNAL):
        contract.add_milestone("Followers_100", 100)
    assert json.loads(contract.get_catalogue()) == [{"milestone": "FOUNDATION", "count": 25},
                                                   {"milestone": "ZENITH", "count": 10000}]


# --- role key shape -----------------------------------------------------------------------

def test_refuses_a_malformed_role_key(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    for bad in ["Photographer", "photo grapher", "p", "photographer_", "_photographer", "photo__grapher",
                "9lives", "photo-grapher", "a" * 49]:
        with direct_vm.expect_revert(BAD_ROLE_KEY):
            claim(contract, "FOUNDATION", records(25, role=ROLE), role=bad)
    hashes, levels, roles = records(25)
    roles[5] = "Video Editor"
    with direct_vm.expect_revert(BAD_ROLE_KEY):
        contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, levels, roles)
    with direct_vm.expect_revert(BAD_ROLE_KEY):
        contract.is_confirmed(ENTRANT, "Photographer", "FOUNDATION")
    assert contract.get_claim_count() == 0
    # 48 characters is the longest accepted key.
    long_role = "a" * 48
    assert claim(contract, "FOUNDATION", records(25, role=long_role), role=long_role)["verdict"] == \
        "MILESTONE_REACHED"


# --- list limits and malformed inputs -------------------------------------------------------

def test_refuses_an_over_long_list(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    with direct_vm.expect_revert(TOO_MANY_RECORDS):
        claim(contract, "ZENITH", records(10001))
    assert contract.get_claim_count() == 0


def test_refuses_malformed_entrant_hashes_levels_and_lists(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    hashes, levels, roles = records(25)
    for bad_entrant in ["Alice Smith", "alice@example.com", ENTRANT[:63], ENTRANT + "0", "g" * 64]:
        with direct_vm.expect_revert(BAD_ENTRANT_ID):
            contract.claim_milestone(bad_entrant, ROLE, "FOUNDATION", hashes, levels, roles)

    for bad_hash in [hashes[0][:40], "z" * 64, "https://snaplink.example/work/1", ""]:
        bad = list(hashes)
        bad[2] = bad_hash
        with direct_vm.expect_revert(BAD_WORK_HASH):
            contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", bad, levels, roles)

    for bad_level in ["", "   ", "SELF REPORTED", "ATTESTED!", "X" * 33]:
        bad = list(levels)
        bad[4] = bad_level
        with direct_vm.expect_revert(BAD_EVIDENCE_LEVEL):
            contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, bad, roles)

    with direct_vm.expect_revert(BAD_WORK_RECORDS):
        contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, levels[:24], roles)
    with direct_vm.expect_revert(BAD_WORK_RECORDS):
        contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, levels, roles + [ROLE])
    with direct_vm.expect_revert(BAD_WORK_RECORDS):
        contract.claim_milestone(ENTRANT, ROLE, "FOUNDATION", hashes, levels[:24] + [7], roles)
    assert contract.get_claim_count() == 0


# --- owner-managed catalogue ----------------------------------------------------------------

def test_refuses_claims_and_catalogue_changes_from_anyone_but_the_owner(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy)
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(NOT_OWNER):
            contract.add_milestone("ASCENT", 100)
        with direct_vm.expect_revert(NOT_OWNER):
            claim(contract, "FOUNDATION", records(25))
    assert contract.get_claim_count() == 0
    assert len(json.loads(contract.get_catalogue())) == 2


def test_owner_adds_a_milestone_between_foundation_and_zenith(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_deploy)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    assert contract.get_milestone("foundation") == 25
    assert contract.get_milestone("ZENITH") == 10000

    assert contract.add_milestone(" Ascent ", 100) == {"milestone": "ASCENT", "count": 100}
    assert json.loads(contract.get_catalogue()) == [{"milestone": "FOUNDATION", "count": 25},
                                                   {"milestone": "ZENITH", "count": 10000},
                                                   {"milestone": "ASCENT", "count": 100}]
    result = claim(contract, "ascent", records(99))
    assert result["verdict"] == "NOT_REACHED"
    assert result["shortfall"] == 1

    with direct_vm.expect_revert(MILESTONE_EXISTS):
        contract.add_milestone("ascent", 200)
    with direct_vm.expect_revert(MILESTONE_EXISTS):
        contract.add_milestone("ZENITH", 10000)
    for bad_name in ["", "9TO5", "SUMMIT PEAK", "S" * 33]:
        with direct_vm.expect_revert(BAD_MILESTONE_NAME):
            contract.add_milestone(bad_name, 50)
    for bad_count in [0, -5, 10001, True]:
        with direct_vm.expect_revert(BAD_MILESTONE_COUNT):
            contract.add_milestone("SUMMIT", bad_count)
    assert contract.get_milestone("ASCENT") == 100
    assert len(json.loads(contract.get_catalogue())) == 3


# --- views ------------------------------------------------------------------------------------

def test_views_and_rules(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    rules = json.loads(contract.get_rules())
    assert rules["counting_levels"] == ["ATTESTED", "SNAPLINK_VERIFIED"]
    assert rules["max_records"] == 10000
    for word in ["likes", "followers", "votes", "voting", "paid", "subscription", "premium", "membership",
                 "boost", "boosted"]:
        assert word in rules["forbidden_words"]
    assert contract.get_claim_count() == 0
    with direct_vm.expect_revert(BAD_INDEX):
        contract.get_claim(0)
    with direct_vm.expect_revert(NOT_CONFIRMED):
        contract.get_confirmation(ENTRANT, ROLE, "FOUNDATION")
    with direct_vm.expect_revert(BAD_ENTRANT_ID):
        contract.is_confirmed("Alice Smith", ROLE, "FOUNDATION")
