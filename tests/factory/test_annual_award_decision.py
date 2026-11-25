"""Direct-mode tests for contracts/factory/annual_award_decision.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 11 and the award-contract rules. The LLM is mocked (the contract reads no
web page), so these tests check the contract's own logic (finalist-stage gate, input
checks, refusals, the forbidden-signal filter, parsing, the winner-is-a-finalist and
quoted-criterion checks, storage, the validator's comparison), not a model's judgment
or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_annual_award_decision.py -v
"""
import hashlib
import json
import re
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "annual_award_decision.py")

CRITERIA = (
    "SnapLink Photographer of the Year, published criteria, season 2026\n"
    "C1. A finalist must have at least 12 jobs credited in the named role during the season.\n"
    "C2. Only work delivered and credited on SnapLink during the season is considered.\n"
    "C3. The winner shows the strongest body of work across the season, judged on technical quality, "
    "consistency and client outcomes.\n"
    "C4. If finalists are level on C3, the finalist with more on-time deliveries in the season wins.\n"
    "C5. If no finalist meets C1 and C2, no award is made."
)
CRIT_C1 = "A finalist must have at least 12 jobs credited in the named role during the season."
CRIT_C3 = "The winner shows the strongest body of work across the season"
CRIT_C4 = "If finalists are level on C3, the finalist with more on-time deliveries in the season wins."
CRIT_C5 = "If no finalist meets C1 and C2, no award is made."

ROLE = "wedding_photographer"
CODE = "PHOTOGRAPHER_OF_THE_YEAR"
SEASON = 2026
AWARD_KEY = "wedding_photographer|PHOTOGRAPHER_OF_THE_YEAR|2026"

HASH_A = hashlib.sha256(b"finalist a private evidence bundle").hexdigest()
HASH_B = hashlib.sha256(b"finalist b private evidence bundle").hexdigest()
HASH_C = hashlib.sha256(b"finalist c private evidence bundle").hexdigest()
SUMMARY_A = ("38 jobs credited as wedding_photographer in season 2026, all delivered on SnapLink; "
             "36 on-time deliveries; published series of 12 weddings with consistent low-light work.")
SUMMARY_B = ("41 jobs credited as wedding_photographer in season 2026, all delivered on SnapLink; "
             "41 on-time deliveries; published work shows the widest technical range of the season.")
SUMMARY_C = "9 jobs credited as wedding_photographer in season 2026; strong editorial portfolio."

ERR_FORBIDDEN = ("[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid "
                 "plan, subscription, premium or membership tier, or a boost")
ERR_TOO_FEW = "[EXPECTED] TOO_FEW_FINALISTS: an award decision needs at least two finalists"
ERR_NOT_AT_FINALISTS = ("[EXPECTED] SEASON_NOT_AT_FINALISTS: this season has not reached the finalist stage; "
                        "awards are decided only after the owner opens the season's finalist stage")
ERR_DECIDED = "[EXPECTED] AWARD_ALREADY_DECIDED: this role, award and season already has a decision"
ERR_BAD_FINALISTS = ("[EXPECTED] BAD_FINALISTS: finalists_json must be a JSON array of at most 40000 characters "
                     "whose items are objects with exactly finalist_id, evidence_summary and evidence_sha256")

ALL_CODES = {
    "PHOTOGRAPHER_OF_THE_YEAR": "Photographer of the Year",
    "DESIGNER_OF_THE_YEAR": "Designer of the Year",
    "FILMMAKER_OF_THE_YEAR": "Filmmaker of the Year",
    "EMERGING_TALENT": "Emerging Talent",
    "CREATIVE_BUSINESS_OF_THE_YEAR": "Creative Business of the Year",
    "STUDIO_OF_THE_YEAR": "Studio of the Year",
}


def finalist(finalist_id, summary, evidence):
    return {"finalist_id": finalist_id, "evidence_summary": summary, "evidence_sha256": evidence}


FINALISTS = [
    finalist("fin-a1", SUMMARY_A, HASH_A),
    finalist("fin-b2", SUMMARY_B, HASH_B),
    finalist("fin-c3", SUMMARY_C, HASH_C),
]


