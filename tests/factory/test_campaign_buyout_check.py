"""Direct-mode tests for contracts/factory/campaign_buyout_check.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
owner's row 16 ("Role contracts (one per role)", Commercial Model) and the shared role-contract
refusals. The LLM is mocked (the contract reads no web page), so these tests check the
contract's own logic (owner gate, input checks, the date rule, the evidence-hash check, the
same-case check, parsing, the quoted-term check, storage, the validator's comparison), not a
model's judgment or GenVM consensus.

Every refusal is asserted with its exact text: `refused(...)` requires the raised
gl.vm.UserError's message to equal the expected text, not merely contain it.

Run from the repository root:
    pip install genlayer-test==0.29.2 pytest
    pytest tests/factory/test_campaign_buyout_check.py -v
"""
import ast
import hashlib
import json
import re
from contextlib import contextmanager
from pathlib import Path

import pytest

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "campaign_buyout_check.py")

HEAD = "Commercial buyout (public summary)\nShoot: 1 day studio, spring skincare campaign"
TERM_CHANNELS = "Channels: social media (Instagram, Facebook, TikTok) and the brand website"
TERM_TERRITORY = "Territory: United Kingdom and Ireland"
TERM_PERIOD = "Term: 12 months from first use"
TERMS = (
    HEAD + "\n"
    "Booking date: 2026-03-02\n"
    + TERM_CHANNELS + "\n"
    + TERM_TERRITORY + "\n"
    + TERM_PERIOD
)
ACCOUNT_WITHIN = (
    "Campaign use: spring skincare campaign\n"
    "First use: 2026-03-16\n"
    "Channel: Instagram feed posts and the brand website homepage banner\n"
    "Territory: UK\n"
    "URL: https://example.com/campaign/spring-glow"
)
ACCOUNT_EXCEEDED = (
    "Campaign use: spring skincare campaign\n"
    "Use dates: 2026-03-16 to 2026-09-30\n"
    "Channel: Instagram feed posts; a 48-sheet billboard at a railway station in Manchester\n"
    "Territory: UK\n"
    "URL: https://example.com/ooh/spring-glow-48sheet"
)
CASE = "case-buyout-1601"
BOOKING = "2026-03-02"
FIRST_USE = "2026-03-16"

QUOTE_FROM_ACCOUNT = "a 48-sheet billboard at a railway station in Manchester"

ERR_USE_BEFORE = "[EXPECTED] USE_BEFORE_BOOKING: the campaign use is dated before the booking"
ERR_NO_BOOKING_DATE = ("[EXPECTED] NO_BOOKING_DATE: agreed_terms needs exactly one line starting 'Booking date:' "
                       "followed by the booking date as YYYY-MM-DD")
ERR_NO_USE_DATE = ("[EXPECTED] NO_USE_DATE: what_happened needs a line starting 'Use date:', 'Use dates:' or "
                   "'First use:' followed by the date of the use as YYYY-MM-DD")
ERR_BAD_DATE = ("[EXPECTED] BAD_DATE: a booking date or use date line does not begin with a real calendar date "
                "written YYYY-MM-DD")
ERR_HASH = ("[EXPECTED] EVIDENCE_HASH_MISMATCH: evidence_sha256 must be the sha256 (64 hexadecimal "
            "characters) of the what_happened text exactly as supplied")
ERR_SAME_CASE = "[EXPECTED] SAME_CASE_TWICE: this case_id already has a verdict"
ERR_EMPTY_TERMS = "[EXPECTED] EMPTY_TERMS: agreed_terms must not be empty"
ERR_TERMS_TOO_LONG = "[EXPECTED] TERMS_TOO_LONG: agreed_terms must be at most 8000 characters"
ERR_EMPTY_WHAT = "[EXPECTED] EMPTY_WHAT_HAPPENED: what_happened must not be empty"
ERR_WHAT_TOO_LONG = "[EXPECTED] WHAT_HAPPENED_TOO_LONG: what_happened must be at most 8000 characters"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: only the contract owner can request a buyout review"
ERR_BAD_CASE_ID = "[EXPECTED] BAD_CASE_ID: case_id must be 1 to 64 characters from A-Z a-z 0-9 . _ -"
ERR_NO_REVIEW = "[EXPECTED] NO_REVIEW: no review is stored for this case_id"
ERR_BAD_INDEX = "[EXPECTED] BAD_INDEX: nothing at this index"
ERR_LLM_FORMAT = "[LLM_ERROR] the model did not return a JSON object"
ERR_LLM_VERDICT = "[LLM_ERROR] the model returned no verdict of WITHIN_BUYOUT or BUYOUT_EXCEEDED"
ERR_LLM_TERM = "[LLM_ERROR] the model's exceeded term is not 3 to 400 characters quoted from the agreed terms"
ERR_LLM_REASON = "[LLM_ERROR] the model returned no reason"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


