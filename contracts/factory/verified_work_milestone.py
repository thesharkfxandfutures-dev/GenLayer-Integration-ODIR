# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

"""Verified Work Milestone -- GenLayer Intelligent Contract (contract factory draft).

Award contract for SnapLink's Verified Work trophies, Foundation (25 pieces)
to Zenith (10,000 pieces). One contract serves every SnapLink role: the role
key is an input.

Decision: is every counted piece of work attested or SnapLink-verified, done
in the named role and counted once, so that the milestone is reached? The
answer is MILESTONE_REACHED, or NOT_REACHED with the shortfall, plus a reason
sentence. A verdict is an opinion only: it grants nothing until SnapLink's own
checks accept it.

This decision is counting, so it is plain deterministic code: no model, no
web read, no equivalence principle; every validator recomputes the same answer.

Constructor: VerifiedWorkMilestone() takes no arguments. The deployer becomes
the owner (SnapLink's account). The catalogue starts with the two milestones
the owner's page names: FOUNDATION = 25 and ZENITH = 10000; the owner adds the
levels in between with add_milestone.

Calldata is public: send only public data (64-hex hashes, level words, role
keys), never a name, an email or private evidence.
  entrant_id       sha256 hex (64 hex characters) standing for the entrant
  role_key         lowercase snake_case, 2..48 characters, e.g. "photographer".
                   Only the shape is checked: SnapLink's list of 45 role keys
                   is not on chain
  milestone        a catalogue name, case-insensitive (FOUNDATION, ZENITH, ...)
  work_hashes      list of work-record hashes, 64 hex characters each
  evidence_levels  list of level words, one per record (letters, digits or _,
                   at most 32 characters, case-insensitive)
  work_roles       list of role keys, one per record (same rule as role_key)
The three lists are parallel: record i is (work_hashes[i], evidence_levels[i],
work_roles[i]). A claim lists at most 10000 records.

Counting rule: a record counts if and only if its evidence level is ATTESTED
or SNAPLINK_VERIFIED and its role equals role_key. Any other well-formed level
word (SELF_REPORTED, PENDING, ...) is accepted but not counted. The milestone
is reached if and only if counted >= the milestone's count; otherwise the
answer is NOT_REACHED with shortfall = count - counted.

Forbidden selection signals: paid membership must never improve anyone's
chance of an award, so every text input is split into words (runs of ASCII
letters; case-insensitive) and the claim is refused if any word is one of
FORBIDDEN_LIST below (likes, followers, votes, paid plan, subscription,
premium, membership, boost families).

Write methods (owner only):
  claim_milestone(entrant_id, role_key, milestone, work_hashes,
                  evidence_levels, work_roles)
    Returns {"claim_index", "entrant_id", "role_key", "milestone", "verdict",
    "required", "counted", "shortfall", "records", "not_counted_level",
    "not_counted_role", "reason"}. Every answered claim is logged; a
    MILESTONE_REACHED claim is also stored as the confirmation for (entrant,
    role, milestone). NOT_REACHED confirms nothing and does not block a later
    claim.
  add_milestone(name, count)
    Adds a milestone (letter first, then letters, digits or _, at most 32
    characters, stored upper-case; count 1..10000). Returns
    {"milestone", "count"}.

View methods:
  get_owner(); get_rules(); get_catalogue(); get_milestone(name)
  is_confirmed(entrant_id, role_key, milestone)
  get_confirmation(entrant_id, role_key, milestone)
  get_claim_count(); get_claim(index)

Refusals (gl.vm.UserError, exact text in the ERR_* constants below):
  UNKNOWN_MILESTONE (not in the catalogue); DUPLICATE_WORK_HASH (the same work
  hash twice in one claim); ALREADY_CONFIRMED (the milestone is already
  confirmed for this entrant and role); FORBIDDEN_SIGNAL (a text input carries
  a forbidden selection signal); NOT_OWNER; BAD_ROLE_KEY; BAD_ENTRANT_ID;
  BAD_WORK_HASH; BAD_EVIDENCE_LEVEL; BAD_WORK_RECORDS; TOO_MANY_RECORDS;
  BAD_MILESTONE_NAME; BAD_MILESTONE_COUNT; MILESTONE_EXISTS; NOT_CONFIRMED;
  BAD_INDEX. A refused call writes nothing.

Limits: the contract counts what it is given. It cannot see SnapLink's work
records, so whether a hash, its level and its role are true is SnapLink's own
check, and a hash reused in another claim, role or entrant is not detected on
chain. The work list itself is not stored (it stays in the public calldata).
Not deployed or run on GenVM by the factory; the owner deploys and signs.
"""

import json
import typing

