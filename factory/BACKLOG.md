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

## 15. editorial_usage_check — `drafted (PR #17)`

Role contract (owner's page "Role contracts (one per role)", row 15; the role is Fashion Model, role key
`model_fashion`, fixed by the contract, not an input). A review contract for the dispute this role meets most:
did what happened match what was agreed?

Is a published use editorial, as agreed, or advertising that needs a new fee?

- **Inputs:** the agreed terms (the booking's terms, including its usage terms; text both parties agree to make
  public), what happened (the published use: a placement description and/or public URLs, as text) and
  `evidence_sha256` of that account; plus a public `case_id`, added only so that "the same case twice" can be
  refused (public data only).
- **Decision:** `EDITORIAL` or `COMMERCIAL_USE`, with the placement quoted from the published use (for both
  words). Comparative equivalence on the verdict word.
- **Must refuse:** usage terms missing from the booking (the row's own); an evidence hash that does not match;
  the same case twice; empty terms (the table's shared refusals).
- **Role-contract rules (rows 13-57):** one review contract per role; the three shared inputs; the shared
  refusals each with exact text and their own test; the answer words are exactly the row's; built on the
  row-13 template (shared helpers and runner, then the row's own check and prompt).