HASH_WITHIN = sha(ACCOUNT_WITHIN)
HASH_EXCEEDED = sha(ACCOUNT_EXCEEDED)


def answer(verdict, term="", reason="One sentence."):
    return json.dumps({"verdict": verdict, "exceeded_term": term, "reason": reason})


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


def review(contract, case_id=CASE, terms=TERMS, account=ACCOUNT_WITHIN, evidence=None):
    if evidence is None:
        evidence = sha(account) if isinstance(account, str) else ""
    return contract.review_campaign_use(case_id, terms, account, evidence)


def terms_with_booking(line):
    return HEAD + "\n" + line + "\n" + TERM_CHANNELS + "\n" + TERM_TERRITORY + "\n" + TERM_PERIOD


def account_with_use(*lines):
    return "Campaign use: spring skincare campaign\n" + "\n".join(lines) + "\nTerritory: UK"


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
    assert "Constructor: CampaignBuyoutCheck() takes no arguments" in doc


# --- answers -------------------------------------------------------------------------------

def test_within_buyout_when_the_use_stays_inside_the_buyout(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", "", "Instagram and the website in the UK, as bought."))

    result = review(contract)

    assert result == {"case_id": CASE, "role": "model_commercial", "verdict": "WITHIN_BUYOUT",
                      "exceeded_term": "", "reason": "Instagram and the website in the UK, as bought.",
                      "booking_date": BOOKING, "first_use_date": FIRST_USE}
    assert stored(contract) == {
        "case_id": CASE, "role": "model_commercial", "agreed_terms": TERMS, "terms_sha256": sha(TERMS),
        "what_happened": ACCOUNT_WITHIN, "evidence_sha256": HASH_WITHIN,
        "booking_date": BOOKING, "first_use_date": FIRST_USE, "verdict": "WITHIN_BUYOUT",
        "exceeded_term": "", "reason": "Instagram and the website in the UK, as bought.",
        "reviewed_by": address_hex(direct_owner).lower(),
    }
    assert contract.has_review(CASE) is True
    assert contract.has_review("CASE-BUYOUT-1601") is True
    assert contract.get_review_count() == 1
    assert contract.get_review_id(0) == CASE


def test_buyout_exceeded_quotes_the_term_exceeded(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_CHANNELS, "A billboard is out of home, not bought."))

    result = review(contract, account=ACCOUNT_EXCEEDED)

    assert result == {"case_id": CASE, "role": "model_commercial", "verdict": "BUYOUT_EXCEEDED",
                      "exceeded_term": TERM_CHANNELS, "reason": "A billboard is out of home, not bought.",
                      "booking_date": BOOKING, "first_use_date": FIRST_USE}
    record = stored(contract)
    assert record["verdict"] == "BUYOUT_EXCEEDED"
    assert record["exceeded_term"] == TERM_CHANNELS
    assert record["exceeded_term"] in TERMS
    assert record["evidence_sha256"] == HASH_EXCEEDED
    assert record["what_happened"] == ACCOUNT_EXCEEDED


