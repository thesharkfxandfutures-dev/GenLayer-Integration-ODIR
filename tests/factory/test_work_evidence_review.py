"""Direct-mode tests for contracts/factory/work_evidence_review.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
backlog item. The LLM is mocked, so these tests check the contract's own logic
(input checks, refusals, parsing, storage, the validator's verdict comparison), not
a model's judgment and not GenVM consensus.

Run from the repository root:
    pip install genlayer-test pytest
    pytest tests/factory/test_work_evidence_review.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "work_evidence_review.py")

BRIEF = (
    "Design a logo for the Harbour Bakery. Deliver SVG and PNG files, use only navy "
    "and white, and include a one-page usage guide."
)
DELIVERY_OK = (
    "Delivered the Harbour Bakery logo as SVG and PNG files. The palette is navy "
    "(#1F2A44) and white only. A one-page PDF usage guide covers spacing and minimum size."
)
DELIVERY_SHORT = (
    "Delivered the Harbour Bakery logo as a PNG file in navy, white and gold. "
    "The usage guide will follow next week."
)
EVIDENCE_OK = "private: final-logo.svg, final-logo.png, usage-guide.pdf, client sign-off email"
EVIDENCE_SHORT = "private: logo-draft.png"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def answer(verdict, quote, reason="One sentence."):
    return json.dumps({"verdict": verdict, "quote": quote, "reason": reason})


def deploy(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    return contract


# --- decision outcomes ---------------------------------------------------------------

def test_meets_requirements(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer(
        "MEETS_REQUIREMENTS", "as SVG and PNG files", "Formats, palette and guide are all delivered."))

    result = contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))

    assert result["verdict"] == "MEETS_REQUIREMENTS"
    assert result["case_id"] == sha(EVIDENCE_OK)
    assert result["quote"] == "as SVG and PNG files"
    assert result["quote"] in DELIVERY_OK
    stored = json.loads(contract.get_case(sha(EVIDENCE_OK)))
    assert stored["verdict"] == "MEETS_REQUIREMENTS"
    assert stored["evidence_sha256"] == sha(EVIDENCE_OK)
    assert stored["delivery_sha256"] == sha(DELIVERY_OK)
    assert contract.get_case_count() == 1
    assert contract.get_case_id(0) == sha(EVIDENCE_OK)


def test_does_not_meet_requirements(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer(
        "DOES_NOT_MEET_REQUIREMENTS", "The usage guide will follow next week.",
        "No SVG, gold breaks the palette and the guide is missing."))

    result = contract.review_work(BRIEF, DELIVERY_SHORT, sha(EVIDENCE_SHORT))

    assert result["verdict"] == "DOES_NOT_MEET_REQUIREMENTS"
    assert result["quote"] == "The usage guide will follow next week."
    assert json.loads(contract.get_case(sha(EVIDENCE_SHORT)))["verdict"] == "DOES_NOT_MEET_REQUIREMENTS"


def test_validator_agrees_on_verdict_word_only(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))
    contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))

    # Same verdict word, different quote and reason: the validator agrees.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Harbour Bakery", answer(
        "MEETS_REQUIREMENTS", "navy (#1F2A44) and white only", "Different wording."))
    assert direct_vm.run_validator() is True

    # A different verdict word: the validator disagrees.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Harbour Bakery", answer("DOES_NOT_MEET_REQUIREMENTS", "as SVG and PNG files"))
    assert direct_vm.run_validator() is False

    # A leader quote that is not in the delivery text is rejected outright.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))
    forged = {"verdict": "MEETS_REQUIREMENTS", "quote": "approved by the client", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False

    # A leader error is never accepted.
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


# --- must refuse ---------------------------------------------------------------------

def test_refuses_evidence_that_does_not_match_the_hash(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))
    contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))

    with direct_vm.expect_revert("EVIDENCE_HASH_MISMATCH"):
        contract.check_evidence(sha(EVIDENCE_OK), EVIDENCE_OK + " (edited)")

    confirmed = json.loads(contract.check_evidence(sha(EVIDENCE_OK), EVIDENCE_OK))
    assert confirmed == {"case_id": sha(EVIDENCE_OK), "evidence_matches": True,
                         "verdict": "MEETS_REQUIREMENTS"}


def test_refuses_the_same_evidence_twice(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "Delivered the Harbour Bakery logo"))
    contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))

    with direct_vm.expect_revert("DUPLICATE_SUBMISSION: this evidence_sha256 already has a decision"):
        contract.review_work(BRIEF, DELIVERY_SHORT, sha(EVIDENCE_OK))
    # Upper-case hex is the same case.
    with direct_vm.expect_revert("DUPLICATE_SUBMISSION"):
        contract.review_work(BRIEF, DELIVERY_SHORT, sha(EVIDENCE_OK).upper())
    assert contract.get_case_count() == 1


def test_refuses_the_same_brief_and_delivery_twice(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))
    contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))

    # A fresh hash does not buy a second verdict on the same case.
    with direct_vm.expect_revert("DUPLICATE_SUBMISSION: this brief and delivery already have a decision"):
        contract.review_work(BRIEF, DELIVERY_OK, sha("another private file"))
    assert contract.get_case_count() == 1


def test_refuses_an_empty_brief(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r".*", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))

    with direct_vm.expect_revert("[EXPECTED] EMPTY_BRIEF: the brief must not be empty"):
        contract.review_work("", DELIVERY_OK, sha(EVIDENCE_OK))
    with direct_vm.expect_revert("EMPTY_BRIEF"):
        contract.review_work("   \n ", DELIVERY_OK, sha(EVIDENCE_OK))
    assert contract.get_case_count() == 0


# --- other refusals ------------------------------------------------------------------

def test_refuses_a_malformed_hash_and_empty_delivery(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r".*", answer("MEETS_REQUIREMENTS", "as SVG and PNG files"))

    with direct_vm.expect_revert("BAD_EVIDENCE_HASH"):
        contract.review_work(BRIEF, DELIVERY_OK, "not-a-hash")
    with direct_vm.expect_revert("BAD_EVIDENCE_HASH"):
        contract.review_work(BRIEF, DELIVERY_OK, "g" * 64)
    with direct_vm.expect_revert("EMPTY_DELIVERY"):
        contract.review_work(BRIEF, " ", sha(EVIDENCE_OK))
    with direct_vm.expect_revert("UNKNOWN_CASE"):
        contract.get_case(sha(EVIDENCE_OK))
    assert contract.get_case_count() == 0


def test_refuses_a_model_quote_that_is_not_in_the_delivery(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("MEETS_REQUIREMENTS", "the client approved everything"))

    with direct_vm.expect_revert("[LLM_ERROR] the model's quote is not an exact substring"):
        contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))
    assert contract.get_case_count() == 0


def test_refuses_a_model_answer_without_a_verdict_word(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    direct_vm.mock_llm(r"Harbour Bakery", answer("PROBABLY_FINE", "as SVG and PNG files"))

    with direct_vm.expect_revert("[LLM_ERROR] the model returned no valid verdict word"):
        contract.review_work(BRIEF, DELIVERY_OK, sha(EVIDENCE_OK))
    assert contract.get_case_count() == 0
