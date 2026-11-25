"""Direct-mode tests for contracts/factory/recognition_plaque_award.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (storage), then written to the owner's
row 8 and the award-contract rules. The contract makes no web or LLM call (the decision is
integer arithmetic), so nothing is mocked and no validator is captured. These tests check the
contract's own logic (the band arithmetic, refusals, storage, views), not GenVM on a network.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_recognition_plaque_award.py -v
"""
import hashlib
import json
from pathlib import Path

import pytest

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "recognition_plaque_award.py")

ROLE = "wedding_photographer"
SCOPE = "city"
AREA = "GB-LND"
SEASON = "2026"
BASIS = "Verified completed bookings in the 2026 season, each entrant counted once"
SNAPSHOT = hashlib.sha256(b"wedding_photographer city GB-LND 2026 ranking snapshot").hexdigest()
OTHER_SNAPSHOT = hashlib.sha256(b"a different ranking snapshot").hexdigest()

ERR_NOT_ISSUER = "[EXPECTED] NOT_ISSUER: only the issuer that deployed this contract can record a verdict"
ERR_BAD_ENTRANT_ID = "[EXPECTED] BAD_ENTRANT_ID: entrant_id must be a public hash of 64 hexadecimal characters, never a name"
ERR_BAD_SNAPSHOT_HASH = "[EXPECTED] BAD_SNAPSHOT_HASH: snapshot_sha256 must be 64 hexadecimal characters"
ERR_BAD_ROLE_KEY = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case of 2 to 48 characters "
                    "(a-z, 0-9, single '_' between words), starting with a letter")
ERR_BAD_SCOPE = "[EXPECTED] BAD_SCOPE: scope must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_AREA_CODE = "[EXPECTED] BAD_AREA_CODE: area_code must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_SEASON = "[EXPECTED] BAD_SEASON: season must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_RANKING_BASIS = "[EXPECTED] BAD_RANKING_BASIS: ranking_basis must be 1 to 200 printable ASCII characters of public text"
ERR_FORBIDDEN_SIGNAL = ("[EXPECTED] FORBIDDEN_SIGNAL: likes, followers, votes, a paid plan or a boost "
                        "must never select an award")
ERR_BAD_BAND = "[EXPECTED] BAD_BAND: band must be TOP_1, TOP_3, TOP_5 or TOP_10"
ERR_BAD_ENTRANTS = "[EXPECTED] BAD_ENTRANTS: eligible_entrants must be a whole number of at most 1000000000"
ERR_COHORT_TOO_SMALL = "[EXPECTED] COHORT_TOO_SMALL: eligible_entrants must be at least 100"
ERR_BAD_RANK = "[EXPECTED] BAD_RANK: rank must be a whole number from 1 to eligible_entrants"
ERR_ALREADY_DECIDED = "[EXPECTED] ALREADY_DECIDED: this entrant already has a verdict for this role, area and season"
ERR_COHORT_MISMATCH = ("[EXPECTED] COHORT_MISMATCH: this role, area and season is pinned to another "
                       "snapshot_sha256 or eligible_entrants")
ERR_UNKNOWN_VERDICT = "[EXPECTED] UNKNOWN_VERDICT: no verdict is stored for this entrant, role, area and season"
ERR_UNKNOWN_COHORT = "[EXPECTED] UNKNOWN_COHORT: no cohort is stored for this role, area and season"
ERR_BAD_INDEX = "[EXPECTED] BAD_INDEX: no verdict at this index"


def entrant(n):
    """A public entrant hash, never a name."""
    return hashlib.sha256(("snaplink entrant " + str(n)).encode()).hexdigest()


ENTRANT = entrant(1)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def deploy(direct_deploy):
    """Deployed by the default sender (direct_owner), which becomes the issuer."""
    return direct_deploy(CONTRACT)


def decide(contract, who=ENTRANT, role=ROLE, scope=SCOPE, area=AREA, season=SEASON, basis=BASIS,
           rank=12, eligible=1260, band="TOP_1", snapshot=SNAPSHOT):
    return contract.decide_band(who, role, scope, area, season, basis, rank, eligible, band, snapshot)


def verdict(contract, who=ENTRANT, role=ROLE, scope=SCOPE, area=AREA, season=SEASON):
    return json.loads(contract.get_verdict(who, role, scope, area, season))


# --- answers ---------------------------------------------------------------------------

