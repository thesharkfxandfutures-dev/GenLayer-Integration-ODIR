// Unit tests for the RPC guard rails. No network: they check what the adapter refuses before
// any request is made, and that the chain it would use is the client's own definition.
import test from 'node:test';
import assert from 'node:assert/strict';
import { selectChain, readView, RpcError, VIEW_METHODS, PINNED_CLIENT } from '../src/rpc.js';

const chains = { studionet: { id: 61999, rpcUrls: { default: { http: ['https://studio.genlayer.com/api'] } } }, other: { id: 4221, rpcUrls: { default: { http: ['https://example.invalid/rpc'] } } } };
const config = { chain_id: 61999, rpc_url: 'https://studio.genlayer.com/api', contract_address: '0xFE76B46a8345Fd8e07A8aA092BA715c8a4C3C646', permitted_methods: ['get_slice'] };

test('the chain is selected from the pinned client by id, and the config URL must agree', () => {
  assert.equal(selectChain(chains, config).id, 61999);
  assert.throws(() => selectChain(chains, { ...config, chain_id: 1 }), (e) => e instanceof RpcError && e.exit === 5);
  assert.throws(() => selectChain(chains, { ...config, rpc_url: 'https://somewhere.else/api' }), (e) => e instanceof RpcError && e.category === 'configuration_failure');
});

// The pinned client (genlayer-js 1.1.8) defines both testnets as chain 4221. These mirror its
// definitions so the rule is tested without the client installed.
const ASIMOV_URL = 'https://rpc-asimov.genlayer.com';
const BRADBURY_URL = 'https://rpc-bradbury.genlayer.com';
const asimov = { id: 4221, name: 'Genlayer Asimov Testnet', rpcUrls: { default: { http: [ASIMOV_URL] } } };
const bradbury = { id: 4221, name: 'Genlayer Bradbury Testnet', rpcUrls: { default: { http: [BRADBURY_URL] } } };
const studionet = { id: 61999, name: 'Genlayer Studio Network', rpcUrls: { default: { http: ['https://studio.genlayer.com/api'] } } };
const shared = { studionet, testnetAsimov: asimov, testnetBradbury: bradbury };
const sharedReversed = { testnetBradbury: bradbury, testnetAsimov: asimov, studionet };
const refused = (pattern) => (e) => e instanceof RpcError && e.exit === 5 && e.category === 'configuration_failure' && pattern.test(e.message);

test('a Bradbury config resolves to Bradbury and an Asimov config to Asimov, whatever the order', () => {
  for (const set of [shared, sharedReversed]) {
    assert.equal(selectChain(set, { chain_id: 4221, rpc_url: BRADBURY_URL }), bradbury);
    assert.equal(selectChain(set, { chain_id: 4221, rpc_url: ASIMOV_URL }), asimov);
    assert.equal(selectChain(set, { chain_id: 4221, rpc_url: `${BRADBURY_URL}/` }), bradbury);
    assert.equal(selectChain(set, { chain_id: 4221, chain_name: 'bradbury' }), bradbury);
    assert.equal(selectChain(set, { chain_id: 4221, chain_name: 'asimov' }), asimov);
    assert.equal(selectChain(set, { chain_id: 4221, chain_name: 'testnetBradbury', rpc_url: BRADBURY_URL }), bradbury);
    assert.equal(selectChain(set, { chain_id: 61999, rpc_url: 'https://studio.genlayer.com/api' }), studionet);
    assert.equal(selectChain(set, { chain_id: 4221, chain_name: null, rpc_url: BRADBURY_URL }), bradbury);
  }
});

test('a chain name may be the export key, the key without "testnet", or the client name', () => {
  for (const name of ['testnetBradbury', 'testnet-bradbury', 'Bradbury', 'Genlayer Bradbury Testnet', ' BRADBURY ']) {
    assert.equal(selectChain(shared, { chain_id: 4221, chain_name: name }), bradbury, name);
  }
  assert.equal(selectChain(shared, { chain_id: 4221, chain_name: 'Genlayer Asimov Testnet' }), asimov);
  // Whole names only: a fragment never picks a chain.
  for (const fragment of ['brad', 'bury', 'testnet', 'genlayer', 'asim']) {
    assert.throws(() => selectChain(shared, { chain_id: 4221, chain_name: fragment }), refused(/chain_name/), fragment);
  }
});