VERDICT_REACHED = "MILESTONE_REACHED"
VERDICT_NOT_REACHED = "NOT_REACHED"
COUNTING_LEVELS = ("ATTESTED", "SNAPLINK_VERIFIED")
SEED_MILESTONES = (("FOUNDATION", 25), ("ZENITH", 10000))
MAX_RECORDS = 10000
ROLE_KEY_MIN = 2
ROLE_KEY_MAX = 48
WORD_MAX = 32

FORBIDDEN_LIST = (
    "like", "likes", "liked", "liking",
    "follower", "followers",
    "vote", "votes", "voted", "voting", "upvote", "upvotes", "upvoted",
    "paid", "subscription", "subscriptions", "subscriber", "subscribers",
    "premium", "membership", "memberships",
    "boost", "boosts", "boosted", "boosting",
)
FORBIDDEN_WORDS = frozenset(FORBIDDEN_LIST)

LOWER_CHARS = "abcdefghijklmnopqrstuvwxyz"
UPPER_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
ROLE_CHARS = LOWER_CHARS + DIGITS + "_"
WORD_CHARS = UPPER_CHARS + DIGITS + "_"
ASCII_LOWER = str.maketrans(UPPER_CHARS, LOWER_CHARS)
ASCII_UPPER = str.maketrans(LOWER_CHARS, UPPER_CHARS)

ERR_NOT_OWNER = "[EXPECTED] NOT_OWNER: only the contract owner (the deployer) can do this"
ERR_FORBIDDEN_SIGNAL = ("[EXPECTED] FORBIDDEN_SIGNAL: inputs must not carry a selection signal "
                        "(likes, followers, votes, paid plan or boost)")
ERR_BAD_ROLE_KEY = "[EXPECTED] BAD_ROLE_KEY: a role key must be lowercase snake_case, 2 to 48 characters"
ERR_BAD_ENTRANT_ID = ("[EXPECTED] BAD_ENTRANT_ID: entrant_id must be 64 hexadecimal characters "
                      "(a public hash, never a name)")
ERR_BAD_WORK_HASH = "[EXPECTED] BAD_WORK_HASH: every work-record hash must be 64 hexadecimal characters"
ERR_BAD_EVIDENCE_LEVEL = ("[EXPECTED] BAD_EVIDENCE_LEVEL: an evidence level must be one word of letters, "
                          "digits or underscores, at most 32 characters")
ERR_BAD_WORK_RECORDS = ("[EXPECTED] BAD_WORK_RECORDS: work_hashes, evidence_levels and work_roles must be "
                        "lists of text of the same length")
ERR_TOO_MANY_RECORDS = "[EXPECTED] TOO_MANY_RECORDS: a claim may list at most 10000 work records"
ERR_UNKNOWN_MILESTONE = "[EXPECTED] UNKNOWN_MILESTONE: this milestone is not in the catalogue"
ERR_DUPLICATE_WORK_HASH = "[EXPECTED] DUPLICATE_WORK_HASH: the same work hash appears more than once in this claim"
ERR_ALREADY_CONFIRMED = ("[EXPECTED] ALREADY_CONFIRMED: this milestone is already confirmed for this "
                         "entrant and role")
ERR_BAD_MILESTONE_NAME = ("[EXPECTED] BAD_MILESTONE_NAME: a milestone name must start with a letter and use "
                          "only letters, digits or underscores, at most 32 characters")
ERR_BAD_MILESTONE_COUNT = "[EXPECTED] BAD_MILESTONE_COUNT: a milestone count must be a whole number from 1 to 10000"
ERR_MILESTONE_EXISTS = "[EXPECTED] MILESTONE_EXISTS: this milestone is already in the catalogue"
ERR_NOT_CONFIRMED = "[EXPECTED] NOT_CONFIRMED: no confirmation is stored for this entrant, role and milestone"
ERR_BAD_INDEX = "[EXPECTED] BAD_INDEX: no claim at this index"


def _separator_table() -> dict:
    """Map every ASCII character that is not a letter to a space."""
    table = {}
    code = 0
    while code < 128:
        char = chr(code)
        if char not in UPPER_CHARS and char not in LOWER_CHARS:
            table[code] = " "
        code += 1
    return table


SEPARATORS = _separator_table()


