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

## 11. annual_award_decision — `drafted (PR #13)`

Award contract (owner's page, award table row 11). The annual awards: Photographer, Designer and Filmmaker of the
Year; Emerging Talent; Creative Business and Studio of the Year (award codes `PHOTOGRAPHER_OF_THE_YEAR`,
`DESIGNER_OF_THE_YEAR`, `FILMMAKER_OF_THE_YEAR`, `EMERGING_TALENT`, `CREATIVE_BUSINESS_OF_THE_YEAR`,
`STUDIO_OF_THE_YEAR`).

Which finalist best meets the published criteria, or does nobody meet them?

- **Inputs:** role key, award code, season, the published criteria text, and each finalist's public id, public
  evidence summary and evidence hash (public data only).
- **Decision:** `WINNER` + finalist id, or `NO_AWARD`, with the criterion relied on quoted from the criteria text.
  Comparative equivalence: validators agree on `WINNER` with the same finalist id, or on `NO_AWARD`.
- **Must refuse:** fewer than two finalists; a decision before the season reaches finalists; a second decision for
  the same award and season.
- **Award-contract rules (rows 7–12):** one universal contract for all roles (role key is an input, shape checked
  only); refuse inputs that rely on a forbidden selection signal (likes, followers, votes, paid plan / subscription /
  premium / membership tier, boost) with `FORBIDDEN_SIGNAL`, because paid membership must never improve anyone's
  chance of an award.
