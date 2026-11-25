"""Direct-mode tests for contracts/factory/photo_claim_adjudication.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 6. The LLM is mocked (the contract reads no web page), so these tests check
the contract's own logic (input checks, refusals, parsing, the verbatim-fact check,
storage, the validator's comparison), not a model's judgment or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_photo_claim_adjudication.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "photo_claim_adjudication.py")

MEDIA = hashlib.sha256(b"lighthouse-dusk.jpg bytes").hexdigest()
OTHER_MEDIA = hashlib.sha256(b"market-morning.jpg bytes").hexdigest()
EVIDENCE_A = hashlib.sha256(b"claimant a raw file").hexdigest()
EVIDENCE_B = hashlib.sha256(b"claimant b raw file").hexdigest()

STATEMENT_A = ("I shot this at the north pier lighthouse at dusk and first posted it on my "
               "portfolio on 2024-03-02, with the full RAW series of 14 frames.")
STATEMENT_B = "I took this photo and posted it on my feed in May 2024."
URL_A = "https://portfolio.example/series/lighthouse-dusk"
URL_B = "https://social.example/posts/88231"
DATE_A = "2024-03-02"
DATE_B = "2024-05-19"

FACT_A = "the full RAW series of 14 frames"
FACT_B = "I took this photo"


def answer(verdict, fact="", reason="One sentence."):
    return json.dumps({"verdict": verdict, "deciding_fact": fact, "reason": reason})


def deploy(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    return contract


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def claim_a(contract, media=MEDIA, statement=STATEMENT_A, url=URL_A, date=DATE_A, evidence=EVIDENCE_A):
    return contract.submit_claim(media, statement, url, date, evidence)


def claim_b(direct_vm, contract, who, media=MEDIA, statement=STATEMENT_B, url=URL_B, date=DATE_B,
            evidence=EVIDENCE_B):
    with direct_vm.prank(who):
        return contract.submit_claim(media, statement, url, date, evidence)


def both_in(direct_vm, contract, direct_bob):
    claim_a(contract)
    claim_b(direct_vm, contract, direct_bob)


def dispute(contract, media=MEDIA):
    return json.loads(contract.get_dispute(media))


# --- answers -------------------------------------------------------------------------

def test_claimant_a_with_the_deciding_fact_quoted(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    assert claim_a(contract) == {"media_sha256": MEDIA, "role": "CLAIMANT_A", "status": "AWAITING_CLAIMANT_B"}
    assert claim_b(direct_vm, contract, direct_bob) == {"media_sha256": MEDIA, "role": "CLAIMANT_B",
                                                       "status": "READY_FOR_DECISION"}
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", FACT_A, "A names an earlier, specific source."))

    result = contract.decide(MEDIA)

    assert result == {"media_sha256": MEDIA, "verdict": "CLAIMANT_A", "deciding_fact": FACT_A,
                      "fact_source": "statement_a", "reason": "A names an earlier, specific source."}
    stored = dispute(contract)
    assert stored["status"] == "DECIDED"
    assert stored["verdict"] == "CLAIMANT_A"
    assert stored["claimant_a"] == address_hex(direct_alice).lower()
    assert stored["claimant_b"] == address_hex(direct_bob).lower()
    assert stored["claim_a"] == {"statement": STATEMENT_A, "first_publication_url": URL_A,
                                 "first_publication_date": DATE_A, "evidence_sha256": EVIDENCE_A}
    assert stored["claim_b"]["evidence_sha256"] == EVIDENCE_B


def test_claimant_b_with_a_quoted_date(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_a(contract, statement="It is mine.", date="2024-08-01")
    claim_b(direct_vm, contract, direct_bob, date="2023-11-30")
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_B", "2023-11-30", "B's stated first publication is earlier."))

    result = contract.decide(MEDIA)

    assert result["verdict"] == "CLAIMANT_B"
    assert result["deciding_fact"] == "2023-11-30"
    assert result["fact_source"] == "date_b"
    assert dispute(contract)["verdict"] == "CLAIMANT_B"


def test_undecided_is_a_valid_answer(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_a(contract, statement="This is my photo.")
    claim_b(direct_vm, contract, direct_bob, statement="No, this is my photo.", date=DATE_A)
    direct_vm.mock_llm(r"INPUT_JSON", answer("UNDECIDED", "", "Neither claim gives a checkable fact."))

    result = contract.decide(MEDIA)

    assert result == {"media_sha256": MEDIA, "verdict": "UNDECIDED", "deciding_fact": "",
                      "fact_source": "", "reason": "Neither claim gives a checkable fact."}
    assert dispute(contract)["status"] == "DECIDED"


def test_prompt_carries_only_the_public_claims(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    # The mock only answers when the prompt carries both claims (sorted keys: date, url, statement),
    # and never the evidence hashes, which the model cannot inspect.
    direct_vm.mock_llm(r"(?s)^(?!.*" + EVIDENCE_A + r")(?!.*" + EVIDENCE_B + r")"
                       r".*2024-03-02.*lighthouse-dusk.*north pier lighthouse.*2024-05-19.*posts/88231.*my feed",
                       answer("CLAIMANT_A", URL_A))
    assert contract.decide(MEDIA)["fact_source"] == "url_a"


# --- must refuse (the owner's row) ------------------------------------------------------

def test_refuses_a_third_claimant(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)

    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("[EXPECTED] THIRD_CLAIMANT: this photo already has two claimants"):
            contract.submit_claim(MEDIA, "Actually it is mine.", "https://third.example/p/1", "2022-01-01",
                                  EVIDENCE_A)
    stored = dispute(contract)
    assert stored["claimant_b"] == address_hex(direct_bob).lower()
    assert stored["claim_b"]["statement"] == STATEMENT_B


def test_refuses_an_edit_after_both_are_in(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_a(contract)
    # While B is missing, A may edit their own claim.
    edited = contract.edit_claim(MEDIA, "Edited: " + STATEMENT_A, URL_A, DATE_A, EVIDENCE_A)
    assert edited == {"media_sha256": MEDIA, "role": "CLAIMANT_A", "status": "AWAITING_CLAIMANT_B"}
    assert dispute(contract)["claim_a"]["statement"] == "Edited: " + STATEMENT_A
    claim_b(direct_vm, contract, direct_bob)

    locked = "[EXPECTED] STATEMENT_LOCKED: both claims are in; statements can no longer be edited"
    with direct_vm.expect_revert(locked):
        contract.edit_claim(MEDIA, "Changed after B joined.", URL_A, "2020-01-01", EVIDENCE_A)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert(locked):
            contract.edit_claim(MEDIA, "B changes too.", URL_B, DATE_B, EVIDENCE_B)
    stored = dispute(contract)
    assert stored["claim_a"]["statement"] == "Edited: " + STATEMENT_A
    assert stored["claim_a"]["first_publication_date"] == DATE_A
    assert stored["claim_b"]["statement"] == STATEMENT_B


def test_refuses_a_decision_before_both_exist(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("[EXPECTED] UNKNOWN_DISPUTE: no dispute is stored for this media hash"):
        contract.decide(MEDIA)
    claim_a(contract)
    # No LLM mock: the refusal comes before any model call.
    with direct_vm.expect_revert("[EXPECTED] BOTH_CLAIMS_REQUIRED: a decision needs both claimants' statements"):
        contract.decide(MEDIA)
    assert dispute(contract)["status"] == "AWAITING_CLAIMANT_B"


def test_refuses_a_second_decision(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", FACT_A))
    contract.decide(MEDIA)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_B", FACT_B))

    with direct_vm.expect_revert("[EXPECTED] ALREADY_DECIDED: this dispute is already decided"):
        contract.decide(MEDIA)
    assert dispute(contract)["verdict"] == "CLAIMANT_A"


# --- other refusals ---------------------------------------------------------------------

def test_refuses_a_second_claim_from_a_party_and_edits_from_others(direct_vm, direct_deploy, direct_alice,
                                                                    direct_bob, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_a(contract)
    with direct_vm.expect_revert(
            "[EXPECTED] ALREADY_A_CLAIMANT: this address already has a claim on this photo; use edit_claim"):
        claim_a(contract, statement="Again.")
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("[EXPECTED] NOT_A_CLAIMANT: only a claimant can edit their own claim"):
            contract.edit_claim(MEDIA, "Not mine to edit.", URL_B, DATE_B, EVIDENCE_B)
    with direct_vm.expect_revert("UNKNOWN_DISPUTE"):
        contract.edit_claim(OTHER_MEDIA, STATEMENT_A, URL_A, DATE_A, EVIDENCE_A)
    claim_b(direct_vm, contract, direct_bob)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("ALREADY_A_CLAIMANT"):
            contract.submit_claim(MEDIA, "Again.", URL_B, DATE_B, EVIDENCE_B)


def test_refuses_malformed_hashes(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for bad in ["", "not-a-hash", "g" * 64, MEDIA[:63], MEDIA + "0"]:
        with direct_vm.expect_revert("[EXPECTED] BAD_MEDIA_HASH: media_sha256 must be 64 hexadecimal characters"):
            claim_a(contract, media=bad)
        with direct_vm.expect_revert(
                "[EXPECTED] BAD_EVIDENCE_HASH: evidence_sha256 must be 64 hexadecimal characters"):
            claim_a(contract, evidence=bad)
    with direct_vm.expect_revert("BAD_MEDIA_HASH"):
        contract.decide("photo-1")
    assert contract.get_dispute_count() == 0
    # Upper-case hex is accepted and stored lower-case.
    claim_a(contract, media=MEDIA.upper(), evidence=EVIDENCE_A.upper())
    assert dispute(contract)["claim_a"]["evidence_sha256"] == EVIDENCE_A
    assert contract.get_dispute_id(0) == MEDIA


def test_refuses_malformed_dates(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    bad_date = "[EXPECTED] BAD_DATE: first_publication_date must be a real calendar date written YYYY-MM-DD"
    for bad in ["", "2024-3-02", "02-03-2024", "2024/03/02", "2024-13-01", "2024-00-10", "2024-04-31",
                "2023-02-29", "2024-03-0x", "1700-01-01", "2024-03-02T10:00"]:
        with direct_vm.expect_revert(bad_date):
            claim_a(contract, date=bad)
    assert contract.get_dispute_count() == 0
    claim_a(contract, date="2024-02-29")
    assert dispute(contract)["claim_a"]["first_publication_date"] == "2024-02-29"


def test_refuses_empty_or_long_statements_and_bad_urls(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for bad in ["", "   ", "\n\t"]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_STATEMENT: statement must not be empty"):
            claim_a(contract, statement=bad)
    with direct_vm.expect_revert("[EXPECTED] STATEMENT_TOO_LONG: statement must be at most 2000 characters"):
        claim_a(contract, statement="x" * 2001)
    bad_url = ("[EXPECTED] BAD_URL: first_publication_url must be an http:// or https:// URL "
               "of at most 500 characters with no spaces")
    for bad in ["", "ftp://files.example/a.jpg", "https://", "portfolio.example/a",
                "https://portfolio.example/a b", "https://x.example/" + "a" * 500]:
        with direct_vm.expect_revert(bad_url):
            claim_a(contract, url=bad)
    assert contract.get_dispute_count() == 0
    with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: no dispute at this index"):
        contract.get_dispute_id(0)


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"deciding_fact": FACT_A, "reason": "x"}),
         "[LLM_ERROR] the model returned no verdict of CLAIMANT_A, CLAIMANT_B or UNDECIDED"),
        (answer("ALICE", FACT_A), "no verdict of CLAIMANT_A, CLAIMANT_B or UNDECIDED"),
        (answer("CLAIMANT_A", ""), "[LLM_ERROR] the model's deciding fact is not quoted verbatim from the claims"),
        (answer("CLAIMANT_A", "a RAW series of 14 frames"), "deciding fact is not quoted verbatim"),
        (answer("UNDECIDED", "both say it is theirs"), "deciding fact is not quoted verbatim"),
        (answer("CLAIMANT_A", FACT_A, "   "), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            contract.decide(MEDIA)
    assert dispute(contract)["status"] == "READY_FOR_DECISION"

    # A lower-case verdict word is read as the word.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("claimant_b", FACT_B))
    assert contract.decide(MEDIA)["verdict"] == "CLAIMANT_B"


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", FACT_A, "Leader wording."))
    contract.decide(MEDIA)

    # Same verdict word, different quoted fact and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", DATE_A, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("UNDECIDED", "", "Not enough."))
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_B", FACT_B))
    assert direct_vm.run_validator() is False

    # A leader fact that is not verbatim in the claims, or a malformed leader result: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", FACT_A))
    forged = {"verdict": "CLAIMANT_A", "deciding_fact": "A holds the original negative", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    unquoted = {"verdict": "CLAIMANT_A", "deciding_fact": "", "reason": "x"}
    assert direct_vm.run_validator(leader_result=unquoted) is False
    bad_word = {"verdict": "A", "deciding_fact": FACT_A, "reason": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_undecided(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    direct_vm.mock_llm(r"INPUT_JSON", answer("UNDECIDED", "", "Leader: even."))
    contract.decide(MEDIA)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("UNDECIDED", FACT_B, "Validator quotes something."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("CLAIMANT_A", FACT_A))
    assert direct_vm.run_validator() is False


def test_disputes_are_keyed_by_media_hash(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    both_in(direct_vm, contract, direct_bob)
    # A third address may still open a dispute on another photo.
    with direct_vm.prank(direct_charlie):
        opened = contract.submit_claim(OTHER_MEDIA, STATEMENT_B, URL_B, DATE_B, EVIDENCE_B)
    assert opened["role"] == "CLAIMANT_A"
    assert contract.get_dispute_count() == 2
    assert contract.get_dispute_id(1) == OTHER_MEDIA
    assert dispute(contract, OTHER_MEDIA)["claimant_a"] == address_hex(direct_charlie).lower()
