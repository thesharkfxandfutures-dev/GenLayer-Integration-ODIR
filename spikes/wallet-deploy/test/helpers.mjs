// Test doubles: an EIP-1193 wallet, the direct Bradbury RPC, and a genlayer-js client.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const SOURCE = readFileSync(join(ROOT, 'contract', 'storage.py'), 'utf8');
export const ACCOUNT = '0x1111111111111111111111111111111111111111';
export const OTHER_ACCOUNT = '0x2222222222222222222222222222222222222222';
export const TX_ID = `0x${'ab'.repeat(32)}`;
export const EVM_HASH = `0x${'cd'.repeat(32)}`;
export const CONTRACT = '0x3333333333333333333333333333333333333333';
export const HEAD = 0xae46e;
export const blockHash = (n, salt = 'b') => `0x${n.toString(16).padStart(8, '0')}${salt.repeat(56)}`;

export const rejection = (message = 'User rejected the request.') => Object.assign(new Error(message), { code: 4001 });
/** viem-style wrapping: the 4001 sits on the cause, not the outer error. */
export const wrappedRejection = () => Object.assign(new Error('An internal error was received.'), {
  name: 'UserRejectedRequestError', shortMessage: 'User rejected the request.', cause: rejection(),
});
/** viem's outer TransactionExecutionError: nothing at the top says "rejected"; only the cause carries 4001. */
export const deepRejection = () => Object.assign(new Error('Transaction failed.'), { name: 'TransactionExecutionError', cause: rejection() });

/**
 * A wallet. `chainId` is where it starts, `known` the chains it can switch to; `handlers` override any method.
 * It refuses anything a correct page never asks for (Snaps, signing a private key, unknown methods).
 */
export function mockWallet({ chainId = '0x107d', known = ['0x107d'], accounts = [ACCOUNT], head = HEAD, salt = 'b', handlers = {} } = {}) {
  const calls = [];
  const state = { chainId, known: new Set(known), accounts };
  const base = {
    eth_chainId: () => state.chainId,
    eth_requestAccounts: () => state.accounts,
    eth_accounts: () => state.accounts,
    wallet_switchEthereumChain: ([p]) => {
      if (!state.known.has(p.chainId)) throw Object.assign(new Error('Unrecognized chain ID'), { code: 4902 });
      state.chainId = p.chainId;
      return null;
    },
    wallet_addEthereumChain: ([p]) => { state.known.add(p.chainId); return null; },
    eth_blockNumber: () => `0x${head.toString(16)}`,
    eth_getBlockByNumber: ([n]) => ({ number: n, hash: blockHash(parseInt(n, 16), salt) }),
    eth_sendTransaction: () => { throw new Error('no eth_sendTransaction handler in this test'); },
  };
  const forbidden = new Set(['wallet_requestSnaps', 'wallet_getSnaps', 'wallet_invokeSnap', 'eth_sign', 'personal_sign', 'eth_signTypedData_v4']);
  const provider = {
    calls,
    state,
    async request({ method, params = [] }) {
      calls.push({ method, params });
      if (forbidden.has(method)) throw new Error(`forbidden wallet method ${method}`);
      const fn = handlers[method] ?? base[method];
      if (!fn) throw new Error(`unexpected wallet method ${method}`);
      return fn(params, state);
    },
  };
  return provider;
}

/** Bradbury's RPC as the page reads it directly. Same block hashes as mockWallet unless `salt` differs. */
export function mockRpc({ head = HEAD + 2, salt = 'b', handlers = {} } = {}) {
  const calls = [];
  const base = {
    eth_blockNumber: () => `0x${head.toString(16)}`,
    eth_getBlockByNumber: ([n]) => ({ number: n, hash: blockHash(parseInt(n, 16), salt) }),
    eth_getCode: () => `0x${'60'.repeat(1159)}`, // a deployed proxy's worth of bytes
  };
  const rpc = async (method, params) => {
    calls.push({ method, params });
    const fn = handlers[method] ?? base[method];
    if (!fn) throw new Error(`unexpected rpc method ${method}`);
    return fn(params);
  };
  rpc.calls = calls;
  return rpc;
}

export const okReceipt = (over = {}) => ({
  statusName: 'ACCEPTED', txExecutionResultName: 'FINISHED_WITH_RETURN', recipient: CONTRACT, ...over,
});

/** A genlayer-js client double. connect() throws: the page must never call it. */
export function mockClient({ deploy = async () => TX_ID, receipt = async () => okReceipt(), code = async () => SOURCE } = {}) {
  const calls = [];
  return {
    calls,
    async deployContract(a) { calls.push(['deployContract', a]); return deploy(a); },
    async waitForTransactionReceipt(a) { calls.push(['waitForTransactionReceipt', a]); return receipt(a); },
    async getContractCode(addr) { calls.push(['getContractCode', addr]); return code(addr); },
    async connect() { calls.push(['connect']); throw new Error('client.connect() must never be called'); },
  };
}
