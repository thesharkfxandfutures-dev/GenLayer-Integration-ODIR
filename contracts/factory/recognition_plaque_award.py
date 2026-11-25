# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

"""Recognition Plaque Award -- GenLayer Intelligent Contract (contract factory draft).

Percentage plaques (Top 1%, 3%, 5%, 10%): does the band hold by the entrant's
actual rank divided by the eligible entrants (decided by rank, never by a
rounded percentage), with each person counted once? One universal award
contract for every SnapLink role: the role key is an input.

Constructor: RecognitionPlaqueAward() takes no arguments. The deploying
address becomes the issuer, the only sender that may record a verdict
(SnapLink's own account). It grants nothing else and cannot be changed.

Calldata and storage are public. Send only public data: hashes, public codes
and public text. Never names, emails or private evidence.

Write method:
  decide_band(entrant_id, role_key, scope, area_code, season, ranking_basis,
              rank, eligible_entrants, band, snapshot_sha256)
    entrant_id         public hash of the entrant, 64 hex characters (never a
                       name or email)
    role_key           a SnapLink role key: lowercase snake_case, 2..48
                       characters, starting with a letter. Shape only: the
                       list of 45 role keys is not checked on chain.
    scope, area_code,  public codes, 1..32 characters of letters, digits,
    season             '-', '_' or '.', stored and compared in lowercase
    ranking_basis      public text naming what the rank counts, 1..200
                       printable ASCII characters
    rank               the entrant's rank in the cohort, 1..eligible_entrants
    eligible_entrants  the cohort size with each person counted once, at least
                       MIN_ELIGIBLE_ENTRANTS (100) and at most 1000000000
    band               TOP_1, TOP_3, TOP_5 or TOP_10 (case-insensitive)
    snapshot_sha256    sha256 hex of the ranking snapshot the rank comes from
  Returns {"verdict", "band", "actual_percentage", "rank",
  "eligible_entrants", "reason"}. verdict is BAND_CONFIRMED when
  rank * 100 <= band_percent * eligible_entrants in integers, else
  NOT_ELIGIBLE. actual_percentage is informational and never decides:
  rank * 100 / eligible_entrants as a decimal string rounded UP to 4 places,
  so it can never read inside a band that does not hold. reason states the
  integer comparison.
  One verdict per entrant, role, area (scope + area_code) and season,
  whatever the band. The first verdict in a role / area / season cohort pins
  its snapshot_sha256 and eligible_entrants for every later verdict there.

View methods:
  get_verdict(entrant_id, role_key, scope, area_code, season)  JSON text
  get_cohort(role_key, scope, area_code, season)               JSON text
  get_verdict_count() / get_verdict_key(i)
  get_rules()  bands, cohort limits, forbidden terms and issuer as JSON text

Refusals (gl.vm.UserError, exact text in the ERR_* constants below):
  BAD_BAND for a band outside the four; COHORT_TOO_SMALL for a cohort below
  the minimum; ALREADY_DECIDED for a second verdict for the same entrant, role,
  area and season; FORBIDDEN_SIGNAL when any text input (role_key, scope,
  area_code, season, ranking_basis) names likes, followers, votes, a paid plan,
  subscription, premium or membership tier, or boosts (case-insensitive whole
  words); BAD_ROLE_KEY; COHORT_MISMATCH; NOT_ISSUER; BAD_ENTRANT_ID,
  BAD_SNAPSHOT_HASH, BAD_SCOPE, BAD_AREA_CODE, BAD_SEASON, BAD_RANKING_BASIS,
  BAD_ENTRANTS, BAD_RANK; UNKNOWN_VERDICT, UNKNOWN_COHORT and BAD_INDEX for the
  views. A refused call writes nothing.

Consensus: none needed. The decision is integer arithmetic and string checks,
identical on every validator; no web or LLM call is made.

Limits: the contract trusts the issuer's rank, cohort size and snapshot hash.
It cannot see the snapshot, check that each person is counted once inside it,
or check that the ranking really ignores paid plans. It checks the arithmetic
and the rules above and records what was asserted. A verdict grants nothing
until SnapLink's own checks accept it.
Not deployed or run on GenVM by the factory; the owner deploys and signs.
"""