def answer(decision, finalist_id="", quote=CRIT_C3, reason="One sentence."):
    return json.dumps({"decision": decision, "finalist_id": finalist_id, "criteria_quote": quote,
                       "reason": reason})


def setup(direct_vm, direct_deploy, direct_owner, open_stage=True):
    """The owner deploys and (by default) opens season 2026's finalist stage."""
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    if open_stage:
        assert contract.open_finalists(SEASON) == {"season_year": SEASON, "finalists_open": True}
    return contract


def decide(contract, role=ROLE, code=CODE, season=SEASON, criteria=CRITERIA, finalists=None):
    if finalists is None:
        finalists = FINALISTS
    payload = finalists if isinstance(finalists, str) else json.dumps(finalists)
    return contract.decide_award(role, code, season, criteria, payload)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def stored(contract, key=AWARD_KEY):
    return json.loads(contract.get_decision_by_key(key))


# --- answers -------------------------------------------------------------------------

def test_winner_names_one_finalist_and_quotes_the_criteria(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_decision_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2", CRIT_C3, "Widest range and all on time."))

    result = decide(contract)

    assert result == {"award_key": AWARD_KEY, "award_name": "Photographer of the Year", "decision": "WINNER",
                      "winner_id": "fin-b2", "criteria_quote": CRIT_C3,
                      "reason": "Widest range and all on time."}
    record = stored(contract)
    assert record == {
        "award_key": AWARD_KEY, "role_key": ROLE, "award_code": CODE, "award_name": "Photographer of the Year",
        "season_year": SEASON, "criteria_text": CRITERIA,
        "criteria_sha256": hashlib.sha256(CRITERIA.encode("utf-8")).hexdigest(),
        "finalists": FINALISTS, "decision": "WINNER", "winner_id": "fin-b2", "criteria_quote": CRIT_C3,
        "reason": "Widest range and all on time.", "decided_by": address_hex(direct_owner).lower(),
    }
    assert record["criteria_quote"] in CRITERIA
    assert json.loads(contract.get_decision(ROLE, " photographer_of_the_year ", SEASON)) == record
    assert contract.get_decision_count() == 1
    assert contract.get_decision_key(0) == AWARD_KEY


def test_no_award_when_no_finalist_meets_the_criteria(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # A finalist id sent with NO_AWARD is ignored: NO_AWARD never names a winner.
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "fin-a1", CRIT_C5, "Nobody meets C1 and C2."))
    weak = [finalist("fin-c3", SUMMARY_C, HASH_C),
            finalist("fin-d4", "4 jobs credited as wedding_photographer in season 2026.", HASH_A)]

    result = decide(contract, finalists=weak)

    assert result == {"award_key": AWARD_KEY, "award_name": "Photographer of the Year", "decision": "NO_AWARD",
                      "winner_id": "", "criteria_quote": CRIT_C5, "reason": "Nobody meets C1 and C2."}
    record = stored(contract)
    assert record["decision"] == "NO_AWARD"
    assert record["winner_id"] == ""
    assert [item["finalist_id"] for item in record["finalists"]] == ["fin-c3", "fin-d4"]


