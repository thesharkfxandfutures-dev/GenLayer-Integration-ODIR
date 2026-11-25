"""Direct-mode tests for contracts/factory/service_medal_award.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 10 and the award-contract rules. The LLM is mocked (the contract reads no
web page), so these tests check the contract's own logic (input checks, refusals, the
forbidden-signal filter, parsing the model's count, the verdict and gap derived from it,
storage, the validator's comparison), not a model's judgment or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_service_medal_award.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "service_medal_award.py")

ROLE = "wedding_photographer"
ENTRANT = hashlib.sha256(b"snaplink public entrant id 0001").hexdigest()
OTHER_ENTRANT = hashlib.sha256(b"snaplink public entrant id 0002").hexdigest()
ACTIVITY = hashlib.sha256(b"full dated activity records, kept off chain").hexdigest()
SUMMARY = (
    "Dated jobs credited as wedding_photographer:\n"
    "2019-06-14 wedding, Kent\n2020-07-02 wedding, Surrey\n2021-05-29 wedding, Kent\n"
    "2022-08-20 wedding, Essex\n2023-06-10 wedding, Kent\n2024-09-07 wedding, Sussex\n"
    "2025-07-19 wedding, Kent"
)
SUMMARY_SHORT = "Dated jobs credited as wedding_photographer: 2023-04-01 wedding; 2024-05-11 wedding."

ERR_FORBIDDEN = ("[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid "
                 "plan, subscription, premium or membership tier, or a boost")
ERR_YEARS = "[EXPECTED] MEDAL_YEARS_NOT_OFFERED: medal_years must be 1, 5, 10, 15, 20 or 25"
ERR_DECIDED = "[EXPECTED] MEDAL_ALREADY_DECIDED: this entrant already has a decision for this role and medal"
ERR_NO_DECISION = "[EXPECTED] NO_DECISION: no decision is stored for this entrant, role and medal"


def answer(years, reason="Counted from the earliest to the latest dated job."):
    return json.dumps({"years_shown": years, "reason": reason})


def deploy(direct_vm, direct_deploy, direct_owner):
    direct_vm.sender = direct_owner
    return direct_deploy(CONTRACT)


def decide(contract, entrant=ENTRANT, role=ROLE, years=5, summary=SUMMARY, activity=ACTIVITY):
    return contract.decide_medal(entrant, role, years, summary, activity)


def key(entrant=ENTRANT, role=ROLE, years=5):
    return entrant + "|" + role + "|" + str(years)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def stored(contract, medal_key=None):
    return json.loads(contract.get_decision_by_key(medal_key or key()))


# --- answers -------------------------------------------------------------------------

def test_medal_confirmed_when_the_records_show_the_years(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(6, "Dated jobs from 2019-06-14 to 2025-07-19, one in every year."))

    result = decide(contract, years=5)

    assert result == {"medal_key": key(), "medal_years": 5, "verdict": "MEDAL_CONFIRMED", "gap": 0,
                      "reason": "Dated jobs from 2019-06-14 to 2025-07-19, one in every year."}
    record = stored(contract)
    assert record == {
        "medal_key": key(), "entrant_id": ENTRANT, "role_key": ROLE, "medal_years": 5,
        "activity_summary": SUMMARY, "activity_sha256": ACTIVITY, "verdict": "MEDAL_CONFIRMED", "gap": 0,
        "reason": "Dated jobs from 2019-06-14 to 2025-07-19, one in every year.",
        "decided_by": address_hex(direct_owner).lower(),
    }
    assert json.loads(contract.get_decision(ENTRANT.upper(), ROLE, 5)) == record
    assert contract.has_decision(ENTRANT, ROLE, 5) is True
    assert contract.has_decision(ENTRANT, ROLE, 10) is False
    assert contract.get_decision_count() == 1
    assert contract.get_decision_key(0) == key()


def test_not_yet_reports_the_gap(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(6, "Six whole years of dated jobs."))

    result = decide(contract, years=10)

    assert result == {"medal_key": key(years=10), "medal_years": 10, "verdict": "NOT_YET", "gap": 4,
                      "reason": "Six whole years of dated jobs."}
    record = stored(contract, key(years=10))
    assert record["verdict"] == "NOT_YET"
    assert record["gap"] == 4


def test_verdict_and_gap_follow_from_the_count_for_every_medal(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(12))
    expected = {1: ("MEDAL_CONFIRMED", 0), 5: ("MEDAL_CONFIRMED", 0), 10: ("MEDAL_CONFIRMED", 0),
                15: ("NOT_YET", 3), 20: ("NOT_YET", 8), 25: ("NOT_YET", 13)}
    for years in [1, 5, 10, 15, 20, 25]:
        result = decide(contract, years=years)
        assert (result["verdict"], result["gap"]) == expected[years]
        assert result["medal_key"] == key(years=years)
    assert contract.get_decision_count() == 6
    assert json.loads(contract.get_medal_years()) == [1, 5, 10, 15, 20, 25]


def test_edges_exact_years_one_short_and_none(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    cases = [(5, ENTRANT, "MEDAL_CONFIRMED", 0), (4, OTHER_ENTRANT, "NOT_YET", 1)]
    for count, entrant, verdict, gap in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer(count))
        result = decide(contract, entrant=entrant, years=5)
        assert (result["verdict"], result["gap"]) == (verdict, gap)
    # No dated activity in the role at all: the whole medal is the gap.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(0, "No dated activity in the role."))
    result = decide(contract, years=25, summary="Has worked as a wedding photographer for many years.")
    assert (result["verdict"], result["gap"]) == ("NOT_YET", 25)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(1))
    assert decide(contract, years=1, summary=SUMMARY_SHORT)["verdict"] == "MEDAL_CONFIRMED"


def test_prompt_carries_the_public_inputs_only(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the counting rules, the no-forbidden-signal instruction, the role
    # and the summary (sorted keys), and the absence of the entrant id, the activity hash and
    # the medal sought (the model counts without knowing the target).
    direct_vm.mock_llm(r"(?s)^(?!.*" + ENTRANT + r")(?!.*" + ACTIVITY + r")(?!.*medal_years)"
                       r".*only activity in the named role that carries a date counts"
                       r".*successive 12-month periods.*has ended by the date of the latest dated activity"
                       r".*Never weigh likes, followers, votes.*INPUT_JSON"
                       r".*\"activity_summary\":\"Dated jobs credited as wedding_photographer:\\n2019-06-14"
                       r".*2025-07-19 wedding, Kent\",\"role_key\":\"wedding_photographer\"}$",
                       answer(6))
    assert decide(contract, years=20)["gap"] == 14


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_medal_years_outside_the_six(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    # No LLM mock: the refusal comes before any model call.
    for years in [0, 2, 3, 4, 6, 9, 11, 30, 50, -5, True, "5", None]:
        with direct_vm.expect_revert(ERR_YEARS):
            decide(contract, years=years)
        with direct_vm.expect_revert(ERR_YEARS):
            contract.get_decision(ENTRANT, ROLE, years)
    assert contract.get_decision_count() == 0


def test_refuses_the_same_medal_twice(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(3))
    assert decide(contract, years=5)["verdict"] == "NOT_YET"
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(9))

    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, years=5)
    # Same medal with the entrant id written in upper case, a new summary and a new hash: still refused.
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, entrant=" " + ENTRANT.upper() + " ", summary=SUMMARY_SHORT, activity=OTHER_ENTRANT)
    assert stored(contract)["verdict"] == "NOT_YET"
    assert stored(contract)["gap"] == 2
    assert contract.get_decision_count() == 1

    # Another medal, role or entrant is a different medal.
    assert decide(contract, years=1)["verdict"] == "MEDAL_CONFIRMED"
    decide(contract, role="portrait_photographer")
    decide(contract, entrant=OTHER_ENTRANT)
    assert contract.get_decision_count() == 4
    # A confirmed medal is refused the same way.
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, years=1)
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, entrant=OTHER_ENTRANT)


# --- award-contract rules: forbidden selection signals -----------------------------------

def test_refuses_an_activity_summary_with_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    summaries = [
        SUMMARY + "\nPortfolio has 9,000 likes.",                            # likes
        "Active since 2019-06-14 with 20k FOLLOWERS.",                       # followers
        "2019-06-14 wedding; won the community votes in 2021.",              # votes
        "Clients kept voting for this photographer since 2018-01-01.",       # voting
        "Upvoted top photographer every year since 2015-03-02.",             # upvoted
        "On the Pro paid plan since 2019-06-14.",                            # paid plan
        "2019-06-14 wedding. Subscription active since 2019.",               # subscription
        "Premium member, dated jobs from 2010-01-01.",                       # premium
        "Highest membership tier since 2019-06-14.",                         # membership tier
        "Profile #Boosted from 2020-01-01 to 2025-01-01.",                   # boosted
        "2019-06-14 wedding after a boost.",                                 # boost
    ]
    for summary in summaries:
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            decide(contract, summary=summary)
    assert contract.get_decision_count() == 0

    # Whole words only: these contain a term inside a longer word and are accepted.
    direct_vm.mock_llm(r"INPUT_JSON", answer(6))
    result = decide(contract, summary=SUMMARY + "\nA devoted photographer; a strong likeness in every portrait.")
    assert result["verdict"] == "MEDAL_CONFIRMED"
    assert json.loads(contract.get_forbidden_signals())[0] == "likes"


def test_refuses_a_role_key_with_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    for role in ["premium_photographer", "boosted_editor", "paid_plan_member", "followers_curator",
                 "votes_counter"]:
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            decide(contract, role=role)
    assert contract.get_decision_count() == 0


# --- other refusals ---------------------------------------------------------------------

def test_refuses_malformed_role_keys(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    bad_role = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 48 characters "
                "from a-z 0-9 _")
    for role in ["", "a", "Wedding_photographer", "wedding-photographer", "wedding photographer", "_wedding",
                 "wedding_", "wedding__photographer", "1st_photographer", "x" * 49, None]:
        with direct_vm.expect_revert(bad_role):
            decide(contract, role=role)
        with direct_vm.expect_revert(bad_role):
            contract.has_decision(ENTRANT, role, 5)
    assert contract.get_decision_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer(5))
    assert decide(contract, role="drone_pilot_2")["medal_key"] == key(role="drone_pilot_2")
    assert decide(contract, role="x" * 48)["verdict"] == "MEDAL_CONFIRMED"


def test_refuses_malformed_entrant_ids_and_activity_hashes(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    bad_entrant = ("[EXPECTED] BAD_ENTRANT_ID: entrant_id must be 64 hexadecimal characters "
                   "(a public hash, never a name)")
    bad_activity = "[EXPECTED] BAD_ACTIVITY_HASH: activity_sha256 must be 64 hexadecimal characters"
    for bad in ["", "Jane Doe", "jane@example.com", "g" * 64, ENTRANT[:63], ENTRANT + "0", "0x" + ENTRANT[:62],
                None]:
        with direct_vm.expect_revert(bad_entrant):
            decide(contract, entrant=bad)
        with direct_vm.expect_revert(bad_activity):
            decide(contract, activity=bad)
    with direct_vm.expect_revert(bad_entrant):
        contract.get_decision("Jane Doe", ROLE, 5)
    assert contract.get_decision_count() == 0
    # Upper-case hex is accepted and stored lower-case.
    direct_vm.mock_llm(r"INPUT_JSON", answer(5))
    decide(contract, entrant=ENTRANT.upper(), activity=ACTIVITY.upper())
    assert stored(contract)["entrant_id"] == ENTRANT
    assert stored(contract)["activity_sha256"] == ACTIVITY


def test_refuses_empty_or_long_activity_summaries(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "   ", "\n\t", None]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_ACTIVITY_SUMMARY: activity_summary must not be empty"):
            decide(contract, summary=bad)
    with direct_vm.expect_revert(
            "[EXPECTED] ACTIVITY_SUMMARY_TOO_LONG: activity_summary must be at most 4000 characters"):
        decide(contract, summary="2019-06-14 " + "x" * 3990)
    assert contract.get_decision_count() == 0
    # 4000 characters after trimming is accepted, and the stored summary is trimmed.
    direct_vm.mock_llm(r"INPUT_JSON", answer(0))
    long_summary = "2019-06-14 " + "x" * 3989
    assert len(long_summary) == 4000
    assert decide(contract, summary="  " + long_summary + "\n")["verdict"] == "NOT_YET"
    assert stored(contract)["activity_summary"] == long_summary


def test_only_the_owner_decides(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(
                "[EXPECTED] OWNER_ONLY: only the contract owner can request a medal decision"):
            decide(contract)
    assert contract.get_decision_count() == 0
    assert contract.has_decision(ENTRANT, ROLE, 5) is False


def test_reads_on_a_fresh_contract(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    assert contract.get_decision_count() == 0
    assert contract.get_medal_years() == "[1,5,10,15,20,25]"
    assert "boost" in json.loads(contract.get_forbidden_signals())
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: nothing at this index"):
        contract.get_decision_key(0)
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_decision_key(-1)
    with direct_vm.expect_revert(ERR_NO_DECISION):
        contract.get_decision(ENTRANT, ROLE, 5)
    with direct_vm.expect_revert(ERR_NO_DECISION):
        contract.get_decision_by_key(key())


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    no_years = "[LLM_ERROR] the model returned no whole number of years_shown from 0 to 100"
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        ("[6]", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"reason": "x"}), no_years),
        (answer(-1), no_years),
        (answer(101), no_years),
        (answer("4.5"), no_years),
        (answer("1000"), no_years),
        (answer("five"), no_years),
        (answer("6 years"), no_years),
        (answer(True), no_years),
        (answer(None), no_years),
        (answer(6, "   "), "[LLM_ERROR] the model returned no reason"),
        (json.dumps({"years_shown": 6}), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            decide(contract)
    assert contract.get_decision_count() == 0

    # A whole number written as text is read as the number; 100 is the largest count accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(" 7 "))
    assert decide(contract, years=10)["gap"] == 3
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(100))
    assert decide(contract, years=25)["verdict"] == "MEDAL_CONFIRMED"


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(6, "Leader wording."))
    decide(contract, years=5)

    # Same verdict word, another count above the medal and another reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(5, "Other words."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(9, "More years counted."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(4, "One year short."))
    assert direct_vm.run_validator() is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_on_not_yet_needs_a_gap_within_one_year(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(7, "Leader: seven years."))
    assert decide(contract, years=10)["gap"] == 3

    for count, agrees in [(7, True), (6, True), (8, True), (5, False), (9, False), (0, False), (10, False)]:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer(count, "Validator wording."))
        assert direct_vm.run_validator() is agrees, count


def test_validator_rejects_forged_or_malformed_leader_results(direct_vm, direct_deploy, direct_owner):
    contract = deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(3))
    decide(contract, years=5)
    # The validator itself counts 3 (NOT_YET, gap 2) throughout.
    genuine = {"verdict": "NOT_YET", "gap": 2, "years_shown": 3, "reason": "x"}
    assert direct_vm.run_validator(leader_result=genuine) is True
    forged = [
        {"verdict": "MEDAL_CONFIRMED", "gap": 0, "years_shown": 3, "reason": "x"},   # verdict not from count
        {"verdict": "NOT_YET", "gap": 1, "years_shown": 3, "reason": "x"},           # gap not from count
        {"verdict": "NOT_YET", "gap": True, "years_shown": 4, "reason": "x"},        # gap not a number
        {"verdict": "NOT_YET", "gap": 2, "years_shown": "3", "reason": "x"},         # count not a number
        {"verdict": "NOT_YET", "gap": 2, "years_shown": 3},                          # no reason
        {"verdict": "NOT_YET", "gap": 2, "years_shown": 3, "reason": "  "},          # blank reason
        {"verdict": "MEDAL_CONFIRMED", "gap": 0, "years_shown": 101, "reason": "x"},  # count out of range
        {"verdict": "NOT_YET", "gap": 6, "years_shown": -1, "reason": "x"},          # negative count
        {"verdict": "YES", "gap": 2, "years_shown": 3, "reason": "x"},               # not a verdict word
    ]
    for leader in forged:
        assert direct_vm.run_validator(leader_result=leader) is False, leader
    assert direct_vm.run_validator(leader_result="NOT_YET") is False
    assert direct_vm.run_validator(leader_result=None) is False