import json
import typing

VERDICT_CONFIRMED = "BAND_CONFIRMED"
VERDICT_NOT_ELIGIBLE = "NOT_ELIGIBLE"
BAND_NAMES = ["TOP_1", "TOP_3", "TOP_5", "TOP_10"]
BAND_PERCENTS = [1, 3, 5, 10]
MIN_ELIGIBLE_ENTRANTS = 100
MAX_ELIGIBLE_ENTRANTS = 1000000000
PERCENT_PLACES = 4
ROLE_KEY_MIN = 2
ROLE_KEY_MAX = 48
CODE_LIMIT = 32
BASIS_LIMIT = 200
KEY_SEPARATOR = "|"

HEX_DIGITS = "0123456789abcdef"
DIGITS = "0123456789"
LOWER_LETTERS = "abcdefghijklmnopqrstuvwxyz"
WORD_CHARS = LOWER_LETTERS + DIGITS
ROLE_CHARS = LOWER_LETTERS + DIGITS + "_"
CODE_CHARS = LOWER_LETTERS + DIGITS + "-_."
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")

FORBIDDEN_WORDS = [
    "likes", "liked",
    "follower", "followers",
    "vote", "votes", "voted", "voting", "voter", "voters", "upvote", "upvotes", "upvoted",
    "subscription", "subscriptions", "subscriber", "subscribers", "premium",
    "boost", "boosts", "boosted", "boosting",
]
FORBIDDEN_PHRASES = [
    "like count", "like counts",
    "paid plan", "paid plans", "paid tier", "paid tiers", "paid member", "paid members",
    "paid membership", "paid memberships",
    "membership tier", "membership tiers", "membership plan", "membership plans",
]

ERR_NOT_ISSUER = "[EXPECTED] NOT_ISSUER: only the issuer that deployed this contract can record a verdict"
ERR_BAD_ENTRANT_ID = "[EXPECTED] BAD_ENTRANT_ID: entrant_id must be a public hash of 64 hexadecimal characters, never a name"
ERR_BAD_SNAPSHOT_HASH = "[EXPECTED] BAD_SNAPSHOT_HASH: snapshot_sha256 must be 64 hexadecimal characters"
ERR_BAD_ROLE_KEY = ("[EXPECTED] BAD_ROLE_KEY: role_key must be lowercase snake_case of 2 to 48 characters "
                    "(a-z, 0-9, single '_' between words), starting with a letter")
ERR_BAD_SCOPE = "[EXPECTED] BAD_SCOPE: scope must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_AREA_CODE = "[EXPECTED] BAD_AREA_CODE: area_code must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_SEASON = "[EXPECTED] BAD_SEASON: season must be 1 to 32 characters of letters, digits, '-', '_' or '.'"
ERR_BAD_RANKING_BASIS = "[EXPECTED] BAD_RANKING_BASIS: ranking_basis must be 1 to 200 printable ASCII characters of public text"
ERR_FORBIDDEN_SIGNAL = ("[EXPECTED] FORBIDDEN_SIGNAL: likes, followers, votes, a paid plan or a boost "
                        "must never select an award")
ERR_BAD_BAND = "[EXPECTED] BAD_BAND: band must be TOP_1, TOP_3, TOP_5 or TOP_10"
ERR_BAD_ENTRANTS = "[EXPECTED] BAD_ENTRANTS: eligible_entrants must be a whole number of at most 1000000000"
ERR_COHORT_TOO_SMALL = "[EXPECTED] COHORT_TOO_SMALL: eligible_entrants must be at least " + str(MIN_ELIGIBLE_ENTRANTS)
ERR_BAD_RANK = "[EXPECTED] BAD_RANK: rank must be a whole number from 1 to eligible_entrants"
ERR_ALREADY_DECIDED = "[EXPECTED] ALREADY_DECIDED: this entrant already has a verdict for this role, area and season"
ERR_COHORT_MISMATCH = ("[EXPECTED] COHORT_MISMATCH: this role, area and season is pinned to another "
                       "snapshot_sha256 or eligible_entrants")
