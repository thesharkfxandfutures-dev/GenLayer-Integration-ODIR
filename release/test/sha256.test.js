// The bundle's own SHA-256 must equal node:crypto byte for byte, or every hash it checks is wrong.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { cryptoShim, sha256Bytes, sha256Hex, utf8Bytes } from '../src/sha256.js';
import { ROOT } from './helpers.js';

const node = (text) => crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');

test('FIPS 180-4 vectors', () => {
  assert.equal(sha256Hex(''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  assert.equal(sha256Hex('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  assert.equal(sha256Hex('abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'), '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1');
  assert.equal(sha256Hex('a'.repeat(1000000)), 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0');
});

test('equals node:crypto at every padding boundary (0–200 bytes) and on long input', () => {
  for (let n = 0; n <= 200; n++) assert.equal(sha256Hex('x'.repeat(n)), node('x'.repeat(n)), `length ${n}`);
  const long = crypto.randomBytes(300000).toString('latin1');
  assert.equal(sha256Hex(long), node(long));
});

test('UTF-8 like Node: multi-byte, astral, and lone surrogates as U+FFFD', () => {
  const cases = ['£650 — café, € and ’quotes’', 'Ελληνικά 日本語 한국어', '😀🎞️ astral', '\ud800', 'a\udc00b', '\udc00\ud800', 'x\ud83d', '\u0000\u007f\u0080߿ࠀ￿'];
  for (const s of cases) {
    assert.equal(sha256Hex(s), node(s), JSON.stringify(s));
    assert.deepEqual(Buffer.from(utf8Bytes(s)), Buffer.from(s, 'utf8'), JSON.stringify(s));
  }
  for (let i = 0; i < 300; i++) {
    const s = String.fromCharCode(...Array.from({ length: 1 + (i % 40) }, () => Math.floor(Math.random() * 0x10000)));
    assert.equal(sha256Hex(s), node(s));
  }
});

test('equals node:crypto on the real templates and schemas', () => {
  for (const f of ['templates/bases/p2p.json', 'templates/bases/b2p.json', 'templates/roles/photographer/module.json', 'schema/agreement.v1.json']) {
    const text = fs.readFileSync(path.join(ROOT, f), 'utf8');
    assert.equal(sha256Hex(text), node(text), f);
  }
});

test('sha256Bytes takes bytes', () => {
  assert.equal(sha256Bytes([0x61, 0x62, 0x63]), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});

test('the node:crypto shim does exactly what canon.js asks and refuses the rest', () => {
  assert.equal(cryptoShim.createHash('sha256').update('ab', 'utf8').update('c', 'utf8').digest('hex'), node('abc'));
  assert.throws(() => cryptoShim.createHash('sha1'), /only sha256/);
  assert.throws(() => cryptoShim.createHash('sha256').update('x', 'latin1'), /utf8/);
  assert.throws(() => cryptoShim.createHash('sha256').update(Buffer.from('x'), 'utf8'), /utf8/);
  assert.throws(() => cryptoShim.createHash('sha256').update('x', 'utf8').digest('base64'), /hex/);
  assert.ok(Object.isFrozen(cryptoShim));
});