def test_the_exceeded_term_may_be_any_buyout_term(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    quotes = [TERM_TERRITORY, TERM_PERIOD, "12 months from first use", "United Kingdom and Ireland"]
    index = 0
    while index < len(quotes):
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", quotes[index]))
        result = review(contract, case_id="case-" + str(index), account=ACCOUNT_EXCEEDED)
        assert result["exceeded_term"] == quotes[index]
        index += 1


def test_the_exceeded_term_must_be_quoted_from_the_agreed_terms_not_the_use(direct_vm, direct_deploy,
                                                                            direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert QUOTE_FROM_ACCOUNT in ACCOUNT_EXCEEDED and QUOTE_FROM_ACCOUNT not in TERMS
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", QUOTE_FROM_ACCOUNT))
    with refused(ERR_LLM_TERM):
        review(contract, account=ACCOUNT_EXCEEDED)
    assert contract.get_review_count() == 0


def test_exceeded_term_quote_is_matched_up_to_whitespace(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    terms = HEAD + "\nBooking date: 2026-03-02\nTerritory:\n  United Kingdom\tand\n Ireland only"
    item = "Territory: United Kingdom and Ireland only"
    assert item not in terms
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", "  Territory: United Kingdom \n and  Ireland only ",
                                             "  Used in France.\n "))
    assert review(contract, terms=terms, account=ACCOUNT_EXCEEDED)["exceeded_term"] == item
    assert stored(contract)["exceeded_term"] == item
    assert stored(contract)["reason"] == "Used in France."


def test_within_buyout_stores_no_exceeded_term(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for index, term in enumerate([TERM_CHANNELS, "none", "a billboard in Times Square", None, 5]):
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", json.dumps({"verdict": "WITHIN_BUYOUT", "exceeded_term": term,
                                                      "reason": "Inside the buyout."}))
        result = review(contract, case_id="case-" + str(index))
        assert result["verdict"] == "WITHIN_BUYOUT"
        assert result["exceeded_term"] == ""
        assert stored(contract, "case-" + str(index))["exceeded_term"] == ""
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", json.dumps({"verdict": "WITHIN_BUYOUT", "reason": "No key at all."}))
    assert review(contract, case_id="case-x")["exceeded_term"] == ""


def test_verdict_word_spelling_is_normalised(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    spellings = [(" buyout exceeded ", "BUYOUT_EXCEEDED"), ("Buyout-Exceeded", "BUYOUT_EXCEEDED"),
                 ("within_buyout", "WITHIN_BUYOUT"), ("Within Buyout", "WITHIN_BUYOUT")]
    index = 0
    while index < len(spellings):
        word, expected = spellings[index]
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer(word, TERM_CHANNELS))
        result = review(contract, case_id="case-" + str(index), account=ACCOUNT_EXCEEDED)
        assert result["verdict"] == expected
        index += 1