def test_every_annual_award_code_is_served(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert json.loads(contract.get_award_codes()) == ALL_CODES
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-a1", CRIT_C1))
    for code, name in ALL_CODES.items():
        result = decide(contract, code=code.lower())
        assert result["award_name"] == name
        assert result["award_key"] == ROLE + "|" + code + "|2026"
        assert result["winner_id"] == "fin-a1"
    assert contract.get_decision_count() == len(ALL_CODES)


def test_prompt_carries_the_public_inputs_and_no_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the instruction, the award, the criteria, every finalist's id and summary
    # (sorted keys, input order), the role and season, and the absence of every evidence hash.
    pattern = (r"(?s)^(?!.*" + HASH_A + r")(?!.*" + HASH_B + r")(?!.*" + HASH_C + r")"
               r".*place in the list.*Never weigh likes, followers, votes.*INPUT_JSON"
               r".*\"award_code\":\"PHOTOGRAPHER_OF_THE_YEAR\".*no award is made"
               r".*\"award_name\":\"Photographer of the Year\",\"finalists\":\["
               r"\{\"evidence_summary\":\"" + re.escape(SUMMARY_A) + r"\",\"finalist_id\":\"fin-a1\"\},"
               r"\{\"evidence_summary\":\"" + re.escape(SUMMARY_B) + r"\",\"finalist_id\":\"fin-b2\"\},"
               r"\{\"evidence_summary\":\"" + re.escape(SUMMARY_C) + r"\",\"finalist_id\":\"fin-c3\"\}\]"
               r",\"role_key\":\"wedding_photographer\",\"season_year\":2026\}$")
    direct_vm.mock_llm(pattern, answer("WINNER", "fin-a1", CRIT_C4))
    assert decide(contract)["criteria_quote"] == CRIT_C4


def test_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The criteria break the line between C1 and C2; the model's quote crosses it with a single
    # space, and the stored quote has every run of whitespace collapsed to one space.
    quote = "in the named role during the season. C2. Only work delivered"
    assert quote not in CRITERIA
    assert "in the named role during the season.\nC2. Only work delivered" in CRITERIA
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2", "  " + quote.replace("C2. Only", "C2.\n\t Only")))
    assert decide(contract)["criteria_quote"] == quote
    assert stored(contract)["criteria_quote"] == quote


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_fewer_than_two_finalists(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # No LLM mock: the refusal comes before any model call.
    for finalists in [[], [FINALISTS[0]], [finalist("solo", SUMMARY_A, HASH_A)]]:
        with direct_vm.expect_revert(ERR_TOO_FEW):
            decide(contract, finalists=finalists)
    # The same finalist twice is not two finalists.
    with direct_vm.expect_revert("[EXPECTED] DUPLICATE_FINALIST: each finalist_id may appear only once"):
        decide(contract, finalists=[FINALISTS[0], finalist("FIN-A1", SUMMARY_B, HASH_B)])
    assert contract.get_decision_count() == 0
    # Two finalists is enough.
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-a1", CRIT_C1))
    assert decide(contract, finalists=FINALISTS[:2])["winner_id"] == "fin-a1"


def test_refuses_a_decision_before_the_season_reaches_finalists(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner, open_stage=False)
    assert contract.is_finalists_open(SEASON) is False
    with direct_vm.expect_revert(ERR_NOT_AT_FINALISTS):
        decide(contract)
    assert contract.get_decision_count() == 0

    # Another season's finalist stage does not open this one.
    assert contract.open_finalists(2025) == {"season_year": 2025, "finalists_open": True}
    with direct_vm.expect_revert(ERR_NOT_AT_FINALISTS):
        decide(contract)
    contract.open_finalists(SEASON)
    assert contract.is_finalists_open(SEASON) is True
    assert json.loads(contract.get_finalist_seasons()) == [2025, 2026]
    with direct_vm.expect_revert(
            "[EXPECTED] SEASON_ALREADY_AT_FINALISTS: this season has already reached the finalist stage"):
        contract.open_finalists(SEASON)

    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2"))
    assert decide(contract)["decision"] == "WINNER"
    with direct_vm.expect_revert(ERR_NOT_AT_FINALISTS):
        decide(contract, season=2027)


def test_refuses_a_second_decision_for_the_same_award_and_season(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    contract.open_finalists(2025)
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "", CRIT_C5))
    decide(contract)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2", CRIT_C3))

    # A NO_AWARD is a decision: the award is locked for the season.
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract)
    # Same award written differently, other finalists and other criteria: still refused.
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, code=" Photographer_Of_The_Year ", criteria=CRITERIA + "\nC6. Extra.",
               finalists=[finalist("fin-x9", SUMMARY_B, HASH_B), finalist("fin-y8", SUMMARY_A, HASH_A)])
    assert stored(contract)["decision"] == "NO_AWARD"
    assert contract.get_decision_count() == 1

    # Another role, award or season is a different award.
    decide(contract, role="portrait_photographer")
    decide(contract, code="EMERGING_TALENT")
    decide(contract, season=2025)
    assert contract.get_decision_count() == 4
    with direct_vm.expect_revert(ERR_DECIDED):
        decide(contract, code="emerging_talent")


# --- award-contract rules: forbidden selection signals -----------------------------------

