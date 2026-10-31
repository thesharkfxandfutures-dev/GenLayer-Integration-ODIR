import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonical, digest, sha256, CanonError } from '../src/canon.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'fixtures', 'd1', 'canon-vectors.json'), 'utf8'));

test('canonical encoding reproduces the CPython bytes for every shared vector', () => {
  for (const v of vectors.vectors) {
    assert.equal(canonical(v.value), v.canonical, v.name);
    assert.equal(digest(v.value), v.sha256, v.name);
  }
});

test('evidence text hashes as the contract hashes it', () => {
  const { text, sha256: want } = vectors.evidence_text_sha256;
  assert.equal(sha256(text), want);
});

test('key order and undefined do not change the encoding', () => {
  assert.equal(canonical({ b: 1, a: 2, c: undefined }), canonical({ a: 2, b: 1 }));
});

test('floats are refused: Python and JavaScript print them differently', () => {
  assert.throws(() => canonical({ x: 1.5 }), CanonError);
  assert.throws(() => canonical([0.1]), CanonError);
});

test('one changed byte changes the digest', () => {
  const a = digest({ evidence: 'single owner' });
  const b = digest({ evidence: 'single owner.' });
  assert.notEqual(a, b);
});
