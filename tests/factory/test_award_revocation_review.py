"""Direct-mode tests for contracts/factory/award_revocation_review.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 12 and the award-contract rules. The LLM is mocked (the contract reads no
web page), so these tests check the contract's own logic (rules registry, issued-award
registry, input checks, refusals, the forbidden-signal filter, the reason hash, parsing,
the quoted-rule check, storage, the validator's comparison), not a model's judgment or
GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_award_revocation_review.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "award_revocation_review.py")

RULES_V1 = (
    "SnapLink award rules, version 2026.1\n"
    "G1. Every award rests on the evidence recorded when it was issued and counts only work credited in the "
    "named role.\n"
    "R1. An award is revoked when the evidence it rested on is withdrawn by the person or client who supplied it.\n"
    "R2. An award is revoked when fraud is found in the evidence or in the work counted for the award.\n"
    "R3. An award is revoked when the work it counted was not done in the named role.\n"
    "R4. A complaint about taste or quality, or an allegation the evidence does not support, is not a ground "
    "for revocation; the award is kept."
)
RULES_V2 = RULES_V1.replace("version 2026.1", "version 2026.2")
RULES_SHA = hashlib.sha256(RULES_V1.encode("utf-8")).hexdigest()
RULE_R1 = "An award is revoked when the evidence it rested on is withdrawn by the person or client who supplied it."
RULE_R2 = "An award is revoked when fraud is found in the evidence or in the work counted for the award."
RULE_R3 = "An award is revoked when the work it counted was not done in the named role."
RULE_R4 = "A complaint about taste or quality, or an allegation the evidence does not support, is not a ground"

ROLE = "wedding_photographer"
AWARD = hashlib.sha256(b"snaplink award record 2026-0001").hexdigest()
AWARD_2 = hashlib.sha256(b"snaplink award record 2026-0002").hexdigest()
NEVER_ISSUED = hashlib.sha256(b"an award reference never issued").hexdigest()
EVIDENCE = hashlib.sha256(b"private evidence bundle for the revocation").hexdigest()

REASON_FRAUD = "Fraud found: two of the counted jobs were invoiced to a client that does not exist."
SUMMARY_FRAUD = ("SnapLink's audit found that jobs 14 and 15 counted for the award were invoiced to a company "
                 "with no registration and no reachable contact; the payments came from the entrant's own account.")
REASON_TASTE = "The client did not like the colour grading of the album."
SUMMARY_TASTE = "A message from the client says the colours were too warm; the job was delivered and paid on time."


def reason_sha(reason):
    return hashlib.sha256(" ".join(reason.split()).lower().encode("utf-8")).hexdigest()


ERR_FORBIDDEN = ("[EXPECTED] FORBIDDEN_SIGNAL: award inputs must not rely on likes, followers, votes, a paid "
                 "plan, subscription, premium or membership, or a boost")
ERR_NOT_ISSUED = "[EXPECTED] AWARD_NOT_ISSUED: no issued award is recorded under this award reference"
ERR_DECIDED = "[EXPECTED] REASON_ALREADY_DECIDED: this award already has a decision on the same reason"
ERR_REVOKED = "[EXPECTED] AWARD_ALREADY_REVOKED: this award is already revoked"


def answer(verdict, quote=RULE_R2, explanation="One sentence."):
    return json.dumps({"verdict": verdict, "rule_quote": quote, "explanation": explanation})


def setup(direct_vm, direct_deploy, direct_owner, record=True):
    """The owner deploys, registers rules v1 and (by default) records AWARD as issued under v1."""
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    assert contract.register_rules("v1", RULES_V1) == {"rules_version": "v1", "rules_sha256": RULES_SHA}
    if record:
        assert contract.record_issued_award(AWARD, ROLE, "champion_seat", "v1") == {
            "award_ref_sha256": AWARD, "role_key": ROLE, "award_type": "CHAMPION_SEAT",
            "rules_version": "v1", "status": "ISSUED"}
    return contract


def review(contract, award=AWARD, version="v1", reason=REASON_FRAUD, summary=SUMMARY_FRAUD, evidence=EVIDENCE):
    return contract.review_revocation(award, version, reason, summary, evidence)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def key_of(award, reason):
    return award + "|" + reason_sha(reason)


# --- fresh contract ------------------------------------------------------------------

def test_fresh_contract_is_empty(direct_vm, direct_deploy, direct_owner):
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    assert contract.get_rules_count() == 0
    assert contract.get_award_count() == 0
    assert contract.get_decision_count() == 0
    assert contract.get_award_status(AWARD) == "NOT_ISSUED"


# --- answers -------------------------------------------------------------------------

def test_revoke_when_fraud_is_found(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R2, "The audit shows invented clients."))

    result = review(contract)

    key = key_of(AWARD, REASON_FRAUD)
    assert result == {"decision_key": key, "award_ref_sha256": AWARD, "verdict": "REVOKE",
                      "rule_quote": RULE_R2, "explanation": "The audit shows invented clients.",
                      "rules_version": "v1", "reason_sha256": reason_sha(REASON_FRAUD),
                      "award_status": "REVOKED"}
    record = json.loads(contract.get_decision_by_key(key))
    assert record == {
        "decision_key": key, "award_ref_sha256": AWARD, "role_key": ROLE, "award_type": "CHAMPION_SEAT",
        "rules_version": "v1", "rules_sha256": RULES_SHA, "reason": REASON_FRAUD,
        "reason_sha256": reason_sha(REASON_FRAUD), "evidence_summary": SUMMARY_FRAUD,
        "evidence_sha256": EVIDENCE, "verdict": "REVOKE", "rule_quote": RULE_R2,
        "explanation": "The audit shows invented clients.",
        "reviewed_by": address_hex(direct_owner).lower(),
    }
    assert record["rule_quote"] in RULES_V1
    assert json.loads(contract.get_decision(AWARD.upper(), "  " + REASON_FRAUD.upper())) == record
    assert contract.get_decision_count() == 1
    assert contract.get_decision_key(0) == key
    assert contract.get_award_status(AWARD) == "REVOKED"
    award = json.loads(contract.get_award(AWARD))
    assert award["status"] == "REVOKED"
    assert award["revoked_by"] == key


def test_keep_when_the_reason_is_a_complaint_about_taste(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4, "Taste is not a ground."))

    result = review(contract, reason=REASON_TASTE, summary=SUMMARY_TASTE)

    assert result["verdict"] == "KEEP"
    assert result["rule_quote"] == RULE_R4
    assert result["award_status"] == "ISSUED"
    assert contract.get_award_status(AWARD) == "ISSUED"
    assert json.loads(contract.get_award(AWARD))["revoked_by"] == ""
    assert json.loads(contract.get_decision(AWARD, REASON_TASTE))["verdict"] == "KEEP"


def test_one_contract_serves_every_award_type_and_role(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner, record=False)
    cases = [
        ("champion_seat", "wedding_photographer", "CHAMPION_SEAT"),
        ("Recognition_Plaque", "portrait_photographer", "RECOGNITION_PLAQUE"),
        (" verified_work_milestone ", "drone_pilot", "VERIFIED_WORK_MILESTONE"),
        ("SERVICE_MEDAL", "video_editor", "SERVICE_MEDAL"),
        ("annual_award", "makeup_artist_2", "ANNUAL_AWARD"),
    ]
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R3, "Work was in another role."))
    index = 0
    while index < len(cases):
        given, role, stored_type = cases[index]
        ref = hashlib.sha256(("award " + str(index)).encode("utf-8")).hexdigest()
        assert contract.record_issued_award(ref, role, given, "v1")["award_type"] == stored_type
        result = review(contract, award=ref, reason="Work not in the role: the counted jobs were for another role.")
        assert result["verdict"] == "REVOKE"
        record = json.loads(contract.get_decision_by_key(result["decision_key"]))
        assert record["role_key"] == role
        assert record["award_type"] == stored_type
        index += 1
    assert contract.get_award_count() == len(cases)
    assert contract.get_decision_count() == len(cases)


def test_prompt_carries_the_public_inputs_and_no_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the no-forbidden-signal instruction, the rules text, the award type,
    # the summary, the reason and the role (sorted keys), and the absence of both hashes.
    direct_vm.mock_llm(r"(?s)^(?!.*" + AWARD + r")(?!.*" + EVIDENCE + r")"
                       r".*Never weigh likes, followers, votes.*INPUT_JSON.*R3\. An award is revoked when the work"
                       r".*\"award_type\":\"CHAMPION_SEAT\".*payments came from the entrant's own account"
                       r".*\"revocation_reason\":\"Fraud found: two of the counted jobs"
                       r".*\"role_key\":\"wedding_photographer\"",
                       answer("REVOKE", RULE_R2))
    assert review(contract)["verdict"] == "REVOKE"


def test_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The rules break the line between R1 and R2; the model's quote crosses it with spaces and tabs,
    # and the stored quote has every run of whitespace collapsed to one space.
    quote = "who supplied it. R2. An award is revoked when fraud"
    assert quote not in RULES_V1
    assert "who supplied it.\nR2. An award is revoked when fraud" in RULES_V1
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", "  " + quote.replace("it. R2.", "it. \n\t R2.")))
    assert review(contract)["rule_quote"] == quote
    assert json.loads(contract.get_decision(AWARD, REASON_FRAUD))["rule_quote"] == quote


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_a_revocation_of_an_award_never_issued(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner, record=False)
    # No LLM mock: the refusal comes before any model call.
    with direct_vm.expect_revert(ERR_NOT_ISSUED):
        review(contract)
    contract.record_issued_award(AWARD_2, ROLE, "service_medal", "v1")
    for ref in [AWARD, NEVER_ISSUED, NEVER_ISSUED.upper()]:
        with direct_vm.expect_revert(ERR_NOT_ISSUED):
            review(contract, award=ref)
    with direct_vm.expect_revert(ERR_NOT_ISSUED):
        contract.get_award(NEVER_ISSUED)
    assert contract.get_award_status(NEVER_ISSUED) == "NOT_ISSUED"
    assert contract.get_award_status(AWARD_2) == "ISSUED"
    assert contract.get_decision_count() == 0

    # Once recorded as issued, the same reference can be reviewed.
    contract.record_issued_award(AWARD, ROLE, "annual_award", "v1")
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4))
    assert review(contract)["verdict"] == "KEEP"


def test_refuses_a_second_decision_on_the_same_reason(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    contract.record_issued_award(AWARD_2, ROLE, "champion_seat", "v1")
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4, "Not supported."))
    assert review(contract)["verdict"] == "KEEP"
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R2))

    with direct_vm.expect_revert(ERR_DECIDED):
        review(contract)
    # The same reason written with other case and spacing, with other evidence: still refused.
    with direct_vm.expect_revert(ERR_DECIDED):
        review(contract, award=AWARD.upper(), reason="  " + REASON_FRAUD.upper().replace(" ", "\n  "),
               summary="A new and fuller audit summary.", evidence=NEVER_ISSUED)
    assert json.loads(contract.get_decision(AWARD, REASON_FRAUD))["verdict"] == "KEEP"
    assert contract.get_decision_count() == 1
    assert contract.get_award_status(AWARD) == "ISSUED"

    # Another reason on the same award, or the same reason on another award, is a new decision.
    assert review(contract, reason=REASON_FRAUD + " A third job too.")["verdict"] == "REVOKE"
    assert review(contract, award=AWARD_2)["verdict"] == "REVOKE"
    assert contract.get_decision_count() == 3
    # After a REVOKE, the same reason is still REASON_ALREADY_DECIDED (not AWARD_ALREADY_REVOKED).
    with direct_vm.expect_revert(ERR_DECIDED):
        review(contract, award=AWARD_2)


# --- award-contract rules: forbidden selection signals -----------------------------------

def test_refuses_a_reason_or_summary_that_carries_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    texts = [
        "Revoke: the entrant has fewer likes than the runner-up.",            # likes
        "The entrant LIKED their own posts.",                                 # liked
        "The entrant lost most of their Followers.",                          # followers
        "The community votes went against this award.",                      # votes
        "Clients kept voting to remove it.",                                  # voting
        "Upvotes on the complaint passed 500.",                               # upvotes
        "The entrant left the paid plan in March.",                           # paid plan
        "Subscription lapsed, so the award should go.",                       # subscription
        "The entrant cancelled premium.",                                     # premium
        "Gold membership ended last week.",                                   # membership
        "The entrant downgraded from the Pro plan.",                          # pro plan
        "Profile was #Boosted during the season.",                            # boosted
        "Revoke after a boost was refunded.",                                 # boost
    ]
    for text in texts:
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            review(contract, reason=text)
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            review(contract, summary=text)
    assert contract.get_decision_count() == 0
    assert contract.get_award_status(AWARD) == "ISSUED"

    # Whole words only: a term inside a longer word is accepted.
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4))
    result = review(contract, reason="A devoted rival says the likeness in the portraits is poor.")
    assert result["verdict"] == "KEEP"
    assert json.loads(contract.get_forbidden_signals())[0] == "likes"


def test_refuses_rules_text_that_carries_a_forbidden_signal(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    rules = [
        "An award is revoked when its likes fall below 100.",
        "An award is revoked when the follower count drops.",
        "A public vote can revoke any award.",
        "Awards of entrants who leave a paid plan are revoked.",
        "Premium entrants keep their awards.",
        "Membership protects an award from revocation.",
        "Boosted profiles are never revoked.",
        "Subscribers keep their awards.",
    ]
    index = 0
    while index < len(rules):
        with direct_vm.expect_revert(ERR_FORBIDDEN):
            contract.register_rules("v-bad-" + str(index), rules[index])
        index += 1
    assert contract.get_rules_count() == 1
    assert contract.get_rules_version(0) == "v1"


# --- other refusals ---------------------------------------------------------------------

def test_refuses_a_new_reason_on_a_revoked_award(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R2))
    review(contract)
    with direct_vm.expect_revert(ERR_REVOKED):
        review(contract, reason="Evidence withdrawn: the client withdrew the reference letter.")
    assert contract.get_decision_count() == 1


def test_refuses_an_unknown_or_mismatched_rules_version(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    unknown = "[EXPECTED] UNKNOWN_RULES_VERSION: no award rules are registered under this version"
    for version in ["v2", "V1", "", "v1 "]:
        with direct_vm.expect_revert(unknown):
            review(contract, version=version)
        with direct_vm.expect_revert(unknown):
            contract.record_issued_award(AWARD_2, ROLE, "champion_seat", version)
    with direct_vm.expect_revert(unknown):
        contract.get_rules("v2")
    assert contract.get_award_count() == 1

    contract.register_rules("v2", RULES_V2)
    mismatch = ("[EXPECTED] RULES_VERSION_MISMATCH: rules_version is not the rules version this award was "
                "issued under")
    with direct_vm.expect_revert(mismatch):
        review(contract, version="v2")
    assert contract.get_decision_count() == 0
    # An award issued under v2 is reviewed under v2, and the model sees the v2 text.
    contract.record_issued_award(AWARD_2, ROLE, "champion_seat", "v2")
    with direct_vm.expect_revert(mismatch):
        review(contract, award=AWARD_2, version="v1")
    direct_vm.mock_llm(r"(?s)^(?!.*version 2026\.1).*INPUT_JSON.*version 2026\.2", answer("KEEP", RULE_R4))
    assert review(contract, award=AWARD_2, version="v2")["verdict"] == "KEEP"


def test_refuses_malformed_hashes(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_ref = "[EXPECTED] BAD_AWARD_REF: award_ref_sha256 must be 64 hexadecimal characters"
    bad_evidence = "[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters"
    for bad in ["", "not-a-hash", "g" * 64, AWARD[:63], AWARD + "0"]:
        with direct_vm.expect_revert(bad_ref):
            review(contract, award=bad)
        with direct_vm.expect_revert(bad_ref):
            contract.record_issued_award(bad, ROLE, "champion_seat", "v1")
        with direct_vm.expect_revert(bad_ref):
            contract.get_award_status(bad)
        with direct_vm.expect_revert(bad_evidence):
            review(contract, evidence=bad)
    assert contract.get_decision_count() == 0
    assert contract.get_award_count() == 1
    # Upper-case hex is accepted and stored lower-case.
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4))
    result = review(contract, award=AWARD.upper(), evidence=EVIDENCE.upper())
    record = json.loads(contract.get_decision_by_key(result["decision_key"]))
    assert record["award_ref_sha256"] == AWARD
    assert record["evidence_sha256"] == EVIDENCE


def test_record_issued_award_refusals(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_role = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case, 2 to 40 characters "
                "from a-z 0-9 _")
    for role in ["", "a", "Wedding_photographer", "wedding-photographer", "wedding photographer", "_wedding",
                 "wedding_", "wedding__photographer", "1st_photographer", "x" * 41]:
        with direct_vm.expect_revert(bad_role):
            contract.record_issued_award(AWARD_2, role, "champion_seat", "v1")
    bad_type = ("[EXPECTED] BAD_AWARD_TYPE: award_type must be CHAMPION_SEAT, RECOGNITION_PLAQUE, "
                "VERIFIED_WORK_MILESTONE, SERVICE_MEDAL or ANNUAL_AWARD")
    for kind in ["", "trophy", "champion seat", "CHAMPION_SEATS"]:
        with direct_vm.expect_revert(bad_type):
            contract.record_issued_award(AWARD_2, ROLE, kind, "v1")
    recorded = "[EXPECTED] AWARD_ALREADY_RECORDED: this award reference is already recorded as issued"
    for ref in [AWARD, AWARD.upper(), " " + AWARD]:
        with direct_vm.expect_revert(recorded):
            contract.record_issued_award(ref, "portrait_photographer", "annual_award", "v1")
    assert contract.get_award_count() == 1
    assert contract.get_award_ref(0) == AWARD
    assert json.loads(contract.get_award(AWARD))["award_type"] == "CHAMPION_SEAT"
    assert contract.record_issued_award(AWARD_2, "x" * 40, "service_medal", "v1")["role_key"] == "x" * 40
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: nothing at this index"):
        contract.get_award_ref(2)


def test_refuses_empty_or_long_reasons_and_summaries(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for bad in ["", "   ", "\n\t"]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_REASON: reason must not be empty"):
            review(contract, reason=bad)
        with direct_vm.expect_revert("[EXPECTED] EMPTY_EVIDENCE_SUMMARY: evidence_summary must not be empty"):
            review(contract, summary=bad)
    with direct_vm.expect_revert("[EXPECTED] REASON_TOO_LONG: reason must be at most 1000 characters"):
        review(contract, reason="x" * 1001)
    with direct_vm.expect_revert(
            "[EXPECTED] EVIDENCE_SUMMARY_TOO_LONG: evidence_summary must be at most 2000 characters"):
        review(contract, summary="x" * 2001)
    assert contract.get_decision_count() == 0
    # The limits themselves are accepted.
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4))
    assert review(contract, reason="x" * 1000, summary="y" * 2000)["verdict"] == "KEEP"


def test_only_the_owner_writes(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    owner_only = ("[EXPECTED] OWNER_ONLY: only the contract owner can register rules, record an issued award "
                  "or request a revocation review")
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(owner_only):
            contract.register_rules("v2", RULES_V2)
        with direct_vm.expect_revert(owner_only):
            contract.record_issued_award(AWARD_2, ROLE, "champion_seat", "v1")
        with direct_vm.expect_revert(owner_only):
            review(contract)
    assert contract.get_rules_count() == 1
    assert contract.get_award_count() == 1
    assert contract.get_decision_count() == 0


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
        contract.get_decision_key(0)
    no_decision = "[EXPECTED] NO_DECISION: no decision is stored for this award and reason"
    with direct_vm.expect_revert(no_decision):
        contract.get_decision_by_key(key_of(AWARD, REASON_FRAUD))
    with direct_vm.expect_revert(no_decision):
        contract.get_decision(AWARD, REASON_FRAUD)


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"rule_quote": RULE_R2, "explanation": "x"}),
         "[LLM_ERROR] the model returned no verdict of REVOKE or KEEP"),
        (answer("YES"), "no verdict of REVOKE or KEEP"),
        (answer("REVOKED"), "no verdict of REVOKE or KEEP"),
        (answer("REVOKE", ""),
         "[LLM_ERROR] the model's rule quote is not 10 to 400 characters quoted from the award rules text"),
        (answer("REVOKE", "Fraud always revokes an award."), "rule quote is not 10 to 400 characters"),
        (answer("KEEP", "R4."), "rule quote is not 10 to 400 characters"),
        (answer("REVOKE", RULES_V1), "rule quote is not 10 to 400 characters"),
        (json.dumps({"verdict": "REVOKE", "explanation": "x"}), "rule quote is not 10 to 400 characters"),
        (answer("REVOKE", RULE_R2, "   "), "[LLM_ERROR] the model returned no explanation"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            review(contract)
    assert contract.get_decision_count() == 0
    assert contract.get_award_status(AWARD) == "ISSUED"

    # A model error stores nothing, so the same reason can be retried; a lower-case word is read as the word.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer(" revoke ", RULE_R2))
    assert review(contract)["verdict"] == "REVOKE"


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R2, "Leader wording."))
    review(contract)

    # Same verdict word, different quoted rule and explanation: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R1, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4, "Not supported."))
    assert direct_vm.run_validator() is False

    # A leader quote that is not in the rules text, or a malformed leader result: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R2))
    forged = {"verdict": "REVOKE", "rule_quote": "Any award can be revoked at the owner's wish.", "explanation": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    short = {"verdict": "REVOKE", "rule_quote": "R2.", "explanation": "x"}
    assert direct_vm.run_validator(leader_result=short) is False
    bad_word = {"verdict": "YES", "rule_quote": RULE_R2, "explanation": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False
    no_explanation = {"verdict": "REVOKE", "rule_quote": RULE_R2}
    assert direct_vm.run_validator(leader_result=no_explanation) is False
    assert direct_vm.run_validator(leader_result="REVOKE") is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_keep(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R4, "Leader: taste only."))
    review(contract, reason=REASON_TASTE, summary=SUMMARY_TASTE)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("KEEP", RULE_R1, "Validator quotes another rule."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("REVOKE", RULE_R4))
    assert direct_vm.run_validator() is False
