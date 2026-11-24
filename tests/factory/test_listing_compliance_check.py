"""Direct-mode tests for contracts/factory/listing_compliance_check.py.

Scaffolded with genskill-mcp genlayer_scaffold_test (llm-judge), then written to the
backlog item. The LLM is mocked, so these tests check the contract's own logic
(rulebook publishing, input checks, refusals, parsing, storage, the validator's
comparison), not a model's judgment and not GenVM consensus.

Run from the repository root:
    pip install genlayer-test pytest
    pytest tests/factory/test_listing_compliance_check.py -v
"""
import hashlib
import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parents[2] / "contracts" / "factory" / "listing_compliance_check.py")

RULES_V1 = [
    {"id": "SHOP-CONDITION", "text": "The listing must state the item's condition: new, used or refurbished."},
    {"id": "SHOP-ANIMALS", "text": "No live animals."},
]
LIMIT_V1 = 600

BOARD = (
    "Handmade oak chopping board",
    "New. Solid English oak, 40 x 25 cm, finished with food-safe oil. Ships from Leeds in 2 days.",
    "Home & Kitchen",
)
PATCH = (
    "WW2 SS Totenkopf patch, original",
    "Used. Genuine SS skull patch, great for collectors who honour the cause.",
    "Militaria",
)
TRAINERS = (
    "Brand new trainers, best price",
    "New in box. Pay by bank transfer before I post and message me on WhatsApp, not here.",
    "Fashion",
)
MUG = (
    "Blue glazed coffee mug",
    "Hand-thrown stoneware mug, 350 ml, dishwasher safe.",
    "Home & Kitchen",
)


def listing_sha(listing):
    text = json.dumps(list(listing), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def answer(verdict, rules, quote, reason="One sentence."):
    return json.dumps({"verdict": verdict, "rules": rules, "quote": quote, "reason": reason})


def deploy(direct_vm, direct_deploy, direct_owner, direct_alice):
    """Owner deploys and publishes rulebook v1; alice then asks for checks."""
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    contract.publish_rulebook("v1", json.dumps(RULES_V1), LIMIT_V1)
    direct_vm.sender = direct_alice
    return contract


# --- decision outcomes ---------------------------------------------------------------

def test_compliant(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Handmade oak chopping board", answer(
        "COMPLIANT", [], "", "Lawful kitchenware, condition stated, no fraud signals."))

    result = contract.check_listing(*BOARD, "v1")

    assert result == {
        "listing_sha256": listing_sha(BOARD),
        "verdict": "COMPLIANT",
        "rule_id": "",
        "quote": "",
        "reason": "Lawful kitchenware, condition stated, no fraud signals.",
        "rulebook_version": "v1",
    }
    stored = json.loads(contract.get_verdict(listing_sha(BOARD)))
    assert stored["verdict"] == "COMPLIANT"
    assert stored["rule_id"] == "" and stored["rules_broken"] == []
    assert stored["title"] == BOARD[0] and stored["category"] == BOARD[2]
    assert stored["rulebook_version"] == "v1"
    assert stored["rules_sha256"] == json.loads(contract.get_rulebook("v1"))["rules_sha256"]
    assert contract.get_verdict_count() == 1
    assert contract.get_listing_id(0) == listing_sha(BOARD)
    assert contract.listing_hash(*BOARD) == listing_sha(BOARD)


def test_hold_names_the_rule_that_holds_it(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Totenkopf", answer(
        "HOLD", ["PROHIBITED-CATEGORY", "UK-LAW"], "who honour the cause",
        "Offensive memorabilia that glorifies a hate group."))

    result = contract.check_listing(*PATCH, "v1")

    assert result["verdict"] == "HOLD"
    assert result["rule_id"] == "PROHIBITED-CATEGORY"
    assert result["quote"] == "who honour the cause"
    assert result["quote"] in PATCH[1]
    stored = json.loads(contract.get_verdict(listing_sha(PATCH)))
    assert stored["rules_broken"] == ["PROHIBITED-CATEGORY", "UK-LAW"]
    baseline = json.loads(contract.get_baseline_rules())
    assert stored["rule_text"] == baseline[1]["text"]
    assert [rule["id"] for rule in baseline] == ["UK-LAW", "PROHIBITED-CATEGORY", "FRAUD-SIGNAL"]


def test_hold_on_a_rulebook_rule_and_on_fraud_signals(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    # The model's rule id is matched ignoring case and stored in the rulebook's spelling.
    direct_vm.mock_llm(r"coffee mug", answer(
        "HOLD", ["shop-condition"], "Hand-thrown stoneware mug", "Condition is not stated."))
    result = contract.check_listing(*MUG, "v1")
    assert result["rule_id"] == "SHOP-CONDITION"
    stored = json.loads(contract.get_verdict(listing_sha(MUG)))
    assert stored["rule_text"] == RULES_V1[0]["text"]

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"WhatsApp", answer(
        "HOLD", "FRAUD-SIGNAL", "Pay by bank transfer before I post", "Off-platform payment request."))
    result = contract.check_listing(*TRAINERS, "v1")
    assert result["verdict"] == "HOLD" and result["rule_id"] == "FRAUD-SIGNAL"
    assert contract.get_verdict_count() == 2


