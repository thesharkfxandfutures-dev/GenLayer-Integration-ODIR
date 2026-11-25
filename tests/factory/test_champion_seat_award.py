"""Direct-mode tests for contracts/factory/champion_seat_award.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 7 and the award-contract rules. The LLM is mocked (the contract reads no
web page), so these tests check the contract's own logic (rules registry, season
gate, input checks, refusals, the forbidden-signal filter, parsing, the quoted-rule
check, storage, the validator's comparison), not a model's judgment or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_champion_seat_award.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "champion_seat_award.py")

RULES_V1 = (
    "SnapLink champion allocation rules, version 2026.1\n"
    "A1. Only jobs credited to the entrant in the named role during the season count toward that role's standings.\n"
    "A2. One seat per winner: an entrant who qualifies for several seats holds only the highest seat, and the "
    "next eligible entrant moves up.\n"
    "A3. Ties on credited points are broken first by the higher number of credited jobs, then by the earlier "
    "date on which the final qualifying job was credited.\n"
    "A4. A County Shield needs at least 3 credited jobs in the named role in the season.\n"
    "A5. Seats are allocated from the final standings snapshot published when the season closes."
)
RULES_SHA = hashlib.sha256(RULES_V1.encode("utf-8")).hexdigest()
RULE_A1 = "Only jobs credited to the entrant in the named role during the season count toward that role's standings."
RULE_A2 = "One seat per winner: an entrant who qualifies for several seats holds only the highest seat"
RULE_A3 = "Ties on credited points are broken first by the higher number of credited jobs"
RULE_A4 = "A County Shield needs at least 3 credited jobs in the named role in the season."

ROLE = "wedding_photographer"
SEASON = 2026
STANDINGS = hashlib.sha256(b"standings snapshot 2026 final").hexdigest()
EVIDENCE = hashlib.sha256(b"entrant private evidence bundle").hexdigest()
SUMMARY_WORLD = ("Ranked 1st in the final world standings for wedding_photographer in season 2026 with 412 "
                 "credited points from 38 credited jobs in this role; holds no other seat.")
SUMMARY_COUNTY = "Ranked 1st in the county standings for wedding_photographer in 2026 with 2 credited jobs."

SEAT_TROPHY = "wedding_photographer|world|WORLD|2026|1"
ERR_FORBIDDEN = ("[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid "
                 "plan, subscription, premium or membership tier, or a boost")


def answer(verdict, quote=RULE_A1, reason="One sentence."):
    return json.dumps({"verdict": verdict, "rule_quote": quote, "reason": reason})


def setup(direct_vm, direct_deploy, direct_owner, finish=True):
    """The owner deploys, registers rules v1 and (by default) marks season 2026 finished."""
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    assert contract.register_rules("v1", RULES_V1) == {"rules_version": "v1", "rules_sha256": RULES_SHA}
    if finish:
        assert contract.finish_season(SEASON) == {"season_year": SEASON, "finished": True}
    return contract


def review(contract, role=ROLE, scope="world", area="WORLD", season=SEASON, seat=1, standings=STANDINGS,
           version="v1", rules=RULES_V1, summary=SUMMARY_WORLD, evidence=EVIDENCE):
    return contract.review_seat(role, scope, area, season, seat, standings, version, rules, summary, evidence)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def stored(contract, key=SEAT_TROPHY):
    return json.loads(contract.get_verdict_by_key(key))


# --- answers -------------------------------------------------------------------------

def test_confirmed_world_seat_one_is_the_snaplink_trophy(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A1, "Highest credited points in the role."))

    result = review(contract)

    assert result == {"seat_key": SEAT_TROPHY, "award": "SnapLink Trophy", "verdict": "CONFIRMED",
                      "rule_quote": RULE_A1, "reason": "Highest credited points in the role.",
                      "rules_version": "v1"}
    record = stored(contract)
    assert record == {
        "seat_key": SEAT_TROPHY, "role_key": ROLE, "scope": "world", "area_code": "WORLD",
        "season_year": SEASON, "seat": 1, "award": "SnapLink Trophy", "standings_sha256": STANDINGS,
        "rules_version": "v1", "rules_sha256": RULES_SHA, "evidence_summary": SUMMARY_WORLD,
        "evidence_sha256": EVIDENCE, "verdict": "CONFIRMED", "rule_quote": RULE_A1,
        "reason": "Highest credited points in the role.",
        "reviewed_by": address_hex(direct_owner).lower(),
    }
    assert record["rule_quote"] in RULES_V1
    assert json.loads(contract.get_verdict(ROLE, "World", "world", SEASON, 1)) == record
    assert contract.get_verdict_count() == 1
    assert contract.get_verdict_key(0) == SEAT_TROPHY


def test_not_confirmed_county_seat_quotes_the_minimum_rule(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("NOT_CONFIRMED", RULE_A4, "Only 2 credited jobs."))

    result = review(contract, scope="county", area="gb-kent", seat=1, summary=SUMMARY_COUNTY)

    key = "wedding_photographer|county|GB-KENT|2026|1"
    assert result == {"seat_key": key, "award": "County Shield", "verdict": "NOT_CONFIRMED",
                      "rule_quote": RULE_A4, "reason": "Only 2 credited jobs.", "rules_version": "v1"}
    record = stored(contract, key)
    assert record["verdict"] == "NOT_CONFIRMED"
    assert record["area_code"] == "GB-KENT"
    assert record["award"] == "County Shield"


def test_award_names_follow_scope_and_seat(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A2))
    cases = [
        ("world", "WORLD", 2, "World Plaque"),
        ("world", "WORLD", 10, "World Plaque"),
        ("continental", "EU", 1, "Continental Plaque"),
        ("continental", "EU", 10, "Continental Plaque"),
        ("national", "GB", 1, "National Cup"),
        ("national", "GB", 11, "National Cup"),
    ]
    for scope, area, seat, award in cases:
        result = review(contract, scope=scope, area=area, seat=seat)
        assert result["award"] == award
        assert result["seat_key"] == ROLE + "|" + scope + "|" + area + "|2026|" + str(seat)
    assert contract.get_verdict_count() == len(cases)


def test_prompt_carries_the_public_inputs_and_no_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the rules text, the award, the role, the seat and the summary
    # (sorted keys), the no-forbidden-signal instruction, and the absence of both hashes.
    direct_vm.mock_llm(r"(?s)^(?!.*" + STANDINGS + r")(?!.*" + EVIDENCE + r")"
                       r".*Never weigh likes, followers, votes.*INPUT_JSON.*County Shield needs at least 3"
                       r".*\"award\":\"SnapLink Trophy\".*412 credited points.*\"role_key\":\"wedding_photographer\""
                       r".*\"season_year\":2026,\"seat\":1",
                       answer("CONFIRMED", RULE_A3))
    assert review(contract)["rule_quote"] == RULE_A3


def test_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The rules break the line between A2 and A3; the model's quote crosses it with a single
    # space, and the stored quote has every run of whitespace collapsed to one space.
    quote = "the next eligible entrant moves up. A3. Ties on credited points"
    assert quote not in RULES_V1
    assert "the next eligible entrant moves up.\nA3. Ties on credited points" in RULES_V1
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", "  " + quote.replace("the next", "the \n\t next")))
    assert review(contract)["rule_quote"] == quote
    assert stored(contract)["rule_quote"] == quote


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_an_unknown_rules_version(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    unknown = "[EXPECTED] UNKNOWN_RULES_VERSION: no allocation rules are registered under this version"
    # No LLM mock: the refusal comes before any model call.
    for version in ["v2", "V1", "", "v1 "]:
        with direct_vm.expect_revert(unknown):
            review(contract, version=version)
    with direct_vm.expect_revert(unknown):
        contract.get_rules("v2")
    assert contract.get_verdict_count() == 0


def test_refuses_rules_text_that_is_not_the_registered_text(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    mismatch = "[EXPECTED] RULES_TEXT_MISMATCH: rules_text is not the text registered for this rules version"
    for rules in ["", RULES_V1 + " ", RULES_V1.replace("at least 3", "at least 1"), RULES_V1.upper()]:
        with direct_vm.expect_revert(mismatch):
            review(contract, rules=rules)
    assert contract.get_verdict_count() == 0


def test_refuses_a_season_that_is_not_finished(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner, finish=False)
    not_finished = ("[EXPECTED] SEASON_NOT_FINISHED: this season is not finished; seats are reviewed only "
                    "after the owner marks the season finished")
    assert contract.is_season_finished(SEASON) is False
    with direct_vm.expect_revert(not_finished):
        review(contract)
    assert contract.get_verdict_count() == 0

    contract.finish_season(2025)
    with direct_vm.expect_revert(not_finished):
        review(contract)
    contract.finish_season(SEASON)
    assert contract.is_season_finished(SEASON) is True
    assert json.loads(contract.get_finished_seasons()) == [2025, 2026]
    with direct_vm.expect_revert("[EXPECTED] SEASON_ALREADY_FINISHED: this season is already marked finished"):
        contract.finish_season(SEASON)

    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED"))
    assert review(contract)["verdict"] == "CONFIRMED"
    with direct_vm.expect_revert(not_finished):
        review(contract, season=2027)


def test_refuses_a_second_verdict_for_the_same_role_area_season_and_seat(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    contract.finish_season(2025)
    direct_vm.mock_llm(r"INPUT_JSON", answer("NOT_CONFIRMED", RULE_A3))
    review(contract)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A1))

    decided = "[EXPECTED] SEAT_ALREADY_DECIDED: this role, area, season and seat already has a verdict"
    with direct_vm.expect_revert(decided):
        review(contract)
    # Same seat written differently (scope and area case), another entrant's evidence: still refused.
    with direct_vm.expect_revert(decided):
        review(contract, scope=" World ", area="world", summary="Another entrant ranked 1st.",
               evidence=STANDINGS)
    assert stored(contract)["verdict"] == "NOT_CONFIRMED"
    assert contract.get_verdict_count() == 1

    # Another role, seat, season or area is a different seat.
    review(contract, role="portrait_photographer")
    review(contract, seat=2)
    review(contract, season=2025)
    review(contract, scope="national", area="GB")
    review(contract, scope="national", area="IE")
    assert contract.get_verdict_count() == 6
    with direct_vm.expect_revert(decided):
        review(contract, scope="national", area="gb")


def test_refuses_seats_out_of_range(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    out_of_range = ("[EXPECTED] SEAT_OUT_OF_RANGE: seat must be 1-10 for world, 1-10 for continental, "
                    "1-11 for national and 1 for county")
    bad = [("world", "WORLD", 0), ("world", "WORLD", 11), ("world", "WORLD", -1),
           ("continental", "EU", 0), ("continental", "EU", 11),
           ("national", "GB", 0), ("national", "GB", 12),
           ("county", "GB-KENT", 0), ("county", "GB-KENT", 2), ("world", "WORLD", True)]
    for scope, area, seat in bad:
        with direct_vm.expect_revert(out_of_range):
            review(contract, scope=scope, area=area, seat=seat)
        with direct_vm.expect_revert(out_of_range):
            contract.get_verdict(ROLE, scope, area, SEASON, seat)
    assert contract.get_verdict_count() == 0
    # The edges are seats (no verdict stored yet, so the read says NO_VERDICT).
    for scope, area, seat in [("world", "WORLD", 10), ("continental", "EU", 10), ("national", "GB", 11),
                              ("county", "GB-KENT", 1)]:
        with direct_vm.expect_revert("[EXPECTED] NO_VERDICT: no verdict is stored for this seat"):
            contract.get_verdict(ROLE, scope, area, SEASON, seat)


# --- award-contract rules: forbidden selection signals -----------------------------------

def test_refuses_an_evidence_summary_that_relies_on_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    summaries = [
        "Ranked 1st with 9,000 likes on the season's portfolio.",                 # likes
        "Top entrant by FOLLOWERS in the region.",                                # followers
        "Won the community votes for the role.",                                  # votes
        "Clients kept voting for this entrant all season.",                       # voting
        "Entrant is on the Pro paid plan and ranked 1st.",                        # paid plan
        "Ranked 1st; subscription active since January.",                         # subscription
        "Premium member, 38 credited jobs.",                                      # premium
        "Highest membership tier and 38 credited jobs.",                          # membership tier
        "Profile was #Boosted for the final month.",                              # boost
        "Ranked 1st after a boost.",                                              # boost
    ]
    for summary in summaries:
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            review(contract, summary=summary)
    assert contract.get_verdict_count() == 0

    # Whole words only: these contain a term inside a longer word and are accepted.
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED"))
    result = review(contract, summary="A devoted entrant with a strong likeness to the brief; 38 credited jobs.")
    assert result["verdict"] == "CONFIRMED"
    assert json.loads(contract.get_forbidden_signals())[0] == "likes"


def test_refuses_rules_text_that_relies_on_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    rules = [
        "Ties are broken by the higher number of likes.",
        "Ties are broken by follower count.",
        "The panel's votes decide the seat.",
        "Entrants on a paid plan get one extra point.",
        "Premium members are ranked first.",
        "Each membership tier adds a bonus.",
        "Boosted profiles break ties.",
        "Subscribers rank above others.",
    ]
    index = 0
    while index < len(rules):
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            contract.register_rules("v-bad-" + str(index), rules[index])
        index += 1
    assert contract.get_rules_count() == 1
    assert contract.get_rules_version(0) == "v1"


# --- other refusals ---------------------------------------------------------------------

def test_refuses_malformed_role_keys(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_role = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters "
                "from a-z 0-9 _")
    for role in ["", "a", "Wedding_photographer", "wedding-photographer", "wedding photographer", "_wedding",
                 "wedding_", "wedding__photographer", "1st_photographer", "x" * 41]:
        with direct_vm.expect_revert(bad_role):
            review(contract, role=role)
    assert contract.get_verdict_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED"))
    assert review(contract, role="drone_pilot_2")["seat_key"] == "drone_pilot_2|world|WORLD|2026|1"
    assert review(contract, role="x" * 40)["verdict"] == "CONFIRMED"


def test_refuses_bad_scopes_and_area_codes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    with direct_vm.expect_revert("[EXPECTED] BAD_SCOPE: scope must be world, continental, national or county"):
        review(contract, scope="global")
    with direct_vm.expect_revert("BAD_SCOPE"):
        review(contract, scope="")
    bad_area = ("[EXPECTED] BAD_AREA_CODE: area_code must be WORLD for the world scope, otherwise 2 to 16 "
                "characters from A-Z 0-9 -")
    for scope, area in [("world", "GB"), ("world", ""), ("national", "WORLD"), ("national", "G"),
                        ("national", "G B"), ("county", "GB_KENT"), ("county", "A" * 17)]:
        with direct_vm.expect_revert(bad_area):
            review(contract, scope=scope, area=area, seat=1)
    assert contract.get_verdict_count() == 0


def test_refuses_bad_season_years(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_year = "[EXPECTED] BAD_SEASON_YEAR: season_year must be a whole year from 2000 to 2199"
    for year in [1999, 2200, 0, -2026, True]:
        with direct_vm.expect_revert(bad_year):
            review(contract, season=year)
        with direct_vm.expect_revert(bad_year):
            contract.finish_season(year)
    assert json.loads(contract.get_finished_seasons()) == [SEASON]


def test_refuses_malformed_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "not-a-hash", "g" * 64, STANDINGS[:63], STANDINGS + "0"]:
        with direct_vm.expect_revert(
                "[EXPECTED] BAD_STANDINGS_HASH: standings_sha256 must be 64 hexadecimal characters"):
            review(contract, standings=bad)
        with direct_vm.expect_revert(
                "[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters"):
            review(contract, evidence=bad)
    assert contract.get_verdict_count() == 0
    # Upper-case hex is accepted and stored lower-case.
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED"))
    review(contract, standings=STANDINGS.upper(), evidence=EVIDENCE.upper())
    assert stored(contract)["standings_sha256"] == STANDINGS
    assert stored(contract)["evidence_sha256"] == EVIDENCE


def test_refuses_empty_or_long_evidence_summaries(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "   ", "\n\t"]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty"):
            review(contract, summary=bad)
    with direct_vm.expect_revert(
            "[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters"):
        review(contract, summary="x" * 2001)
    assert contract.get_verdict_count() == 0


def test_only_the_owner_writes(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    owner_only = ("[EXPECTED] OWNER_ONLY: only the contract owner can register rules, finish a season or "
                  "request a seat review")
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(owner_only):
            contract.register_rules("v2", RULES_V1)
        with direct_vm.expect_revert(owner_only):
            contract.finish_season(2025)
        with direct_vm.expect_revert(owner_only):
            review(contract)
    assert contract.get_rules_count() == 1
    assert contract.is_season_finished(2025) is False
    assert contract.get_verdict_count() == 0


def test_rules_registry(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    registered = json.loads(contract.get_rules("v1"))
    assert registered["rules_text"] == RULES_V1
    assert registered["rules_sha256"] == RULES_SHA
    with direct_vm.expect_revert(
            "[EXPECTED] RULES_VERSION_EXISTS: a registered rules version cannot be changed"):
        contract.register_rules("v1", "A different text for the same version.")
    bad_version = ("[EXPECTED] BAD_RULES_VERSION: rules_version must be 1 to 32 characters from "
                   "A-Z a-z 0-9 . _ -")
    for version in ["", "v 2", "v2/2026", "v" * 33]:
        with direct_vm.expect_revert(bad_version):
            contract.register_rules(version, RULES_V1)
    bad_text = "[EXPECTED] BAD_RULES_TEXT: rules_text must be 1 to 8000 characters and not blank"
    for text in ["", "  \n ", "x" * 8001]:
        with direct_vm.expect_revert(bad_text):
            contract.register_rules("v2", text)
    assert contract.get_rules_count() == 1
    assert contract.register_rules("2026.2-final", "x" * 8000)["rules_version"] == "2026.2-final"
    assert contract.get_rules_version(1) == "2026.2-final"
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: nothing at this index"):
        contract.get_rules_version(2)
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_verdict_key(0)
    with direct_vm.expect_revert("[EXPECTED] NO_VERDICT: no verdict is stored for this seat"):
        contract.get_verdict_by_key(SEAT_TROPHY)


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"rule_quote": RULE_A1, "reason": "x"}),
         "[LLM_ERROR] the model returned no verdict of CONFIRMED or NOT_CONFIRMED"),
        (answer("YES"), "no verdict of CONFIRMED or NOT_CONFIRMED"),
        (answer("CONFIRMED", ""),
         "[LLM_ERROR] the model's rule quote is not 10 to 400 characters quoted from the allocation rules text"),
        (answer("CONFIRMED", "Highest credited points win the seat."), "rule quote is not 10 to 400 characters"),
        (answer("NOT_CONFIRMED", "A4."), "rule quote is not 10 to 400 characters"),
        (answer("CONFIRMED", RULES_V1 + " " + RULES_V1), "rule quote is not 10 to 400 characters"),
        (json.dumps({"verdict": "CONFIRMED", "reason": "x"}), "rule quote is not 10 to 400 characters"),
        (answer("CONFIRMED", RULE_A1, "   "), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            review(contract)
    assert contract.get_verdict_count() == 0

    # A lower-case or spaced verdict word is read as the word.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("not confirmed", RULE_A2))
    assert review(contract)["verdict"] == "NOT_CONFIRMED"


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A1, "Leader wording."))
    review(contract)

    # Same verdict word, different quoted rule and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A2, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("NOT_CONFIRMED", RULE_A4, "Not enough jobs."))
    assert direct_vm.run_validator() is False

    # A leader quote that is not in the rules text, or a malformed leader result: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A1))
    forged = {"verdict": "CONFIRMED", "rule_quote": "The entrant with the most followers wins.", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    short = {"verdict": "CONFIRMED", "rule_quote": "A1.", "reason": "x"}
    assert direct_vm.run_validator(leader_result=short) is False
    bad_word = {"verdict": "YES", "rule_quote": RULE_A1, "reason": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False
    no_reason = {"verdict": "CONFIRMED", "rule_quote": RULE_A1}
    assert direct_vm.run_validator(leader_result=no_reason) is False
    assert direct_vm.run_validator(leader_result="CONFIRMED") is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_not_confirmed(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("NOT_CONFIRMED", RULE_A4, "Leader: too few jobs."))
    review(contract, scope="county", area="GB-KENT", summary=SUMMARY_COUNTY)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("NOT_CONFIRMED", RULE_A1, "Validator quotes another rule."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CONFIRMED", RULE_A4))
    assert direct_vm.run_validator() is False