ERR_UNKNOWN_VERDICT = "[EXPECTED] UNKNOWN_VERDICT: no verdict is stored for this entrant, role, area and season"
ERR_UNKNOWN_COHORT = "[EXPECTED] UNKNOWN_COHORT: no cohort is stored for this role, area and season"
ERR_BAD_INDEX = "[EXPECTED] BAD_INDEX: no verdict at this index"


def _canonical(value: typing.Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _lower(text: str) -> str:
    return text.translate(ASCII_LOWER)


def _upper(text: str) -> str:
    return text.translate(ASCII_UPPER)


def _only_chars(value: str, allowed: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] not in allowed:
            return False
        index += 1
    return True


def _has_any_char(value: str, wanted: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] in wanted:
            return True
        index += 1
    return False


def _normal_hex(value: typing.Any, error: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(error)
    candidate = _lower(value.strip())
    if len(candidate) != 64 or not _only_chars(candidate, HEX_DIGITS):
        raise gl.vm.UserError(error)
    return candidate


def _check_role_key(value: typing.Any) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(ERR_BAD_ROLE_KEY)
    role = value.strip()
    if len(role) < ROLE_KEY_MIN or len(role) > ROLE_KEY_MAX:
        raise gl.vm.UserError(ERR_BAD_ROLE_KEY)
    if not _only_chars(role, ROLE_CHARS) or role[0] not in LOWER_LETTERS:
        raise gl.vm.UserError(ERR_BAD_ROLE_KEY)
    if role[len(role) - 1] == "_" or "__" in role:
        raise gl.vm.UserError(ERR_BAD_ROLE_KEY)
    return role


def _check_code(value: typing.Any, error: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(error)
    code = _lower(value.strip())
    if len(code) < 1 or len(code) > CODE_LIMIT:
        raise gl.vm.UserError(error)
    if not _only_chars(code, CODE_CHARS) or not _has_any_char(code, WORD_CHARS):
        raise gl.vm.UserError(error)
    return code


def _check_basis(value: typing.Any) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError(ERR_BAD_RANKING_BASIS)
    basis = value.strip()
    if len(basis) < 1 or len(basis) > BASIS_LIMIT:
        raise gl.vm.UserError(ERR_BAD_RANKING_BASIS)
    index = 0
    while index < len(basis):
        code_point = ord(basis[index])
        if code_point < 32 or code_point > 126:
            raise gl.vm.UserError(ERR_BAD_RANKING_BASIS)
        index += 1
    return basis


def _words(text: str) -> list:
    """Lowercase runs of ASCII letters and digits; everything else separates words."""
    lower = _lower(text)
    out = []
    current = ""
    index = 0
    while index < len(lower):
        char = lower[index]
        if char in WORD_CHARS:
            current = current + char
        elif current != "":
            out.append(current)
            current = ""
        index += 1
    if current != "":
        out.append(current)
    return out


def _carries_forbidden_signal(text: str) -> bool:
    words = _words(text)
    index = 0
    while index < len(words):
        if words[index] in FORBIDDEN_WORDS:
            return True
        if index + 1 < len(words) and (words[index] + " " + words[index + 1]) in FORBIDDEN_PHRASES:
            return True
        index += 1
    return False


def _refuse_forbidden_signal(texts: list) -> None:
    index = 0
    while index < len(texts):
        if _carries_forbidden_signal(texts[index]):
            raise gl.vm.UserError(ERR_FORBIDDEN_SIGNAL)
        index += 1


def _check_band(value: typing.Any) -> typing.Any:
    if not isinstance(value, str):
        raise gl.vm.UserError(ERR_BAD_BAND)
    name = _upper(value.strip())
    index = 0
    while index < len(BAND_NAMES):
        if name == BAND_NAMES[index]:
            return [name, BAND_PERCENTS[index]]
        index += 1
    raise gl.vm.UserError(ERR_BAD_BAND)


def _is_whole_number(value: typing.Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_entrants(value: typing.Any) -> int:
    if not _is_whole_number(value) or value > MAX_ELIGIBLE_ENTRANTS:
        raise gl.vm.UserError(ERR_BAD_ENTRANTS)
    if value < MIN_ELIGIBLE_ENTRANTS:
        raise gl.vm.UserError(ERR_COHORT_TOO_SMALL)
    return value


def _check_rank(value: typing.Any, entrants: int) -> int:
    if not _is_whole_number(value) or value < 1 or value > entrants:
        raise gl.vm.UserError(ERR_BAD_RANK)
    return value


def _percentage(rank: int, entrants: int) -> str:
    """rank * 100 / entrants as a decimal string, rounded UP to PERCENT_PLACES places."""
    scale = 10 ** PERCENT_PLACES
    scaled = (rank * 100 * scale + entrants - 1) // entrants
    fraction = str(scaled % scale)
    while len(fraction) < PERCENT_PLACES:
        fraction = "0" + fraction
    return str(scaled // scale) + "." + fraction


def _reason(rank: int, entrants: int, band: str, percent: int, holds: bool) -> str:
    left = rank * 100
    right = percent * entrants
    text = ("rank " + str(rank) + " of " + str(entrants) + ": " + str(rank) + " x 100 = " + str(left))
    if holds:
        return text + " <= " + str(percent) + " x " + str(entrants) + " = " + str(right) + ", so " + band + " holds"
    return text + " > " + str(percent) + " x " + str(entrants) + " = " + str(right) + ", so " + band + " does not hold"


def _join(parts: list) -> str:
    out = ""
    index = 0
    while index < len(parts):
        if index > 0:
            out = out + KEY_SEPARATOR
        out = out + parts[index]
        index += 1
    return out


def _verdict_key(entrant_id: typing.Any, role_key: typing.Any, scope: typing.Any, area_code: typing.Any,
                 season: typing.Any) -> str:
    return _join([
        _normal_hex(entrant_id, ERR_BAD_ENTRANT_ID),
        _check_role_key(role_key),
        _check_code(scope, ERR_BAD_SCOPE),
        _check_code(area_code, ERR_BAD_AREA_CODE),
        _check_code(season, ERR_BAD_SEASON),
    ])


def _cohort_key(role_key: typing.Any, scope: typing.Any, area_code: typing.Any, season: typing.Any) -> str:
    return _join([
        _check_role_key(role_key),
        _check_code(scope, ERR_BAD_SCOPE),
        _check_code(area_code, ERR_BAD_AREA_CODE),
        _check_code(season, ERR_BAD_SEASON),
    ])


class RecognitionPlaqueAward(gl.Contract):
    issuer: Address
    verdicts: TreeMap[str, str]
    verdict_keys: DynArray[str]
    cohorts: TreeMap[str, str]

    def __init__(self):
        self.issuer = gl.message.sender_address

    @gl.public.write
    def decide_band(self, entrant_id: str, role_key: str, scope: str, area_code: str, season: str,
                    ranking_basis: str, rank: int, eligible_entrants: int, band: str,
                    snapshot_sha256: str) -> typing.Any:
        sender = _lower(gl.message.sender_address.as_hex)
        if sender != _lower(self.issuer.as_hex):
            raise gl.vm.UserError(ERR_NOT_ISSUER)
        entrant = _normal_hex(entrant_id, ERR_BAD_ENTRANT_ID)
        role = _check_role_key(role_key)
        scope_code = _check_code(scope, ERR_BAD_SCOPE)
        area = _check_code(area_code, ERR_BAD_AREA_CODE)
        season_code = _check_code(season, ERR_BAD_SEASON)
        basis = _check_basis(ranking_basis)
        snapshot = _normal_hex(snapshot_sha256, ERR_BAD_SNAPSHOT_HASH)
        _refuse_forbidden_signal([role, scope_code, area, season_code, basis])
        band_choice = _check_band(band)
        band_name = band_choice[0]
        percent = band_choice[1]
        entrants = _check_entrants(eligible_entrants)
        position = _check_rank(rank, entrants)

        key = _join([entrant, role, scope_code, area, season_code])
        if key in self.verdicts:
            raise gl.vm.UserError(ERR_ALREADY_DECIDED)
        cohort_key = _join([role, scope_code, area, season_code])
        if cohort_key in self.cohorts:
            cohort = json.loads(self.cohorts[cohort_key])
            if cohort["snapshot_sha256"] != snapshot or cohort["eligible_entrants"] != entrants:
                raise gl.vm.UserError(ERR_COHORT_MISMATCH)
        else:
            cohort = {
                "role_key": role,
                "scope": scope_code,
                "area_code": area,
                "season": season_code,
                "snapshot_sha256": snapshot,
                "eligible_entrants": entrants,
                "verdicts": 0,
            }

        holds = position * 100 <= percent * entrants
        verdict = VERDICT_NOT_ELIGIBLE
        if holds:
            verdict = VERDICT_CONFIRMED
        percentage = _percentage(position, entrants)
        reason = _reason(position, entrants, band_name, percent, holds)
        record = {
            "entrant_id": entrant,
            "role_key": role,
            "scope": scope_code,
            "area_code": area,
            "season": season_code,
            "ranking_basis": basis,
            "rank": position,
            "eligible_entrants": entrants,
            "band": band_name,
            "band_percent": percent,
            "verdict": verdict,
            "actual_percentage": percentage,
            "reason": reason,
            "snapshot_sha256": snapshot,
            "issued_by": sender,
        }
        cohort["verdicts"] = cohort["verdicts"] + 1
        self.verdicts[key] = _canonical(record)
        self.verdict_keys.append(key)
        self.cohorts[cohort_key] = _canonical(cohort)
        return {
            "verdict": verdict,
            "band": band_name,
            "actual_percentage": percentage,
            "rank": position,
            "eligible_entrants": entrants,
            "reason": reason,
        }

    @gl.public.view
    def get_verdict(self, entrant_id: str, role_key: str, scope: str, area_code: str, season: str) -> str:
        key = _verdict_key(entrant_id, role_key, scope, area_code, season)
        if key not in self.verdicts:
            raise gl.vm.UserError(ERR_UNKNOWN_VERDICT)
        return self.verdicts[key]

    @gl.public.view
    def get_cohort(self, role_key: str, scope: str, area_code: str, season: str) -> str:
        key = _cohort_key(role_key, scope, area_code, season)
        if key not in self.cohorts:
            raise gl.vm.UserError(ERR_UNKNOWN_COHORT)
        return self.cohorts[key]

    @gl.public.view
    def get_verdict_count(self) -> int:
        return len(self.verdict_keys)

    @gl.public.view
    def get_verdict_key(self, index: int) -> str:
        if index < 0 or index >= len(self.verdict_keys):
            raise gl.vm.UserError(ERR_BAD_INDEX)
        return self.verdict_keys[index]

    @gl.public.view
    def get_rules(self) -> str:
        bands = {}
        index = 0
        while index < len(BAND_NAMES):
            bands[BAND_NAMES[index]] = BAND_PERCENTS[index]
            index += 1
        return _canonical({
            "bands": bands,
            "min_eligible_entrants": MIN_ELIGIBLE_ENTRANTS,
            "max_eligible_entrants": MAX_ELIGIBLE_ENTRANTS,
            "percentage_places": PERCENT_PLACES,
            "forbidden_words": FORBIDDEN_WORDS,
            "forbidden_phrases": FORBIDDEN_PHRASES,
            "issuer": _lower(self.issuer.as_hex),
        })
