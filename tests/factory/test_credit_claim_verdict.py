"""Direct-mode tests for contracts/factory/credit_claim_verdict.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (web-oracle), then written to the
backlog item. The web page and the LLM are mocked, so these tests check the contract's
own logic (input checks, refusals, HTML reduction, the handle gate, parsing, storage,
the validator's comparison), not a model's judgment, a live page or GenVM consensus.

Run from the repository root:
    pip install genlayer-test pytest
    pytest tests/factory/test_credit_claim_verdict.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "credit_claim_verdict.py")

MEDIA = hashlib.sha256(b"harbour-sunrise.jpg bytes").hexdigest()
OTHER_MEDIA = hashlib.sha256(b"city-night.jpg bytes").hexdigest()
HANDLE = "@alice_shoots"
POST_URL = "https://social.example/@harbourbakery/posts/1180"
OTHER_URL = "https://portfolio.example/alice/harbour-sunrise"

PAGE_CREDIT = (
    "<html><head><title>Harbour Bakery</title>"
    "<meta property=\"og:description\" content=\"Sunrise over the harbour this morning.\">"
    "<script>var feed = {\"author\": \"someone\"};</script></head>"
    "<body><article><p>Sunrise over the harbour this morning.</p>"
    "<p>Photo by <a href=\"/@alice_shoots\">&#64;alice_shoots</a> &amp; edited in-house.</p>"
    "</article></body></html>"
)
PAGE_MENTION = (
    "<html><body><p>Lovely light today. What do you think, @alice_shoots?</p>"
    "<p>Photo: our own team.</p></body></html>"
)
PAGE_NO_HANDLE = "<html><body><p>Sunrise over the harbour. Photo by our own team.</p></body></html>"
PAGE_SCRIPT_ONLY = (
    "<html><head><script>window.mentions = [\"@alice_shoots\"];</script></head>"
    "<body><p>Sunrise over the harbour.</p></body></html>"
)

CREDIT_QUOTE = "Photo by @alice_shoots"


def creator_hex(address):
    """0x hex of a test address (the direct-mode fixtures may hand back raw bytes)."""
    if isinstance(address, (bytes, bytearray)):
        return "0x" + bytes(address).hex()
    return address.as_hex


def answer(names_handle, quote="", reason="One sentence."):
    return json.dumps({"names_handle": names_handle, "quote": quote, "reason": reason})


def page(body, status=200):
    return {"status": status, "body": body}


def deploy(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    return contract


def open_claim(contract, creator, media=MEDIA, handle=HANDLE, url=POST_URL):
    return contract.open_claim(media, handle, creator_hex(creator), url)["claim_id"]


def confirm(direct_vm, contract, creator, claim_id):
    with direct_vm.prank(creator):
        return contract.confirm_claim(claim_id)


def claim(contract, claim_id):
    return json.loads(contract.get_claim(claim_id))


def verified_claim(direct_vm, contract, creator, media=MEDIA, handle=HANDLE, url=POST_URL):
    claim_id = open_claim(contract, creator, media, handle, url)
    confirm(direct_vm, contract, creator, claim_id)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_web(r"https://portfolio\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE))
    result = contract.decide_claim(claim_id)
    assert result["verdict"] == "VERIFIED"
    direct_vm.clear_mocks()
    return claim_id


# --- decision outcomes ---------------------------------------------------------------

def test_verified_when_confirmed_and_the_post_names_the_handle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    assert claim(contract, claim_id)["status"] == "OPEN"
    confirm(direct_vm, contract, direct_bob, claim_id)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE, "The post credits the photo to the handle."))

    result = contract.decide_claim(claim_id)

    assert result == {"claim_id": claim_id, "verdict": "VERIFIED", "missing": [],
                      "quote": CREDIT_QUOTE, "reason": "The post credits the photo to the handle."}
    stored = claim(contract, claim_id)
    assert stored["status"] == "VERIFIED"
    assert stored["creator"] == creator_hex(direct_bob).lower()
    assert stored["credited_handle"] == "alice_shoots"
    assert stored["creator_confirmed"] is True
    assert stored["decision_count"] == 1
    assert json.loads(contract.get_verified_claim(MEDIA))["claim_id"] == claim_id


def test_not_verified_until_the_creator_confirms(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE))

    first = contract.decide_claim(claim_id)

    assert first["verdict"] == "NOT_VERIFIED"
    assert first["missing"] == ["CREATOR_NOT_CONFIRMED"]
    with direct_vm.expect_revert("MEDIA_NOT_VERIFIED"):
        contract.get_verified_claim(MEDIA)

    # A NOT_VERIFIED claim can be decided again once the missing condition is met.
    confirm(direct_vm, contract, direct_bob, claim_id)
    second = contract.decide_claim(claim_id)
    assert second["verdict"] == "VERIFIED"
    assert claim(contract, claim_id)["decision_count"] == 2


def test_not_verified_when_the_post_does_not_contain_the_handle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_id)
    # No LLM mock: the handle gate decides before any model call (an unmocked call would fail).
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_NO_HANDLE))

    result = contract.decide_claim(claim_id)

    assert result["verdict"] == "NOT_VERIFIED"
    assert result["missing"] == ["POST_DOES_NOT_NAME_HANDLE"]
    assert result["quote"] == ""


def test_not_verified_when_the_post_only_mentions_the_handle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_id)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_MENTION))
    direct_vm.mock_llm(r"alice_shoots", answer(False, "", "The handle is asked a question, not credited."))

    result = contract.decide_claim(claim_id)

    assert result["verdict"] == "NOT_VERIFIED"
    assert result["missing"] == ["POST_DOES_NOT_NAME_HANDLE"]
    assert result["reason"] == "The handle is asked a question, not credited."


def test_not_verified_lists_every_missing_condition(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    direct_vm.mock_web(r"https://social\.example/.*", page("gone", status=404))

    result = contract.decide_claim(claim_id)

    assert result["verdict"] == "NOT_VERIFIED"
    assert result["missing"] == ["CREATOR_NOT_CONFIRMED", "POST_UNAVAILABLE"]
    assert "HTTP 404" in result["reason"]


def test_server_error_refuses_and_writes_nothing(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    direct_vm.mock_web(r"https://social\.example/.*", page("busy", status=503))

    with direct_vm.expect_revert("[TRANSIENT] POST_FETCH_FAILED"):
        contract.decide_claim(claim_id)
    stored = claim(contract, claim_id)
    assert stored["status"] == "OPEN"
    assert stored["decision_count"] == 0


# --- must refuse ---------------------------------------------------------------------

def test_refuses_a_confirmation_from_another_address(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)

    # The claimant who opened it is not the creator.
    with direct_vm.expect_revert("[EXPECTED] NOT_THE_CREATOR: only the creator address named in the claim can confirm it"):
        contract.confirm_claim(claim_id)
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("NOT_THE_CREATOR"):
            contract.confirm_claim(claim_id)
    assert claim(contract, claim_id)["creator_confirmed"] is False

    assert confirm(direct_vm, contract, direct_bob, claim_id) == {"claim_id": claim_id, "creator_confirmed": True}
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("ALREADY_CONFIRMED"):
            contract.confirm_claim(claim_id)


def test_refuses_a_claim_on_media_already_verified_for_someone_else(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    # A rival claim opened before the first one is verified.
    rival_id = open_claim(contract, direct_charlie, handle="@charlie_lens")
    verified_claim(direct_vm, contract, direct_bob)

    taken = "[EXPECTED] MEDIA_ALREADY_VERIFIED: this media hash is already verified for someone else"
    with direct_vm.expect_revert(taken):
        open_claim(contract, direct_charlie, handle="@charlie_lens", url=OTHER_URL)
    with direct_vm.expect_revert("MEDIA_ALREADY_VERIFIED"):
        open_claim(contract, direct_bob, handle="@someone_else")
    with direct_vm.expect_revert("MEDIA_ALREADY_VERIFIED"):
        open_claim(contract, direct_charlie, handle=HANDLE)
    # The rival claim can no longer be confirmed or decided.
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("MEDIA_ALREADY_VERIFIED"):
            contract.confirm_claim(rival_id)
    with direct_vm.expect_revert("MEDIA_ALREADY_VERIFIED"):
        contract.decide_claim(rival_id)
    # The same creator and handle again is refused too, with its own reason.
    with direct_vm.expect_revert("ALREADY_VERIFIED: this media hash is already verified for this creator and handle"):
        open_claim(contract, direct_bob, url=OTHER_URL)
    # Other media is unaffected.
    open_claim(contract, direct_charlie, media=OTHER_MEDIA, handle="@charlie_lens")
    assert contract.get_claim_count() == 2 + 1


def test_refuses_a_second_decision_on_a_verified_claim(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = verified_claim(direct_vm, contract, direct_bob)

    with direct_vm.expect_revert("[EXPECTED] ALREADY_VERIFIED: this claim is already verified"):
        contract.decide_claim(claim_id)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("ALREADY_VERIFIED"):
            contract.confirm_claim(claim_id)
    assert claim(contract, claim_id)["decision_count"] == 1


# --- consensus -----------------------------------------------------------------------

def test_validator_agrees_on_the_answers_not_the_wording(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_id)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE))
    contract.decide_claim(claim_id)

    # Same answer, different quote and reason: the validator agrees.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, "by @alice_shoots &", "Other words."))
    assert direct_vm.run_validator() is True

    # The validator's model says the post does not credit the handle: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(False))
    assert direct_vm.run_validator() is False

    # The validator finds the post gone: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page("gone", status=404))
    assert direct_vm.run_validator() is False

    # A leader quote that is not on the validator's copy of the page, or does not name the handle.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE))
    forged = {"post_available": True, "names_handle": True, "quote": "Shot by @alice_shoots", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    unnamed = {"post_available": True, "names_handle": True, "quote": "Sunrise over the harbour", "reason": "x"}
    assert direct_vm.run_validator(leader_result=unnamed) is False
    malformed = {"post_available": True, "names_handle": "yes", "quote": CREDIT_QUOTE, "reason": "x"}
    assert direct_vm.run_validator(leader_result=malformed) is False

    # A leader error is never accepted.
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_a_post_without_the_handle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_NO_HANDLE))
    contract.decide_claim(claim_id)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_NO_HANDLE))
    assert direct_vm.run_validator() is True

    # The validator's copy now credits the handle: the answers differ.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer(True, CREDIT_QUOTE))
    assert direct_vm.run_validator() is False


# --- reading the post ----------------------------------------------------------------

def test_reads_entities_and_meta_content_but_not_scripts(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    meta_page = (
        "<html><head><meta property=\"og:description\" "
        "content=\"Harbour sunrise &#8212; photo by @Alice_Shoots\"></head><body></body></html>"
    )
    claim_meta = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_meta)
    direct_vm.mock_web(r"https://social\.example/.*", page(meta_page))
    direct_vm.mock_llm(r"alice_shoots", answer(True, "photo by @Alice_Shoots"))
    result = contract.decide_claim(claim_meta)
    assert result["verdict"] == "VERIFIED"
    assert result["quote"] == "photo by @Alice_Shoots"

    # A handle only inside a <script> is not post text: no model call, not named.
    direct_vm.clear_mocks()
    claim_script = open_claim(contract, direct_bob, media=OTHER_MEDIA)
    confirm(direct_vm, contract, direct_bob, claim_script)
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_SCRIPT_ONLY))
    assert contract.decide_claim(claim_script)["missing"] == ["POST_DOES_NOT_NAME_HANDLE"]


def test_the_handle_must_appear_as_a_whole_handle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_id)
    longer = "<p>Photo by @alice_shoots2 and @alice_shoots_fan and @alice_shoots.studio</p>"
    direct_vm.mock_web(r"https://social\.example/.*", page(longer))
    assert contract.decide_claim(claim_id)["missing"] == ["POST_DOES_NOT_NAME_HANDLE"]

    # Sentence punctuation after the handle still counts as the handle.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page("<p>Photo by @alice_shoots.</p>"))
    direct_vm.mock_llm(r"alice_shoots", answer(True, "Photo by @alice_shoots."))
    assert contract.decide_claim(claim_id)["verdict"] == "VERIFIED"


# --- other refusals ------------------------------------------------------------------

def test_refuses_malformed_inputs(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    bob = creator_hex(direct_bob)

    for bad_hash in ["", "not-a-hash", "g" * 64, MEDIA[:63]]:
        with direct_vm.expect_revert("BAD_MEDIA_HASH"):
            contract.open_claim(bad_hash, HANDLE, bob, POST_URL)
    for bad_handle in ["", "@", "@@alice", "alice shoots", "a" * 65, "...", "al!ce", "Kate"]:
        with direct_vm.expect_revert("BAD_HANDLE"):
            contract.open_claim(MEDIA, bad_handle, bob, POST_URL)
    for bad_creator in ["", bob[2:], "0x1234", "0x" + "z" * 40, bob + "00"]:
        with direct_vm.expect_revert("BAD_CREATOR_ADDRESS"):
            contract.open_claim(MEDIA, HANDLE, bad_creator, POST_URL)
    for bad_url in ["", "http://social.example/p/1", "https://", "https://social.example/a b",
                    "https://social.example/\"x\"", "https://x.example/" + "a" * 500]:
        with direct_vm.expect_revert("BAD_POST_URL"):
            contract.open_claim(MEDIA, HANDLE, bob, bad_url)
    assert contract.get_claim_count() == 0

    claim_id = open_claim(contract, direct_bob)
    with direct_vm.expect_revert("[EXPECTED] DUPLICATE_CLAIM: this claim is already open"):
        contract.open_claim(MEDIA.upper(), "@Alice_Shoots", bob.upper().replace("0X", "0x"), POST_URL)
    with direct_vm.expect_revert("UNKNOWN_CLAIM"):
        contract.decide_claim(OTHER_MEDIA)
    with direct_vm.expect_revert("BAD_CLAIM_ID"):
        contract.decide_claim("claim-1")
    with direct_vm.expect_revert("UNKNOWN_CLAIM"):
        contract.get_claim(OTHER_MEDIA)
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_claim_id(1)
    assert contract.get_claim_id(0) == claim_id
    assert contract.get_claim_count() == 1


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    claim_id = open_claim(contract, direct_bob)
    confirm(direct_vm, contract, direct_bob, claim_id)
    cases = [
        ("no json at all", "[LLM_ERROR] the model did not return a JSON object"),
        (json.dumps({"quote": CREDIT_QUOTE, "reason": "x"}), "no true/false names_handle"),
        (answer("maybe", CREDIT_QUOTE), "no true/false names_handle"),
        (answer(True, "Photo by @alice_shoots for the bakery"), "the model's quote is not an exact substring"),
        (answer(True, "Sunrise over the harbour"), "the model's quote is not an exact substring"),
        (answer(True, ""), "the model's quote is not an exact substring"),
        (answer(True, CREDIT_QUOTE, "   "), "[LLM_ERROR] the model returned no reason"),
    ]
    for response, expected in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
        direct_vm.mock_llm(r"alice_shoots", response)
        with direct_vm.expect_revert(expected):
            contract.decide_claim(claim_id)
    assert claim(contract, claim_id)["decision_count"] == 0

    # "true" as a string is read as true.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://social\.example/.*", page(PAGE_CREDIT))
    direct_vm.mock_llm(r"alice_shoots", answer("true", CREDIT_QUOTE))
    assert contract.decide_claim(claim_id)["verdict"] == "VERIFIED"


def test_claim_id_matches_the_documented_formula(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    bob = creator_hex(direct_bob)
    expected = hashlib.sha256(json.dumps(
        [MEDIA, "alice_shoots", bob.lower(), POST_URL],
        sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()

    assert contract.claim_id_for(MEDIA, HANDLE, bob, POST_URL) == expected
    assert contract.claim_id_for(MEDIA.upper(), "ALICE_SHOOTS", bob.lower(), POST_URL) == expected
    assert open_claim(contract, direct_bob) == expected
