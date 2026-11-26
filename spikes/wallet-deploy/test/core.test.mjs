// Unit tests for core.js helpers: hashing, account, network switch/add, same-chain check, rejections.
import test from 'node:test';
import assert from 'node:assert/strict';
import { ADD_CHAIN_PARAMS } from '../src/bradbury.js';
import {
  checkSameChain, ensureWalletOnBradbury, isRejection, lfNormalise, oneSignatureProvider, requestAccount, sha256Hex, verifyCode,
} from '../src/core.js';
import {
  ACCOUNT, CONTRACT, EVM_HASH, SOURCE, mockClient, mockRpc, mockWallet, rejection, wrappedRejection,
} from './helpers.mjs';

const methods = (w) => w.calls.map((c) => c.method);

test('lfNormalise turns CRLF and lone CR into LF and leaves everything else', () => {
  assert.equal(lfNormalise('a\r\nb\rc\nd'), 'a\nb\nc\nd');
  assert.equal(lfNormalise('\r\n\r\n'), '\n\n');
  assert.equal(lfNormalise('tab\tand ünïcode\n'), 'tab\tand ünïcode\n');
  assert.throws(() => lfNormalise(undefined), (e) => e.code === 'BAD_SOURCE');
  assert.throws(() => lfNormalise(new Uint8Array(1)), (e) => e.code === 'BAD_SOURCE');
});