test('ids compare strictly, URLs ignore any run of trailing slashes, and a chain with no URL cannot contradict one', () => {
  assert.throws(() => selectChain(shared, { chain_id: '4221', chain_name: 'bradbury' }), refused(/not a chain the pinned client knows/));
  assert.equal(selectChain(shared, { chain_id: 4221, rpc_url: `${BRADBURY_URL}//` }), bradbury);
  const bare = { id: 7, name: 'No URL' };
  assert.equal(selectChain({ bare }, { chain_id: 7, rpc_url: 'https://any.example/rpc' }), bare);
});

test('a shared chain id with nothing else to choose by is refused, never the first match', () => {
  for (const set of [shared, sharedReversed]) {
    assert.throws(() => selectChain(set, { chain_id: 4221 }), refused(/shared by (testnetAsimov, testnetBradbury|testnetBradbury, testnetAsimov) /));
    assert.throws(() => selectChain(set, { chain_id: 4221, rpc_url: null }), refused(/set rpc_url or chain_name/));
  }
});

test('a name, URL or id that disagree with each other is refused', () => {
  assert.throws(() => selectChain(shared, { chain_id: 4221, chain_name: 'bradbury', rpc_url: ASIMOV_URL }), refused(/rpc_url differs/));
  assert.throws(() => selectChain(shared, { chain_id: 4221, chain_name: 'studionet' }), refused(/chain_name "studionet" is not chain 4221/));
  assert.throws(() => selectChain(shared, { chain_id: 61999, chain_name: 'bradbury' }), refused(/chain_name/));
  assert.throws(() => selectChain(shared, { chain_id: 4221, rpc_url: 'https://somewhere.else/rpc' }), refused(/rpc_url differs/));
  assert.throws(() => selectChain(shared, { chain_id: 4221, chain_name: 'bradbury-mainnet' }), refused(/chain_name/));
  for (const bad of ['', '  ', '--', 4221, {}, true]) {
    assert.throws(() => selectChain(shared, { chain_id: 4221, chain_name: bad, rpc_url: BRADBURY_URL }), refused(/chain_name must be a non-empty string/), String(bad));
  }
});

test('only view methods, and only those the config permits, can be read', async () => {
  await assert.rejects(readView(config, 'submit_evidence', ['D1', 'x']), (e) => e instanceof RpcError && e.exit === 5);
  await assert.rejects(readView(config, 'get_config', []), (e) => e instanceof RpcError && /permitted_methods/.test(e.message));
  assert.deepEqual(VIEW_METHODS, ['get_slice', 'get_attempt', 'can_consume', 'get_config']);
  assert.equal(PINNED_CLIENT, 'genlayer-js@1.1.8');
});

test('the installed client, when present, defines studionet exactly as the config expects', async (t) => {
  let real;
  try { real = await import('genlayer-js/chains'); } catch { t.skip('genlayer-js not installed'); return; }
  const chain = selectChain(real, config);
  assert.equal(chain.id, 61999);
  assert.equal(chain.rpcUrls.default.http[0].replace(/\/+$/, ''), config.rpc_url);
});

test('the installed client, when present, resolves Bradbury and Asimov to their own chains', async (t) => {
  let real;
  try { real = await import('genlayer-js/chains'); } catch { t.skip('genlayer-js not installed'); return; }
  // The premise of the rule: the pinned client gives both testnets one id.
  assert.equal(real.testnetAsimov.id, 4221);
  assert.equal(real.testnetBradbury.id, 4221);
  assert.equal(selectChain(real, { chain_id: 4221, rpc_url: BRADBURY_URL }), real.testnetBradbury);
  assert.equal(selectChain(real, { chain_id: 4221, rpc_url: ASIMOV_URL }), real.testnetAsimov);
  assert.equal(selectChain(real, { chain_id: 4221, chain_name: 'bradbury' }), real.testnetBradbury);
  assert.equal(selectChain(real, { chain_id: 4221, chain_name: 'asimov' }), real.testnetAsimov);
  assert.throws(() => selectChain(real, { chain_id: 4221 }), refused(/shared by/));
});