def test_prompt_carries_the_public_inputs_and_dates_and_no_hash_or_case_id(direct_vm, direct_deploy,
                                                                          direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    # The only mock needs the decision rules, the agreed terms, both dates, the campaign use and the
    # role, and the absence of the evidence hash, the terms hash and the case id (canonical JSON:
    # sorted keys).
    rules = [
        "when the buyout lists channels, the use is limited to the channels listed.",
        "Territory: the countries or regions the buyout covers.",
        "Term: the period the buyout runs for, counted as the buyout says",
        "Answer BUYOUT_EXCEEDED when the campaign use goes beyond a channel, territory or term that the "
        "buyout in agreed_terms states: a channel the buyout does not include, a territory outside the "
        "buyout's territory, or use after the buyout's term has ended.",
        "Otherwise answer WITHIN_BUYOUT: every channel, territory and date of the use is inside what the "
        "buyout states.",
        "A limit the buyout does not state cannot be exceeded, and a fact campaign_use does not show is "
        "not a breach by itself.",
        "for BUYOUT_EXCEEDED the buyout term the use exceeds, copied character for character from "
        "agreed_terms",
        "for WITHIN_BUYOUT an empty string",
    ]
    direct_vm.mock_llm(r"(?s)^(?!.*" + HASH_WITHIN + r")(?!.*" + sha(TERMS) + r")(?!.*" + CASE + r")"
                       r".*" + r".*".join(re.escape(rule) for rule in rules) + r".*INPUT_JSON"
                       r".*\"agreed_terms\":\"Commercial buyout.*Booking date: 2026-03-02.*Term: 12 months"
                       r".*\"booking_date\":\"2026-03-02\""
                       r".*\"campaign_use\":\"Campaign use: spring skincare.*First use: 2026-03-16"
                       r".*\"first_use_date\":\"2026-03-16\""
                       r".*\"role\":\"model_commercial\"",
                       answer("WITHIN_BUYOUT"))
    assert review(contract)["verdict"] == "WITHIN_BUYOUT"


# --- must refuse: the row's own (a use dated before the booking) ---------------------------

def test_refuses_a_use_dated_before_the_booking(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    before = [
        account_with_use("First use: 2026-03-01"),                       # one day before
        account_with_use("Use date: 2026-02-28"),                        # across a month end
        account_with_use("Use dates: 2025-12-31 to 2026-06-30"),         # across a year end
        account_with_use("Use date: 2026-03-20", "First use: 2026-03-01"),   # the earliest line counts
        account_with_use("First use: 2026-03-20", "Use dates: 2026-01-15 to 2026-02-15"),
        account_with_use("Use date: 1999-03-02"),
    ]
    for account in before:
        with refused(ERR_USE_BEFORE):
            review(contract, account=account)
    # Booking at a year start, use on the last day of the year before.
    with refused(ERR_USE_BEFORE):
        review(contract, terms=terms_with_booking("Booking date: 2027-01-01"),
               account=account_with_use("First use: 2026-12-31"))
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False


def test_a_use_on_or_after_the_booking_date_is_allowed(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    cases = [
        (account_with_use("First use: 2026-03-02"), "2026-03-02"),       # the same day
        (account_with_use("First use: 2026-03-03"), "2026-03-03"),       # one day after
        (account_with_use("Use dates: 2026-03-02 to 2026-03-01"), "2026-03-02"),  # only the first date is read
        (account_with_use("Use date: 2026-05-01", "First use: 2026-04-01", "Use dates: 2026-06-01 to 2026-07-01"),
         "2026-04-01"),                                                  # the earliest line is the use date
        (account_with_use("First use: 2027-01-01"), "2027-01-01"),
    ]
    index = 0
    while index < len(cases):
        account, first_use = cases[index]
        result = review(contract, case_id="case-" + str(index), account=account)
        assert result["booking_date"] == "2026-03-02"
        assert result["first_use_date"] == first_use
        assert stored(contract, "case-" + str(index))["first_use_date"] == first_use
        index += 1
    result = review(contract, case_id="case-year", terms=terms_with_booking("Booking date: 2026-12-31"),
                    account=account_with_use("First use: 2026-12-31"))
    assert result["booking_date"] == "2026-12-31" and result["first_use_date"] == "2026-12-31"


def test_refuses_malformed_dates(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    bad_values = [
        "", "   ", "2026-3-2", "26-03-02", "2026/03/02", "02-03-2026", "2 March 2026", "March 2, 2026",
        "2026-13-01", "2026-00-10", "2026-03-00", "2026-03-32", "2026-04-31", "2026-02-29", "2100-02-29",
        "0000-01-01", "2026-03-021", "2026-03-02T10:00", "2026-03-02x", "２０２６-03-02", "2026-0a-02",
        "TBC", "to be agreed", "-2026-03-02",
    ]
    for value in bad_values:
        with refused(ERR_BAD_DATE):
            review(contract, terms=terms_with_booking("Booking date: " + value))
        with refused(ERR_BAD_DATE):
            review(contract, account=account_with_use("First use: " + value))
    # One bad use-date line among good ones is refused too.
    with refused(ERR_BAD_DATE):
        review(contract, account=account_with_use("First use: 2026-03-16", "Use date: 2026-02-30"))
    assert contract.get_review_count() == 0


def test_real_calendar_dates_and_layouts_are_read(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    cases = [
        ("Booking date: 2028-02-29", "First use: 2028-02-29", "2028-02-29", "2028-02-29"),   # leap year
        ("Booking date: 2000-02-29", "First use: 2000-03-01", "2000-02-29", "2000-03-01"),   # 400-year leap
        ("Booking date: 0999-01-01", "First use: 0999-12-31", "0999-01-01", "0999-12-31"),   # padded output
        ("booking date: 2026-03-02", "first use: 2026-03-02", "2026-03-02", "2026-03-02"),   # any case
        ("BOOKING DATE:2026-03-02", "USE DATE:2026-03-04", "2026-03-02", "2026-03-04"),
        ("- Booking date: 2026-03-02", "* Use date: 2026-03-05", "2026-03-02", "2026-03-05"),  # list marks
        ("1. Booking date: 2026-03-02", "2) First use date: 2026-03-06", "2026-03-02", "2026-03-06"),
        ("**Booking date:** 2026-03-02", "**First use**: **2026-03-07**", "2026-03-02", "2026-03-07"),  # bold
        ("Booking date: 2026-03-02 10:00 UTC", "Use date: 2026-03-08 (Instagram post)", "2026-03-02",
         "2026-03-08"),                                                  # a time or note after a space
        ("Booking date:\t2026-03-02.", "Use dates: 2026-03-09, 2026-03-10", "2026-03-02", "2026-03-09"),
    ]
    index = 0
    while index < len(cases):
        booking_line, use_line, booking, first_use = cases[index]
        result = review(contract, case_id="case-" + str(index), terms=terms_with_booking(booking_line),
                        account=account_with_use(use_line))
        assert (result["booking_date"], result["first_use_date"]) == (booking, first_use)
        index += 1
    crlf_terms = terms_with_booking("Booking date: 2026-03-02").replace("\n", "\r\n")
    crlf_account = account_with_use("First use: 2026-03-02").replace("\n", "\r\n")
    assert review(contract, case_id="case-crlf", terms=crlf_terms, account=crlf_account)["first_use_date"] == "2026-03-02"
    cr_terms = terms_with_booking("Booking date: 2026-03-02").replace("\n", "\r")
    cr_account = account_with_use("First use: 2026-03-02").replace("\n", "\r")
    assert review(contract, case_id="case-cr", terms=cr_terms, account=cr_account)["booking_date"] == "2026-03-02"


def test_refuses_terms_without_exactly_one_booking_date(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    bad_terms = [
        HEAD,
        HEAD + "\n" + TERM_CHANNELS,
        HEAD + "\nBooked on 2026-03-02",
        HEAD + "\nBooking date 2026-03-02",
        HEAD + "\nBooking dates: 2026-03-02",
        HEAD + "\nDate of booking: 2026-03-02",
        HEAD + "\nNotes: booking date: 2026-03-02",
        HEAD + "\nRebooking date: 2026-03-02",
        HEAD + "\nConfirmation: booking date 2026-03-02",   # the label must start the line
        HEAD + "\nUse date: 2026-03-02",
        HEAD + "\nBooking date: 2026-03-02\nBooking date: 2026-03-02",
        HEAD + "\nBooking date: 2026-03-02\nbooking date: 2026-04-02",
    ]
    for terms in bad_terms:
        with refused(ERR_NO_BOOKING_DATE):
            review(contract, terms=terms)
    # A booking date in the account does not count.
    account = account_with_use("Booking date: 2026-03-02", "First use: 2026-03-16")
    with refused(ERR_NO_BOOKING_DATE):
        review(contract, terms=HEAD, account=account)
    assert contract.get_review_count() == 0


def test_refuses_an_account_without_a_use_date(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    bad_accounts = [
        "Campaign use: spring skincare campaign\nTerritory: UK",
        account_with_use("Ran from 2026-03-16 on Instagram"),
        account_with_use("Use date 2026-03-16"),
        account_with_use("Usage date: 2026-03-16"),
        account_with_use("Date of use: 2026-03-16"),
        account_with_use("Notes: first use: 2026-03-16"),
        account_with_use("Reuse date: 2026-03-16"),
        account_with_use("Comments: use date 2026-03-16"),      # the label must start the line
        account_with_use("Booking date: 2026-03-16"),
    ]
    for account in bad_accounts:
        with refused(ERR_NO_USE_DATE):
            review(contract, account=account)
    # A use date in the terms does not count.
    with refused(ERR_NO_USE_DATE):
        review(contract, terms=TERMS + "\nFirst use: 2026-03-16", account=bad_accounts[0])
    assert contract.get_review_count() == 0


def test_the_date_checks_come_after_the_shared_input_checks(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    no_use_date = "Campaign use: spring skincare campaign\nTerritory: UK"
    # The hash is checked before the account's dates are read.
    with refused(ERR_HASH):
        contract.review_campaign_use(CASE, TERMS, no_use_date, HASH_WITHIN)
    with refused(ERR_HASH):
        contract.review_campaign_use(CASE, TERMS, account_with_use("First use: 2026-03-01"), HASH_WITHIN)
    # The booking date is read before the account is looked at.
    with refused(ERR_NO_BOOKING_DATE):
        contract.review_campaign_use(CASE, HEAD, "", "")
    with refused(ERR_BAD_DATE):
        contract.review_campaign_use(CASE, terms_with_booking("Booking date: soon"), "", "")
    assert contract.get_review_count() == 0


# --- must refuse: shared by every role contract -----------------------------------------------

def test_refuses_empty_terms(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for terms in ["", " ", "   ", "\n\t \r\n"]:
        with refused(ERR_EMPTY_TERMS):
            review(contract, terms=terms)
    # Empty terms are refused before the date rule and before the evidence is looked at.
    with refused(ERR_EMPTY_TERMS):
        contract.review_campaign_use(CASE, "", ACCOUNT_WITHIN, "not-a-hash")
    with refused(ERR_EMPTY_TERMS):
        contract.review_campaign_use(CASE, None, "", "")
    assert contract.get_review_count() == 0


def test_refuses_terms_over_the_limit(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    first = "Booking date: 2026-03-02\n"
    long_terms = first + "x" * (8000 - len(first))
    assert len(long_terms) == 8000
    assert review(contract, terms=long_terms)["verdict"] == "WITHIN_BUYOUT"
    with refused(ERR_TERMS_TOO_LONG):
        review(contract, case_id="case-2", terms=long_terms + "x")
    assert contract.get_review_count() == 1


def test_refuses_an_empty_or_overlong_account_of_what_happened(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    for account in ["", "   ", "\n\t"]:
        with refused(ERR_EMPTY_WHAT):
            contract.review_campaign_use(CASE, TERMS, account, sha(account))
    with refused(ERR_EMPTY_WHAT):
        contract.review_campaign_use(CASE, TERMS, None, "")
    first = "First use: 2026-03-16\n"
    long_account = first + "x" * (8001 - len(first))
    with refused(ERR_WHAT_TOO_LONG):
        contract.review_campaign_use(CASE, TERMS, long_account, sha(long_account))
    assert contract.get_review_count() == 0
    assert review(contract, account=long_account[:8000])["verdict"] == "WITHIN_BUYOUT"


def test_refuses_an_evidence_hash_that_does_not_match(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    wrong = [
        HASH_EXCEEDED,                               # the hash of another account
        sha(TERMS),                                  # the hash of the terms
        sha(ACCOUNT_WITHIN + " "),                   # one trailing space: the text is hashed exactly as given
        sha(ACCOUNT_WITHIN.replace("2026-03-16", "2026-03-17")),
        "0" * 64,
        HASH_WITHIN[:63], HASH_WITHIN + "0", "g" * 64, "not-a-hash", "", "   ",
        "0x" + HASH_WITHIN,
        None, 1601,
    ]
    for evidence in wrong:
        with refused(ERR_HASH):
            contract.review_campaign_use(CASE, TERMS, ACCOUNT_WITHIN, evidence)
    # The text edited after hashing (here: its use date) does not match either.
    with refused(ERR_HASH):
        contract.review_campaign_use(CASE, TERMS, ACCOUNT_WITHIN.replace("2026-03-16", "2026-03-17"), HASH_WITHIN)
    assert contract.get_review_count() == 0
    assert contract.has_review(CASE) is False

    # The account is hashed as supplied: with a trailing newline, the hash of the trimmed text is refused.
    padded = ACCOUNT_WITHIN + "\n"
    with refused(ERR_HASH):
        contract.review_campaign_use(CASE, TERMS, padded, HASH_WITHIN)
    assert contract.get_review_count() == 0

    # The exact hash is accepted; upper-case hex and surrounding spaces are read as the same hash.
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    contract.review_campaign_use(CASE, TERMS, ACCOUNT_WITHIN, "  " + HASH_WITHIN.upper() + " ")
    assert stored(contract)["evidence_sha256"] == HASH_WITHIN
    contract.review_campaign_use("case-padded", TERMS, padded, sha(padded))
    assert stored(contract, "case-padded")["evidence_sha256"] == sha(padded)
    assert stored(contract, "case-padded")["what_happened"] == padded


def test_refuses_the_same_case_twice(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_CHANNELS, "First verdict."))
    review(contract, account=ACCOUNT_EXCEEDED)
    first = contract.get_review(CASE)

    # The same inputs, the same id in other case, and the same id with other terms or evidence.
    other_terms = TERMS.replace("12 months", "24 months")
    attempts = [
        dict(account=ACCOUNT_EXCEEDED),
        dict(case_id="CASE-BUYOUT-1601", account=ACCOUNT_EXCEEDED),
        dict(account=ACCOUNT_WITHIN),
        dict(terms=other_terms, account=ACCOUNT_EXCEEDED),
    ]
    for attempt in attempts:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", "", "Second verdict."))
        with refused(ERR_SAME_CASE):
            review(contract, **attempt)
    assert contract.get_review(CASE) == first
    assert stored(contract)["verdict"] == "BUYOUT_EXCEEDED"
    assert contract.get_review_count() == 1

    # A different case id is a different case, even with identical text.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", "", "Other case."))
    assert review(contract, case_id="case-buyout-1602", account=ACCOUNT_EXCEEDED)["verdict"] == "WITHIN_BUYOUT"
    assert contract.get_review_count() == 2
    assert contract.get_review_id(1) == "case-buyout-1602"


def test_a_refused_review_does_not_lock_the_case(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    with refused(ERR_LLM_FORMAT):
        review(contract)
    with refused(ERR_USE_BEFORE):
        review(contract, account=account_with_use("First use: 2026-03-01"))
    with refused(ERR_NO_BOOKING_DATE):
        review(contract, terms=HEAD)
    with refused(ERR_HASH):
        review(contract, evidence=HASH_EXCEEDED)
    assert contract.has_review(CASE) is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    assert review(contract)["verdict"] == "WITHIN_BUYOUT"


def test_only_the_owner_requests_reviews(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_owner().lower() == address_hex(direct_owner).lower()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    with direct_vm.prank(direct_alice):
        with refused(ERR_OWNER_ONLY):
            review(contract)
    assert contract.get_review_count() == 0
    assert review(contract)["verdict"] == "WITHIN_BUYOUT"


def test_refuses_bad_case_ids(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    for case_id in ["", " ", "case 1", "case/1", "case\n1", "x" * 65, "café", "case:1", 1601, None]:
        with refused(ERR_BAD_CASE_ID):
            review(contract, case_id=case_id)
        with refused(ERR_BAD_CASE_ID):
            contract.has_review(case_id)
    assert contract.get_review_count() == 0
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    review(contract, case_id="X" * 64)
    assert contract.get_review_id(0) == "x" * 64


def test_reads(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    assert contract.get_role() == "model_commercial"
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
        (json.dumps({"exceeded_term": TERM_CHANNELS, "reason": "x"}), ERR_LLM_VERDICT),
        (answer("YES"), ERR_LLM_VERDICT),
        (answer("EXCEEDED", TERM_CHANNELS), ERR_LLM_VERDICT),
        (answer("WITHIN", ""), ERR_LLM_VERDICT),
        (answer("NOT_WITHIN_BUYOUT", TERM_CHANNELS), ERR_LLM_VERDICT),
        (answer("USE_BEFORE_BOOKING", TERM_CHANNELS), ERR_LLM_VERDICT),
        (json.dumps({"verdict": 1, "exceeded_term": TERM_CHANNELS, "reason": "x"}), ERR_LLM_VERDICT),
        (answer("BUYOUT_EXCEEDED", ""), ERR_LLM_TERM),
        (answer("BUYOUT_EXCEEDED", "Channels: print only"), ERR_LLM_TERM),
        (answer("BUYOUT_EXCEEDED", "Ch"), ERR_LLM_TERM),
        (answer("BUYOUT_EXCEEDED", QUOTE_FROM_ACCOUNT), ERR_LLM_TERM),
        (answer("BUYOUT_EXCEEDED", TERMS + " " + ACCOUNT_EXCEEDED), ERR_LLM_TERM),
        (json.dumps({"verdict": "BUYOUT_EXCEEDED", "reason": "x"}), ERR_LLM_TERM),
        (json.dumps({"verdict": "BUYOUT_EXCEEDED", "exceeded_term": [TERM_CHANNELS], "reason": "x"}),
         ERR_LLM_TERM),
        (answer("BUYOUT_EXCEEDED", TERM_CHANNELS, "   "), ERR_LLM_REASON),
        (json.dumps({"verdict": "BUYOUT_EXCEEDED", "exceeded_term": TERM_CHANNELS}), ERR_LLM_REASON),
        (json.dumps({"verdict": "WITHIN_BUYOUT", "exceeded_term": "", "reason": 5}), ERR_LLM_REASON),
        (json.dumps({"verdict": "WITHIN_BUYOUT", "exceeded_term": ""}), ERR_LLM_REASON),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"INPUT_JSON", response)
        with refused(expected):
            review(contract, account=ACCOUNT_EXCEEDED)
    assert contract.get_review_count() == 0


def test_model_json_wrapped_in_text_is_read(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", "Here you go: " + answer("BUYOUT_EXCEEDED", TERM_CHANNELS) + " done")
    assert review(contract, account=ACCOUNT_EXCEEDED)["verdict"] == "BUYOUT_EXCEEDED"


def test_refuses_a_term_over_the_limit_and_truncates_the_reason(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    terms = TERMS + "\nChannels detail: " + "social posts on every listed platform in every listed market. " * 8
    quote = terms[terms.index("Channels detail:"):]
    assert len(_squash(quote)) > 400
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", quote))
    with refused(ERR_LLM_TERM):
        review(contract, terms=terms, account=ACCOUNT_EXCEEDED)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", _squash(quote)[:400].rstrip(), "r" * 500))
    result = review(contract, terms=terms, account=ACCOUNT_EXCEEDED)
    assert result["verdict"] == "BUYOUT_EXCEEDED"
    assert len(stored(contract)["exceeded_term"]) <= 400
    assert result["reason"] == "r" * 400
    assert stored(contract)["reason"] == "r" * 400


# --- consensus ---------------------------------------------------------------------------

def test_validator_agrees_on_the_verdict_word_not_the_wording(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_CHANNELS, "Leader wording."))
    review(contract, account=ACCOUNT_EXCEEDED)

    # Same verdict word, another quoted term and reason: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_TERRITORY, "Other words."))
    assert direct_vm.run_validator() is True

    # Different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", "", "Looks inside the buyout."))
    assert direct_vm.run_validator() is False

    # A leader result that is malformed or forged: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_CHANNELS))
    forged = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": "Channels: print only", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    from_account = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": QUOTE_FROM_ACCOUNT, "reason": "x"}
    assert direct_vm.run_validator(leader_result=from_account) is False
    short = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": "Ch", "reason": "x"}
    assert direct_vm.run_validator(leader_result=short) is False
    no_term = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": "", "reason": "x"}
    assert direct_vm.run_validator(leader_result=no_term) is False
    missing_key = {"verdict": "BUYOUT_EXCEEDED", "reason": "x"}
    assert direct_vm.run_validator(leader_result=missing_key) is False
    bad_word = {"verdict": "EXCEEDED", "exceeded_term": TERM_CHANNELS, "reason": "x"}
    assert direct_vm.run_validator(leader_result=bad_word) is False
    lower_word = {"verdict": "buyout_exceeded", "exceeded_term": TERM_CHANNELS, "reason": "x"}
    assert direct_vm.run_validator(leader_result=lower_word) is False
    no_reason = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": TERM_CHANNELS}
    assert direct_vm.run_validator(leader_result=no_reason) is False
    blank_reason = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": TERM_CHANNELS, "reason": " "}
    assert direct_vm.run_validator(leader_result=blank_reason) is False
    assert direct_vm.run_validator(leader_result="BUYOUT_EXCEEDED") is False
    good = {"verdict": "BUYOUT_EXCEEDED", "exceeded_term": TERM_PERIOD, "reason": "x"}
    assert direct_vm.run_validator(leader_result=good) is True

    # The validator's own model answer is malformed: disagree. A leader error is never accepted.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", "no json")
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_CHANNELS))
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_within_buyout(direct_vm, direct_deploy, direct_owner):
    contract = setup(direct_vm, direct_deploy, direct_owner)
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", "", "Leader: inside the buyout."))
    review(contract)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT", TERM_CHANNELS, "Validator wording."))
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("BUYOUT_EXCEEDED", TERM_TERRITORY, "Reads as outside the territory."))
    assert direct_vm.run_validator() is False

    # WITHIN_BUYOUT must carry an empty exceeded term and a reason.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"INPUT_JSON", answer("WITHIN_BUYOUT"))
    assert direct_vm.run_validator(
        leader_result={"verdict": "WITHIN_BUYOUT", "exceeded_term": TERM_CHANNELS, "reason": "x"}) is False
    assert direct_vm.run_validator(leader_result={"verdict": "WITHIN_BUYOUT", "reason": "x"}) is False
    assert direct_vm.run_validator(
        leader_result={"verdict": "WITHIN_BUYOUT", "exceeded_term": "", "reason": ""}) is False
    assert direct_vm.run_validator(
        leader_result={"verdict": "WITHIN_BUYOUT", "exceeded_term": "", "reason": "x"}) is True