def test_refuses_an_evidence_summary_that_carries_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    summaries = [
        "38 credited jobs and 9,000 likes on the season's portfolio.",           # likes
        "Top finalist by FOLLOWERS in the region.",                              # followers
        "Won the community votes for the role.",                                 # votes
        "Clients kept voting for this finalist all season.",                     # voting
        "Finalist is on the Pro paid plan with 38 credited jobs.",               # paid plan
        "38 credited jobs; subscription active since January.",                  # subscription
        "Premium member, 38 credited jobs.",                                     # premium
        "Highest membership tier and 38 credited jobs.",                         # membership tier
        "Profile was #Boosted for the final month.",                             # boosted
        "Ranked first after a boost.",                                           # boost
    ]
    for summary in summaries:
        # The signal is refused wherever it sits in the finalist list.
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            decide(contract, finalists=[FINALISTS[0], finalist("fin-b2", summary, HASH_B)])
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            decide(contract, finalists=[finalist("fin-a1", summary, HASH_A), FINALISTS[1]])
    assert contract.get_decision_count() == 0

    # Whole words only: these contain a term inside a longer word and are accepted.
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2"))
    clean = finalist("fin-b2", "A devoted finalist with a strong likeness to the brief; 41 credited jobs.", HASH_B)
    assert decide(contract, finalists=[FINALISTS[0], clean])["decision"] == "WINNER"
    assert json.loads(contract.get_forbidden_signals())[0] == "likes"


def test_refuses_criteria_text_that_carries_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_criteria = [
        "C1. Ties are broken by the higher number of likes.",
        "C1. Ties are broken by follower count.",
        "C1. The public votes decide the winner.",
        "C1. Finalists on a paid plan get one extra point.",
        "C1. Premium members are ranked first.",
        "C1. Each membership tier adds a bonus.",
        "C1. Boosted profiles break ties.",
        "C1. Subscribers rank above others.",
    ]
    for criteria in bad_criteria:
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            decide(contract, criteria=CRITERIA + "\n" + criteria)
    assert contract.get_decision_count() == 0


# --- other refusals ---------------------------------------------------------------------

def test_refuses_more_than_ten_finalists(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    eleven = [finalist("fin-" + str(n), SUMMARY_A, HASH_A) for n in range(11)]
    with direct_vm.expect_revert(
            "[EXPECTED] TOO_MANY_FINALISTS: an award decision takes at most 10 finalists"):
        decide(contract, finalists=eleven)
    assert contract.get_decision_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-9"))
    assert decide(contract, finalists=eleven[:10])["winner_id"] == "fin-9"


def test_refuses_malformed_finalists_json(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    a, b = FINALISTS[0], FINALISTS[1]
    bad = [
        "not json",
        "",
        json.dumps({"finalists": FINALISTS}),
        json.dumps([a, "fin-b2"]),
        json.dumps([a, [b]]),
        json.dumps([a, {"finalist_id": "fin-b2", "evidence_summary": SUMMARY_B}]),
        json.dumps([a, dict(b, name="A Person")]),
        json.dumps([a, {"finalist_id": "fin-b2", "evidence_summary": SUMMARY_B, "evidence_hash": HASH_B}]),
        "[" + json.dumps(a) + "," + json.dumps(b) + "]" + " " * 40000,
    ]
    for payload in bad:
        with direct_vm.expect_revert(ERR_BAD_FINALISTS):
            decide(contract, finalists=payload)
    assert contract.get_decision_count() == 0


def test_refuses_bad_finalist_ids(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_id = ("[EXPECTED] BAD_FINALIST_ID: finalist_id must be a public id of 2 to 64 characters from "
              "a-z 0-9 _ - (never a name or email)")
    for finalist_id in ["", "a", "fin a1", "someone@example.com", "_fin", "-fin", "fin.a1", "x" * 65, 12, None]:
        with direct_vm.expect_revert(bad_id):
            decide(contract, finalists=[FINALISTS[0], finalist(finalist_id, SUMMARY_B, HASH_B)])
    assert contract.get_decision_count() == 0
    # Ids are trimmed and stored lower-case; 64 characters is the edge.
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "FIN-B2"))
    result = decide(contract, finalists=[finalist("x" * 64, SUMMARY_A, HASH_A), finalist(" FIN-B2 ", SUMMARY_B, HASH_B)])
    assert result["winner_id"] == "fin-b2"
    assert [item["finalist_id"] for item in stored(contract)["finalists"]] == ["x" * 64, "fin-b2"]


def test_refuses_malformed_evidence_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "not-a-hash", "g" * 64, HASH_B[:63], HASH_B + "0", 7]:
        with direct_vm.expect_revert(
                "[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters"):
            decide(contract, finalists=[FINALISTS[0], finalist("fin-b2", SUMMARY_B, bad)])
    assert contract.get_decision_count() == 0
    # Upper-case hex is accepted and stored lower-case.
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2"))
    decide(contract, finalists=[FINALISTS[0], finalist("fin-b2", SUMMARY_B, HASH_B.upper())])
    assert stored(contract)["finalists"][1]["evidence_sha256"] == HASH_B


