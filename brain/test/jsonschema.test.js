import test from 'node:test';
import assert from 'node:assert/strict';
import { validate, assertSupported } from '../src/jsonschema.js';

test('a schema keyword the validator does not enforce is refused, wherever it sits', () => {
  assert.throws(() => assertSupported({ type: 'object', properties: { a: { type: 'string', format: 'email' } } }), /format/);
  assert.throws(() => assertSupported({ $defs: { x: { oneOf: [] } } }), /oneOf/);
  assert.throws(() => assertSupported({ items: { anyOf: [] } }), /anyOf/);
  assert.throws(() => validate({ if: {} }, 1), /if/);
});

test('keywords beside $ref are refused instead of silently ignored', () => {
  const s = { $defs: { k: { type: 'string' } }, properties: { a: { $ref: '#/$defs/k', maxLength: 2 } } };
  assert.throws(() => assertSupported(s), /beside \$ref/);
  assert.throws(() => validate(s, { a: 'abc' }), /beside \$ref/);
  assert.equal(assertSupported({ $defs: { k: { type: 'string' } }, properties: { a: { $ref: '#/$defs/k', description: 'ok' } } }), true);
});

test('uniqueItems ignores key order', () => {
  const r = validate({ type: 'array', uniqueItems: true }, [{ a: 1, b: 2 }, { b: 2, a: 1 }]);
  assert.equal(r.ok, false);
});

test('types, enums, patterns and required fields are enforced', () => {
  const s = { type: 'object', additionalProperties: false, required: ['n'], properties: { n: { type: 'integer', minimum: 1 }, e: { enum: ['x'] }, p: { type: 'string', pattern: '^a' } } };
  assert.equal(validate(s, { n: 1, e: 'x', p: 'ab' }).ok, true);
  assert.equal(validate(s, { n: 0 }).ok, false);
  assert.equal(validate(s, { n: 1.5 }).ok, false);
  assert.equal(validate(s, { n: 1, e: 'y' }).ok, false);
  assert.equal(validate(s, { n: 1, p: 'b' }).ok, false);
  assert.equal(validate(s, {}).ok, false);
  assert.equal(validate(s, { n: 1, z: 1 }).ok, false);
});
