// Wallet-deploy spike core (ODIR Brain slice B1). Pure logic: the wallet (EIP-1193 provider), the direct
// Bradbury RPC and the genlayer-js client all come in as arguments, so every path runs under node --test
// with a mock wallet. main.js wires the real ones in the browser.
//
// Two phases, and the owner is between them:
//   prepare()          source hash, account, network switch (adding Bradbury if needed), same-chain check,
//                      and the consensus contract really has code on chain. Nothing is signed. The page then shows the hash, network and consensus contract.
//   deployAndVerify()  only after the owner ticks "I have checked" and presses Deploy: one MetaMask
//                      signature, wait for consensus, address from the receipt's recipient, code read back.
//
// Never: client.connect() (it installs a MetaMask Snap and swaps client.chain), a private key, mainnet,
// a second transaction, or a retry that signs again. genlayer-js 1.1.8 itself retries a failed send with a second
// calldata encoding (_sendTransaction's ABI-mismatch fallback); the client only ever sees oneSignatureProvider(),
// which lets exactly one eth_sendTransaction through and refuses every other signing method.

import {
  ADD_CHAIN_PARAMS, BRADBURY, DeployError, EXPECTED_SOURCE_SHA256, GENLAYER_JS_VERSION, INITIAL_STORAGE,
  assertBradburyChain,
} from './bradbury.js';

export const RECORD_SCHEMA = 'odir.b1-wallet-deploy-record.v1';
export const SOURCE_PATH = 'spikes/wallet-deploy/contract/storage.py';
/** Consensus can take minutes on a testnet: 240 polls x 5 s = 20 min before the page reports NOT_DECIDED. */
export const DEFAULT_WAIT = Object.freeze({ retries: 240, interval: 5000 });

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const ZERO_ADDRESS = /^0x0{40}$/;
const TX_ID = /^0x[0-9a-fA-F]{64}$/;
const ZERO_HASH = /^0x0{64}$/;
const DECIDED_OK = new Set(['ACCEPTED', 'FINALIZED']);

/** CRLF and lone CR become LF. Nothing else changes: the deployed bytes are exactly these. */
export function lfNormalise(text) {
  if (typeof text !== 'string') throw new DeployError('BAD_SOURCE', 'contract source is not text');
  return text.replace(/\r\n?/g, '\n');
}

/** SHA-256 of the UTF-8 bytes of `text`, lower-case hex (WebCrypto: browser and Node alike). */
export async function sha256Hex(text, subtle = globalThis.crypto?.subtle) {
  if (!subtle) throw new DeployError('NO_CRYPTO', 'WebCrypto is not available');
  const digest = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
}

/** Walks an error and its causes (viem wraps wallet errors), returning the first value `pick` finds. */
function findInErrorChain(err, pick) {
  const seen = new Set();
  for (let e = err; e && typeof e === 'object' && !seen.has(e); e = e.cause) {
    seen.add(e);
    const v = pick(e);
    if (v !== undefined && v !== null) return v;
  }
  return undefined;
}
const errorCodes = (err) => {
  const codes = [];
  findInErrorChain(err, (e) => { codes.push(e.code, e.data?.originalError?.code); return undefined; });
  return codes.filter((c) => c !== undefined);
};
// Our own refusals (a DeployError somewhere in viem's wrapping) say exactly what happened; prefer them.
const errorText = (err) => findInErrorChain(err, (e) => (e.name === 'DeployError' ? e.message : undefined))
  ?? findInErrorChain(err, (e) => e.shortMessage || e.message) ?? String(err);
/** EIP-1193 4001, or viem's UserRejectedRequestError anywhere in the chain. */
export const isRejection = (err) =>
  errorCodes(err).includes(4001) || findInErrorChain(err, (e) => (e.name === 'UserRejectedRequestError' ? true : undefined)) === true;
const isUnknownChain = (err) => errorCodes(err).includes(4902);

const toInt = (hex) => (typeof hex === 'string' && /^0x[0-9a-fA-F]+$/.test(hex) ? parseInt(hex, 16) : NaN);
const normChainId = (hex) => (Number.isFinite(toInt(hex)) ? `0x${toInt(hex).toString(16)}` : String(hex));
const sameAddress = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();

const SIGNING_METHODS = new Set(['eth_sendTransaction', 'eth_signTransaction', 'eth_sign', 'personal_sign', 'eth_signTypedData', 'eth_signTypedData_v3', 'eth_signTypedData_v4']);
const SNAP_METHODS = /^wallet_(requestSnaps|getSnaps|invokeSnap)$/;

/**
 * The wallet as the genlayer-js client sees it: one eth_sendTransaction, ever; no other signing method; no Snaps.
 * Everything else is passed through. Keeps the EVM hash the wallet returns, so a failure after the broadcast is
 * still recorded (gas was spent).
 */
