# Brain queue

The owner edits this file on `main`. The Brain reads it every run and keeps no state of its own.

- `registry_sha256` pins the SnapLink role registry the queue was planned against (the
  Inspector's `registry_sha256`). While it is `unpinned`, or when the Inspector sees a different
  hash, every run stops at `registry_hash_changed` and says so once in the `brain-blocked` issue.
  To re-plan: check the roles, then paste the hash the issue reports.
- `order: registry` drafts the roles listed under Queue first, then every other registry role in
  registry order. `order: listed` drafts only the listed roles.

registry_sha256: unpinned
order: registry

## Queue

- photographer
