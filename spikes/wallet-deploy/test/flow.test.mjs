// The two phases end to end with a mock wallet and a mock genlayer-js client: every outcome the page can show.
import test from 'node:test';
import assert from 'node:assert/strict';
import { testnetAsimov, testnetBradbury } from 'genlayer-js/chains';
import { BRADBURY, EXPECTED_SOURCE_SHA256, INITIAL_STORAGE } from '../src/bradbury.js';
import { DEFAULT_WAIT, RECORD_SCHEMA, deployAndVerify, prepare } from '../src/core.js';
import {
  ACCOUNT, CONTRACT, OTHER_ACCOUNT, SOURCE, TX_ID, deepRejection, mockClient, mockRpc, mockWallet, okReceipt, rejection, wrappedRejection,
} from './helpers.mjs';

const clock = () => { let t = 0; return () => `2026-11-26T12:00:${String((t += 1)).padStart(2, '0')}Z`; };

async function ready({ wallet = mockWallet(), rpc = mockRpc(), source = SOURCE } = {}) {
  const prepared = await prepare({ provider: wallet, rpcRequest: rpc, chain: testnetBradbury, source, now: clock() });
  return { wallet, rpc, prepared };
}

function run(opts = {}) {
  const { prepared, wallet, client = mockClient(), chain = testnetBradbury, steps = [], wait } = opts;
  const confirmed = Object.hasOwn(opts, 'confirmed') ? opts.confirmed : true; // an explicit undefined stays undefined
  const made = [];
  const makeClient = (args) => { made.push(args); return client; };
  const p = deployAndVerify({
    prepared, provider: wallet, makeClient, chain, confirmed, wait, now: clock(), onStep: (s, r) => steps.push([s, { ...r }]),
  });
  return { p, made, client, steps };
}

test('prepare: hash, account, network and same-chain check — and no signature of any kind', async () => {
  const { wallet, prepared } = await ready();
  assert.equal(prepared.sourceSha256, EXPECTED_SOURCE_SHA256);
  assert.equal(prepared.account, ACCOUNT);
  assert.equal(prepared.code, SOURCE);
  assert.equal(prepared.bytes, Buffer.byteLength(SOURCE));
  assert.ok(Object.isFrozen(prepared));
  assert.ok(!wallet.calls.some((c) => /send|sign/i.test(c.method)), 'prepare never asks the wallet to send or sign');
});

test('prepare refuses a source whose hash is not the pinned one, before touching the wallet', async () => {
  const wallet = mockWallet();
  await assert.rejects(
    prepare({ provider: wallet, rpcRequest: mockRpc(), chain: testnetBradbury, source: `${SOURCE}# extra\n` }),
    (e) => e.code === 'SOURCE_MISMATCH',
  );
  assert.equal(wallet.calls.length, 0);
});

test('prepare deploys LF bytes: a CRLF copy of the source passes and is normalised', async () => {
  const { prepared } = await ready({ source: SOURCE.replace(/\n/g, '\r\n') });
  assert.ok(!prepared.code.includes('\r'));
  assert.equal(prepared.sourceSha256, EXPECTED_SOURCE_SHA256);
});

test('prepare refuses Asimov\'s chain object before touching the wallet', async () => {
  const wallet = mockWallet();
  await assert.rejects(prepare({ provider: wallet, rpcRequest: mockRpc(), chain: testnetAsimov, source: SOURCE }), (e) => e.code === 'WRONG_CONFIG');
  assert.equal(wallet.calls.length, 0);
});

test('prepare stops on a wallet whose 4221 is another chain (block hash differs)', async () => {
  await assert.rejects(ready({ wallet: mockWallet({ salt: 'c' }) }), (e) => e.code === 'WRONG_CHAIN');
});

