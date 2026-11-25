"""Direct-mode tests for contracts/factory/video_cut_review.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 14 ("Role contracts (one per role)", Videographer) and the shared role-contract
refusals. The LLM is mocked (the contract reads no web page), so these tests check the
contract's own logic (owner gate, input checks, the runtime check, the evidence-hash check,
the same-case check, parsing, the quoted-item check, storage, the validator's comparison),
not a model's judgment or GenVM consensus.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_video_cut_review.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "video_cut_review.py")

HEAD = "Brand film brief (public summary)\n"
RUNTIME_LINE = "Runtime: 90 seconds (plus or minus 5 seconds)"
REST = (
    "\nAspect ratios: 16:9 and 9:16\n"
    "Deliverables: master cut, 15-second cutdown, burned-in English subtitles, ProRes 422 and MP4 files"
)
TERMS = HEAD + RUNTIME_LINE + REST
ACCOUNT_OK = (
    "Delivery note 3 March: master cut delivered, runtime 1:32, in 16:9 and 9:16. Also delivered: "
    "15-second cutdown, burned-in English subtitles, ProRes 422 and MP4 files. "
    "Review link: https://example.com/review/video-5520"
)
ACCOUNT_SHORT = (
    "Delivery note 3 March: master cut delivered, runtime 2:05, in 16:9 only. Also delivered: "
    "15-second cutdown and MP4 files. Review link: https://example.com/review/video-5520"
)
CASE = "case-video-5520"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


HASH_OK = sha(ACCOUNT_OK)
HASH_SHORT = sha(ACCOUNT_SHORT)

ITEM_RUNTIME = RUNTIME_LINE
ITEM_RATIO = "9:16"
ITEM_SUBTITLES = "burned-in English subtitles"
ITEM_FROM_ACCOUNT = "runtime 2:05, in 16:9 only"

ERR_NO_RUNTIME = ("[EXPECTED] NO_RUNTIME: the brief states no runtime; agreed_terms needs a line starting "
                  "'Runtime:' (or 'Run time:', 'Running time:', 'Duration:') with a duration in digits such as "
                  "'90 seconds', '3 min' or '2:30'")
ERR_HASH = ("[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal "
            "characters) of the what_happened text exactly as supplied")
ERR_SAME_CASE = "[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict"
ERR_EMPTY_TERMS = "[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty"
ERR_ITEM = ("[LLM_ERROR] the model's missing item is not 3 to 400 characters quoted from the agreed terms "
            "or the delivery account")


def answer(verdict, item="", reason="One sentence."):
    return json.dumps({"verdict": verdict, "missing_item": item, "reason": reason})


def setup(direct_vm, direct_deploy, direct_owner):
    """The owner deploys the contract."""
    direct_vm.sender = direct_owner
    return direct_deploy(CONTRACT)


def review(contract, case_id=CASE, terms=TERMS, account=ACCOUNT_OK, evidence=None):
    if evidence is None:
        evidence = sha(account) if isinstance(account, str) else ""
    return contract.review_cut(case_id, terms, account, evidence)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def stored(contract, case_id=CASE):
    return json.loads(contract.get_review(case_id))


def _squash(text):
    return " ".join(text.split())


# --- answers -------------------------------------------------------------------------

def test_delivered_when_the_cut_meets_the_brief(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Runtime, ratios and deliverables all met."))

    result = review(contract)

    assert result == {"case_id": CASE, "role": "videographer", "verdict": "DELIVERED", "missing_item": "",
                      "reason": "Runtime, ratios and deliverables all met."}
    assert stored(contract) == {
        "case_id": CASE, "role": "videographer", "agreed_terms": TERMS, "terms_sha256": sha(TERMS),
        "what_happened": ACCOUNT_OK, "evidence_sha256": HASH_OK, "verdict": "DELIVERED", "missing_item": "",
        "reason": "Runtime, ratios and deliverables all met.",
        "reviewed_by": address_hex(direct_owner).lower(),
    }
    assert contract.has_review(CASE) is True
    assert contract.has_review("CASE-VIDEO-5520") is True
    assert contract.get_review_count() == 1
    assert contract.get_review_id(0) == CASE


def test_shortfall_names_the_missing_item_quoted_from_the_terms(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_RUNTIME, "Agreed 90 s +/- 5 s, delivered 2:05."))

    result = review(contract, account=ACCOUNT_SHORT)

    assert result == {"case_id": CASE, "role": "videographer", "verdict": "SHORTFALL",
                      "missing_item": ITEM_RUNTIME, "reason": "Agreed 90 s +/- 5 s, delivered 2:05."}
    record = stored(contract)
    assert record["verdict"] == "SHORTFALL"
    assert record["missing_item"] == ITEM_RUNTIME
    assert record["missing_item"] in TERMS
    assert record["evidence_sha256"] == HASH_SHORT


def test_shortfall_item_may_be_quoted_from_the_delivery_account(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_FROM_ACCOUNT, "Too long and 16:9 only."))
    result = review(contract, account=ACCOUNT_SHORT)
    assert result["missing_item"] == ITEM_FROM_ACCOUNT
    assert result["missing_item"] in ACCOUNT_SHORT and result["missing_item"] not in TERMS


def test_item_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The terms break the line between the runtime and the aspect ratios; the model's quote crosses
    # it with other whitespace, and the stored item has every run of whitespace collapsed.
    item = "(plus or minus 5 seconds) Aspect ratios: 16:9 and 9:16"
    assert item not in TERMS
    assert "(plus or minus 5 seconds)\nAspect ratios: 16:9 and 9:16" in TERMS
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", "  (plus or minus 5 seconds) \n\t Aspect ratios:  16:9 and 9:16 "))
    assert review(contract)["missing_item"] == item
    assert stored(contract)["missing_item"] == item


def test_delivered_never_stores_a_missing_item(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", ITEM_RATIO, "Model added an item by mistake."))
    assert review(contract)["missing_item"] == ""
    assert stored(contract)["missing_item"] == ""


def test_a_lower_case_verdict_word_is_read_as_the_word(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer(" shortfall ", ITEM_SUBTITLES))
    assert review(contract)["verdict"] == "SHORTFALL"


def test_prompt_carries_the_public_inputs_and_no_hash_or_case_id(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the three checks in order, the brief, the delivery account and the role,
    # and the absence of the evidence hash, the terms hash and the case id (canonical JSON: sorted keys).
    direct_vm.mock_llm(r"(?s)^(?!.*" + HASH_OK + r")(?!.*" + sha(TERMS) + r")(?!.*" + CASE + r")"
                       r".*videographer.*\(1\) runtime.*\(2\) aspect ratios.*\(3\) deliverables list.*INPUT_JSON"
                       r".*\"agreed_terms\":\"Brand film brief.*\"delivery_account\":\"Delivery note 3 March: master cut"
                       r".*\"role\":\"videographer\"",
                       answer("DELIVERED"))
    assert review(contract)["verdict"] == "DELIVERED"


# --- must refuse: the row's own ------------------------------------------------------------

def test_refuses_a_brief_with_no_runtime(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_runtime_lines = [
        "",                                                   # no runtime line at all
        "The film should run about 90 seconds.",              # only in a sentence, no label
        "Runtime 90 seconds",                                 # label without a colon
        "Runtime:",                                           # blank
        "Runtime:   ",
        "Runtime: TBC",
        "Runtime: none",
        "Run time: to be agreed",
        "Runtime: N/A",
        "Duration: short",                                    # no digits
        "Runtime: about ninety seconds",                      # number in words
        "Runtime: 0 seconds",                                 # zero
        "Runtime: 00:00",
        "Runtime: 90",                                        # no unit
        "Runtime: 16:9",                                      # an aspect ratio, not a clock
        "Runtime: 16:9 widescreen",
        "Runtime: 4K at 25 fps",                              # numbers without a time unit
        "Runtime: 90 frames",
        "Runtime: 90 seconds TBC",                            # a placeholder on the line
        "Running time: 3 min, to be confirmed",
        "Runtime: 2 minutes (not yet agreed)",
        "Runtimes: 90 seconds",                               # not the label
        "Shoot duration: 8 hours",                            # another duration, not the cut's
        "Deliverables: 90-second film",                       # a duration under another label
        "Runtime:\n- 90 seconds",                             # a list under a bare label is not read
    ]
    for line in bad_runtime_lines:
        terms = HEAD + line + REST
        with direct_vm.expect_revert(ERR_NO_RUNTIME):
            review(contract, terms=terms)
    # The runtime check runs before the account and its hash are looked at.
    with direct_vm.expect_revert(ERR_NO_RUNTIME):
        contract.review_cut(CASE, HEAD + REST, ACCOUNT_OK, "not-a-hash")
    assert contract.get_review_count() == 0


def test_a_runtime_line_is_found_in_any_common_layout(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    good_terms = [
        TERMS,
        HEAD + "Runtime: 3 minutes" + REST,
        HEAD + "RUN TIME: 2:30" + REST,
        HEAD + "Running time: 1:02:30" + REST,
        HEAD + "- Duration: 45s" + REST,
        HEAD + "1) Target runtime: 60-90 seconds" + REST,
        HEAD + "  * run-time : 2 mins" + REST,
        HEAD + "Runtime: 1.5 min" + REST,
        HEAD + "Runtime: 2.0 minutes" + REST,                 # the decimal is read with its whole part
        HEAD + "Runtime: a 90-second spot" + REST,
        HEAD + "Runtime: 0:45" + REST,
        HEAD + "Target duration: 1 hr 20 min" + REST,
        HEAD + "Runtime: master 90 s, cutdowns 15 s and 6 s" + REST,
        HEAD + "Runtime: 16:9 master runs 2 min" + REST,
        (HEAD + RUNTIME_LINE + REST).replace("\n", "\r\n"),
        (HEAD + RUNTIME_LINE + REST).replace("\n", "\r"),     # bare CR line ends
        RUNTIME_LINE + "\n" + HEAD + REST.lstrip("\n"),
    ]
    index = 0
    while index < len(good_terms):
        result = review(contract, case_id="case-" + str(index), terms=good_terms[index])
        assert result["verdict"] == "DELIVERED"
        index += 1
    assert contract.get_review_count() == len(good_terms)


# --- must refuse: shared by every role contract -----------------------------------------------

def test_refuses_empty_terms(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for terms in ["", " ", "   ", "\n\t \r\n"]:
        with direct_vm.expect_revert(ERR_EMPTY_TERMS):
            review(contract, terms=terms)
    # Empty terms are refused before the runtime check and before the evidence is looked at.
    with direct_vm.expect_revert(ERR_EMPTY_TERMS):
        contract.review_cut(CASE, "", ACCOUNT_OK, "not-a-hash")
    assert contract.get_review_count() == 0


def test_refuses_terms_over_the_limit(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    head = "Runtime: 90 seconds\n"
    long_terms = head + "x" * (8000 - len(head))
    assert len(long_terms) == 8000
    assert review(contract, terms=long_terms)["verdict"] == "DELIVERED"
    with direct_vm.expect_revert("[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters"):
        review(contract, case_id="case-2", terms=long_terms + "x")
    assert contract.get_review_count() == 1


def test_refuses_an_empty_or_overlong_account_of_what_happened(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for account in ["", "   ", "\n\t"]:
        with direct_vm.expect_revert("[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty"):
            contract.review_cut(CASE, TERMS, account, sha(account))
    long_account = "x" * 8001
    with direct_vm.expect_revert(
            "[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters"):
        contract.review_cut(CASE, TERMS, long_account, sha(long_account))
    assert contract.get_review_count() == 0


def test_refuses_an_evidence_hash_that_does_not_match(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    wrong = [
        HASH_SHORT,                          # the hash of another account
        sha(TERMS),                          # the hash of the terms
        sha(ACCOUNT_OK + " "),               # one trailing space: the text is hashed exactly as given
        sha(ACCOUNT_OK.replace("1:32", "1:33")),
        "0" * 64,
        HASH_OK[:63], HASH_OK + "0", "g" * 64, "not-a-hash", "", "   ",
        "0x" + HASH_OK,
    ]
    for evidence in wrong:
        with direct_vm.expect_revert(ERR_HASH):
            contract.review_cut(CASE, TERMS, ACCOUNT_OK, evidence)
    # The text edited after hashing does not match either.
    with direct_vm.expect_revert(ERR_HASH):
        contract.review_cut(CASE, TERMS, ACCOUNT_OK.replace("1:32", "1:33"), HASH_OK)
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False

    # The exact hash is accepted; upper-case hex and surrounding spaces are read as the same hash.
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    contract.review_cut(CASE, TERMS, ACCOUNT_OK, "  " + HASH_OK.upper() + " ")
    assert stored(contract)["evidence_sha256"] == HASH_OK


def test_refuses_the_same_case_twice(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_RUNTIME, "First verdict."))
    review(contract, account=ACCOUNT_SHORT)
    first = contract.get_review(CASE)

    # The same inputs, the same id in other case, and the same id with other terms or evidence.
    other_terms = TERMS.replace("90 seconds", "120 seconds")
    attempts = [
        dict(account=ACCOUNT_SHORT),
        dict(case_id="CASE-VIDEO-5520", account=ACCOUNT_SHORT),
        dict(account=ACCOUNT_OK),
        dict(terms=other_terms, account=ACCOUNT_SHORT),
    ]
    for attempt in attempts:
        direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Second verdict."))
        with direct_vm.expect_revert(ERR_SAME_CASE):
            review(contract, **attempt)
    assert contract.get_review(CASE) == first
    assert stored(contract)["verdict"] == "SHORTFALL"
    assert contract.get_review_count() == 1

    # A different case id is a different case, even with identical text.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Other case."))
    assert review(contract, case_id="case-video-5521", account=ACCOUNT_SHORT)["verdict"] == "DELIVERED"
    assert contract.get_review_count() == 2
    assert contract.get_review_id(1) == "case-video-5521"


def test_a_refused_review_does_not_lock_the_case(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    with direct_vm.expect_revert("[LLM_ERROR] the model did not return a JSON object"):
        review(contract)
    with direct_vm.expect_revert(ERR_NO_RUNTIME):
        review(contract, terms="Aspect ratios: 16:9 and 9:16")
    assert contract.has_review(CASE) is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    assert review(contract)["verdict"] == "DELIVERED"


def test_only_the_owner_requests_reviews(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert(
                "[EXPECTED] OWNER_ONLY: only the contract owner can request a cut review"):
            review(contract)
    assert contract.get_review_count() == 0
    assert review(contract)["verdict"] == "DELIVERED"


def test_refuses_bad_case_ids(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    bad_id = "[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -"
    for case_id in ["", " ", "case 1", "case/1", "case\n1", "x" * 65, "café", "case:1", 5520, None]:
        with direct_vm.expect_revert(bad_id):
            review(contract, case_id=case_id)
        with direct_vm.expect_revert(bad_id):
            contract.has_review(case_id)
    assert contract.get_review_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    review(contract, case_id="X" * 64)
    assert contract.get_review_id(0) == "x" * 64


def test_reads(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_role() == "videographer"
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False
    with direct_vm.expect_revert("[EXPECTED] NO_REVIEW: no review is stored for this case_id"):
        contract.get_review(CASE)
    for index in [0, -1, 5]:
        with direct_vm.expect_revert("[EXPECTED] BAD_INDEX: nothing at this index"):
            contract.get_review_id(index)


# --- the model's answer ----------------------------------------------------------------------

def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    verdict_error = "[LLM_ERROR] the model returned no verdict of DELIVERED or SHORTFALL"
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"missing_item": ITEM_RATIO, "reason": "x"}), verdict_error),
        (answer("YES"), verdict_error),
        (answer("NOT_DELIVERED", ITEM_RATIO), verdict_error),
        (json.dumps({"verdict": 1, "reason": "x"}), verdict_error),
        (answer("SHORTFALL", ""), ERR_ITEM),
        (answer("SHORTFALL", "a director's cut with commentary"), ERR_ITEM),
        (answer("SHORTFALL", "16"), ERR_ITEM),
        (answer("SHORTFALL", "ab"), ERR_ITEM),
        (answer("SHORTFALL", TERMS + " " + ACCOUNT_OK), ERR_ITEM),
        (json.dumps({"verdict": "SHORTFALL", "reason": "x"}), ERR_ITEM),
        (json.dumps({"verdict": "SHORTFALL", "missing_item": ["a list"], "reason": "x"}), ERR_ITEM),
        (answer("DELIVERED", "", "   "), "[LLM_ERROR] the model returned no reason"),
        (json.dumps({"verdict": "DELIVERED"}), "[LLM_ERROR] the model returned no reason"),
        (answer("SHORTFALL", ITEM_RATIO, ""), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with direct_vm.expect_revert(expected):
            review(contract)
    assert contract.get_review_count() == 0


def test_refuses_an_item_over_the_limit(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    long_terms = TERMS + "\nNotes: " + "the edit runs through many rounds of notes and colour passes. " * 8
    quote = long_terms[long_terms.index("Notes:"):]
    assert len(quote) > 400
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", quote))
    with direct_vm.expect_revert(ERR_ITEM):
        review(contract, terms=long_terms)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", _squash(quote)[:400].rstrip()))
    assert review(contract, terms=long_terms)["verdict"] == "SHORTFALL"
    assert len(stored(contract)["missing_item"]) <= 400


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_RUNTIME, "Leader wording."))
    review(contract, account=ACCOUNT_SHORT)

    # Same verdict word, another item and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_RATIO, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Looks complete."))
    assert direct_vm.run_validator() is False

    # A leader result that is malformed or forged: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_RUNTIME))
    forged = {"verdict": "SHORTFALL", "missing_item": "a director's cut with commentary", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    short = {"verdict": "SHORTFALL", "missing_item": "16", "reason": "x"}
    assert direct_vm.run_validator(leader_result=short) is False
    no_item = {"verdict": "SHORTFALL", "missing_item": "", "reason": "x"}
    assert direct_vm.run_validator(leader_result=no_item) is False
    missing_key = {"verdict": "SHORTFALL", "reason": "x"}
    assert direct_vm.run_validator(leader_result=missing_key) is False
    bad_word = {"verdict": "YES", "missing_item": ITEM_RUNTIME, "reason": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False
    no_reason = {"verdict": "SHORTFALL", "missing_item": ITEM_RUNTIME}
    assert direct_vm.run_validator(leader_result=no_reason) is False
    assert direct_vm.run_validator(leader_result="SHORTFALL") is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_delivered(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Leader: complete."))
    review(contract)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED", "", "Validator wording."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("SHORTFALL", ITEM_SUBTITLES, "No subtitles."))
    assert direct_vm.run_validator() is False

    # DELIVERED must carry no item: a leader result that names one is malformed.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("DELIVERED"))
    with_item = {"verdict": "DELIVERED", "missing_item": ITEM_RUNTIME, "reason": "x"}
    assert direct_vm.run_validator(leader_result=with_item) is False
    assert direct_vm.run_validator(leader_result={"verdict": "DELIVERED", "reason": "x"}) is False
