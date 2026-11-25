# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

"""Agreement Registry -- GenLayer Intelligent Contract (contract factory draft).

No judgment: records that an agreement exists and which state it is in
(ODIR Brain slice B2). Deterministic storage only; no LLM and no web call.

Constructor: AgreementRegistry() takes no arguments. The deploying address
becomes the owner (admin). No relayer is set at deploy; the owner sets exactly
one relayer address with set_relayer (and may change or remove it later).

Roles:
  owner    may do everything: set_relayer, remove_relayer, append_agreement,
           move_state.
  relayer  may only append_agreement and move_state. Any owner-only call from
           the relayer is refused with OWNER_ONLY.
  anyone else is refused with UNAUTHORIZED on every write method.
  View methods are open to everyone.

States (fixed, ordered, forward-only; the owner may want to change this list):
  0 PROPOSED -> 1 ACCEPTED -> 2 SIGNED -> 3 ANCHORED -> 4 CLOSED
  A record's state moves only to a state later in this list. Skipping ahead is
  allowed (ACCEPTED -> ANCHORED is valid); the same state or an earlier one is
  refused with INVALID_TRANSITION. CLOSED is terminal: nothing follows it, and
  the outcome code says how the agreement ended.

Write methods:
  set_relayer(relayer)             owner only. relayer is 0x + 40 hex characters.
    Returns {"relayer"} (lowercase hex). Replaces any earlier relayer.
  remove_relayer()                 owner only. Returns {"relayer": ""}.
  append_agreement(agreement_id, terms_hash, role_keys, base,
                   template_version, state, outcome_code)
                                   owner or relayer.
    agreement_id      sha256 hex of the agreement id (64 hex, optional 0x)
    terms_hash        sha256 hex of the agreement terms (64 hex, optional 0x)
    role_keys         comma-separated public role-key strings, 1..16 keys,
                      each 1..128 characters from A-Z a-z 0-9 _ . : -, no repeats
    base              public string, 1..128 printable ASCII characters
    template_version  public string, 1..32 characters from A-Z a-z 0-9 _ . -
    state             one of the states above (the record's starting state)
    outcome_code      short public code, 0..32 characters from A-Z 0-9 _
                      ("" means no outcome yet)
    Hashes are stored lowercase without 0x, so 0x/bare/upper-case spellings of
    one id are the same id. Returns {"agreement_id", "state", "index"}.
  move_state(agreement_id, new_state, outcome_code)
                                   owner or relayer. Moves the record forward.
    outcome_code "" keeps the stored outcome code; otherwise it replaces it.
    Returns {"agreement_id", "from_state", "state", "outcome_code"}.

View methods:
  get_agreement(agreement_id)  the stored record as JSON text (sorted keys):
                               agreement_id, terms_hash, role_keys (list), base,
                               template_version, state, outcome_code, index
  get_count()                  number of records
  get_agreement_id(index)      the agreement id stored at index (0-based)
  get_owner() / get_relayer()  lowercase hex ("" when no relayer is set)
  get_states()                 the ordered state list

Refusals (gl.vm.UserError, exact text in the ERR_* constants below):
  UNAUTHORIZED, OWNER_ONLY, DUPLICATE_ID, UNKNOWN_AGREEMENT, UNKNOWN_STATE,
  INVALID_TRANSITION, BAD_AGREEMENT_ID, BAD_TERMS_HASH, BAD_ROLE_KEYS, BAD_BASE,
  BAD_TEMPLATE_VERSION, BAD_OUTCOME_CODE, BAD_ADDRESS, INDEX_OUT_OF_RANGE.
  A refused call writes nothing.

Only public data: hashes, public role keys, public strings and short codes.
Never send names, emails or private evidence to this contract.
"""

import json

STATES = ["PROPOSED", "ACCEPTED", "SIGNED", "ANCHORED", "CLOSED"]

