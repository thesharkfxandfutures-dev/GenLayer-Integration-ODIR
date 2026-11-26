// The real genlayer-js 1.1.8 client with a mock wallet and a stubbed Bradbury RPC (global fetch): what exactly
// would MetaMask be asked to sign, and does the library route signing to the wallet and reads to the RPC?
import test from 'node:test';
import assert from 'node:assert/strict';
import { createClient } from 'genlayer-js';
import { testnetBradbury } from 'genlayer-js/chains';
import { decodeFunctionData, encodeEventTopics, zeroAddress } from 'viem';
import { BRADBURY, INITIAL_STORAGE } from '../src/bradbury.js';
import { deployAndVerify, prepare } from '../src/core.js';
import { ACCOUNT, CONTRACT, EVM_HASH, SOURCE, TX_ID, mockRpc, mockWallet, rejection } from './helpers.mjs';

/** Stubs global fetch as Bradbury's RPC. Records every JSON-RPC method and the URL it was sent to. */
function stubFetch(answers) {
  const seen = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    const { method, params, id } = JSON.parse(init.body);
    seen.push({ url: String(url), method, params });
    const fn = answers[method];
    const body = fn ? { jsonrpc: '2.0', id, result: await fn(params) } : { jsonrpc: '2.0', id, error: { code: -32601, message: `stub: no ${method}` } };
    return { ok: true, status: 200, json: async () => body };
  };
  return { seen, restore: () => { globalThis.fetch = original; } };
}

const RPC_BASICS = {
  eth_getTransactionCount: () => '0x7',
  eth_estimateGas: () => '0x30d40',
  eth_gasPrice: () => '0x3b9aca00',
  eth_chainId: () => '0x107d',
  eth_blockNumber: () => '0xae470',
};

function evmReceipt() {
  const topics = encodeEventTopics({
    abi: testnetBradbury.consensusMainContract.abi, eventName: 'NewTransaction', args: { txId: TX_ID, recipient: CONTRACT, activator: ACCOUNT },
  });
  return {
    transactionHash: EVM_HASH, transactionIndex: '0x0', blockHash: `0x${'ee'.repeat(32)}`, blockNumber: '0xae470',
    from: ACCOUNT, to: BRADBURY.consensusMainContract, cumulativeGasUsed: '0x5208', gasUsed: '0x5208', effectiveGasPrice: '0x3b9aca00',
    contractAddress: null, logsBloom: `0x${'0'.repeat(512)}`, status: '0x1', type: '0x0',
    logs: [{
      address: BRADBURY.consensusMainContract, topics, data: '0x', blockNumber: '0xae470', blockHash: `0x${'ee'.repeat(32)}`,
      transactionHash: EVM_HASH, transactionIndex: '0x0', logIndex: '0x0', removed: false,
    }],
  };
}

test('deployContract asks the wallet to sign one legacy tx to Bradbury\'s consensus contract, carrying the exact source', async (t) => {
  const rpc = stubFetch(RPC_BASICS);
  t.after(rpc.restore);
  let sent;
  const wallet = mockWallet({ handlers: { eth_sendTransaction: ([tx]) => { sent = tx; throw rejection(); } } });
  const client = createClient({ chain: testnetBradbury, account: ACCOUNT, provider: wallet });
  await assert.rejects(client.deployContract({ code: SOURCE, args: [INITIAL_STORAGE], leaderOnly: false }));

  assert.equal(sent.to, BRADBURY.consensusMainContract, '"to" is Bradbury\'s consensus main contract — what MetaMask shows');
  assert.equal(sent.from, ACCOUNT);
  assert.equal(sent.chainId, '0x107d');
  assert.equal(sent.type, '0x0');
  assert.equal(sent.value, '0x0');
  assert.equal(sent.nonce, '0x7', 'nonce comes from Bradbury\'s RPC, not the wallet');
  const call = decodeFunctionData({ abi: testnetBradbury.consensusMainContract.abi, data: sent.data });
  assert.equal(call.functionName, 'addTransaction');
  assert.equal(call.args[0].toLowerCase(), ACCOUNT);
  assert.equal(call.args[1], zeroAddress, 'recipient zero = a deploy');
  assert.ok(sent.data.includes(Buffer.from(SOURCE, 'utf8').toString('hex')), 'the calldata carries the exact LF source bytes');

  // Signing went to the wallet; reads went to Bradbury's RPC and nowhere else.
  assert.deepEqual(wallet.calls.map((c) => c.method), ['eth_chainId', 'eth_sendTransaction']);
  assert.ok(rpc.seen.length > 0);
  assert.ok(rpc.seen.every((s) => s.url === BRADBURY.rpcUrl), 'every direct read goes to rpc-bradbury');
  assert.ok(!rpc.seen.some((s) => s.method === 'eth_sendTransaction' || s.method === 'eth_sendRawTransaction'), 'nothing is sent around the wallet');
});