def test_refuses_empty_or_long_evidence_summaries(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "   ", "\n\t", None]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty"):
            decide(contract, finalists=[FINALISTS[0], finalist("fin-b2", bad, HASH_B)])
    with direct_vm.expect_revert(
            "[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters"):
        decide(contract, finalists=[FINALISTS[0], finalist("fin-b2", "x" * 2001, HASH_B)])
    assert contract.get_decision_count() == 0


def test_refuses_malformed_role_keys(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_role = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters "
                "from a-z 0-9 _")
    for role in ["", "a", "Wedding_photographer", "wedding-photographer", "wedding photographer", "_wedding",
                 "wedding_", "wedding__photographer", "1st_photographer", "x" * 41]:
        with direct_vm.expect_revert(bad_role):
            decide(contract, role=role)
    assert contract.get_decision_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-a1"))
    assert decide(contract, role="drone_pilot_2")["award_key"] == "drone_pilot_2|PHOTOGRAPHER_OF_THE_YEAR|2026"
    assert decide(contract, role="x" * 40)["decision"] == "WINNER"


def test_refuses_unknown_award_codes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    unknown = ("[EXPECTED] UNKNOWN_AWARD_CODE: award_code must be PHOTOGRAPHER_OF_THE_YEAR, DESIGNER_OF_THE_YEAR, "
               "FILMMAKER_OF_THE_YEAR, EMERGING_TALENT, CREATIVE_BUSINESS_OF_THE_YEAR or STUDIO_OF_THE_YEAR")
    for code in ["", "PHOTOGRAPHER", "Photographer of the Year", "PHOTOGRAPHER-OF-THE-YEAR",
                 "CREATIVE_BUSINESS_AND_STUDIO_OF_THE_YEAR", "BEST_IN_SHOW", 7]:
        with direct_vm.expect_revert(unknown):
            decide(contract, code=code)
        with direct_vm.expect_revert(unknown):
            contract.get_decision(ROLE, code, SEASON)
    assert contract.get_decision_count() == 0


def test_refuses_bad_season_years(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_year = "[EXPECTED] BAD_SEASON_YEAR: season_year must be a whole year from 2000 to 2199"
    for year in [1999, 2200, 0, -2026, True, "2026"]:
        with direct_vm.expect_revert(bad_year):
            decide(contract, season=year)
        with direct_vm.expect_revert(bad_year):
            contract.open_finalists(year)
    assert json.loads(contract.get_finalist_seasons()) == [SEASON]


def test_refuses_bad_criteria_text(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_text = "[EXPECTED] BAD_CRITERIA_TEXT: criteria_text must be 1 to 8000 characters and not blank"
    for criteria in ["", "  \n ", "x" * 8001, None]:
        with direct_vm.expect_revert(bad_text):
            decide(contract, criteria=criteria)
    assert contract.get_decision_count() == 0
    long_criteria = CRITERIA + "\n" + "x" * (8000 - len(CRITERIA) - 1)
    assert len(long_criteria) == 8000
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "", CRIT_C5))
    assert decide(contract, criteria=long_criteria)["decision"] == "NO_AWARD"


