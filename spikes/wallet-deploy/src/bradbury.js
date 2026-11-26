// Pinned facts about the one network this page may deploy to: GenLayer testnet Bradbury.
// Everything here is checked against genlayer-js 1.1.8's own `testnetBradbury` (test/bradbury.test.mjs),
// so a library upgrade that moves any of them fails the tests instead of silently redirecting a deploy.
//
// Why the consensus contract matters (A1, 25 Nov): Bradbury and Asimov share chain id 4221 and the same
// underlying L2 (both RPCs serve rpc.testnet-chain.genlayer.com's blocks). What makes a deploy a
// Bradbury deploy is the transaction's `to`: Bradbury's consensus main contract. The page shows it
// before the owner signs, and MetaMask shows it again in its confirmation.
//
// Testnet only. There is no mainnet entry here and the guard refuses anything that is not exactly this.

export const BRADBURY = Object.freeze({
  key: 'testnetBradbury',
  name: 'Genlayer Bradbury Testnet',
  chainId: 4221,
  chainIdHex: '0x107d',
  rpcUrl: 'https://rpc-bradbury.genlayer.com',
  explorerUrl: 'https://explorer-bradbury.genlayer.com/',
  consensusMainContract: '0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D',
  nativeCurrency: Object.freeze({ name: 'GEN Token', symbol: 'GEN', decimals: 18 }),
  faucetUrl: 'https://testnet-faucet.genlayer.foundation',
});

/** The genlayer-js version this page was built and tested against (package.json pins it exactly). */
export const GENLAYER_JS_VERSION = '1.1.8';

/** sha256 of contract/storage.py, LF-normalised UTF-8. The page refuses to deploy any other bytes. */
export const EXPECTED_SOURCE_SHA256 = '99ad9c8fbf3aead54899c4cb32ed0fb29d2f7f84c467e44615cc007ea2bff294';

/** Constructor argument for the spike deploy. Not personal data; it only proves the constructor ran. */
export const INITIAL_STORAGE = 'odir-b1-wallet-deploy-spike';

/** wallet_addEthereumChain parameters (EIP-3085) for Bradbury. */
export const ADD_CHAIN_PARAMS = Object.freeze({
  chainId: BRADBURY.chainIdHex,
  chainName: BRADBURY.name,
  rpcUrls: Object.freeze([BRADBURY.rpcUrl]),
  nativeCurrency: BRADBURY.nativeCurrency,
  blockExplorerUrls: Object.freeze([BRADBURY.explorerUrl]),
});

export class DeployError extends Error {
  /** @param {string} code  a stable reason the page and the record show  @param {string} message */
  constructor(code, message, detail = undefined) {
    super(`${code}: ${message}`);
    this.name = 'DeployError';
    this.code = code;
    if (detail !== undefined) this.detail = detail;
  }
}

const sameAddress = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();

/**
 * Refuses any chain object that is not exactly testnet Bradbury: id, testnet flag, RPC, consensus contract,
 * not a Studio chain. Returns the list of checks it made (for the record).
 */
export function assertBradburyChain(chain) {
  const problems = [];
  if (!chain || typeof chain !== 'object') throw new DeployError('WRONG_CONFIG', 'no chain object');
  if (chain.id !== BRADBURY.chainId) problems.push(`chain id ${chain.id} is not ${BRADBURY.chainId}`);
  if (chain.testnet !== true) problems.push('chain is not marked testnet');
  if (chain.isStudio) problems.push('chain is a Studio chain');
  const rpc = chain.rpcUrls?.default?.http;
  if (!Array.isArray(rpc) || rpc.length !== 1 || rpc[0] !== BRADBURY.rpcUrl) problems.push(`RPC is ${JSON.stringify(rpc)}, not ${BRADBURY.rpcUrl}`);
  if (!sameAddress(chain.consensusMainContract?.address, BRADBURY.consensusMainContract)) {
    problems.push(`consensus main contract is ${chain.consensusMainContract?.address}, not Bradbury's ${BRADBURY.consensusMainContract}`);
  }
  if (problems.length) throw new DeployError('WRONG_CONFIG', `not testnet Bradbury — ${problems.join('; ')}`);
  return ['chain id 4221', 'testnet', 'not Studio', `RPC ${BRADBURY.rpcUrl}`, `consensus ${BRADBURY.consensusMainContract}`];
}