ERR_UNAUTHORIZED = "[EXPECTED] UNAUTHORIZED: only the owner or the relayer may call this"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: the relayer may only append a record or move its state"
ERR_DUPLICATE_ID = "[EXPECTED] DUPLICATE_ID: an agreement with this id is already recorded"
ERR_UNKNOWN_AGREEMENT = "[EXPECTED] UNKNOWN_AGREEMENT: no agreement is recorded with this id"
ERR_UNKNOWN_STATE = "[EXPECTED] UNKNOWN_STATE: state must be one of PROPOSED, ACCEPTED, SIGNED, ANCHORED, CLOSED"
ERR_INVALID_TRANSITION = "[EXPECTED] INVALID_TRANSITION: state moves only forward"
ERR_BAD_AGREEMENT_ID = "[EXPECTED] BAD_AGREEMENT_ID: agreement id must be a sha256 hash (64 hex characters, optional 0x)"
ERR_BAD_TERMS_HASH = "[EXPECTED] BAD_TERMS_HASH: terms hash must be a sha256 hash (64 hex characters, optional 0x)"
ERR_BAD_ROLE_KEYS = "[EXPECTED] BAD_ROLE_KEYS: role keys must be 1 to 16 distinct comma-separated keys of 1 to 128 characters from A-Z a-z 0-9 _ . : -"
ERR_BAD_BASE = "[EXPECTED] BAD_BASE: base must be 1 to 128 printable ASCII characters"
ERR_BAD_TEMPLATE_VERSION = "[EXPECTED] BAD_TEMPLATE_VERSION: template version must be 1 to 32 characters from A-Z a-z 0-9 _ . -"
ERR_BAD_OUTCOME_CODE = "[EXPECTED] BAD_OUTCOME_CODE: outcome code must be 0 to 32 characters from A-Z 0-9 _"
ERR_BAD_ADDRESS = "[EXPECTED] BAD_ADDRESS: relayer must be 0x followed by 40 hex characters"
ERR_INDEX_OUT_OF_RANGE = "[EXPECTED] INDEX_OUT_OF_RANGE: no agreement at this index"

HEX = "0123456789abcdef"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
ROLE_KEY_CHARS = UPPER + LOWER + DIGITS + "_.:-"
TEMPLATE_CHARS = UPPER + LOWER + DIGITS + "_.-"
OUTCOME_CHARS = UPPER + DIGITS + "_"

MAX_ROLE_KEYS = 16
MAX_ROLE_KEY_LEN = 128
MAX_BASE_LEN = 128
MAX_TEMPLATE_LEN = 32
MAX_OUTCOME_LEN = 32


def _only_chars(text: str, allowed: str) -> bool:
    i = 0
    while i < len(text):
        if text[i] not in allowed:
            return False
        i += 1
    return True


def _hash_or_empty(value: str) -> str:
    """Lowercase bare 64-hex form of a sha256 hash, or "" when malformed."""
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    if len(text) != 64 or not _only_chars(text, HEX):
        return ""
    return text


def _state_index(state: str) -> int:
    i = 0
    while i < len(STATES):
        if STATES[i] == state:
            return i
        i += 1
    return -1


def _role_keys_or_none(value: str):
    parts = value.split(",")
    if len(parts) < 1 or len(parts) > MAX_ROLE_KEYS:
        return None
    out = []
    i = 0
    while i < len(parts):
        key = parts[i].strip()
        if len(key) < 1 or len(key) > MAX_ROLE_KEY_LEN:
            return None
        if not _only_chars(key, ROLE_KEY_CHARS):
            return None
        if key in out:
            return None
        out.append(key)
        i += 1
    return out


def _printable_ascii(text: str) -> bool:
    i = 0
    while i < len(text):
        code = ord(text[i])
        if code < 32 or code > 126:
            return False
        i += 1
    return True