def _canonical(value: typing.Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _only_chars(value: str, allowed: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] not in allowed:
            return False
        index += 1
    return True


def _carries_forbidden(text: str) -> bool:
    words = text.translate(ASCII_LOWER).translate(SEPARATORS).split()
    index = 0
    while index < len(words):
        if words[index] in FORBIDDEN_WORDS:
            return True
        index += 1
    return False


def _refuse_forbidden(texts: list) -> None:
    """FORBIDDEN_SIGNAL if any text input carries a forbidden word."""
    checked = {}
    index = 0
    while index < len(texts):
        text = texts[index]
        if isinstance(text, str) and text not in checked:
            checked[text] = True
            if _carries_forbidden(text):
                raise gl.vm.UserError(ERR_FORBIDDEN_SIGNAL)
        index += 1


def _hex64(value: typing.Any, error: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(error)
    candidate = value.strip().translate(ASCII_LOWER)
    if len(candidate) != 64:
        raise gl.vm.UserError(error)
    try:
        raw = bytes.fromhex(candidate)
    except ValueError:
        raise gl.vm.UserError(error)
    if len(raw) != 32:
        raise gl.vm.UserError(error)
    return candidate


def _is_role_key(value: typing.Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) < ROLE_KEY_MIN or len(value) > ROLE_KEY_MAX:
        return False
    if value[0] not in LOWER_CHARS or value[len(value) - 1] == "_" or "__" in value:
        return False
    return _only_chars(value, ROLE_CHARS)


def _role_key(value: typing.Any) -> str:
    if not _is_role_key(value):
        raise gl.vm.UserError(ERR_BAD_ROLE_KEY)
    return value


def _level_word(value: typing.Any) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(ERR_BAD_EVIDENCE_LEVEL)
    word = value.strip().translate(ASCII_UPPER)
    if word == "" or len(word) > WORD_MAX or not _only_chars(word, WORD_CHARS):
        raise gl.vm.UserError(ERR_BAD_EVIDENCE_LEVEL)
    return word


def _milestone_name(value: typing.Any) -> str:
    """The upper-case milestone name, or "" when the text is not a well-formed name."""
    if not isinstance(value, str):
        return ""
    name = value.strip().translate(ASCII_UPPER)
    if name == "" or len(name) > WORD_MAX or name[0] not in UPPER_CHARS:
        return ""
    if not _only_chars(name, WORD_CHARS):
        return ""
    return name


def _is_text_list(value: typing.Any) -> bool:
    index = 0
    while index < len(value):
        if not isinstance(value[index], str):
            return False
        index += 1
    return True


def _check_lists(hashes: typing.Any, levels: typing.Any, roles: typing.Any) -> None:
    sequence = (list, tuple)
    if not isinstance(hashes, sequence) or not isinstance(levels, sequence) or not isinstance(roles, sequence):
        raise gl.vm.UserError(ERR_BAD_WORK_RECORDS)
    if len(hashes) > MAX_RECORDS or len(levels) > MAX_RECORDS or len(roles) > MAX_RECORDS:
        raise gl.vm.UserError(ERR_TOO_MANY_RECORDS)
    if len(levels) != len(hashes) or len(roles) != len(hashes):
        raise gl.vm.UserError(ERR_BAD_WORK_RECORDS)
    if not _is_text_list(hashes) or not _is_text_list(levels) or not _is_text_list(roles):
        raise gl.vm.UserError(ERR_BAD_WORK_RECORDS)


def _records(hashes: list, levels: list, roles: list) -> list:
    """Normalised [hash, level, role] records; refuses malformed items and repeated hashes."""
    seen = {}
    level_words = {}
    good_roles = {}
    out = []
    index = 0
    while index < len(hashes):
        work_hash = _hex64(hashes[index], ERR_BAD_WORK_HASH)
        raw_level = levels[index]
        if raw_level in level_words:
            level = level_words[raw_level]
        else:
            level = _level_word(raw_level)
            level_words[raw_level] = level
        role = roles[index]
        if role not in good_roles:
            good_roles[_role_key(role)] = True
        if work_hash in seen:
            raise gl.vm.UserError(ERR_DUPLICATE_WORK_HASH)
        seen[work_hash] = True
        out.append([work_hash, level, role])
        index += 1
    return out


def _tally(records: list, role: str) -> dict:
    counted = 0
    not_counted_level = 0
    not_counted_role = 0
    index = 0
    while index < len(records):
        record = records[index]
        if record[1] not in COUNTING_LEVELS:
            not_counted_level += 1
        elif record[2] != role:
            not_counted_role += 1
        else:
            counted += 1
        index += 1
    return {"counted": counted, "not_counted_level": not_counted_level, "not_counted_role": not_counted_role}


def _confirmation_key(entrant: str, role: str, milestone: str) -> str:
    return entrant + "|" + role + "|" + milestone


class VerifiedWorkMilestone(gl.Contract):
    owner: Address
    milestone_counts: TreeMap[str, u256]
    milestone_names: DynArray[str]
    confirmations: TreeMap[str, str]
    claims: DynArray[str]

    def __init__(self):
        self.owner = gl.message.sender_address
        index = 0
        while index < len(SEED_MILESTONES):
            seed = SEED_MILESTONES[index]
            self.milestone_counts[seed[0]] = seed[1]
            self.milestone_names.append(seed[0])
            index += 1

    def _only_owner(self) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(ERR_NOT_OWNER)

    def _known_milestone(self, value: typing.Any) -> str:
        name = _milestone_name(value)
        if name == "" or name not in self.milestone_counts:
            raise gl.vm.UserError(ERR_UNKNOWN_MILESTONE)
        return name

    def _lookup_key(self, entrant_id: typing.Any, role_key: typing.Any, milestone: typing.Any) -> str:
        entrant = _hex64(entrant_id, ERR_BAD_ENTRANT_ID)
        role = _role_key(role_key)
        name = self._known_milestone(milestone)
        return _confirmation_key(entrant, role, name)

    @gl.public.write
    def claim_milestone(self, entrant_id: str, role_key: str, milestone: str, work_hashes: list[str],
                        evidence_levels: list[str], work_roles: list[str]) -> typing.Any:
        self._only_owner()
        _check_lists(work_hashes, evidence_levels, work_roles)
        _refuse_forbidden([entrant_id, role_key, milestone] + list(work_hashes) + list(evidence_levels)
                          + list(work_roles))
        entrant = _hex64(entrant_id, ERR_BAD_ENTRANT_ID)
        role = _role_key(role_key)
        name = self._known_milestone(milestone)
        key = _confirmation_key(entrant, role, name)
        if key in self.confirmations:
            raise gl.vm.UserError(ERR_ALREADY_CONFIRMED)
        records = _records(work_hashes, evidence_levels, work_roles)
        required = int(self.milestone_counts[name])
        tally = _tally(records, role)
        counted = tally["counted"]
        if counted >= required:
            verdict = VERDICT_REACHED
            shortfall = 0
        else:
            verdict = VERDICT_NOT_REACHED
            shortfall = required - counted
        reason = (
            str(counted) + " of " + str(required) + " required work records counted for role " + role
            + " (" + str(tally["not_counted_level"]) + " not attested or SnapLink-verified, "
            + str(tally["not_counted_role"]) + " in another role)"
        )
        result = {
            "claim_index": len(self.claims),
            "entrant_id": entrant,
            "role_key": role,
            "milestone": name,
            "verdict": verdict,
            "required": required,
            "counted": counted,
            "shortfall": shortfall,
            "records": len(records),
            "not_counted_level": tally["not_counted_level"],
            "not_counted_role": tally["not_counted_role"],
            "reason": reason,
        }
        stored = _canonical(result)
        self.claims.append(stored)
        if verdict == VERDICT_REACHED:
            self.confirmations[key] = stored
        return result

    @gl.public.write
    def add_milestone(self, name: str, count: int) -> typing.Any:
        self._only_owner()
        _refuse_forbidden([name])
        milestone = _milestone_name(name)
        if milestone == "":
            raise gl.vm.UserError(ERR_BAD_MILESTONE_NAME)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > MAX_RECORDS:
            raise gl.vm.UserError(ERR_BAD_MILESTONE_COUNT)
        if milestone in self.milestone_counts:
            raise gl.vm.UserError(ERR_MILESTONE_EXISTS)
        self.milestone_counts[milestone] = count
        self.milestone_names.append(milestone)
        return {"milestone": milestone, "count": count}

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner.as_hex

    @gl.public.view
    def get_rules(self) -> str:
        return _canonical({
            "counting_levels": list(COUNTING_LEVELS),
            "forbidden_words": list(FORBIDDEN_LIST),
            "max_records": MAX_RECORDS,
            "role_key": "lowercase snake_case, 2 to 48 characters; shape only, the role list is not on chain",
        })

    @gl.public.view
    def get_catalogue(self) -> str:
        out = []
        index = 0
        while index < len(self.milestone_names):
            name = self.milestone_names[index]
            out.append({"milestone": name, "count": int(self.milestone_counts[name])})
            index += 1
        return _canonical(out)

    @gl.public.view
    def get_milestone(self, name: str) -> int:
        return int(self.milestone_counts[self._known_milestone(name)])

    @gl.public.view
    def is_confirmed(self, entrant_id: str, role_key: str, milestone: str) -> bool:
        return self._lookup_key(entrant_id, role_key, milestone) in self.confirmations

    @gl.public.view
    def get_confirmation(self, entrant_id: str, role_key: str, milestone: str) -> str:
        key = self._lookup_key(entrant_id, role_key, milestone)
        if key not in self.confirmations:
            raise gl.vm.UserError(ERR_NOT_CONFIRMED)
        return self.confirmations[key]

    @gl.public.view
    def get_claim_count(self) -> int:
        return len(self.claims)

    @gl.public.view
    def get_claim(self, index: int) -> str:
        if not isinstance(index, int) or index < 0 or index >= len(self.claims):
            raise gl.vm.UserError(ERR_BAD_INDEX)
        return self.claims[index]
