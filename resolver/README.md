# Role-contract templates and resolver (slice A3)

Drafts for review, **not legal advice**. A UK solicitor reviews the bases before any real member signs.

## The model

A SnapLink agreement is assembled, not written per role: one **base** (P2P, P2B, B2P, B2B, STAFF) +
the **engager's** role module + the **provider's** role module + the parties' own **overrides**, a
**jurisdiction** (England and Wales, Scotland, Northern Ireland) and, for a person booking for
themselves, the **consumer** variant. Every clause belongs to one of 13 categories
(`src/categories.js`), and each category is drawn under one of the parchment viewer's 7 sections.

| File | What it is | Schema |
|---|---|---|
| `templates/bases/<base>.json` | the shared clauses of one base, all 13 categories | `schema/base-template.v1.json` |
| `templates/roles/<role_key>/module.json` | what a role adds as engager and as provider | `schema/role-template.v1.json` |
| resolver output | the resolved document | `schema/agreement.v1.json` |

## Rules the resolver enforces

- **Merge order** base < engager < provider < overrides. A later layer adds clauses, or replaces an
  earlier clause in place by naming it in `replaces`; ids are prefixed per layer (`p2p.`,
  `photographer.provider.`, `o.`), so nothing is overwritten by accident. Every replacement carries
  `replaces: { id, source }`. A `locked` clause (statutory and record clauses) cannot be replaced.
- **Conditions** `when: { consumer, bases, jurisdictions }` pick the variant. A consumer engager has
  no role module (they book for themselves); only bases whose engager is a person have a consumer
  variant.
- **Blanks** `{{field_key}}` stay in template mode; in agreement mode they are filled in one pass from
  the parties' values or the field's default (a value can never introduce another blank). Terms
  `[[engager]] [[Engager]] [[provider]] [[Provider]] [[jurisdiction]] [[courts]]` are filled by the
  resolver.
- **Hashes** are sha256 of the adapter's canonical encoding (`adapter/src/canon.js`, the same bytes as
  CPython `json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True)`), written
  `sha256:<hex>`. A template's hash and the document's `terms_hash` leave out every `style` block, so
  paper, ink and emphasis can change; one changed word changes the hash.
- **STALE**: a module records the base versions it was drafted against; a different base version
  marks it stale, and `render-all` fails.

## Commands

```bash
cd resolver
npm test                                   # unit, golden and CLI tests
node bin/render-all.mjs [--out dir]        # check every template, render every role x base pair
node bin/check-role-commits.mjs --base <rev> [--head <rev>]   # a role commit touches only its own folder
UPDATE_GOLDEN=1 npm test                   # accept an intended wording change; commit the golden diff with it
```