test('sha256Hex matches the standard vectors and hashes UTF-8 bytes', async () => {
  assert.equal(await sha256Hex(''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  assert.equal(await sha256Hex('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  assert.notEqual(await sha256Hex('é'), await sha256Hex('e'));
  assert.equal(await sha256Hex(lfNormalise(SOURCE.replace(/\n/g, '\r\n'))), await sha256Hex(SOURCE), 'CRLF copy hashes like the LF source');
  await assert.rejects(sha256Hex('x', null), (e) => e.code === 'NO_CRYPTO');
});

test('isRejection finds 4001 directly, on a cause, in originalError, and viem\'s named error', () => {
  assert.ok(isRejection(rejection()));
  assert.ok(isRejection(wrappedRejection()));
  assert.ok(isRejection({ code: -32603, data: { originalError: { code: 4001 } } }));
  assert.ok(isRejection(Object.assign(new Error('x'), { name: 'UserRejectedRequestError' })));
  // viem: TransactionExecutionError → cause with code 4001 only (no rejection marker at the top level)
  const deep = Object.assign(new Error('Transaction failed'), { name: 'TransactionExecutionError', cause: Object.assign(new Error('rejected'), { code: 4001 }) });
  assert.ok(isRejection(deep), 'a 4001 one level down counts');
  assert.ok(isRejection({ name: 'X', cause: { name: 'Y', cause: { code: -32603, data: { originalError: { code: 4001 } } } } }), 'two levels down, inside originalError');
  assert.ok(!isRejection(new Error('insufficient funds')));
  assert.ok(!isRejection(Object.assign(new Error('Unrecognized chain'), { code: 4902 })));
  const loop = new Error('loop'); loop.cause = loop;
  assert.ok(!isRejection(loop), 'a cyclic cause chain ends');
});

test('requestAccount returns the first account; refuses rejection, no account and junk', async () => {
  assert.equal(await requestAccount(mockWallet()), ACCOUNT);
  await assert.rejects(requestAccount(mockWallet({ handlers: { eth_requestAccounts: () => { throw rejection(); } } })), (e) => e.code === 'REJECTED');
  await assert.rejects(requestAccount(mockWallet({ accounts: [] })), (e) => e.code === 'NO_ACCOUNT');
  await assert.rejects(requestAccount(mockWallet({ accounts: ['not-an-address'] })), (e) => e.code === 'NO_ACCOUNT');
  await assert.rejects(requestAccount(mockWallet({ handlers: { eth_requestAccounts: () => { throw new Error('locked'); } } })), (e) => e.code === 'NO_ACCOUNT');
});

test('already on 4221: no switch, no add', async () => {
  const w = mockWallet();
  assert.deepEqual(await ensureWalletOnBradbury(w), { before: '0x107d', switched: false, added: false });
  assert.deepEqual(methods(w), ['eth_chainId']);
});

test('chain id spelling does not matter (0x107D, 0x0107d)', async () => {
  for (const id of ['0x107D', '0x0107d']) {
    const w = mockWallet({ chainId: id });
    assert.equal((await ensureWalletOnBradbury(w)).switched, false);
  }
});

test('on another chain the wallet knows Bradbury: one switch, no add', async () => {
  const w = mockWallet({ chainId: '0x1', known: ['0x1', '0x107d'] });
  assert.deepEqual(await ensureWalletOnBradbury(w), { before: '0x1', switched: true, added: false });
  assert.deepEqual(methods(w), ['eth_chainId', 'wallet_switchEthereumChain', 'eth_chainId']);
  assert.deepEqual(w.calls[1].params, [{ chainId: '0x107d' }]);
});

test('unknown chain (4902): adds Bradbury with exactly its parameters, then switches', async () => {
  const w = mockWallet({ chainId: '0x1', known: ['0x1'] });
  assert.deepEqual(await ensureWalletOnBradbury(w), { before: '0x1', switched: true, added: true });
  assert.deepEqual(methods(w), ['eth_chainId', 'wallet_switchEthereumChain', 'wallet_addEthereumChain', 'wallet_switchEthereumChain', 'eth_chainId']);
  assert.deepEqual(w.calls[2].params, [ADD_CHAIN_PARAMS]);
});

test('4902 wrapped in a -32603 originalError (mobile wallets) is still "unknown chain"', async () => {
  let first = true;
  const w = mockWallet({
    chainId: '0x1', known: ['0x1'],
    handlers: {
      wallet_switchEthereumChain: ([p], s) => {
        if (first) { first = false; throw { code: -32603, data: { originalError: { code: 4902 } } }; }
        s.chainId = p.chainId; return null;
      },
    },
  });
  assert.equal((await ensureWalletOnBradbury(w)).added, true);
});

test('switch, add or second switch rejected → REJECTED; other failures named', async () => {
  const cases = [
    [{ wallet_switchEthereumChain: () => { throw rejection(); } }, ['0x1', '0x107d'], 'REJECTED'],
    [{ wallet_addEthereumChain: () => { throw rejection(); } }, ['0x1'], 'REJECTED'],
    [{ wallet_addEthereumChain: () => { throw new Error('bad rpc url'); } }, ['0x1'], 'ADD_FAILED'],
    [{ wallet_switchEthereumChain: () => { throw new Error('busy'); } }, ['0x1', '0x107d'], 'SWITCH_FAILED'],
  ];
  for (const [handlers, known, code] of cases) {
    const w = mockWallet({ chainId: '0x1', known, handlers });
    await assert.rejects(ensureWalletOnBradbury(w), (e) => e.code === code, code);
    if (code === 'SWITCH_FAILED') assert.ok(!methods(w).includes('wallet_addEthereumChain'), 'a switch error that is not 4902 never adds a network');
  }
  const w32603 = mockWallet({ chainId: '0x1', handlers: { wallet_switchEthereumChain: () => { throw Object.assign(new Error('Internal error'), { code: -32603 }); } } });
  await assert.rejects(ensureWalletOnBradbury(w32603), (e) => e.code === 'SWITCH_FAILED');
  assert.ok(!methods(w32603).includes('wallet_addEthereumChain'));
  let n = 0;
  const secondRejected = mockWallet({
    chainId: '0x1', known: ['0x1'],
    handlers: { wallet_switchEthereumChain: () => { n += 1; throw n === 1 ? Object.assign(new Error('?'), { code: 4902 }) : rejection(); } },
  });
  await assert.rejects(ensureWalletOnBradbury(secondRejected), (e) => e.code === 'REJECTED');
});

test('a wallet that says "switched" but stays elsewhere → WRONG_CHAIN', async () => {
  const w = mockWallet({ chainId: '0x1', handlers: { wallet_switchEthereumChain: () => null } });
  await assert.rejects(ensureWalletOnBradbury(w), (e) => e.code === 'WRONG_CHAIN');
});

test('same chain: compares one block a few below the lower head, both sides', async () => {
  const w = mockWallet(); const rpc = mockRpc();
  const r = await checkSameChain(w, rpc);
  const expected = `0x${(0xae46e - 3).toString(16)}`;
  assert.equal(r.height, expected);
  assert.deepEqual(w.calls.find((c) => c.method === 'eth_getBlockByNumber').params, [expected, false]);
  assert.deepEqual(rpc.calls.find((c) => c.method === 'eth_getBlockByNumber').params, [expected, false]);
});

test('different block hash at the same height → WRONG_CHAIN naming Bradbury\'s RPC', async () => {
  await assert.rejects(checkSameChain(mockWallet({ salt: 'c' }), mockRpc({ salt: 'b' })), (e) => e.code === 'WRONG_CHAIN' && /rpc-bradbury/.test(e.message));
});

test('unusable answers → SAME_CHAIN_UNVERIFIED (never a pass)', async () => {
  const zero = `0x${'0'.repeat(64)}`;
  const cases = [
    [mockWallet({ handlers: { eth_blockNumber: () => { throw new Error('wallet RPC down (522)'); } } }), mockRpc()],
    [mockWallet(), mockRpc({ handlers: { eth_blockNumber: () => 'nope' } })],
    [mockWallet({ head: 2 }), mockRpc({ head: 2 })],
    [mockWallet({ handlers: { eth_getBlockByNumber: () => null } }), mockRpc()],
    [mockWallet(), mockRpc({ handlers: { eth_getBlockByNumber: ([n]) => ({ number: n, hash: zero }) } })],
    [mockWallet({ handlers: { eth_getBlockByNumber: ([n]) => ({ number: n, hash: zero }) } }), mockRpc({ handlers: { eth_getBlockByNumber: ([n]) => ({ number: n, hash: zero }) } })],
    [mockWallet(), mockRpc({ handlers: { eth_getBlockByNumber: () => { throw new Error('timeout'); } } })],
  ];
  for (const [w, rpc] of cases) {
    await assert.rejects(checkSameChain(w, rpc), (e) => e.code === 'SAME_CHAIN_UNVERIFIED');
  }
});

test('verifyCode: raw match, LF-only match, unreadable, bad address', async () => {
  const sha = await sha256Hex(SOURCE);
  assert.deepEqual(await verifyCode(mockClient(), CONTRACT, sha), { sha256: sha, matches: true, matchesAfterLf: true });
  const crlf = await verifyCode(mockClient({ code: async () => SOURCE.replace(/\n/g, '\r\n') }), CONTRACT, sha);
  assert.equal(crlf.matches, false);
  assert.equal(crlf.matchesAfterLf, true);
  const other = await verifyCode(mockClient({ code: async () => `${SOURCE}# changed\n` }), CONTRACT, sha);
  assert.equal(other.matches, false);
  assert.equal(other.matchesAfterLf, false);
  const down = await verifyCode(mockClient({ code: async () => { throw new Error('not found'); } }), CONTRACT, sha);
  assert.equal(down.sha256, null);
  assert.match(down.error, /not found/);
  assert.equal((await verifyCode(mockClient({ code: async () => null }), CONTRACT, sha)).sha256, null);
  await assert.rejects(verifyCode(mockClient(), `0x${'0'.repeat(40)}`, sha), (e) => e.code === 'NO_ADDRESS');
  await assert.rejects(verifyCode(mockClient(), 'x', sha), (e) => e.code === 'NO_ADDRESS');
});

test('oneSignatureProvider: one eth_sendTransaction, then refusal; no other signing; no Snaps; reads pass through', async () => {
  const w = mockWallet({ handlers: { eth_sendTransaction: () => EVM_HASH, personal_sign: () => '0xsig' } });
  const g = oneSignatureProvider(w);
  assert.equal(await g.request({ method: 'eth_chainId' }), '0x107d');
  assert.equal(await g.request({ method: 'eth_sendTransaction', params: [{}] }), EVM_HASH);
  assert.equal(g.state.evmTxHash, EVM_HASH);
  await assert.rejects(g.request({ method: 'eth_sendTransaction', params: [{}] }), (e) => e.code === 'SECOND_SIGNATURE_REFUSED');
  for (const method of ['eth_signTransaction', 'personal_sign', 'eth_sign', 'eth_signTypedData_v4', 'eth_signTypedData']) {
    await assert.rejects(g.request({ method, params: [] }), (e) => e.code === 'SIGNING_REFUSED', method);
  }
  for (const method of ['wallet_requestSnaps', 'wallet_getSnaps', 'wallet_invokeSnap']) {
    await assert.rejects(g.request({ method, params: {} }), (e) => e.code === 'SNAP_REFUSED', method);
  }
  assert.equal(w.calls.filter((x) => x.method === 'eth_sendTransaction').length, 1, 'the wallet saw exactly one send');
  assert.ok(!w.calls.some((x) => /sign|Snap/.test(x.method)), 'refused methods never reach the wallet');
});

test('oneSignatureProvider: a failed or rejected first send still uses up the one signature', async () => {
  for (const fail of [() => { throw rejection(); }, () => { throw new Error('could not decode result data'); }]) {
    const g = oneSignatureProvider(mockWallet({ handlers: { eth_sendTransaction: fail } }));
    await assert.rejects(g.request({ method: 'eth_sendTransaction', params: [{}] }));
    assert.equal(g.state.evmTxHash, null);
    await assert.rejects(g.request({ method: 'eth_sendTransaction', params: [{}] }), (e) => e.code === 'SECOND_SIGNATURE_REFUSED');
  }
  const junk = oneSignatureProvider(mockWallet({ handlers: { eth_sendTransaction: () => 'not-a-hash' } }));
  await junk.request({ method: 'eth_sendTransaction', params: [{}] });
  assert.equal(junk.state.evmTxHash, null, 'only a 32-byte hash counts as broadcast');
});