def test_band_confirmed_by_rank_and_stored_with_the_snapshot(direct_deploy, direct_owner):
    contract = deploy(direct_deploy)

    result = decide(contract, rank=12, eligible=1260, band="TOP_1")

    assert result == {
        "verdict": "BAND_CONFIRMED",
        "band": "TOP_1",
        "actual_percentage": "0.9524",
        "rank": 12,
        "eligible_entrants": 1260,
        "reason": "rank 12 of 1260: 12 x 100 = 1200 <= 1 x 1260 = 1260, so TOP_1 holds",
    }
    assert verdict(contract) == {
        "entrant_id": ENTRANT,
        "role_key": ROLE,
        "scope": "city",
        "area_code": "gb-lnd",
        "season": "2026",
        "ranking_basis": BASIS,
        "rank": 12,
        "eligible_entrants": 1260,
        "band": "TOP_1",
        "band_percent": 1,
        "verdict": "BAND_CONFIRMED",
        "actual_percentage": "0.9524",
        "reason": "rank 12 of 1260: 12 x 100 = 1200 <= 1 x 1260 = 1260, so TOP_1 holds",
        "snapshot_sha256": SNAPSHOT,
        "issued_by": address_hex(direct_owner).lower(),
    }
    assert contract.get_verdict_count() == 1


def test_not_eligible_with_the_actual_percentage_where_rounding_would_say_one_percent(direct_deploy):
    contract = deploy(direct_deploy)
    # 2 / 199 = 1.005...%: a percentage rounded to whole numbers says "1%", the rank says no.
    assert round(2 * 100 / 199) == 1

    result = decide(contract, rank=2, eligible=199, band="TOP_1")

    assert result == {
        "verdict": "NOT_ELIGIBLE",
        "band": "TOP_1",
        "actual_percentage": "1.0051",
        "rank": 2,
        "eligible_entrants": 199,
        "reason": "rank 2 of 199: 2 x 100 = 200 > 1 x 199 = 199, so TOP_1 does not hold",
    }
    assert verdict(contract)["verdict"] == "NOT_ELIGIBLE"


def test_displayed_percentage_rounds_up_so_it_never_reads_inside_a_band_that_fails(direct_deploy):
    contract = deploy(direct_deploy)
    # 100001 / 10000001 = 1.0000099...%: truncated to 4 places it would read "1.0000".
    result = decide(contract, rank=100001, eligible=10000001, band="TOP_1")

    assert result["verdict"] == "NOT_ELIGIBLE"
    assert result["actual_percentage"] == "1.0001"


def test_exact_boundaries_of_all_four_bands(direct_deploy):
    contract = deploy(direct_deploy)
    cases = [
        ("TOP_1", 10, "BAND_CONFIRMED", "1.0000"),
        ("TOP_1", 11, "NOT_ELIGIBLE", "1.1000"),
        ("TOP_3", 30, "BAND_CONFIRMED", "3.0000"),
        ("TOP_3", 31, "NOT_ELIGIBLE", "3.1000"),
        ("TOP_5", 50, "BAND_CONFIRMED", "5.0000"),
        ("TOP_5", 51, "NOT_ELIGIBLE", "5.1000"),
        (" top_10 ", 100, "BAND_CONFIRMED", "10.0000"),
        ("TOP_10", 101, "NOT_ELIGIBLE", "10.1000"),
    ]
    n = 0
    while n < len(cases):
        band, rank, word, percentage = cases[n]
        result = decide(contract, who=entrant(100 + n), rank=rank, eligible=1000, band=band)
        assert result["verdict"] == word, (band, rank)
        assert result["actual_percentage"] == percentage, (band, rank)
        assert result["band"] == band.strip().upper()
        n += 1
    assert json.loads(contract.get_cohort(ROLE, SCOPE, AREA, SEASON)) == {
        "role_key": ROLE, "scope": "city", "area_code": "gb-lnd", "season": "2026",
        "snapshot_sha256": SNAPSHOT, "eligible_entrants": 1000, "verdicts": 8,
    }


