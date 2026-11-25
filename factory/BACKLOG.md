# Contract factory backlog

The queue the factory works through, top to bottom: one contract per run, the first `todo` item.
Each is a real job for a judgment layer (an evidence-bound decision that ordinary code cannot
make), so every contract is worth deploying and worth a steward's time. Add, reorder or remove
items freely; the factory only ever reads this file and flips an item's status.

Statuses: `todo` → `drafted (PR #n)` (factory) → `deployed <network> <address>` (owner, by hand)
→ `submitted` (owner, Points Portal). Only the owner writes the last two.

---

## 1. work_evidence_review — `todo`

Decide whether a piece of completed creative work meets its brief.

- **Inputs:** brief (public text), delivery description (public text), `evidence_sha256` of the
  private evidence kept off-chain.
- **Decision:** `MEETS_REQUIREMENTS` or `DOES_NOT_MEET_REQUIREMENTS`, with one quoted reason from
  the delivery text. Comparative equivalence on the verdict word.
- **Must refuse:** a hash that does not match the supplied evidence text; the same case twice
  (`DUPLICATE_SUBMISSION`); an empty brief.

## 2. listing_compliance_check — `todo`

Check a marketplace listing against a published rulebook before it goes live.

- **Inputs:** listing title, description and category; the rulebook version and text (public).
- **Decision:** `COMPLIANT` or `HOLD`, naming the rule that holds it. Lawful for a UK shop, no
  prohibited category (adult content, drugs, offensive memorabilia), no fraud signals in the text.
- **Must refuse:** an unknown rulebook version; a listing longer than the stated limit; a second
  verdict on the same listing hash.

## 3. credit_claim_verdict — `todo`

Confirm that a creator is the person credited on a piece of media.

- **Inputs:** media hash, the credited handle, the creator's confirmation, a public post URL.
- **Decision:** `VERIFIED` only when the creator has confirmed **and** the public post names the
  credited handle; otherwise `NOT_VERIFIED` with the missing condition.
- **Must refuse:** a confirmation from an address other than the creator's; a claim on a media
  hash already verified for someone else.

## 4. conduct_reason_review — `todo`

Judge whether a late cancellation or no-show reason justifies a trust penalty.

- **Inputs:** the booking terms (public), the stated reason, an evidence summary and its hash.
- **Decision:** `PENALTY_JUSTIFIED` or `PENALTY_NOT_JUSTIFIED`, and a severity band
  (`MINOR` / `STANDARD` / `SEVERE`) with the clause relied on.
- **Must refuse:** a reason submitted after the case is closed; a severity outside the bands.

## 5. photo_claim_adjudication — `todo`

Two parties claim one photograph; decide whose claim the public evidence supports.

- **Inputs:** each party's statement, first-publication URL and date, and an evidence hash.
- **Decision:** `CLAIMANT_A`, `CLAIMANT_B` or `UNDECIDED` (insufficient evidence is a valid
  answer), with the deciding fact quoted.
- **Must refuse:** a third claimant; a statement edited after both are in; a decision request
  before both statements exist.

## 7. champion_seat_award — `drafted (PR #9)`

Award contract (owner's page row 7; replaces the earlier `league_placement_review` proposal and covers
the same World #1 case and every other seat). Champion trophies and places: World (SnapLink Trophy for
seat 1, World Plaque for seats 2–10), Continental Plaque (seats 1–10), National Cup (seats 1–11), County
Shield (seat 1).

Does this entrant's seat hold under the published allocation rules: only work in the named role counted,
one seat per winner (highest wins), published tie-breaks, county minimum of 3 credited jobs?

- **Inputs:** role key, scope + area code, season year, seat number, standings snapshot hash, allocation
  rules version + text, the entrant's evidence summary + hash (public data only).
- **Decision:** `CONFIRMED` or `NOT_CONFIRMED`, with the rule relied on quoted from the allocation rules
  text. Comparative equivalence on the verdict word.
- **Must refuse:** an unknown rules version; a season not finished; a second verdict for the same role,
  area, season and seat.
- **Award-contract rules (rows 7–12):** one universal contract for all roles (role key is an input, shape
  checked only); refuse inputs that rely on a forbidden selection signal (likes, followers, votes, paid
  plan / subscription / premium / membership tier, boost) with `FORBIDDEN_SIGNAL`, because paid
  membership must never improve anyone's chance of an award; scope and seat checked against the places
  above.
