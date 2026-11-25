"""Direct-mode tests for contracts/factory/editorial_usage_check.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 15 ("Role contracts (one per role)", Fashion Model) and the shared role-contract
refusals. The LLM is mocked (the contract reads no web page), so these tests check the
contract's own logic (owner gate, input checks, the usage-terms check, the evidence-hash
check, the same-case check, parsing, the quoted-placement check, storage, the validator's
comparison), not a model's judgment or GenVM consensus.

Every refusal is asserted with its exact text: `refused(...)` requires the raised
gl.vm.UserError's message to equal the expected text, not merely contain it.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_editorial_usage_check.py -v
"""
import ast
import hashlib
import json
import re
from contextlib import contextmanager
from pathlib import Path

import pytest

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "editorial_usage_check.py")

HEAD = (
    "Fashion editorial booking (public summary)\n"
    "Shoot: 1 day studio, autumn knitwear story\n"
    "Client: a fashion magazine (editorial booking)"
)
TERMS = (
    HEAD + "\n"
    "Usage: editorial only, print and online issues of the magazine, 12 months; no advertising, "
    "advertorial or brand use without a new fee"
)
ACCOUNT_EDITORIAL = (
    "Published use: 8-page fashion story 'Autumn Knits' in the magazine's November print issue, "
    "pages 112-119, and the same story on the magazine's website. "
    "URL: https://example.com/fashion/autumn-knits"
)
ACCOUNT_COMMERCIAL = (
    "Published use: the same story in the November print issue, pages 112-119; "
    "one image from the shoot used in a paid Instagram advertisement for a knitwear brand, "
    "running 1-14 November. Ad library: https://example.com/ads/knitwear-7731"
)
CASE = "case-usage-7731"

PLACEMENT_EDITORIAL = "8-page fashion story 'Autumn Knits' in the magazine's November print issue"
PLACEMENT_AD = "a paid Instagram advertisement for a knitwear brand"
PLACEMENT_URL = "https://example.com/ads/knitwear-7731"
QUOTE_FROM_TERMS = "no advertising, advertorial or brand use without a new fee"

ERR_NO_USAGE = ("[EXPECTED] NO_USAGE_TERMS: the booking states no usage terms; agreed_terms needs a line "
                "starting 'Usage:' or 'Usage terms:' (or 'Usage rights:') followed by the agreed usage")
ERR_HASH = ("[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal "
            "characters) of the what_happened text exactly as supplied")
ERR_SAME_CASE = "[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict"
ERR_EMPTY_TERMS = "[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty"
ERR_TERMS_TOO_LONG = "[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters"
ERR_EMPTY_WHAT = "[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty"
ERR_WHAT_TOO_LONG = "[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: only the contract owner can request a usage review"
ERR_BAD_CASE_ID = "[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -"
ERR_NO_REVIEW = "[EXPECTED] NO_REVIEW: no review is stored for this case_id"
ERR_BAD_INDEX = "[EXPECTED] BAD_INDEX: nothing at this index"
ERR_LLM_FORMAT = "[LLM_ERROR] the model did not return a JSON object"
ERR_LLM_VERDICT = "[LLM_ERROR] the model returned no verdict of EDITORIAL or COMMERCIAL_USE"
ERR_LLM_PLACEMENT = "[LLM_ERROR] the model's placement is not 3 to 400 characters quoted from the published use"
ERR_LLM_REASON = "[LLM_ERROR] the model returned no reason"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


HASH_EDITORIAL = sha(ACCOUNT_EDITORIAL)
HASH_COMMERCIAL = sha(ACCOUNT_COMMERCIAL)


def answer(verdict, placement=PLACEMENT_EDITORIAL, reason="One sentence."):
    return json.dumps({"verdict": verdict, "placement": placement, "reason": reason})


@contextmanager
def refused(text):
    """The call must raise gl.vm.UserError whose message is exactly `text`."""
    with pytest.raises(Exception) as info:
        yield
    message = getattr(info.value, "message", None)
    assert type(info.value).__name__ == "UserError", repr(info.value)
    assert message == text