export function oneSignatureProvider(provider) {
  const state = { sendAttempts: 0, evmTxHash: null };
  return {
    state,
    async request(args) {
      const method = args?.method;
      if (SNAP_METHODS.test(method ?? '')) throw new DeployError('SNAP_REFUSED', `${method} is never part of this deploy`);
      if (SIGNING_METHODS.has(method)) {
        if (method !== 'eth_sendTransaction') throw new DeployError('SIGNING_REFUSED', `${method} is never part of this deploy`);
        if (state.sendAttempts >= 1) {
          throw new DeployError('SECOND_SIGNATURE_REFUSED', 'the library asked for a second signature (its fallback encoding); refused — one signature per Connect');
        }
        state.sendAttempts += 1;
        const hash = await provider.request(args);
        if (typeof hash === 'string' && TX_ID.test(hash)) state.evmTxHash = hash;
        return hash;
      }
      return provider.request(args);
    },
  };
}

/** eth_requestAccounts → the first account. */
export async function requestAccount(provider) {
  let accounts;
  try {
    accounts = await provider.request({ method: 'eth_requestAccounts' });
  } catch (err) {
    if (isRejection(err)) throw new DeployError('REJECTED', 'the wallet connection was rejected');
    throw new DeployError('NO_ACCOUNT', errorText(err));
  }
  if (!Array.isArray(accounts) || !ADDRESS.test(accounts[0] ?? '')) throw new DeployError('NO_ACCOUNT', 'the wallet returned no account');
  return accounts[0];
}

/**
 * Puts the wallet on chain 4221 with wallet_switchEthereumChain; if the wallet does not know the chain (4902),
 * adds Bradbury with wallet_addEthereumChain and switches again. Never requests a Snap.
 */
export async function ensureWalletOnBradbury(provider) {
  const before = normChainId(await provider.request({ method: 'eth_chainId' }));
  if (before === BRADBURY.chainIdHex) return { before, switched: false, added: false };
  let added = false;
  const switchChain = () => provider.request({ method: 'wallet_switchEthereumChain', params: [{ chainId: BRADBURY.chainIdHex }] });
  try {
    await switchChain();
  } catch (err) {
    if (isRejection(err)) throw new DeployError('REJECTED', 'the network switch was rejected in the wallet');
    if (!isUnknownChain(err)) throw new DeployError('SWITCH_FAILED', errorText(err));
    try {
      await provider.request({ method: 'wallet_addEthereumChain', params: [ADD_CHAIN_PARAMS] });
      added = true;
    } catch (addErr) {
      if (isRejection(addErr)) throw new DeployError('REJECTED', 'adding Bradbury was rejected in the wallet');
      throw new DeployError('ADD_FAILED', errorText(addErr));
    }
    try {
      await switchChain();
    } catch (err2) {
      if (isRejection(err2)) throw new DeployError('REJECTED', 'the network switch was rejected in the wallet');
      throw new DeployError('SWITCH_FAILED', errorText(err2));
    }
  }
  const after = normChainId(await provider.request({ method: 'eth_chainId' }));
  if (after !== BRADBURY.chainIdHex) throw new DeployError('WRONG_CHAIN', `the wallet is on ${after} after switching, not ${BRADBURY.chainIdHex}`);
  return { before, switched: true, added };
}

/**
 * Chain id 4221 is not proof of the chain: any network can claim it. Compares the hash of one recent block
 * as the wallet's RPC sees it and as Bradbury's RPC sees it. (Asimov's RPC serves the same L2, so this
 * proves the L2, not the testnet; the testnet is fixed by the consensus contract the transaction calls.)
 */
export async function checkSameChain(provider, rpcRequest, { lag = 3 } = {}) {
  let walletHead; let rpcHead;
  try {
    [walletHead, rpcHead] = await Promise.all([
      provider.request({ method: 'eth_blockNumber' }),
      rpcRequest('eth_blockNumber', []),
    ]);
  } catch (err) {
    throw new DeployError('SAME_CHAIN_UNVERIFIED', `could not read the block height: ${errorText(err)}`);
  }
  const height = Math.min(toInt(walletHead), toInt(rpcHead)) - lag;
  if (!Number.isFinite(height) || height <= 0) throw new DeployError('SAME_CHAIN_UNVERIFIED', `bad block heights ${walletHead} / ${rpcHead}`);
  const heightHex = `0x${height.toString(16)}`;
  let walletBlock; let rpcBlock;
  try {
    [walletBlock, rpcBlock] = await Promise.all([
      provider.request({ method: 'eth_getBlockByNumber', params: [heightHex, false] }),
      rpcRequest('eth_getBlockByNumber', [heightHex, false]),
    ]);
  } catch (err) {
    throw new DeployError('SAME_CHAIN_UNVERIFIED', `could not read block ${heightHex}: ${errorText(err)}`);
  }
  const wHash = walletBlock?.hash; const rHash = rpcBlock?.hash;
  if (typeof wHash !== 'string' || typeof rHash !== 'string' || ZERO_HASH.test(rHash) || ZERO_HASH.test(wHash)) {
    throw new DeployError('SAME_CHAIN_UNVERIFIED', `no usable block hash at ${heightHex}`);
  }
  if (wHash.toLowerCase() !== rHash.toLowerCase()) {
    throw new DeployError('WRONG_CHAIN', `the wallet's chain 4221 is not Bradbury's chain (block ${heightHex}: ${wHash} vs ${rHash}). Point the wallet's 4221 network at ${BRADBURY.rpcUrl}.`);
  }
  return { height: heightHex, hash: rHash };
}