def test_only_the_owner_writes(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    owner_only = ("[EXPECTED] OWNER_ONLY: only the contract owner can open a season's finalist stage or "
                  "request an award decision")
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(owner_only):
            contract.open_finalists(2025)
        with direct_vm.expect_revert(owner_only):
            decide(contract)
    assert contract.is_finalists_open(2025) is False
    assert contract.get_decision_count() == 0


def test_reads_refuse_missing_decisions_and_indexes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    no_decision = "[EXPECTED] NO_DECISION: no decision is stored for this award and season"
    with direct_vm.expect_revert(no_decision):
        contract.get_decision(ROLE, CODE, SEASON)
    with direct_vm.expect_revert(no_decision):
        contract.get_decision_by_key(AWARD_KEY)
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: nothing at this index"):
        contract.get_decision_key(0)
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_decision_key(-1)


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    winner_missing = "[LLM_ERROR] the model's WINNER does not name one of the finalist ids"
    bad_quote = "[LLM_ERROR] the model's criteria quote is not 10 to 400 characters quoted from the criteria text"
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"finalist_id": "fin-a1", "criteria_quote": CRIT_C1, "reason": "x"}),
         "[LLM_ERROR] the model returned no decision of WINNER or NO_AWARD"),
        (answer("YES", "fin-a1"), "no decision of WINNER or NO_AWARD"),
        (answer("WINNER: fin-a1", "fin-a1"), "no decision of WINNER or NO_AWARD"),
        (answer("WINNER", "fin-z9"), winner_missing),
        (answer("WINNER", ""), winner_missing),
        (json.dumps({"decision": "WINNER", "criteria_quote": CRIT_C1, "reason": "x"}), winner_missing),
        (json.dumps({"decision": "WINNER", "finalist_id": 1, "criteria_quote": CRIT_C1, "reason": "x"}),
         winner_missing),
        (answer("WINNER", "fin-a1", ""), bad_quote),
        (answer("WINNER", "fin-a1", "The finalist with the most jobs wins."), bad_quote),
        (answer("NO_AWARD", "", "C5."), bad_quote),
        (answer("WINNER", "fin-a1", CRITERIA + " " + CRITERIA), bad_quote),
        (json.dumps({"decision": "NO_AWARD", "finalist_id": "", "reason": "x"}), bad_quote),
        (answer("WINNER", "fin-a1", CRIT_C1, "   "), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            decide(contract)
    assert contract.get_decision_count() == 0

    # A lower-case or spaced decision word is read as the word; the id is trimmed and lower-cased.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("no award", "", CRIT_C5))
    assert decide(contract)["decision"] == "NO_AWARD"
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("winner", " Fin-C3 ", CRIT_C1))
    assert decide(contract, code="STUDIO_OF_THE_YEAR")["winner_id"] == "fin-c3"


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_same_winner_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2", CRIT_C3, "Leader wording."))
    decide(contract)

    # Same winner, different quoted criterion, reason and id case: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("winner", "FIN-B2", CRIT_C4, "Other words."))
    assert direct_vm.run_validator() is True

    # Another finalist, or NO_AWARD: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-a1", CRIT_C3))
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "", CRIT_C5))
    assert direct_vm.run_validator() is False

    # A forged or malformed leader result: disagree, even when the validator's own answer is fin-b2.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-b2", CRIT_C3))
    good = {"decision": "WINNER", "winner_id": "fin-b2", "criteria_quote": CRIT_C3, "reason": "x"}
    assert direct_vm.run_validator(leader_result=good) is True
    forged = [
        dict(good, winner_id="fin-z9"),                                        # not a finalist
        dict(good, winner_id="FIN-B2"),                                        # not normalised
        dict(good, winner_id=""),                                              # WINNER without an id
        dict(good, decision="NO_AWARD"),                                       # NO_AWARD naming an id
        dict(good, decision="YES"),                                            # not an answer word
        dict(good, criteria_quote="The finalist with the most followers wins."),  # not in the criteria
        dict(good, criteria_quote="C3."),                                      # too short
        {"decision": "WINNER", "winner_id": "fin-b2", "criteria_quote": CRIT_C3},  # no reason
    ]
    for leader in forged:
        assert direct_vm.run_validator(leader_result=leader) is False
    assert direct_vm.run_validator(leader_result="WINNER") is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-z9", CRIT_C3))
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_no_award(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "", CRIT_C5, "Leader: nobody meets C1."))
    decide(contract)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("NO_AWARD", "fin-a1", CRIT_C1, "Validator quotes another criterion."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WINNER", "fin-a1", CRIT_C1))
    assert direct_vm.run_validator() is False