def setup(direct_vm, direct_deploy, direct_owner):
    """The owner deploys the contract."""
    direct_vm.sender = direct_owner
    return direct_deploy(CONTRACT)


def review(contract, case_id=CASE, terms=TERMS, account=ACCOUNT_EDITORIAL, evidence=None):
    if evidence is None:
        evidence = sha(account) if isinstance(account, str) else ""
    return contract.review_usage(case_id, terms, account, evidence)


def address_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def stored(contract, case_id=CASE):
    return json.loads(contract.get_review(case_id))


def _squash(text):
    return " ".join(text.split())


# --- source shape ------------------------------------------------------------------------

def test_source_shape_header_and_module_docstring():
    source = Path(CONTRACT).read_text(encoding="utf-8")
    lines = source.split("\n")
    assert lines[0] == '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
    assert not lines[1].lstrip().startswith("#")
    doc = ast.get_docstring(ast.parse(source))
    assert doc is not None
    assert "Constructor: EditorialUsageCheck() takes no arguments" in doc


# --- answers -------------------------------------------------------------------------------

def test_editorial_when_the_published_use_is_editorial(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", PLACEMENT_EDITORIAL, "A magazine story, as agreed."))

    result = review(contract)

    assert result == {"case_id": CASE, "role": "model_fashion", "verdict": "EDITORIAL",
                      "placement": PLACEMENT_EDITORIAL, "reason": "A magazine story, as agreed."}
    assert stored(contract) == {
        "case_id": CASE, "role": "model_fashion", "agreed_terms": TERMS, "terms_sha256": sha(TERMS),
        "what_happened": ACCOUNT_EDITORIAL, "evidence_sha256": HASH_EDITORIAL, "verdict": "EDITORIAL",
        "placement": PLACEMENT_EDITORIAL, "reason": "A magazine story, as agreed.",
        "reviewed_by": address_hex(direct_owner).lower(),
    }
    assert contract.has_review(CASE) is True
    assert contract.has_review("CASE-USAGE-7731") is True
    assert contract.get_review_count() == 1
    assert contract.get_review_id(0) == CASE


def test_commercial_use_quotes_the_advertising_placement(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_AD, "A paid brand ad is not editorial."))

    result = review(contract, account=ACCOUNT_COMMERCIAL)

    assert result == {"case_id": CASE, "role": "model_fashion", "verdict": "COMMERCIAL_USE",
                      "placement": PLACEMENT_AD, "reason": "A paid brand ad is not editorial."}
    record = stored(contract)
    assert record["verdict"] == "COMMERCIAL_USE"
    assert record["placement"] == PLACEMENT_AD
    assert record["placement"] in ACCOUNT_COMMERCIAL
    assert record["evidence_sha256"] == HASH_COMMERCIAL
    assert record["what_happened"] == ACCOUNT_COMMERCIAL


def test_the_placement_may_be_a_public_url_in_the_published_use(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_URL, "The ad library shows a paid ad."))
    assert review(contract, account=ACCOUNT_COMMERCIAL)["placement"] == PLACEMENT_URL


def test_the_placement_must_be_quoted_from_the_published_use_not_the_terms(direct_vm, direct_deploy,
                                                                          direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert QUOTE_FROM_TERMS in TERMS and QUOTE_FROM_TERMS not in ACCOUNT_COMMERCIAL
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", QUOTE_FROM_TERMS))
    with refused(ERR_LLM_PLACEMENT):
        review(contract, account=ACCOUNT_COMMERCIAL)
    assert contract.get_review_count() == 0


def test_placement_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    account = "Published use:\n  paid Instagram\tadvertisement\n for a knitwear brand, 1-14 November"
    item = "paid Instagram advertisement for a knitwear brand"
    assert item not in account
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", "  paid Instagram \n advertisement  for a knitwear brand ",
                                             "  A paid ad.\n "))
    assert review(contract, account=account)["placement"] == item
    assert stored(contract)["placement"] == item
    assert stored(contract)["reason"] == "A paid ad."