def test_validator_agrees_on_verdict_and_named_rule(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Totenkopf", answer("HOLD", ["PROHIBITED-CATEGORY"], "SS skull patch"))
    contract.check_listing(*PATCH, "v1")

    # Same verdict, the leader's rule among the validator's, other quote and order: agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Totenkopf", answer(
        "HOLD", ["UK-LAW", "PROHIBITED-CATEGORY"], "WW2 SS Totenkopf patch", "Other words."))
    assert direct_vm.run_validator() is True

    # Same verdict but the validator does not find the rule the leader named: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Totenkopf", answer("HOLD", ["UK-LAW"], "SS skull patch"))
    assert direct_vm.run_validator() is False

    # A different verdict word: disagree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Totenkopf", answer("COMPLIANT", [], ""))
    assert direct_vm.run_validator() is False

    # A leader quote that is not in the listing, or a rule that does not exist: reject.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Totenkopf", answer("HOLD", ["PROHIBITED-CATEGORY"], "SS skull patch"))
    forged = {"verdict": "HOLD", "rules": ["PROHIBITED-CATEGORY"], "quote": "approved by the shop", "reason": "x"}
    assert direct_vm.run_validator(leader_result=forged) is False
    invented = {"verdict": "HOLD", "rules": ["MADE-UP"], "quote": "SS skull patch", "reason": "x"}
    assert direct_vm.run_validator(leader_result=invented) is False

    # A leader error is never accepted.
    assert direct_vm.run_validator(leader_error=Exception("[LLM_ERROR] x")) is False


def test_validator_agrees_on_compliant(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Handmade oak chopping board", answer("COMPLIANT", [], ""))
    contract.check_listing(*BOARD, "v1")

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Handmade oak chopping board", answer("COMPLIANT", [], "", "Different reason."))
    assert direct_vm.run_validator() is True

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"Handmade oak chopping board", answer("HOLD", ["SHOP-CONDITION"], "Solid English oak"))
    assert direct_vm.run_validator() is False


# --- must refuse ---------------------------------------------------------------------

def test_refuses_an_unknown_rulebook_version(direct_vm, direct_deploy, direct_owner, direct_alice):
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    direct_vm.mock_llm(r".*", answer("COMPLIANT", [], ""))

    with direct_vm.expect_revert("[EXPECTED] UNKNOWN_RULEBOOK_VERSION: no rulebook is published under this version"):
        contract.check_listing(*BOARD, "v1")

    contract.publish_rulebook("v1", json.dumps(RULES_V1), LIMIT_V1)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("UNKNOWN_RULEBOOK_VERSION"):
        contract.check_listing(*BOARD, "v2")
    with direct_vm.expect_revert("UNKNOWN_RULEBOOK_VERSION"):
        contract.check_listing(*BOARD, "V1")
    with direct_vm.expect_revert("UNKNOWN_RULEBOOK_VERSION"):
        contract.get_rulebook("v2")
    assert contract.get_verdict_count() == 0


def test_refuses_a_listing_longer_than_the_stated_limit(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r".*", answer("COMPLIANT", [], ""))
    title, category = "Oak board", "Home"
    room = LIMIT_V1 - len(title) - len(category)

    with direct_vm.expect_revert(
            "[EXPECTED] LISTING_TOO_LONG: title, description and category together exceed the rulebook's max_listing_chars"):
        contract.check_listing(title, "x" * (room + 1), category, "v1")
    assert contract.get_verdict_count() == 0

    # Exactly at the limit is accepted.
    result = contract.check_listing(title, "x" * room, category, "v1")
    assert result["verdict"] == "COMPLIANT"
    assert contract.get_verdict_count() == 1


