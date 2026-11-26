# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

"""Agreement Registry -- GenLayer Intelligent Contract (contract factory draft,
aligned for ODIR Brain slice B2 on 26 Nov 2026).

No judgment: records that an agreement exists and which state it is in.
Deterministic storage only; no LLM and no web call.

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

Hashes (agreement id, terms hash, seal hash) are sha256: 64 hex characters,
bare or with one 0x or sha256: prefix, any case, no spaces. Every spelling of
one hash is the same hash. Each is stored lowercase in the spelling its
SnapLink source writes, so SnapLink can compare a stored value to its own
with plain string equality:
  terms_hash    sha256:<hex>  (the ODIR resolver's terms_hash, slice A3)
  seal_hash     <hex>         (SnapLink agreementSealHash, slice C4)
  agreement_id  <hex>         (like C4's agreement_ref)

Write methods:
  set_relayer(relayer)             owner only. relayer is 0x + 40 hex characters.
    Returns {"relayer"} (lowercase hex). Replaces any earlier relayer.
  remove_relayer()                 owner only. Returns {"relayer": ""}.
  append_agreement(agreement_id, terms_hash, role_keys, base,
                   template_version, state, outcome_code, seal_hash)
                                   owner or relayer.
    agreement_id      sha256 of the agreement id (see Hashes)
    terms_hash        the resolved agreement's terms hash (A3 terms_hash)
    role_keys         "" (a base-only agreement) or 1 to 2 comma-separated
                      slot:role keys from the agreement's roles: slot is
                      engager or provider, each at most once; role is a-z
                      then 1 to 40 of a-z 0-9 _ (the A3 role key). Stored as a
                      list, engager first.
    base              one of P2P, P2B, B2P, B2B, STAFF (the A3 base key)
    template_version  the ODIR template release tag templates-vX.Y.Z (A4),
                      numbers without leading zeros, at most 32 characters
    state             one of the states above (the record's starting state)
    outcome_code      short public code, 0..32 characters from A-Z 0-9 _
                      ("" means no outcome yet)
    seal_hash         "" (not sealed yet) or the sha256 seal over the parties'
                      e-sign evidence hashes (C4 agreementSealHash)
    Returns {"agreement_id", "state", "index"}.
  move_state(agreement_id, new_state, outcome_code, seal_hash)
                                   owner or relayer. Moves the record forward.
    outcome_code "" keeps the stored outcome code; otherwise it replaces it.
    seal_hash "" keeps the stored seal; otherwise it records the seal, which
    is allowed only while no seal is stored (SEAL_ALREADY_SET).
    Returns {"agreement_id", "from_state", "state", "outcome_code",
    "seal_hash"}.

View methods:
  get_agreement(agreement_id)  the stored record as JSON text (sorted keys):
                               agreement_id, terms_hash, role_keys (list), base,
                               template_version, state, outcome_code,
                               seal_hash, index
  get_count()                  number of records
  get_agreement_id(index)      the agreement id stored at index (0-based)
  get_owner() / get_relayer()  lowercase hex ("" when no relayer is set)
  get_states()                 the ordered state list

Refusals (gl.vm.UserError, exact text in the ERR_* constants below):
  UNAUTHORIZED, OWNER_ONLY, DUPLICATE_ID, UNKNOWN_AGREEMENT, UNKNOWN_STATE,
  INVALID_TRANSITION, BAD_AGREEMENT_ID, BAD_TERMS_HASH, BAD_SEAL_HASH,
  SEAL_ALREADY_SET, BAD_ROLE_KEYS, BAD_BASE, BAD_TEMPLATE_VERSION,
  BAD_OUTCOME_CODE, BAD_ADDRESS, INDEX_OUT_OF_RANGE.
  A refused call writes nothing.

Only public data: hashes, role keys, base keys, a release tag and short codes.
Never send names, emails, pay or private evidence to this contract.
"""

import json

STATES = ["PROPOSED", "ACCEPTED", "SIGNED", "ANCHORED", "CLOSED"]
BASES = ["P2P", "P2B", "B2P", "B2B", "STAFF"]

ERR_UNAUTHORIZED = "[EXPECTED] UNAUTHORIZED: only the owner or the relayer may call this"
ERR_OWNER_ONLY = "[EXPECTED] OWNER_ONLY: the relayer may only append a record or move its state"
ERR_DUPLICATE_ID = "[EXPECTED] DUPLICATE_ID: an agreement with this id is already recorded"
ERR_UNKNOWN_AGREEMENT = "[EXPECTED] UNKNOWN_AGREEMENT: no agreement is recorded with this id"
ERR_UNKNOWN_STATE = "[EXPECTED] UNKNOWN_STATE: state must be one of PROPOSED, ACCEPTED, SIGNED, ANCHORED, CLOSED"
ERR_INVALID_TRANSITION = "[EXPECTED] INVALID_TRANSITION: state moves only forward"
ERR_BAD_AGREEMENT_ID = "[EXPECTED] BAD_AGREEMENT_ID: agreement id must be a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_BAD_TERMS_HASH = "[EXPECTED] BAD_TERMS_HASH: terms hash must be a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_BAD_SEAL_HASH = "[EXPECTED] BAD_SEAL_HASH: seal hash must be empty or a sha256 hash (64 hex characters, optional 0x or sha256: prefix)"
ERR_SEAL_ALREADY_SET = "[EXPECTED] SEAL_ALREADY_SET: the seal hash is already recorded and cannot change"
ERR_BAD_ROLE_KEYS = "[EXPECTED] BAD_ROLE_KEYS: role keys must be empty or 1 to 2 comma-separated slot:role keys (slot engager or provider, each once; role a-z then 1 to 40 of a-z 0-9 _)"
ERR_BAD_BASE = "[EXPECTED] BAD_BASE: base must be one of P2P, P2B, B2P, B2B, STAFF"
ERR_BAD_TEMPLATE_VERSION = "[EXPECTED] BAD_TEMPLATE_VERSION: template version must be a release tag templates-vX.Y.Z (no leading zeros, at most 32 characters)"
ERR_BAD_OUTCOME_CODE = "[EXPECTED] BAD_OUTCOME_CODE: outcome code must be 0 to 32 characters from A-Z 0-9 _"
ERR_BAD_ADDRESS = "[EXPECTED] BAD_ADDRESS: relayer must be 0x followed by 40 hex characters"
ERR_INDEX_OUT_OF_RANGE = "[EXPECTED] INDEX_OUT_OF_RANGE: no agreement at this index"

