# Template release and bundle (slice A4)

Drafts, **not legal advice**. A UK solicitor reviews the templates before any real member signs.

A release turns one tagged commit into four files. SnapLink imports the first in slice D1
(`scripts/importContractTemplates.mjs` → `base44/shared/contracts/templates.generated.js`).

| File | What it is |
|---|---|
| `odir-templates.mjs` | One ES module with **no imports**: every template as the exact text of its file with its whole-file sha256 and its template hash; the three schema files the resolver reads; and the resolver and hash code (`resolver/src/{categories,validate,hash,resolve,render}.js`, `adapter/src/canon.js`, `brain/src/jsonschema.js`) with a plain-ECMAScript SHA-256 in place of `node:crypto`. It runs in the browser, Deno and Node, and in a bare ECMAScript context with no host globals (tested). |
| `odir-templates.manifest.json` | `odir.template-release.v1` (`schema/template-release.v1.json`): tag, commit, the bundle's sha256 and size, every template's hashes, every schema and source file's sha256, and the terms hash of every role × base combination. |
| `RELEASE_NOTES.md` | What the release holds and how to check it. |
| `SHA256SUMS` | `sha256sum -c` format, for the three files above. |

## How it stays honest

- **Reproducible.** The build reads git objects at the commit (`git cat-file`), never the working
  tree, ignoring `git replace` refs and any `GIT_*` setting. No clock, no randomness, no file order,
  LF only, keys sorted. The same tag gives the same bytes on any machine; CI builds twice and compares.
- **Built by its own tooling.** The build scripts run from the checkout, so they must be
  byte-identical to the same files at the commit being built; a dirty checkout, or newer tooling
  building an older tag, is refused. Build a tag from a clean checkout of that tag (the workflow does).
- **Self-computed hashes.** A first pass imports a probe bundle, so every template hash in the
  release is computed by the very code the release ships.
- **Golden-checked.** The finished bundle must reproduce every terms hash in
  `resolver/test/golden/hashes.json` at the same commit. A template edited without its golden diff
  is refused.
- **Carried unchanged.** Each source file is wrapped, not rewritten: only its import lines, the
  word `export`, and two declared patches in `validate.js` (schemas read from the bundle, not the
  disk) change. A patch that no longer matches stops the build. Any other Node-only construct stops it.
- **Tamper checks, in layers.**
  1. In the bundle: `getBase` / `getModule` check the template's whole-file sha256 (any change,
     style too) and its template hash (any word) and refuse on a mismatch. `verifyRelease()` checks all.
  2. Across the files: `SHA256SUMS` (no duplicates), the manifest (schema-checked; its bundle
     sha256, templates, schemas, sources and notice equal to the bundle's; its terms hashes equal
     to the ones the bundle computes) and `RELEASE_NOTES.md` (exactly what the manifest gives).
  3. Against the tag: `verify-release --rebuild` rebuilds from the tag and compares bytes. This is
     the only check that catches a tamper which rewrote every recorded hash consistently, so the
     importer (D1) must rebuild, or compare with the release the owner published on GitHub.

## Commands

```bash
cd release && npm test                                                  # all tests (temp repositories only)
node release/bin/build-release.mjs --ref HEAD --out /tmp/r              # untagged check build (what CI runs)
node release/bin/build-release.mjs --tag templates-v1.0.0 --out dist    # a tagged release
node release/bin/verify-release.mjs --dir dist --rebuild --tag templates-v1.0.0
```

## Releasing (owner)

1. Merge the template change into `main` (with its golden diff).
2. Tag the merge commit `templates-vX.Y.Z` and push the tag. Only the owner tags.
3. `.github/workflows/release-draft.yml` checks the tag is on `main`, runs the tests, builds twice,
   verifies with a rebuild and opens a **draft** release with the four files.
4. Review the draft and publish it. D1 imports only a published release.
