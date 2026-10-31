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