def test_refuses_a_second_verdict_on_the_same_listing(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Handmade oak chopping board", answer("COMPLIANT", [], ""))
    contract.check_listing(*BOARD, "v1")

    with direct_vm.expect_revert("[EXPECTED] DUPLICATE_LISTING: this listing hash already has a verdict"):
        contract.check_listing(*BOARD, "v1")

    # Not under a newer rulebook either, and not from another caller.
    with direct_vm.prank(direct_owner):
        contract.publish_rulebook("v2", json.dumps(RULES_V1), 2000)
    with direct_vm.expect_revert("DUPLICATE_LISTING"):
        contract.check_listing(*BOARD, "v2")
    with direct_vm.prank(direct_owner):
        with direct_vm.expect_revert("DUPLICATE_LISTING"):
            contract.check_listing(*BOARD, "v1")
    assert contract.get_verdict_count() == 1

    # A changed listing is a new hash and gets its own verdict.
    edited = (BOARD[0], BOARD[1] + " ", BOARD[2])
    assert contract.check_listing(*edited, "v1")["listing_sha256"] == listing_sha(edited)
    assert contract.get_verdict_count() == 2


# --- other refusals ------------------------------------------------------------------

def test_refuses_empty_listing_fields(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r".*", answer("COMPLIANT", [], ""))

    with direct_vm.expect_revert("EMPTY_TITLE"):
        contract.check_listing(" ", BOARD[1], BOARD[2], "v1")
    with direct_vm.expect_revert("EMPTY_DESCRIPTION"):
        contract.check_listing(BOARD[0], "", BOARD[2], "v1")
    with direct_vm.expect_revert("EMPTY_CATEGORY"):
        contract.check_listing(BOARD[0], BOARD[1], "\n", "v1")
    assert contract.get_verdict_count() == 0


def test_publish_rulebook_refusals(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    direct_vm.sender = direct_owner
    contract = direct_deploy(CONTRACT)
    owner_hex = "0x" + hashlib.sha256(b"default_sender").digest()[:20].hex()
    assert contract.get_owner().lower() == owner_hex

    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("[EXPECTED] OWNER_ONLY"):
            contract.publish_rulebook("v1", json.dumps(RULES_V1), LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULEBOOK_VERSION"):
        contract.publish_rulebook("v 1", json.dumps(RULES_V1), LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULEBOOK_VERSION"):
        contract.publish_rulebook("", json.dumps(RULES_V1), LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULES"):
        contract.publish_rulebook("v1", "not json", LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULES"):
        contract.publish_rulebook("v1", "[]", LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULES"):
        contract.publish_rulebook("v1", json.dumps([{"id": "A", "text": "x", "extra": 1}]), LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULE_ID"):
        contract.publish_rulebook("v1", json.dumps([{"id": "has space", "text": "x"}]), LIMIT_V1)
    with direct_vm.expect_revert("BAD_RULE_TEXT"):
        contract.publish_rulebook("v1", json.dumps([{"id": "A", "text": "  "}]), LIMIT_V1)
    with direct_vm.expect_revert("RESERVED_RULE_ID"):
        contract.publish_rulebook("v1", json.dumps([{"id": "uk-law", "text": "x"}]), LIMIT_V1)
    with direct_vm.expect_revert("DUPLICATE_RULE_ID"):
        contract.publish_rulebook("v1", json.dumps([{"id": "A", "text": "x"}, {"id": "a", "text": "y"}]), LIMIT_V1)
    with direct_vm.expect_revert("BAD_LISTING_LIMIT"):
        contract.publish_rulebook("v1", json.dumps(RULES_V1), 99)
    with direct_vm.expect_revert("BAD_LISTING_LIMIT"):
        contract.publish_rulebook("v1", json.dumps(RULES_V1), 8001)
    assert contract.get_rulebook_count() == 0

    published = contract.publish_rulebook("v1", json.dumps(RULES_V1), LIMIT_V1)
    assert published["rule_count"] == 2 and published["max_listing_chars"] == LIMIT_V1
    with direct_vm.expect_revert("[EXPECTED] RULEBOOK_VERSION_EXISTS"):
        contract.publish_rulebook("v1", json.dumps([{"id": "A", "text": "changed"}]), LIMIT_V1)
    stored = json.loads(contract.get_rulebook("v1"))
    assert stored["rules"] == RULES_V1 and stored["max_listing_chars"] == LIMIT_V1
    assert contract.get_rulebook_count() == 1 and contract.get_rulebook_version(0) == "v1"
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_rulebook_version(1)


def test_refuses_malformed_model_answers(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    cases = [
        (answer("HOLD", ["PROHIBITED-CATEGORY"], "sold by the shop owner"), "[LLM_ERROR] the model's quote is not an exact substring"),
        (answer("HOLD", ["MADE-UP-RULE"], "SS skull patch"), "[LLM_ERROR] the model's rule list"),
        (answer("HOLD", [], "SS skull patch"), "[LLM_ERROR] the model's rule list"),
        (answer("COMPLIANT", ["UK-LAW"], ""), "[LLM_ERROR] the model's rule list"),
        (answer("PROBABLY_FINE", [], ""), "[LLM_ERROR] the model returned no valid verdict word"),
        (answer("HOLD", ["UK-LAW"], "SS skull patch", ""), "[LLM_ERROR] the model returned no reason"),
        ("no json here", "[LLM_ERROR] the model did not return a JSON object"),
    ]
    for raw, message in cases:
        direct_vm.clear_mocks()
        direct_vm.mock_llm(r"Totenkopf", raw)
        with direct_vm.expect_revert(message):
            contract.check_listing(*PATCH, "v1")
    assert contract.get_verdict_count() == 0


def test_verdict_lookups(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.mock_llm(r"Handmade oak chopping board", answer("COMPLIANT", [], ""))
    contract.check_listing(*BOARD, "v1")

    assert json.loads(contract.get_verdict(listing_sha(BOARD).upper()))["verdict"] == "COMPLIANT"
    with direct_vm.expect_revert("UNKNOWN_LISTING"):
        contract.get_verdict(listing_sha(MUG))
    with direct_vm.expect_revert("BAD_LISTING_HASH"):
        contract.get_verdict("not-a-hash")
    with direct_vm.expect_revert("BAD_INDEX"):
        contract.get_listing_id(1)
