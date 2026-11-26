// The pinned network facts against genlayer-js 1.1.8's own chain objects, and the chain guard.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { localnet, studionet, testnetAsimov, testnetBradbury } from 'genlayer-js/chains';
import {
  ADD_CHAIN_PARAMS, BRADBURY, DeployError, EXPECTED_SOURCE_SHA256, GENLAYER_JS_VERSION, assertBradburyChain,
} from '../src/bradbury.js';
import { ROOT } from './helpers.mjs';

test('the installed genlayer-js is exactly the pinned version', () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, 'node_modules', 'genlayer-js', 'package.json'), 'utf8'));
  assert.equal(pkg.version, GENLAYER_JS_VERSION);
  const ours = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
  assert.equal(ours.dependencies['genlayer-js'], GENLAYER_JS_VERSION, 'package.json pins genlayer-js exactly');
  const lock = JSON.parse(readFileSync(join(ROOT, 'package-lock.json'), 'utf8'));
  assert.equal(lock.packages['node_modules/genlayer-js'].version, GENLAYER_JS_VERSION);
});

test('every pinned Bradbury fact equals the library\'s testnetBradbury', () => {
  assert.equal(testnetBradbury.id, BRADBURY.chainId);
  assert.equal(`0x${testnetBradbury.id.toString(16)}`, BRADBURY.chainIdHex);
  assert.equal(testnetBradbury.name, BRADBURY.name);
  assert.deepEqual(testnetBradbury.rpcUrls.default.http, [BRADBURY.rpcUrl]);
  assert.equal(testnetBradbury.blockExplorers.default.url, BRADBURY.explorerUrl);
  assert.equal(testnetBradbury.consensusMainContract.address, BRADBURY.consensusMainContract);
  assert.equal(testnetBradbury.consensusDataContract.address, BRADBURY.consensusDataContract);
  assert.deepEqual({ ...testnetBradbury.nativeCurrency }, { ...BRADBURY.nativeCurrency });
  assert.equal(testnetBradbury.testnet, true);
});

test('assertBradburyChain accepts testnetBradbury and lists what it checked', () => {
  const checks = assertBradburyChain(testnetBradbury);
  assert.equal(checks.length, 6);
});

test('assertBradburyChain refuses Asimov although it shares chain id 4221 (A1)', () => {
  assert.equal(testnetAsimov.id, testnetBradbury.id, 'precondition: same chain id');
  assert.throws(() => assertBradburyChain(testnetAsimov), (e) => e instanceof DeployError && e.code === 'WRONG_CONFIG' && /consensus main contract/.test(e.message) && /RPC/.test(e.message));
});

test('assertBradburyChain refuses Studionet, localnet, nothing, and a chain claiming Bradbury with one fact changed', () => {
  for (const c of [studionet, localnet, null, undefined, 'testnetBradbury']) {
    assert.throws(() => assertBradburyChain(c), (e) => e.code === 'WRONG_CONFIG');
  }
  const mutants = {
    id: { ...testnetBradbury, id: 4222 },
    notTestnet: { ...testnetBradbury, testnet: false },
    studio: { ...testnetBradbury, isStudio: true },
    rpc: { ...testnetBradbury, rpcUrls: { default: { http: ['https://rpc-asimov.genlayer.com'] } } },
    twoRpcs: { ...testnetBradbury, rpcUrls: { default: { http: [BRADBURY.rpcUrl, 'https://evil.example'] } } },
    consensus: { ...testnetBradbury, consensusMainContract: { ...testnetBradbury.consensusMainContract, address: testnetAsimov.consensusMainContract.address } },
    noConsensus: { ...testnetBradbury, consensusMainContract: undefined },
    dataContract: { ...testnetBradbury, consensusDataContract: { ...testnetBradbury.consensusDataContract, address: testnetAsimov.consensusDataContract.address } },
  };
  for (const [name, chain] of Object.entries(mutants)) {
    assert.throws(() => assertBradburyChain(chain), (e) => e.code === 'WRONG_CONFIG', name);
  }
});

test('wallet_addEthereumChain parameters are Bradbury\'s, and nothing else', () => {
  assert.deepEqual(Object.keys(ADD_CHAIN_PARAMS).sort(), ['blockExplorerUrls', 'chainId', 'chainName', 'nativeCurrency', 'rpcUrls']);
  assert.equal(ADD_CHAIN_PARAMS.chainId, '0x107d');
  assert.deepEqual(ADD_CHAIN_PARAMS.rpcUrls, ['https://rpc-bradbury.genlayer.com']);
  assert.deepEqual(ADD_CHAIN_PARAMS.blockExplorerUrls, ['https://explorer-bradbury.genlayer.com/']);
});

test('the pinned source hash is the hash of contract/storage.py as committed (LF only)', () => {
  const bytes = readFileSync(join(ROOT, 'contract', 'storage.py'));
  assert.ok(!bytes.includes(0x0d), 'no CR in the committed source');
  assert.equal(createHash('sha256').update(bytes).digest('hex'), EXPECTED_SOURCE_SHA256);
});

test('the frozen constants cannot be changed at run time', () => {
  assert.throws(() => { BRADBURY.rpcUrl = 'https://evil.example'; }, TypeError);
  assert.throws(() => { BRADBURY.nativeCurrency.decimals = 0; }, TypeError);
  assert.throws(() => { ADD_CHAIN_PARAMS.chainId = '0x1'; }, TypeError);
});