test('success path: wallet returns the EVM hash, the EVM receipt\'s NewTransaction log gives the GenLayer tx id', async (t) => {
  const rpc = stubFetch({ ...RPC_BASICS, eth_getTransactionReceipt: () => evmReceipt(), eth_getTransactionByHash: () => null });
  t.after(rpc.restore);
  const wallet = mockWallet({ handlers: { eth_sendTransaction: () => EVM_HASH } });
  const client = createClient({ chain: testnetBradbury, account: ACCOUNT, provider: wallet });
  const txId = await client.deployContract({ code: SOURCE, args: [INITIAL_STORAGE], leaderOnly: false });
  assert.equal(txId, TX_ID);
  assert.equal(wallet.calls.filter((c) => c.method === 'eth_sendTransaction').length, 1, 'exactly one signature');
});

test('the library\'s own guard checks only the chain id: a wallet on another chain id is refused …', async (t) => {
  const rpc = stubFetch(RPC_BASICS);
  t.after(rpc.restore);
  const wallet = mockWallet({ chainId: '0x1', handlers: { eth_sendTransaction: () => { throw new Error('must not be reached'); } } });
  const client = createClient({ chain: testnetBradbury, account: ACCOUNT, provider: wallet });
  await assert.rejects(client.deployContract({ code: SOURCE, args: [INITIAL_STORAGE] }), /Wallet is on chain 1/);
  assert.ok(!wallet.calls.some((c) => c.method === 'eth_sendTransaction'));
});

test('… so the page adds the block-hash check: a 4221 wallet on a different chain never reaches the signature', async (t) => {
  const rpc = stubFetch(RPC_BASICS);
  t.after(rpc.restore);
  const wallet = mockWallet({ salt: 'c', handlers: { eth_sendTransaction: () => { throw new Error('must not be reached'); } } });
  await assert.rejects(prepare({ provider: wallet, rpcRequest: mockRpc({ salt: 'b' }), chain: testnetBradbury, source: SOURCE }), (e) => e.code === 'WRONG_CHAIN');
  assert.ok(!wallet.calls.some((c) => c.method === 'eth_sendTransaction'));
});

test('the page with the real client: a rejected MetaMask signature stops at REJECTED and nothing was sent', async (t) => {
  const rpc = stubFetch(RPC_BASICS);
  t.after(rpc.restore);
  const wallet = mockWallet({ handlers: { eth_sendTransaction: () => { throw rejection(); } } });
  const prepared = await prepare({ provider: wallet, rpcRequest: mockRpc(), chain: testnetBradbury, source: SOURCE });
  await assert.rejects(deployAndVerify({
    prepared, provider: wallet, chain: testnetBradbury, confirmed: true,
    makeClient: ({ chain, account, provider }) => createClient({ chain, account, provider }),
  }), (e) => e.code === 'REJECTED');
  const sends = wallet.calls.filter((c) => c.method === 'eth_sendTransaction');
  assert.equal(sends.length, 1, 'one attempt, no retry with the fallback encoding');
  assert.ok(!wallet.calls.some((c) => /^wallet_(requestSnaps|getSnaps|addEthereumChain|switchEthereumChain)$/.test(c.method)), 'no Snap, no network change when already on Bradbury');
});