test('prepare stops when the consensus contract has no code (the 26 Nov genlayer-js 1.1.8 finding) — nothing signed', async () => {
  const wallet = mockWallet();
  const rpc = mockRpc({ handlers: { eth_getCode: () => '0x' } });
  await assert.rejects(prepare({ provider: wallet, rpcRequest: rpc, chain: testnetBradbury, source: SOURCE }), (e) => e.code === 'CONSENSUS_NOT_DEPLOYED' && /out of date/.test(e.message) && /Nothing was signed/.test(e.message));
  assert.deepEqual(rpc.calls.find((c) => c.method === 'eth_getCode').params, [BRADBURY.consensusMainContract, 'latest']);
  assert.ok(!wallet.calls.some((c) => /send|sign/i.test(c.method)));
});

test('prepare stops when the consensus code cannot be read', async () => {
  for (const handler of [() => { throw new Error('rpc down'); }, () => null, () => 'zz', () => 42]) {
    const rpc = mockRpc({ handlers: { eth_getCode: handler } });
    await assert.rejects(prepare({ provider: mockWallet(), rpcRequest: rpc, chain: testnetBradbury, source: SOURCE }), (e) => e.code === 'CONSENSUS_UNVERIFIED');
  }
});

test('success: one deploy of the exact code, address from the receipt\'s recipient, code read back matches', async () => {
  const { wallet, prepared } = await ready();
  const { p, made, client, steps } = run({ prepared, wallet });
  const r = await p;
  assert.equal(r.outcome, 'DEPLOYED_VERIFIED');
  assert.equal(r.schema, RECORD_SCHEMA);
  assert.equal(r.txId, TX_ID);
  assert.equal(r.statusName, 'ACCEPTED');
  assert.equal(r.executionResult, 'FINISHED_WITH_RETURN');
  assert.equal(r.contractAddress, CONTRACT);
  assert.deepEqual(r.code, { sha256: EXPECTED_SOURCE_SHA256, matches: true, matchesAfterLf: true });
  assert.equal(r.network.consensusMainContract, BRADBURY.consensusMainContract);
  assert.equal(r.network.chainId, 4221);
  assert.deepEqual(r.consensus, {
    main: { address: BRADBURY.consensusMainContract, codeBytes: 1159 },
    data: { address: BRADBURY.consensusDataContract, codeBytes: 1159 },
  });
  assert.equal(r.evmTxHash, null, 'the mock client never touches the wallet, so no EVM hash here');
  assert.deepEqual(r.constructorArgs, [INITIAL_STORAGE]);
  assert.ok(r.sentAt && r.decidedAt && r.finishedAt);

  assert.equal(made.length, 1);
  assert.equal(made[0].chain, testnetBradbury);
  assert.equal(made[0].account, ACCOUNT);
  assert.notEqual(made[0].provider, wallet, 'the client gets the one-signature guard, not the raw wallet');
  assert.equal(await made[0].provider.request({ method: 'eth_chainId' }), '0x107d', 'the guard passes reads through to the wallet');
  const names = client.calls.map((c) => c[0]);
  assert.deepEqual(names, ['deployContract', 'waitForTransactionReceipt', 'getContractCode'], 'one deploy, no connect(), no second send');
  assert.deepEqual(client.calls[0][1], { code: SOURCE, args: [INITIAL_STORAGE], leaderOnly: false });
  assert.deepEqual(client.calls[1][1], { hash: TX_ID, status: 'ACCEPTED', retries: DEFAULT_WAIT.retries, interval: DEFAULT_WAIT.interval, fullTransaction: true });
  assert.equal(client.calls[2][1], CONTRACT);
  assert.deepEqual(steps.map((s) => s[0]), ['signing', 'sent', 'decided']);
  assert.equal(steps[1][1].txId, TX_ID, 'the transaction id is shown as soon as it exists');
});

test('the default wait outlasts a slow testnet round: at least 15 minutes of polling, no faster than every 2 s', () => {
  assert.ok(DEFAULT_WAIT.retries * DEFAULT_WAIT.interval >= 15 * 60_000, `waits ${DEFAULT_WAIT.retries * DEFAULT_WAIT.interval} ms`);
  assert.ok(DEFAULT_WAIT.interval >= 2000, 'polls no more often than every 2 s');
  assert.ok(Object.isFrozen(DEFAULT_WAIT));
});