def test_verdict_word_spelling_is_normalised(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    spellings = [(" commercial use ", "COMMERCIAL_USE"), ("Commercial-Use", "COMMERCIAL_USE"),
                 ("editorial", "EDITORIAL")]
    index = 0
    while index < len(spellings):
        word, expected = spellings[index]
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer(word, PLACEMENT_AD))
        result = review(contract, case_id="case-" + str(index), account=ACCOUNT_COMMERCIAL)
        assert result["verdict"] == expected
        index += 1


def test_prompt_carries_the_public_inputs_and_no_hash_or_case_id(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the decision rules, the agreed terms, the published use and the role, and
    # the absence of the evidence hash, the terms hash and the case id (canonical JSON: sorted keys).
    rules = [
        "Editorial use: the images illustrate editorial content",
        "Advertising or commercial use: the images promote or sell a product, brand or service",
        "Answer COMMERCIAL_USE when any placement in published_use is advertising or commercial use "
        "that the usage terms in agreed_terms do not expressly grant; a new fee is then due.",
        "Otherwise answer EDITORIAL: every placement is editorial use, or a use the usage terms "
        "expressly grant.",
        "A placement whose kind published_use does not show is not commercial use by itself.",
        "for COMMERCIAL_USE the first advertising or commercial placement",
    ]
    direct_vm.mock_llm(r"(?s)^(?!.*" + HASH_EDITORIAL + r")(?!.*" + sha(TERMS) + r")(?!.*" + CASE + r")"
                       r".*" + r".*".join(re.escape(rule) for rule in rules) + r".*INPUT_JSON"
                       r".*\"agreed_terms\":\"Fashion editorial booking.*Usage: editorial only"
                       r".*\"published_use\":\"Published use: 8-page fashion story"
                       r".*\"role\":\"model_fashion\"",
                       answer("EDITORIAL"))
    assert review(contract)["verdict"] == "EDITORIAL"


# --- must refuse: the row's own ------------------------------------------------------------

def test_refuses_a_booking_with_no_usage_terms(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    bad_terms = [
        HEAD,
        HEAD + "\nThe images will appear in the magazine.",
        HEAD + "\nUsage terms to be agreed",
        HEAD + "\nUsage:",
        HEAD + "\nUsage:   \n",
        HEAD + "\nUsage: none",
        HEAD + "\nUsage: None.",
        HEAD + "\nUsage rights: N/A",
        HEAD + "\nusage: TBC",
        HEAD + "\nUsage: -",
        HEAD + "\nUsage: ok",
        HEAD + "\nUsage terms: to be agreed",
        HEAD + "\n1. Usage: not specified",
        HEAD + "\nUsage: as agreed",
        HEAD + "\nUsage terms: see contract",
        HEAD + "\nUsage:\n\nShoot: 1 day studio",
        HEAD + "\nUsage fee: 500 per image",
        HEAD + "\nFee: 500 per day, editorial rate",
        HEAD + "\nNotes: usage to be agreed later",
        "Reusage: editorial\n" + HEAD,
    ]
    for terms in bad_terms:
        with refused(ERR_NO_USAGE):
            review(contract, terms=terms)
    assert contract.get_review_count() == 0


def test_a_usage_line_is_found_in_any_common_layout(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    head = HEAD + "\n"
    good_terms = [
        TERMS,
        head + "Usage: web",
        head + "USAGE TERMS: Editorial, print only",
        head + "- Usage rights: editorial online, 6 months",
        head + "2) Agreed usage: editorial print and online",
        head + "  * Permitted usage: editorial, UK only",
        head + "Image usage: editorial",
        head + "Usage licence: editorial, worldwide",
        head + "Usage license: editorial, worldwide",
        head + "**Usage**: editorial only",
        head + "Usage:\n- editorial print\n- 12 months\n\nFee: agreed",
        (head + "Usage: editorial print and online").replace("\n", "\r\n"),
        "Usage: editorial print\n" + head,
    ]
    index = 0
    while index < len(good_terms):
        result = review(contract, case_id="case-" + str(index), terms=good_terms[index])
        assert result["verdict"] == "EDITORIAL"
        index += 1
    assert contract.get_review_count() == len(good_terms)


# --- must refuse: shared by every role contract -----------------------------------------------

def test_refuses_empty_terms(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for terms in ["", " ", "   ", "\n\t \r\n"]:
        with refused(ERR_EMPTY_TERMS):
            review(contract, terms=terms)
    # Empty terms are refused before the usage check and before the evidence is looked at.
    with refused(ERR_EMPTY_TERMS):
        contract.review_usage(CASE, "", ACCOUNT_EDITORIAL, "not-a-hash")
    with refused(ERR_EMPTY_TERMS):
        contract.review_usage(CASE, None, "", "")
    assert contract.get_review_count() == 0


def test_refuses_terms_over_the_limit(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    first = "Usage: editorial only\n"
    long_terms = first + "x" * (8000 - len(first))
    assert len(long_terms) == 8000
    assert review(contract, terms=long_terms)["verdict"] == "EDITORIAL"
    with refused(ERR_TERMS_TOO_LONG):
        review(contract, case_id="case-2", terms=long_terms + "x")
    assert contract.get_review_count() == 1


def test_refuses_an_empty_or_overlong_account_of_what_happened(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", "x" * 10))
    for account in ["", "   ", "\n\t"]:
        with refused(ERR_EMPTY_WHAT):
            contract.review_usage(CASE, TERMS, account, sha(account))
    long_account = "x" * 8001
    with refused(ERR_WHAT_TOO_LONG):
        contract.review_usage(CASE, TERMS, long_account, sha(long_account))
    assert contract.get_review_count() == 0
    assert review(contract, account="x" * 8000)["verdict"] == "EDITORIAL"


def test_refuses_an_evidence_hash_that_does_not_match(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    wrong = [
        HASH_COMMERCIAL,                             # the hash of another account
        sha(TERMS),                                  # the hash of the terms
        sha(ACCOUNT_EDITORIAL + " "),                # one trailing space: the text is hashed exactly as given
        sha(ACCOUNT_EDITORIAL.replace("8-page", "6-page")),
        "0" * 64,
        HASH_EDITORIAL[:63], HASH_EDITORIAL + "0", "g" * 64, "not-a-hash", "", "   ",
        "0x" + HASH_EDITORIAL,
        None, 7731,
    ]
    for evidence in wrong:
        with refused(ERR_HASH):
            contract.review_usage(CASE, TERMS, ACCOUNT_EDITORIAL, evidence)
    # The text edited after hashing does not match either.
    with refused(ERR_HASH):
        contract.review_usage(CASE, TERMS, ACCOUNT_EDITORIAL.replace("8-page", "6-page"), HASH_EDITORIAL)
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False

    # The exact hash is accepted; upper-case hex and surrounding spaces are read as the same hash.
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    contract.review_usage(CASE, TERMS, ACCOUNT_EDITORIAL, "  " + HASH_EDITORIAL.upper() + " ")
    assert stored(contract)["evidence_sha256"] == HASH_EDITORIAL


def test_refuses_the_same_case_twice(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_AD, "First verdict."))
    review(contract, account=ACCOUNT_COMMERCIAL)
    first = contract.get_review(CASE)

    # The same inputs, the same id in other case, and the same id with other terms or evidence.
    other_terms = TERMS.replace("12 months", "24 months")
    attempts = [
        dict(account=ACCOUNT_COMMERCIAL),
        dict(case_id="CASE-USAGE-7731", account=ACCOUNT_COMMERCIAL),
        dict(account=ACCOUNT_EDITORIAL),
        dict(terms=other_terms, account=ACCOUNT_COMMERCIAL),
    ]
    for attempt in attempts:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", PLACEMENT_EDITORIAL, "Second verdict."))
        with refused(ERR_SAME_CASE):
            review(contract, **attempt)
    assert contract.get_review(CASE) == first
    assert stored(contract)["verdict"] == "COMMERCIAL_USE"
    assert contract.get_review_count() == 1

    # A different case id is a different case, even with identical text.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", "the same story in the November print issue",
                                             "Other case."))
    assert review(contract, case_id="case-usage-7732", account=ACCOUNT_COMMERCIAL)["verdict"] == "EDITORIAL"
    assert contract.get_review_count() == 2
    assert contract.get_review_id(1) == "case-usage-7732"


def test_a_refused_review_does_not_lock_the_case(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    with refused(ERR_LLM_FORMAT):
        review(contract)
    with refused(ERR_NO_USAGE):
        review(contract, terms=HEAD)
    with refused(ERR_HASH):
        review(contract, evidence=HASH_COMMERCIAL)
    assert contract.has_review(CASE) is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    assert review(contract)["verdict"] == "EDITORIAL"


def test_only_the_owner_requests_reviews(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    with direct_vm.prank(direct_alice):
        with refused(ERR_OWNER_ONLY):
            review(contract)
    assert contract.get_review_count() == 0
    assert review(contract)["verdict"] == "EDITORIAL"


def test_refuses_bad_case_ids(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for case_id in ["", " ", "case 1", "case/1", "case\n1", "x" * 65, "café", "case:1", 7731, None]:
        with refused(ERR_BAD_CASE_ID):
            review(contract, case_id=case_id)
        with refused(ERR_BAD_CASE_ID):
            contract.has_review(case_id)
    assert contract.get_review_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    review(contract, case_id="X" * 64)
    assert contract.get_review_id(0) == "x" * 64


def test_reads(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_role() == "model_fashion"
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False
    with refused(ERR_NO_REVIEW):
        contract.get_review(CASE)
    for index in [0, -1, 5]:
        with refused(ERR_BAD_INDEX):
            contract.get_review_id(index)


# --- the model's answer ----------------------------------------------------------------------

def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    cases = [
        ("no json at all", ERR_LLM_FORMAT),
        ("[1, 2]", ERR_LLM_FORMAT),
        (json.dumps({"placement": PLACEMENT_AD, "reason": "x"}), ERR_LLM_VERDICT),
        (answer("YES"), ERR_LLM_VERDICT),
        (answer("ADVERTISING", PLACEMENT_AD), ERR_LLM_VERDICT),
        (answer("COMMERCIAL", PLACEMENT_AD), ERR_LLM_VERDICT),
        (answer("NOT_EDITORIAL", PLACEMENT_AD), ERR_LLM_VERDICT),
        (json.dumps({"verdict": 1, "placement": PLACEMENT_AD, "reason": "x"}), ERR_LLM_VERDICT),
        (answer("COMMERCIAL_USE", ""), ERR_LLM_PLACEMENT),
        (answer("EDITORIAL", ""), ERR_LLM_PLACEMENT),
        (answer("COMMERCIAL_USE", "a billboard in Times Square"), ERR_LLM_PLACEMENT),
        (answer("COMMERCIAL_USE", "ad"), ERR_LLM_PLACEMENT),
        (answer("COMMERCIAL_USE", QUOTE_FROM_TERMS), ERR_LLM_PLACEMENT),
        (answer("COMMERCIAL_USE", ACCOUNT_COMMERCIAL + " " + TERMS), ERR_LLM_PLACEMENT),
        (json.dumps({"verdict": "EDITORIAL", "reason": "x"}), ERR_LLM_PLACEMENT),
        (json.dumps({"verdict": "COMMERCIAL_USE", "placement": [PLACEMENT_AD], "reason": "x"}),
         ERR_LLM_PLACEMENT),
        (answer("COMMERCIAL_USE", PLACEMENT_AD, "   "), ERR_LLM_REASON),
        (json.dumps({"verdict": "COMMERCIAL_USE", "placement": PLACEMENT_AD}), ERR_LLM_REASON),
        (json.dumps({"verdict": "EDITORIAL", "placement": "November print issue", "reason": 5}),
         ERR_LLM_REASON),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with refused(expected):
            review(contract, account=ACCOUNT_COMMERCIAL)
    assert contract.get_review_count() == 0


def test_model_json_wrapped_in_text_is_read(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", "Here you go: " + answer("COMMERCIAL_USE", PLACEMENT_AD) + " done")
    assert review(contract, account=ACCOUNT_COMMERCIAL)["verdict"] == "COMMERCIAL_USE"


def test_refuses_a_placement_over_the_limit_and_truncates_the_reason(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    account = ACCOUNT_COMMERCIAL + "\nNotes: " + "the campaign ran on many channels in many countries for weeks. " * 8
    quote = account[account.index("Notes:"):]
    assert len(_squash(quote)) > 400
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", quote))
    with refused(ERR_LLM_PLACEMENT):
        review(contract, account=account)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", _squash(quote)[:400].rstrip(), "r" * 500))
    result = review(contract, account=account)
    assert result["verdict"] == "COMMERCIAL_USE"
    assert len(stored(contract)["placement"]) <= 400
    assert result["reason"] == "r" * 400
    assert stored(contract)["reason"] == "r" * 400


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_AD, "Leader wording."))
    review(contract, account=ACCOUNT_COMMERCIAL)

    # Same verdict word, another placement and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_URL, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", "the same story in the November print issue",
                                             "Looks editorial."))
    assert direct_vm.run_validator() is False

    # A leader result that is malformed or forged: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_AD))
    forged = {"verdict": "COMMERCIAL_USE", "placement": "a billboard in Times Square", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    from_terms = {"verdict": "COMMERCIAL_USE", "placement": QUOTE_FROM_TERMS, "reason": "x"}
    assert direct_vm.run_validator(leader_result=from_terms) is False
    short = {"verdict": "COMMERCIAL_USE", "placement": "ad", "reason": "x"}
    assert direct_vm.run_validator(leader_result=short) is False
    no_placement = {"verdict": "COMMERCIAL_USE", "placement": "", "reason": "x"}
    assert direct_vm.run_validator(leader_result=no_placement) is False
    missing_key = {"verdict": "COMMERCIAL_USE", "reason": "x"}
    assert direct_vm.run_validator(leader_result=missing_key) is False
    bad_word = {"verdict": "ADVERTISING", "placement": PLACEMENT_AD, "reason": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False
    lower_word = {"verdict": "commercial_use", "placement": PLACEMENT_AD, "reason": "x"}
    assert direct_vm.run_validator(leader_result=lower_word) is False
    no_reason = {"verdict": "COMMERCIAL_USE", "placement": PLACEMENT_AD}
    assert direct_vm.run_validator(leader_result=no_reason) is False
    blank_reason = {"verdict": "COMMERCIAL_USE", "placement": PLACEMENT_AD, "reason": " "}
    assert direct_vm.run_validator(leader_result=blank_reason) is False
    assert direct_vm.run_validator(leader_result="COMMERCIAL_USE") is False

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", PLACEMENT_AD))
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_editorial(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", PLACEMENT_EDITORIAL, "Leader: a magazine story."))
    review(contract)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL", "the magazine's website", "Validator wording."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("COMMERCIAL_USE", "the magazine's website", "Reads as an ad."))
    assert direct_vm.run_validator() is False

    # EDITORIAL must carry a placement quoted from the published use too.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("EDITORIAL"))
    assert direct_vm.run_validator(leader_result={"verdict": "EDITORIAL", "placement": "", "reason": "x"}) is False
    assert direct_vm.run_validator(leader_result={"verdict": "EDITORIAL", "reason": "x"}) is False
    assert direct_vm.run_validator(
        leader_result={"verdict": "EDITORIAL", "placement": PLACEMENT_EDITORIAL, "reason": "x"}) is True