/**
 * The deploy is an EVM call to the consensus main contract. If that address has no code, the call "succeeds",
 * spends gas, emits no NewTransaction log and deploys nothing. So: no code there, no signature.
 * (26 Nov 2026, OBSERVED: genlayer-js 1.1.8's Bradbury addresses have no code on chain; see the B1 record.)
 */
export async function checkConsensusDeployed(rpcRequest, address = BRADBURY.consensusMainContract, role = 'consensus') {
  if (!ADDRESS.test(address ?? '')) throw new DeployError('CONSENSUS_UNVERIFIED', `no ${role} contract address`);
  let code;
  try {
    code = await rpcRequest('eth_getCode', [address, 'latest']);
  } catch (err) {
    throw new DeployError('CONSENSUS_UNVERIFIED', `could not read the code at the ${role} contract ${address}: ${errorText(err)}`);
  }
  if (typeof code !== 'string' || !/^0x[0-9a-fA-F]*$/.test(code)) throw new DeployError('CONSENSUS_UNVERIFIED', `unreadable code at ${address}`);
  const bytes = (code.length - 2) / 2;
  if (bytes === 0) {
    throw new DeployError('CONSENSUS_NOT_DEPLOYED', `Bradbury's ${role} contract ${address} (genlayer-js ${GENLAYER_JS_VERSION}) has no code on chain: the library's Bradbury addresses are out of date. A deploy would spend gas and deploy nothing. Nothing was signed.`);
  }
  return { address, codeBytes: bytes };
}

/** Phase 1: everything up to (not including) the signature. Signs nothing. */
export async function prepare({ provider, rpcRequest, chain, source, expectedSha256 = EXPECTED_SOURCE_SHA256, now = () => new Date().toISOString() }) {
  const chainChecks = assertBradburyChain(chain);
  const code = lfNormalise(source);
  const sourceSha256 = await sha256Hex(code);
  if (sourceSha256 !== expectedSha256) {
    throw new DeployError('SOURCE_MISMATCH', `the contract source hashes to ${sourceSha256}, not the pinned ${expectedSha256}`);
  }
  const account = await requestAccount(provider);
  const wallet = await ensureWalletOnBradbury(provider);
  const sameChain = await checkSameChain(provider, rpcRequest);
  // Both: the deploy goes to the main contract, and its status and receipt are read from the data contract.
  const consensus = {
    main: await checkConsensusDeployed(rpcRequest, chain.consensusMainContract.address, 'consensus'),
    data: await checkConsensusDeployed(rpcRequest, chain.consensusDataContract?.address, 'consensus data'),
  };
  return Object.freeze({
    code, sourceSha256, bytes: new TextEncoder().encode(code).length, account, wallet, sameChain, consensus, chainChecks, preparedAt: now(),
  });
}

function baseRecord(prepared) {
  return {
    schema: RECORD_SCHEMA,
    outcome: null,
    network: {
      key: BRADBURY.key, name: BRADBURY.name, chainId: BRADBURY.chainId, rpcUrl: BRADBURY.rpcUrl,
      consensusMainContract: BRADBURY.consensusMainContract, explorerUrl: BRADBURY.explorerUrl,
    },
    genlayerJs: GENLAYER_JS_VERSION,
    account: prepared.account,
    source: { path: SOURCE_PATH, sha256: prepared.sourceSha256, bytes: prepared.bytes, lfNormalised: true },
    constructorArgs: [INITIAL_STORAGE],
    wallet: { switched: prepared.wallet.switched, added: prepared.wallet.added },
    sameChain: prepared.sameChain,
    consensus: prepared.consensus,
    evmTxHash: null, txId: null, statusName: null, executionResult: null, contractAddress: null,
    code: null,
    preparedAt: prepared.preparedAt, sentAt: null, decidedAt: null, finishedAt: null,
    note: 'Paste into the B1 ODIR record. Grade OBSERVED only what this page and the explorer showed.',
  };
}

