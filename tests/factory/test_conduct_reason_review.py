"""Direct-mode tests for contracts/factory/conduct_reason_review.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner page's row 5. The LLM is mocked, so these tests check the contract's own logic
(input checks, the case lifecycle, refusals, parsing, storage, the validator's
comparison), not a model's judgment or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_conduct_reason_review.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "conduct_reason_review.py")

CASE_ID = hashlib.sha256(b"booking-ref-0001").hexdigest()
OTHER_CASE = hashlib.sha256(b"booking-ref-0002").hexdigest()
EVIDENCE_SHA = hashlib.sha256(b"private evidence kept off-chain").hexdigest()

CLAUSE_LATE = "Cancellations made less than 24 hours before the session start incur a STANDARD trust penalty."
CLAUSE_NO_SHOW = "A no-show without notice incurs a SEVERE trust penalty."
CLAUSE_MINOR = "Cancellations made 24 to 48 hours before the session start incur a MINOR trust penalty."
CLAUSE_EXEMPT = "No penalty applies where a documented medical emergency prevented attendance."
TERMS = " ".join(["Booking terms v3.", CLAUSE_MINOR, CLAUSE_LATE, CLAUSE_NO_SHOW, CLAUSE_EXEMPT])

STATED_REASON = "I cancelled 3 hours before because my child was taken to hospital."
SUMMARY = "Hospital admission letter dated the morning of the session (kept off-chain)."

PROMPT = r"booking platform"


def answer(verdict, band, clause, reason="One sentence."):
    return json.dumps({"verdict": verdict, "band": band, "clause": clause, "reason": reason})


def deploy(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    return contract


def case(contract, case_id=CASE_ID):
    return json.loads(contract.get_case(case_id))


def ready_case(contract, case_id=CASE_ID):
    contract.open_case(case_id, TERMS)
    contract.submit_reason(case_id, STATED_REASON, SUMMARY, EVIDENCE_SHA)


def decided(direct_vm, contract, verdict, band, clause, case_id=CASE_ID):
    ready_case(contract, case_id)
    direct_vm.mock_llm(PROMPT, answer(verdict, band, clause))
    result = contract.decide_case(case_id)
    direct_vm.clear_mocks()
    return result


# --- answers -------------------------------------------------------------------------

def test_penalty_justified_standard(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    assert contract.open_case(CASE_ID, TERMS) == {"case_id": CASE_ID, "status": "OPEN"}
    assert contract.submit_reason(CASE_ID, STATED_REASON, SUMMARY, EVIDENCE_SHA) == {
        "case_id": CASE_ID, "status": "REASON_SUBMITTED"}
    direct_vm.mock_llm(PROMPT, answer("PENALTY_JUSTIFIED", "STANDARD", CLAUSE_LATE, "Late cancellation."))

    result = contract.decide_case(CASE_ID)

    assert result == {"case_id": CASE_ID, "verdict": "PENALTY_JUSTIFIED", "band": "STANDARD",
                      "clause": CLAUSE_LATE, "reason": "Late cancellation."}
    stored = case(contract)
    assert stored["status"] == "DECIDED"
    assert stored["verdict"] == "PENALTY_JUSTIFIED"
    assert stored["band"] == "STANDARD"
    assert stored["evidence_sha256"] == EVIDENCE_SHA
    assert stored["booking_terms"] == TERMS


def test_penalty_justified_minor(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    result = decided(direct_vm, contract, "PENALTY_JUSTIFIED", "minor", CLAUSE_MINOR)
    assert result["verdict"] == "PENALTY_JUSTIFIED"
    assert result["band"] == "MINOR"
    assert result["clause"] == CLAUSE_MINOR


def test_penalty_justified_severe(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    result = decided(direct_vm, contract, "PENALTY_JUSTIFIED", "SEVERE", CLAUSE_NO_SHOW)
    assert result["verdict"] == "PENALTY_JUSTIFIED"
    assert result["band"] == "SEVERE"
    assert case(contract)["band"] == "SEVERE"


def test_penalty_not_justified_has_band_none(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    result = decided(direct_vm, contract, "PENALTY_NOT_JUSTIFIED", "NONE", CLAUSE_EXEMPT)
    assert result["verdict"] == "PENALTY_NOT_JUSTIFIED"
    assert result["band"] == "NONE"
    assert result["clause"] == CLAUSE_EXEMPT
    # An empty band on a not-justified answer is stored as NONE too.
    other = decided(direct_vm, contract, "PENALTY_NOT_JUSTIFIED", "", CLAUSE_EXEMPT, case_id=OTHER_CASE)
    assert other["band"] == "NONE"
    assert case(contract, OTHER_CASE)["status"] == "DECIDED"


# --- must refuse ---------------------------------------------------------------------

def test_refuses_a_reason_after_the_case_is_decided(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    decided(direct_vm, contract, "PENALTY_JUSTIFIED", "STANDARD", CLAUSE_LATE)

    with direct_vm.expect_revert("[EXPECTED] CASE_CLOSED: this case is closed and accepts no reason or decision"):
        contract.submit_reason(CASE_ID, "A new excuse.", SUMMARY, EVIDENCE_SHA)
    assert case(contract)["stated_reason"] == STATED_REASON


def test_refuses_a_reason_after_the_case_is_closed(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    contract.open_case(CASE_ID, TERMS)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("[EXPECTED] NOT_THE_OPENER: only the address that opened the case can close it"):
            contract.close_case(CASE_ID)
    assert contract.close_case(CASE_ID) == {"case_id": CASE_ID, "status": "CLOSED"}

    closed = "[EXPECTED] CASE_CLOSED: this case is closed and accepts no reason or decision"
    with direct_vm.expect_revert(closed):
        contract.submit_reason(CASE_ID, STATED_REASON, SUMMARY, EVIDENCE_SHA)
    with direct_vm.expect_revert(closed):
        contract.decide_case(CASE_ID)
    with direct_vm.expect_revert(closed):
        contract.close_case(CASE_ID)
    stored = case(contract)
    assert stored["status"] == "CLOSED"
    assert stored["stated_reason"] == ""


def test_refuses_a_severity_outside_the_bands(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    ready_case(contract)
    out_of_bands = "[EXPECTED] SEVERITY_OUT_OF_BANDS: severity band must be MINOR, STANDARD or SEVERE"
    cases = [
        answer("PENALTY_JUSTIFIED", "EXTREME", CLAUSE_LATE),
        answer("PENALTY_JUSTIFIED", "NONE", CLAUSE_LATE),
        answer("PENALTY_JUSTIFIED", "", CLAUSE_LATE),
        answer("PENALTY_JUSTIFIED", 3, CLAUSE_LATE),
        json.dumps({"verdict": "PENALTY_JUSTIFIED", "clause": CLAUSE_LATE, "reason": "x"}),
        answer("PENALTY_NOT_JUSTIFIED", "MINOR", CLAUSE_EXEMPT),
        answer("PENALTY_NOT_JUSTIFIED", "CRITICAL", CLAUSE_EXEMPT),
    ]
    for response in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(PROMPT, response)
        with direct_vm.expect_revert(out_of_bands):
            contract.decide_case(CASE_ID)
    stored = case(contract)
    assert stored["status"] == "REASON_SUBMITTED"
    assert stored["band"] == ""


def test_refuses_a_second_decision(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    decided(direct_vm, contract, "PENALTY_JUSTIFIED", "MINOR", CLAUSE_MINOR)
    direct_vm.mock_llm(PROMPT, answer("PENALTY_NOT_JUSTIFIED", "NONE", CLAUSE_EXEMPT))

    with direct_vm.expect_revert("[EXPECTED] ALREADY_DECIDED: this case already has a decision"):
        contract.decide_case(CASE_ID)
    with direct_vm.expect_revert("CASE_CLOSED"):
        contract.close_case(CASE_ID)
    assert case(contract)["verdict"] == "PENALTY_JUSTIFIED"


def test_refuses_empty_terms(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for empty in ["", "   ", "\n\t"]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_TERMS: booking_terms must not be empty"):
            contract.open_case(CASE_ID, empty)
    with direct_vm.expect_revert("[EXPECTED] TERMS_TOO_LONG: booking_terms must be at most 8000 characters"):
        contract.open_case(CASE_ID, "a" * 8001)
    assert contract.get_case_count() == 0


def test_refuses_malformed_hashes(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for bad in ["", "booking-1", "g" * 64, CASE_ID[:63], CASE_ID + "0"]:
        with direct_vm.expect_revert("[EXPECTED] BAD_CASE_ID: case_id must be 64 hexadecimal characters"):
            contract.open_case(bad, TERMS)
    contract.open_case(CASE_ID.upper(), TERMS)
    for bad in ["", "not-a-hash", "z" * 64, EVIDENCE_SHA[:40]]:
        with direct_vm.expect_revert("[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters"):
            contract.submit_reason(CASE_ID, STATED_REASON, SUMMARY, bad)
    assert case(contract)["status"] == "OPEN"


def test_refuses_other_lifecycle_and_input_errors(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    contract.open_case(CASE_ID, TERMS)
    with direct_vm.expect_revert("[EXPECTED] DUPLICATE_CASE: a case with this case_id already exists"):
        contract.open_case(CASE_ID, TERMS)
    with direct_vm.expect_revert("[EXPECTED] NO_REASON: no reason has been submitted for this case"):
        contract.decide_case(CASE_ID)
    with direct_vm.expect_revert("[EXPECTED] UNKNOWN_CASE: no case is stored for this case_id"):
        contract.submit_reason(OTHER_CASE, STATED_REASON, SUMMARY, EVIDENCE_SHA)
    with direct_vm.expect_revert("UNKNOWN_CASE"):
        contract.decide_case(OTHER_CASE)
    with direct_vm.expect_revert("UNKNOWN_CASE"):
        contract.get_case(OTHER_CASE)
    for bad in ["", "   ", "x" * 2001]:
        with direct_vm.expect_revert("[EXPECTED] BAD_STATED_REASON: stated_reason must be 1-2000 characters"):
            contract.submit_reason(CASE_ID, bad, SUMMARY, EVIDENCE_SHA)
    for bad in ["", "y" * 4001]:
        with direct_vm.expect_revert("[EXPECTED] BAD_EVIDENCE_SUMMARY: evidence_summary must be 1-4000 characters"):
            contract.submit_reason(CASE_ID, STATED_REASON, bad, EVIDENCE_SHA)
    contract.submit_reason(CASE_ID, STATED_REASON, SUMMARY, EVIDENCE_SHA)
    with direct_vm.expect_revert("[EXPECTED] REASON_ALREADY_SUBMITTED: this case already has a stated reason"):
        contract.submit_reason(CASE_ID, "Another reason.", SUMMARY, EVIDENCE_SHA)
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: no case at this index"):
        contract.get_case_id(1)
    assert contract.get_case_id(0) == CASE_ID
    assert contract.get_case_count() == 1


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    ready_case(contract)
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (answer("MAYBE", "MINOR", CLAUSE_MINOR),
         "[LLM_ERROR] the model returned no PENALTY_JUSTIFIED or PENALTY_NOT_JUSTIFIED verdict"),
        (json.dumps({"band": "MINOR", "clause": CLAUSE_MINOR, "reason": "x"}), "no PENALTY_JUSTIFIED"),
        (answer("PENALTY_JUSTIFIED", "STANDARD", "Late cancellations always incur a penalty."),
         "[LLM_ERROR] the model's clause is not an exact substring of the booking terms"),
        (answer("PENALTY_JUSTIFIED", "STANDARD", ""), "the model's clause is not an exact substring"),
        (answer("PENALTY_JUSTIFIED", "STANDARD", CLAUSE_LATE, "  "), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(PROMPT, response)
        with direct_vm.expect_revert(expected):
            contract.decide_case(CASE_ID)
    assert case(contract)["status"] == "REASON_SUBMITTED"


# --- consensus -----------------------------------------------------------------------

def test_validator_agrees_on_verdict_and_band_not_the_wording(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    ready_case(contract)
    direct_vm.mock_llm(PROMPT, answer("PENALTY_JUSTIFIED", "STANDARD", CLAUSE_LATE, "Leader words."))
    contract.decide_case(CASE_ID)

    # Same verdict and band, a different clause and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(PROMPT, answer("PENALTY_JUSTIFIED", "STANDARD", "less than 24 hours", "Other words."))
    assert direct_vm.run_validator() is True

    # Same verdict, different band: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(PROMPT, answer("PENALTY_JUSTIFIED", "SEVERE", CLAUSE_NO_SHOW))
    assert direct_vm.run_validator() is False

    # Different verdict: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(PROMPT, answer("PENALTY_NOT_JUSTIFIED", "NONE", CLAUSE_EXEMPT))
    assert direct_vm.run_validator() is False

    # The validator's own model answer is malformed: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(PROMPT, answer("PENALTY_JUSTIFIED", "EXTREME", CLAUSE_LATE))
    assert direct_vm.run_validator() is False


def test_validator_rejects_bad_leader_results(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    ready_case(contract)
    direct_vm.mock_llm(PROMPT, answer("PENALTY_NOT_JUSTIFIED", "NONE", CLAUSE_EXEMPT))
    contract.decide_case(CASE_ID)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(PROMPT, answer("PENALTY_NOT_JUSTIFIED", "NONE", CLAUSE_EXEMPT, "Validator."))
    assert direct_vm.run_validator() is True

    good = {"verdict": "PENALTY_NOT_JUSTIFIED", "band": "NONE", "clause": CLAUSE_EXEMPT, "reason": "x"}
    assert direct_vm.run_validator(leader_result=good) is True
    # A leader clause that is not in the booking terms.
    forged = dict(good, clause="No penalty ever applies.")
    assert direct_vm.run_validator(leader_result=forged) is False
    # A leader band outside the bands, or a real band on a not-justified verdict.
    assert direct_vm.run_validator(leader_result=dict(good, band="EXTREME")) is False
    assert direct_vm.run_validator(leader_result=dict(good, band="MINOR")) is False
    assert direct_vm.run_validator(leader_result=dict(good, verdict="MAYBE")) is False
    # A leader error is never accepted.
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False