def test_no_llm_or_web_call_and_no_validator_is_needed(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    direct_vm.strict_mocks = True

    assert decide(contract)["verdict"] == "BAND_CONFIRMED"
    with pytest.raises(RuntimeError, match="No validator captured"):
        direct_vm.run_validator()


# --- must refuse (the owner's row) --------------------------------------------------------

def test_refuses_a_band_outside_the_four(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    bad_bands = ["TOP_2", "TOP_20", "TOP_0", "TOP_1.0", "TOP 1", "1", "1%", "top-1", ""]
    n = 0
    while n < len(bad_bands):
        with direct_vm.expect_revert(ERR_BAD_BAND):
            decide(contract, band=bad_bands[n])
        n += 1
    assert contract.get_verdict_count() == 0


def test_refuses_a_cohort_below_the_minimum(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    sizes = [99, 10, 1, 0, -5]
    n = 0
    while n < len(sizes):
        with direct_vm.expect_revert(ERR_COHORT_TOO_SMALL):
            decide(contract, rank=1, eligible=sizes[n])
        n += 1
    assert contract.get_verdict_count() == 0

    # 100 entrants is the minimum: rank 1 of 100 holds Top 1%.
    assert decide(contract, rank=1, eligible=100, band="TOP_1")["verdict"] == "BAND_CONFIRMED"
    assert json.loads(contract.get_rules())["min_eligible_entrants"] == 100


def test_refuses_a_second_verdict_for_the_same_entrant_role_area_and_season(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    assert decide(contract, rank=13, eligible=1260, band="TOP_1")["verdict"] == "NOT_ELIGIBLE"

    # Any band, any rank, and the same keys written differently are all the same verdict slot.
    with direct_vm.expect_revert(ERR_ALREADY_DECIDED):
        decide(contract, rank=13, eligible=1260, band="TOP_3")
    with direct_vm.expect_revert(ERR_ALREADY_DECIDED):
        decide(contract, rank=12, eligible=1260, band="TOP_1")
    with direct_vm.expect_revert(ERR_ALREADY_DECIDED):
        decide(contract, who=ENTRANT.upper(), area="gb-lnd", scope="CITY", season=" 2026 ", band="TOP_10")
    stored = verdict(contract)
    assert stored["verdict"] == "NOT_ELIGIBLE"
    assert stored["band"] == "TOP_1"
    assert stored["rank"] == 13
    assert contract.get_verdict_count() == 1

    # A different season, role, area, scope or entrant is a different verdict.
    decide(contract, season="2027", snapshot=OTHER_SNAPSHOT, band="TOP_3")
    decide(contract, role="event_dj", band="TOP_3")
    decide(contract, area="GB-MAN", band="TOP_3")
    decide(contract, scope="region", band="TOP_3")
    decide(contract, who=entrant(2), rank=12, band="TOP_1")
    assert contract.get_verdict_count() == 6


def test_refuses_forbidden_selection_signals_in_any_text_input(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    cases = [
        # likes
        {"basis": "Most likes this season"},
        {"basis": "Ranked by like count on posts"},
        {"role": "most_liked_creator"},
        # followers
        {"basis": "Ranked by FOLLOWERS gained"},
        {"area": "follower-hub"},
        # votes
        {"basis": "Community votes"},
        {"season": "voting-2026"},
        {"basis": "Upvotes from clients"},
        # paid plan / subscription / premium / membership tier
        {"basis": "Completed bookings, paid plan members first"},
        {"basis": "Subscription tier"},
        {"scope": "premium"},
        {"basis": "Gold membership tier holders"},
        {"basis": "Paid-Membership holders"},
        # boost
        {"area": "boosted"},
        {"basis": "Bookings plus profile boost"},
        {"basis": "BOOSTING"},
    ]
    n = 0
    while n < len(cases):
        case = cases[n]
        with direct_vm.expect_revert(ERR_FORBIDDEN_SIGNAL):
            decide(contract, role=case.get("role", ROLE), scope=case.get("scope", SCOPE),
                   area=case.get("area", AREA), season=case.get("season", SEASON),
                   basis=case.get("basis", BASIS))
        n += 1
    assert contract.get_verdict_count() == 0

    # Whole words only: words that merely contain a term, and paid bookings, are allowed.
    ok = decide(contract, role="voice_coach",
                basis="Completed paid bookings; unlike-for-like reviews, likeness and followed-up jobs ignored")
    assert ok["verdict"] == "BAND_CONFIRMED"


def test_refuses_a_malformed_role_key_and_does_not_check_the_role_list(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    bad_keys = ["Wedding_Photographer", "wedding photographer", "wedding-photographer", "1st_dj", "_dj",
                "dj_", "dj__mc", "d", "x" * 49, ""]
    n = 0
    while n < len(bad_keys):
        with direct_vm.expect_revert(ERR_BAD_ROLE_KEY):
            decide(contract, role=bad_keys[n])
        n += 1
    assert contract.get_verdict_count() == 0

    # Shape only: a well-formed key that is not one of SnapLink's 45 roles is accepted.
    assert decide(contract, role="space_tour_guide")["verdict"] == "BAND_CONFIRMED"
    assert decide(contract, role="a" * 48)["verdict"] == "BAND_CONFIRMED"


# --- further refusals -----------------------------------------------------------------------

def test_refuses_a_cohort_that_disagrees_with_its_pinned_snapshot_or_size(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    decide(contract, rank=12, eligible=1260)

    with direct_vm.expect_revert(ERR_COHORT_MISMATCH):
        decide(contract, who=entrant(2), rank=5, eligible=1260, snapshot=OTHER_SNAPSHOT)
    with direct_vm.expect_revert(ERR_COHORT_MISMATCH):
        decide(contract, who=entrant(2), rank=5, eligible=1261)
    assert contract.get_verdict_count() == 1

    decide(contract, who=entrant(2), rank=5, eligible=1260, snapshot=SNAPSHOT.upper())
    assert json.loads(contract.get_cohort(ROLE, SCOPE, AREA, SEASON))["verdicts"] == 2


def test_refuses_a_sender_other_than_the_issuer(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_deploy)

    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(ERR_NOT_ISSUER):
            decide(contract)
    assert contract.get_verdict_count() == 0
    assert json.loads(contract.get_rules())["issuer"] == address_hex(direct_owner).lower()


def test_refuses_malformed_hashes_codes_basis_and_numbers(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    cases = [
        (ERR_BAD_ENTRANT_ID, {"who": "Jane Doe"}),
        (ERR_BAD_ENTRANT_ID, {"who": ENTRANT[:63]}),
        (ERR_BAD_ENTRANT_ID, {"who": ENTRANT + "0"}),
        (ERR_BAD_ENTRANT_ID, {"who": "g" * 64}),
        (ERR_BAD_SNAPSHOT_HASH, {"snapshot": ""}),
        (ERR_BAD_SNAPSHOT_HASH, {"snapshot": SNAPSHOT[:40]}),
        (ERR_BAD_SCOPE, {"scope": ""}),
        (ERR_BAD_SCOPE, {"scope": "city wide"}),
        (ERR_BAD_SCOPE, {"scope": "x" * 33}),
        (ERR_BAD_SCOPE, {"scope": "---"}),
        (ERR_BAD_SCOPE, {"scope": "city|x"}),
        (ERR_BAD_AREA_CODE, {"area": "GB LND"}),
        (ERR_BAD_AREA_CODE, {"area": "GB/LND"}),
        (ERR_BAD_SEASON, {"season": "2026 summer"}),
        (ERR_BAD_SEASON, {"season": ""}),
        (ERR_BAD_RANKING_BASIS, {"basis": ""}),
        (ERR_BAD_RANKING_BASIS, {"basis": "   "}),
        (ERR_BAD_RANKING_BASIS, {"basis": "x" * 201}),
        (ERR_BAD_RANKING_BASIS, {"basis": "Café bookings"}),
        (ERR_BAD_RANKING_BASIS, {"basis": "line\nbreak"}),
        (ERR_BAD_ENTRANTS, {"eligible": 1000000001}),
        (ERR_BAD_RANK, {"rank": 0}),
        (ERR_BAD_RANK, {"rank": -1}),
        (ERR_BAD_RANK, {"rank": 1261}),
    ]
    n = 0
    while n < len(cases):
        error, kwargs = cases[n]
        with direct_vm.expect_revert(error):
            decide(contract, **kwargs)
        n += 1
    assert contract.get_verdict_count() == 0

    # Limits are inclusive: rank == eligible, the largest cohort, 32-character codes, 200-character basis.
    assert decide(contract, rank=1260, eligible=1260, band="TOP_10")["verdict"] == "NOT_ELIGIBLE"
    assert decide(contract, who=entrant(2), rank=1, eligible=1000000000, season="x" * 32,
                  basis="b" * 200)["verdict"] == "BAND_CONFIRMED"


# --- views ------------------------------------------------------------------------------------

def test_views(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_deploy)
    assert contract.get_verdict_count() == 0
    with direct_vm.expect_revert(ERR_UNKNOWN_VERDICT):
        contract.get_verdict(ENTRANT, ROLE, SCOPE, AREA, SEASON)
    with direct_vm.expect_revert(ERR_UNKNOWN_COHORT):
        contract.get_cohort(ROLE, SCOPE, AREA, SEASON)
    with direct_vm.expect_revert(ERR_BAD_INDEX):
        contract.get_verdict_key(0)

    decide(contract)

    assert contract.get_verdict_count() == 1
    assert contract.get_verdict_key(0) == ENTRANT + "|wedding_photographer|city|gb-lnd|2026"
    with direct_vm.expect_revert(ERR_BAD_INDEX):
        contract.get_verdict_key(1)
    with direct_vm.expect_revert(ERR_BAD_INDEX):
        contract.get_verdict_key(-1)
    with direct_vm.expect_revert(ERR_BAD_ENTRANT_ID):
        contract.get_verdict("Jane Doe", ROLE, SCOPE, AREA, SEASON)
    assert verdict(contract, who=ENTRANT.upper(), area="gb-lnd")["verdict"] == "BAND_CONFIRMED"

    rules = json.loads(contract.get_rules())
    assert rules["bands"] == {"TOP_1": 1, "TOP_3": 3, "TOP_5": 5, "TOP_10": 10}
    assert rules["min_eligible_entrants"] == 100
    assert rules["max_eligible_entrants"] == 1000000000
    assert rules["percentage_places"] == 4
    assert "likes" in rules["forbidden_words"] and "boost" in rules["forbidden_words"]
    assert "paid plan" in rules["forbidden_phrases"]
    assert rules["issuer"] == address_hex(direct_owner).lower()