HEX = "0123456789abcdef"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
ROLE_CHARS = LOWER + DIGITS + "_"
OUTCOME_CHARS = UPPER + DIGITS + "_"
TAG_PREFIX = "templates-v"
SHA256_PREFIX = "sha256:"

MIN_ROLE_LEN = 2
MAX_ROLE_LEN = 41
MAX_ROLE_KEYS = 2
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
    text = value.lower()
    if text.startswith(SHA256_PREFIX):
        text = text[len(SHA256_PREFIX):]
    elif text.startswith("0x"):
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


def _is_role(role: str) -> bool:
    if len(role) < MIN_ROLE_LEN or len(role) > MAX_ROLE_LEN:
        return False
    if role[0] not in LOWER:
        return False
    return _only_chars(role, ROLE_CHARS)


def _role_keys_or_none(value: str):
    """[] for "", else the slot:role keys with engager first; None when malformed."""
    if value == "":
        return []
    parts = value.split(",")
    if len(parts) > MAX_ROLE_KEYS:
        return None
    engager = ""
    provider = ""
    i = 0
    while i < len(parts):
        key = parts[i]
        colon = key.find(":")
        if colon < 0:
            return None
        slot = key[:colon]
        if not _is_role(key[colon + 1:]):
            return None
        if slot == "engager" and engager == "":
            engager = key
        elif slot == "provider" and provider == "":
            provider = key
        else:
            return None
        i += 1
    out = []
    if engager != "":
        out.append(engager)
    if provider != "":
        out.append(provider)
    return out


def _is_release_tag(text: str) -> bool:
    if len(text) > MAX_TEMPLATE_LEN or not text.startswith(TAG_PREFIX):
        return False
    parts = text[len(TAG_PREFIX):].split(".")
    if len(parts) != 3:
        return False
    i = 0
    while i < len(parts):
        part = parts[i]
        if len(part) < 1 or not _only_chars(part, DIGITS):
            return False
        if len(part) > 1 and part[0] == "0":
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
        seal_hash: str,
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
        if base not in BASES:
            raise gl.vm.UserError(ERR_BAD_BASE)
        if not _is_release_tag(template_version):
            raise gl.vm.UserError(ERR_BAD_TEMPLATE_VERSION)
        if _state_index(state) < 0:
            raise gl.vm.UserError(ERR_UNKNOWN_STATE)
        if len(outcome_code) > MAX_OUTCOME_LEN or not _only_chars(outcome_code, OUTCOME_CHARS):
            raise gl.vm.UserError(ERR_BAD_OUTCOME_CODE)
        seal = ""
        if seal_hash != "":
            seal = _hash_or_empty(seal_hash)
            if seal == "":
                raise gl.vm.UserError(ERR_BAD_SEAL_HASH)
        if agreement in self.records:
            raise gl.vm.UserError(ERR_DUPLICATE_ID)

        index = len(self.ids)
        record = {
            "agreement_id": agreement,
            "terms_hash": SHA256_PREFIX + terms,
            "role_keys": keys,
            "base": base,
            "template_version": template_version,
            "state": state,
            "outcome_code": outcome_code,
            "seal_hash": seal,
            "index": index,
        }
        self.records[agreement] = _dumps(record)
        self.ids.append(agreement)
        return {"agreement_id": agreement, "state": state, "index": index}

    @gl.public.write
    def move_state(self, agreement_id: str, new_state: str, outcome_code: str, seal_hash: str) -> dict:
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
        seal = ""
        if seal_hash != "":
            seal = _hash_or_empty(seal_hash)
            if seal == "":
                raise gl.vm.UserError(ERR_BAD_SEAL_HASH)
        record = json.loads(self.records[agreement])
        current = record["state"]
        if target <= _state_index(current):
            raise gl.vm.UserError(ERR_INVALID_TRANSITION)
        if seal != "" and record["seal_hash"] != "":
            raise gl.vm.UserError(ERR_SEAL_ALREADY_SET)

        record["state"] = new_state
        if outcome_code != "":
            record["outcome_code"] = outcome_code
        if seal != "":
            record["seal_hash"] = seal
        self.records[agreement] = _dumps(record)
        return {
            "agreement_id": agreement,
            "from_state": current,
            "state": new_state,
            "outcome_code": record["outcome_code"],
            "seal_hash": record["seal_hash"],
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