test('FINALIZED is accepted as decided too', async () => {
  const { wallet, prepared } = await ready();
  const r = await run({ prepared, wallet, client: mockClient({ receipt: async () => okReceipt({ statusName: 'FINALIZED' }) }) }).p;
  assert.equal(r.outcome, 'DEPLOYED_VERIFIED');
});

test('nothing is sent without the tick', async () => {
  const { wallet, prepared } = await ready();
  for (const confirmed of [false, undefined, 'yes', 1]) {
    const { p, client } = run({ prepared, wallet, confirmed });
    await assert.rejects(p, (e) => e.code === 'NOT_CONFIRMED');
    assert.equal(client.calls.length, 0);
  }
});

test('wallet moved to another chain after Connect → WRONG_CHAIN, nothing sent', async () => {
  const { wallet, prepared } = await ready();
  wallet.state.chainId = '0x1';
  const { p, client, made } = run({ prepared, wallet });
  await assert.rejects(p, (e) => e.code === 'WRONG_CHAIN');
  assert.equal(client.calls.length, 0);
  assert.equal(made.length, 0);
});

test('wallet account changed after Connect → ACCOUNT_CHANGED, nothing sent', async () => {
  const { wallet, prepared } = await ready();
  wallet.state.accounts = [OTHER_ACCOUNT];
  const { p, client } = run({ prepared, wallet });
  await assert.rejects(p, (e) => e.code === 'ACCOUNT_CHANGED');
  assert.equal(client.calls.length, 0);
});

test('a client that reports another chain is refused before it can send', async () => {
  const { wallet, prepared } = await ready();
  const client = { ...mockClient(), chain: testnetAsimov };
  client.calls = [];
  const deployCalls = [];
  client.deployContract = async (a) => { deployCalls.push(a); return TX_ID; };
  await assert.rejects(deployAndVerify({ prepared, provider: wallet, chain: testnetBradbury, confirmed: true, makeClient: () => client }), (e) => e.code === 'WRONG_CONFIG');
  assert.equal(deployCalls.length, 0);
});

test('prepare stops when the consensus DATA contract has no code (receipts are read from it)', async () => {
  const rpc = mockRpc({ handlers: { eth_getCode: ([addr]) => (addr === BRADBURY.consensusDataContract ? '0x' : `0x${'60'.repeat(1159)}`) } });
  await assert.rejects(prepare({ provider: mockWallet(), rpcRequest: rpc, chain: testnetBradbury, source: SOURCE }), (e) => e.code === 'CONSENSUS_NOT_DEPLOYED' && /consensus data contract/.test(e.message));
  assert.deepEqual(rpc.calls.filter((c) => c.method === 'eth_getCode').map((c) => c.params[0]), [BRADBURY.consensusMainContract, BRADBURY.consensusDataContract]);
});

test('a non-Bradbury chain at deploy time is refused before the client exists', async () => {
  const { wallet, prepared } = await ready();
  const { p, made } = run({ prepared, wallet, chain: testnetAsimov });
  await assert.rejects(p, (e) => e.code === 'WRONG_CONFIG');
  assert.equal(made.length, 0);
});

test('rejected signature (plain 4001, viem-wrapped, or 4001 only on the cause) → REJECTED, no waiting, no retry', async () => {
  for (const err of [rejection(), wrappedRejection(), deepRejection()]) {
    const { wallet, prepared } = await ready();
    const client = mockClient({ deploy: async () => { throw err; } });
    await assert.rejects(run({ prepared, wallet, client }).p, (e) => e.code === 'REJECTED' && /nothing was sent/.test(e.message));
    assert.deepEqual(client.calls.map((c) => c[0]), ['deployContract']);
  }
});

test('send failure and a missing transaction id → SEND_FAILED', async () => {
  for (const deploy of [async () => { throw new Error('insufficient funds for gas'); }, async () => undefined, async () => '0x1234']) {
    const { wallet, prepared } = await ready();
    const client = mockClient({ deploy });
    await assert.rejects(run({ prepared, wallet, client }).p, (e) => e.code === 'SEND_FAILED');
    assert.deepEqual(client.calls.map((c) => c[0]), ['deployContract']);
  }
});