def _dumps(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class AgreementRegistry(gl.Contract):
    owner: str
    relayer: str
    records: TreeMap[str, str]
    ids: DynArray[str]

    def __init__(self):
        self.owner = gl.message.sender_address.as_hex.lower()
        self.relayer = ""

    # --- access ------------------------------------------------------------------

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower()

    def _require_owner(self) -> None:
        sender = self._sender()
        if sender == self.owner:
            return
        if self.relayer != "" and sender == self.relayer:
            raise gl.vm.UserError(ERR_OWNER_ONLY)
        raise gl.vm.UserError(ERR_UNAUTHORIZED)

    def _require_owner_or_relayer(self) -> None:
        sender = self._sender()
        if sender == self.owner:
            return
        if self.relayer != "" and sender == self.relayer:
            return
        raise gl.vm.UserError(ERR_UNAUTHORIZED)

    # --- owner-only writes ---------------------------------------------------------

    @gl.public.write
    def set_relayer(self, relayer: str) -> dict:
        self._require_owner()
        text = relayer.strip().lower()
        if not text.startswith("0x") or len(text) != 42 or not _only_chars(text[2:], HEX):
            raise gl.vm.UserError(ERR_BAD_ADDRESS)
        self.relayer = text
        return {"relayer": text}

    @gl.public.write
    def remove_relayer(self) -> dict:
        self._require_owner()
        self.relayer = ""
        return {"relayer": ""}

    # --- owner or relayer writes ---------------------------------------------------

    @gl.public.write
    def append_agreement(
        self,
        agreement_id: str,
        terms_hash: str,
        role_keys: str,
        base: str,
        template_version: str,
        state: str,
        outcome_code: str,
    ) -> dict:
        self._require_owner_or_relayer()
        agreement = _hash_or_empty(agreement_id)
        if agreement == "":
            raise gl.vm.UserError(ERR_BAD_AGREEMENT_ID)
        terms = _hash_or_empty(terms_hash)
        if terms == "":
            raise gl.vm.UserError(ERR_BAD_TERMS_HASH)
        keys = _role_keys_or_none(role_keys)
        if keys is None:
            raise gl.vm.UserError(ERR_BAD_ROLE_KEYS)
        if len(base) < 1 or len(base) > MAX_BASE_LEN or not _printable_ascii(base):
            raise gl.vm.UserError(ERR_BAD_BASE)
        if (
            len(template_version) < 1
            or len(template_version) > MAX_TEMPLATE_LEN
            or not _only_chars(template_version, TEMPLATE_CHARS)
        ):
            raise gl.vm.UserError(ERR_BAD_TEMPLATE_VERSION)
        if _state_index(state) < 0:
            raise gl.vm.UserError(ERR_UNKNOWN_STATE)
        if len(outcome_code) > MAX_OUTCOME_LEN or not _only_chars(outcome_code, OUTCOME_CHARS):
            raise gl.vm.UserError(ERR_BAD_OUTCOME_CODE)
        if agreement in self.records:
            raise gl.vm.UserError(ERR_DUPLICATE_ID)

        index = len(self.ids)
        record = {
            "agreement_id": agreement,
            "terms_hash": terms,
            "role_keys": keys,
            "base": base,
            "template_version": template_version,
            "state": state,
            "outcome_code": outcome_code,
            "index": index,
        }
        self.records[agreement] = _dumps(record)
        self.ids.append(agreement)
        return {"agreement_id": agreement, "state": state, "index": index}

    @gl.public.write
    def move_state(self, agreement_id: str, new_state: str, outcome_code: str) -> dict:
        self._require_owner_or_relayer()
        agreement = _hash_or_empty(agreement_id)
        if agreement == "":
            raise gl.vm.UserError(ERR_BAD_AGREEMENT_ID)
        if agreement not in self.records:
            raise gl.vm.UserError(ERR_UNKNOWN_AGREEMENT)
        target = _state_index(new_state)
        if target < 0:
            raise gl.vm.UserError(ERR_UNKNOWN_STATE)
        if len(outcome_code) > MAX_OUTCOME_LEN or not _only_chars(outcome_code, OUTCOME_CHARS):
            raise gl.vm.UserError(ERR_BAD_OUTCOME_CODE)
        record = json.loads(self.records[agreement])
        current = record["state"]
        if target <= _state_index(current):
            raise gl.vm.UserError(ERR_INVALID_TRANSITION)

        record["state"] = new_state
        if outcome_code != "":
            record["outcome_code"] = outcome_code
        self.records[agreement] = _dumps(record)
        return {
            "agreement_id": agreement,
            "from_state": current,
            "state": new_state,
            "outcome_code": record["outcome_code"],
        }

    # --- views -------------------------------------------------------------------

    @gl.public.view
    def get_agreement(self, agreement_id: str) -> str:
        agreement = _hash_or_empty(agreement_id)
        if agreement == "":
            raise gl.vm.UserError(ERR_BAD_AGREEMENT_ID)
        if agreement not in self.records:
            raise gl.vm.UserError(ERR_UNKNOWN_AGREEMENT)
        return self.records[agreement]

    @gl.public.view
    def get_count(self) -> int:
        return len(self.ids)

    @gl.public.view
    def get_agreement_id(self, index: int) -> str:
        if index < 0 or index >= len(self.ids):
            raise gl.vm.UserError(ERR_INDEX_OUT_OF_RANGE)
        return self.ids[index]

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner

    @gl.public.view
    def get_relayer(self) -> str:
        return self.relayer

    @gl.public.view
    def get_states(self) -> list:
        out = []
        i = 0
        while i < len(STATES):
            out.append(STATES[i])
            i += 1
        return out