/** Reads the deployed code back and compares its SHA-256 with the source hash (raw bytes, no normalising). */
export async function verifyCode(client, address, expectedSha256) {
  if (!ADDRESS.test(address ?? '') || ZERO_ADDRESS.test(address)) throw new DeployError('NO_ADDRESS', `not a contract address: ${address}`);
  let code;
  try {
    code = await client.getContractCode(address);
  } catch (err) {
    return { sha256: null, matches: false, matchesAfterLf: false, error: errorText(err) };
  }
  if (typeof code !== 'string') return { sha256: null, matches: false, matchesAfterLf: false, error: 'no code returned' };
  const sha256 = await sha256Hex(code);
  const matchesAfterLf = sha256 === expectedSha256 || (await sha256Hex(lfNormalise(code))) === expectedSha256;
  return { sha256, matches: sha256 === expectedSha256, matchesAfterLf };
}

/**
 * Phase 2: one signature. Throws only when the wallet broadcast nothing; once it has broadcast (an EVM hash came
 * back), always returns a record with an outcome, so a slow or failed deploy is still written down.
 */
export async function deployAndVerify({
  prepared, provider, makeClient, chain, confirmed, wait = DEFAULT_WAIT, onStep = () => {}, now = () => new Date().toISOString(),
}) {
  if (confirmed !== true) throw new DeployError('NOT_CONFIRMED', 'tick the confirmation first: source hash, network and consensus contract checked');
  assertBradburyChain(chain);
  // The owner may have changed network or account while reading: re-check both right before the signature.
  const chainNow = normChainId(await provider.request({ method: 'eth_chainId' }));
  if (chainNow !== BRADBURY.chainIdHex) throw new DeployError('WRONG_CHAIN', `the wallet moved to ${chainNow}; press Connect again`);
  const accountsNow = await provider.request({ method: 'eth_accounts' });
  if (!Array.isArray(accountsNow) || !accountsNow.some((a) => sameAddress(a, prepared.account))) {
    throw new DeployError('ACCOUNT_CHANGED', 'the wallet account changed; press Connect again');
  }

  const guarded = oneSignatureProvider(provider);
  const client = makeClient({ chain, account: prepared.account, provider: guarded });
  if (client?.chain && client.chain !== chain) assertBradburyChain(client.chain);
  const record = baseRecord(prepared);
  const finish = (outcome, extra = {}) => Object.assign(record, extra, { outcome, finishedAt: now() });
  onStep('signing', record);

  let txId; let sendError = null;
  try {
    txId = await client.deployContract({ code: prepared.code, args: [INITIAL_STORAGE], leaderOnly: false });
  } catch (err) {
    sendError = err;
  }
  record.evmTxHash = guarded.state.evmTxHash;
  if (sendError || !TX_ID.test(txId ?? '')) {
    const reason = sendError ? errorText(sendError) : `the client returned no transaction id (${txId})`;
    // The wallet broadcast it (gas spent) but no GenLayer transaction came of it: write that down, do not throw.
    if (record.evmTxHash) return finish('SENT_NOT_PROCESSED', { sentAt: now(), error: reason });
    if (sendError && isRejection(sendError)) throw new DeployError('REJECTED', 'the deploy signature was rejected in the wallet; nothing was sent');
    throw new DeployError('SEND_FAILED', `${reason}; nothing was broadcast`);
  }
  record.txId = txId;
  record.sentAt = now();
  onStep('sent', record);

  let receipt;
  try {
    receipt = await client.waitForTransactionReceipt({
      hash: txId, status: 'ACCEPTED', retries: wait.retries, interval: wait.interval, fullTransaction: true,
    });
  } catch (err) {
    return finish('NOT_DECIDED', { error: errorText(err) });
  }
  record.decidedAt = now();
  record.statusName = receipt?.statusName ?? null;
  record.executionResult = receipt?.txExecutionResultName ?? null;
  onStep('decided', record);

  if (!DECIDED_OK.has(record.statusName)) return finish('FAILED_CONSENSUS');
  if (record.executionResult !== 'FINISHED_WITH_RETURN') return finish('FAILED_EXECUTION');

  const address = receipt?.recipient;
  if (!ADDRESS.test(address ?? '') || ZERO_ADDRESS.test(address)) return finish('NO_ADDRESS', { error: `receipt recipient is ${address}` });
  record.contractAddress = address;

  record.code = await verifyCode(client, address, prepared.sourceSha256);
  if (record.code.sha256 === null) return finish('CODE_UNREADABLE');
  if (!record.code.matches) return finish('CODE_MISMATCH');
  return finish('DEPLOYED_VERIFIED');
}