test('consensus never decides in the wait → NOT_DECIDED record with the transaction id (not a throw)', async () => {
  const { wallet, prepared } = await ready();
  const client = mockClient({ receipt: async () => { throw new Error('Timed out waiting for transaction'); } });
  const r = await run({ prepared, wallet, client, wait: { retries: 2, interval: 1 } }).p;
  assert.equal(r.outcome, 'NOT_DECIDED');
  assert.equal(r.txId, TX_ID);
  assert.match(r.error, /Timed out/);
  assert.deepEqual(client.calls[1][1].retries, 2);
  assert.ok(!client.calls.some((c) => c[0] === 'getContractCode'));
});

test('failed execution → FAILED_EXECUTION record (the plan: recorded as failed, then a fix PR)', async () => {
  const { wallet, prepared } = await ready();
  const client = mockClient({ receipt: async () => okReceipt({ txExecutionResultName: 'FINISHED_WITH_ERROR' }) });
  const r = await run({ prepared, wallet, client }).p;
  assert.equal(r.outcome, 'FAILED_EXECUTION');
  assert.equal(r.executionResult, 'FINISHED_WITH_ERROR');
  assert.equal(r.contractAddress, null);
  assert.ok(!client.calls.some((c) => c[0] === 'getContractCode'));
});

test('undecided or cancelled consensus → FAILED_CONSENSUS, even if an execution result is present', async () => {
  for (const statusName of ['UNDETERMINED', 'CANCELED', 'LEADER_TIMEOUT', 'VALIDATORS_TIMEOUT', undefined]) {
    const { wallet, prepared } = await ready();
    const r = await run({ prepared, wallet, client: mockClient({ receipt: async () => okReceipt({ statusName }) }) }).p;
    assert.equal(r.outcome, 'FAILED_CONSENSUS', String(statusName));
  }
});

test('no usable recipient → NO_ADDRESS; the address is never taken from anywhere else', async () => {
  for (const recipient of [undefined, null, `0x${'0'.repeat(40)}`, '0x123', CONTRACT.toUpperCase()]) {
    const { wallet, prepared } = await ready();
    // the contract address is on other fields too: none of them may be used
    const client = mockClient({ receipt: async () => ({ ...okReceipt({ recipient }), to: CONTRACT, to_address: CONTRACT, contractAddress: CONTRACT, txDataDecoded: { contractAddress: CONTRACT } }) });
    const r = await run({ prepared, wallet, client }).p;
    assert.equal(r.outcome, 'NO_ADDRESS', String(recipient));
    assert.equal(r.contractAddress, null);
  }
});

test('code read back differs → CODE_MISMATCH; unreadable → CODE_UNREADABLE', async () => {
  let { wallet, prepared } = await ready();
  let r = await run({ prepared, wallet, client: mockClient({ code: async () => SOURCE.replace('Storage', 'Storag3') }) }).p;
  assert.equal(r.outcome, 'CODE_MISMATCH');
  assert.equal(r.contractAddress, CONTRACT);
  assert.equal(r.code.matches, false);
  ({ wallet, prepared } = await ready());
  r = await run({ prepared, wallet, client: mockClient({ code: async () => { throw new Error('contract not found'); } }) }).p;
  assert.equal(r.outcome, 'CODE_UNREADABLE');
  assert.match(r.code.error, /not found/);
});

test('the record carries no secret and no source text', async () => {
  const { wallet, prepared } = await ready();
  const r = await run({ prepared, wallet }).p;
  const text = JSON.stringify(r);
  assert.ok(!text.includes('class Storage'), 'source text is not in the record (its hash is)');
  assert.ok(!/private|mnemonic|secret/i.test(text));
  assert.deepEqual(Object.keys(r).sort(), [
    'account', 'code', 'consensus', 'constructorArgs', 'decidedAt', 'executionResult', 'finishedAt', 'genlayerJs', 'network', 'note',
    'outcome', 'preparedAt', 'sameChain', 'schema', 'sentAt', 'source', 'statusName', 'txId', 'wallet', 'contractAddress', 'evmTxHash',
  ].sort());
});
