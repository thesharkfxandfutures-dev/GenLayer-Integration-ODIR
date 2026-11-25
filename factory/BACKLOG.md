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

## 9. verified_work_milestone — `drafted (PR pending)`

Award contract (owner's page row 9): Verified Work trophies, Foundation (25) to Zenith (10,000).
Decide whether every counted piece of work is attested or SnapLink-verified, done in the named role
and counted once, so that the milestone is reached. Deterministic counting (no LLM).

- **Inputs:** role key, milestone, list of work-record hashes with evidence level and role (three
  parallel lists), plus `entrant_id` (a public 64-hex hash, never a name). Public data only.
- **Decision:** `MILESTONE_REACHED` or `NOT_REACHED` with the shortfall (count − counted). A record counts
  only if its level is `ATTESTED` or `SNAPLINK_VERIFIED` and its role equals the role key.
- **Must refuse:** a milestone not in the catalogue (`UNKNOWN_MILESTONE`); the same work hash twice in one
  claim (`DUPLICATE_WORK_HASH`); a milestone already confirmed for this entrant and role
  (`ALREADY_CONFIRMED`).
- **Award rules (rows 7–12):** serves all 45 roles with the role key as an input (shape checked only:
  `BAD_ROLE_KEY`); refuses any input carrying a forbidden selection signal — likes, followers, votes,
  paid plan or boost (`FORBIDDEN_SIGNAL`) — because paid membership must never improve anyone's chance
  of an award.
- Record: `factory/records/2026-11-25-verified_work_milestone.md` (open questions: missing levels
  between Foundation and Zenith, owner-only claims, ~1 MB calldata for a full Zenith claim).
