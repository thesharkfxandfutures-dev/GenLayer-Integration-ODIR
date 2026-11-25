# ODIR Brain — loop skeleton (slice A2, dry run)

The Brain moves one item forward by one stage per run, then stops. This folder is the skeleton of
that loop: it takes the lock, works out state, runs the stop checks, writes a run record and
releases the lock. **It drafts nothing.** It never signs, deploys, holds a key or merges, and in
this slice it never writes to GitHub at all.

## One run

1. **Lock** — `brain/lock` is a branch whose head commit carries the lease (run id, `held` or
   `released`, expiry 40 minutes ahead) in its message and in `LEASE.json`.
   - No branch: create it. Creating either succeeds or fails, so only one run holds it.
   - Held and not expired: exit (`LOCK_HELD`).
   - Released or expired: move the branch to a new child commit, fast-forward only. If another
     run moved it first the update is not a fast-forward and this run exits (`LOCK_LOST_RACE`).
   - Before **every** write the run re-reads the branch and stops (`LEASE_LOST`) unless the head
     is still its own `held` commit with more than 60 s left. Renewal and release are
     fast-forwards too. The branch is never deleted.
   - An unreadable lease fails closed (`LOCK_UNREADABLE`); the owner repairs it.
2. **Inspector** (`src/inspector.js`, no LLM) — parses SnapLink's
   `base44/shared/taxonomy/registry.js` text, fetched read-only, without running it; checks the
   result against `schema/inspector-snapshot.v1.json`; hashes it in the adapter's canonical
   encoding. `registry_sha256` covers each role's key, label, family and sectors, in order.
3. **State** (`src/state.js`) — from `main` (`brain/QUEUE.md`, phase 1 files, approved
   templates), the holding bay `brain/holding` and the open pull requests. No state file.
4. **Stop checks** (`src/stops.js`), in order: `registry_hash_changed`, `bases_not_merged`,
   `queue_empty`, `genskill_missing` (on-chain steps only).
5. **brain-blocked issue** (`src/blocked.js`) — one open issue keyed by reason; a reason is
   reported once, removed when it clears, and the issue closes when none is left. In A2 the plan
   is recorded, not applied.
6. **Recorder** (`src/recorder.js`, no LLM) — writes the run record
   (`schema/brain-run.v1.json`, claims graded OBSERVED / CLAIMED / NOT_RUN) behind the lease check.
7. **Release** the lock by fast-forward.

## Run it

```bash
cd brain
npm test                                   # node --test, no dependencies

# Snapshot SnapLink's registry (the file is fetched read-only by the run; not kept in this repo)
node bin/brain.mjs inspect --registry /path/to/registry.js --registry-ref main

# Dry run against a local checkout. The git lock store writes refs/heads/brain/lock in THAT
# local repository only; nothing is pushed.
git fetch origin
node bin/brain.mjs dry-run --repo .. --registry /path/to/registry.js --registry-ref main \
  --lock-store git --pulls pulls.json --out ../out/brain-runs
```

Exit codes: 0 record written · 3 lock not taken · 4 lease lost mid-run · 5 configuration ·
6 lock unreadable.

## Not switched on

The GitHub lock store (`GitHubRefStore`) and issue writes exist and are tested against a fake
GitHub, but the CLI refuses them. Switching the schedule on waits for the owner: the Brain's own
GitHub identity, a ruleset on `main` and CODEOWNERS. Until then "never merges" rests on
`.claude/settings.json` alone.

`brain/QUEUE.md` is `unpinned`, so the first real run stops at `registry_hash_changed` and
reports the observed hash for the owner to pin.
