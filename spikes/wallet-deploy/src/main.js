// Browser glue for the wallet-deploy spike. All decisions live in core.js; this file only wires the
// real wallet (window.ethereum), the real Bradbury RPC and the real genlayer-js client to the page.
// The contract source is bundled into this file at build time (esbuild text loader), so the bytes the
// page hashes and shows are the bytes it deploys.
import { createClient } from 'genlayer-js';
import { testnetBradbury } from 'genlayer-js/chains';
import source from '../contract/storage.py';
import { BRADBURY, EXPECTED_SOURCE_SHA256, GENLAYER_JS_VERSION, INITIAL_STORAGE } from './bradbury.js';
import { deployAndVerify, lfNormalise, prepare, sha256Hex, verifyCode } from './core.js';

const $ = (id) => document.getElementById(id);
const show = (id, text) => { $(id).textContent = text; };
const log = (text) => {
  const li = document.createElement('li');
  li.textContent = `${new Date().toISOString().slice(11, 19)}  ${text}`;
  $('log').append(li);
};

let rpcId = 0;
async function rpcRequest(method, params) {
  const res = await fetch(BRADBURY.rpcUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: (rpcId += 1), method, params }),
  });
  const body = await res.json();
  if (body.error) throw Object.assign(new Error(body.error.message || 'RPC error'), { code: body.error.code });
  return body.result;
}

const makeClient = ({ chain, account, provider }) => createClient({ chain, account, provider });

let prepared = null;
let record = null;

function setRecord(r) {
  record = r;
  show('record', JSON.stringify(r, null, 2));
  $('copy').disabled = !r;
}

function refreshDeployButton() {
  $('deploy').disabled = !(prepared && $('confirm').checked);
}

async function init() {
  show('net-name', BRADBURY.name);
  show('net-chain', `${BRADBURY.chainId} (${BRADBURY.chainIdHex})`);
  show('net-rpc', BRADBURY.rpcUrl);
  show('net-consensus', BRADBURY.consensusMainContract);
  show('net-explorer', BRADBURY.explorerUrl);
  show('lib-version', GENLAYER_JS_VERSION);
  show('ctor-arg', JSON.stringify(INITIAL_STORAGE));
  show('source', lfNormalise(source));
  show('expected-sha', EXPECTED_SOURCE_SHA256);
  const sha = await sha256Hex(lfNormalise(source));
  show('source-sha', sha);
  const ok = sha === EXPECTED_SOURCE_SHA256;
  show('sha-verdict', ok ? 'matches the pinned hash' : 'DOES NOT MATCH the pinned hash — deploy disabled');
  $('sha-verdict').className = ok ? 'ok' : 'bad';
  $('connect').disabled = !ok || !window.ethereum;
  if (!window.ethereum) show('wallet-state', 'No browser wallet found. Install MetaMask and reload this page.');
}

$('connect').addEventListener('click', async () => {
  prepared = null;
  refreshDeployButton();
  $('connect').disabled = true;
  try {
    log('Asking the wallet for an account, switching it to Bradbury (adding the network if needed), comparing a recent block, checking the consensus contract has code…');
    prepared = await prepare({ provider: window.ethereum, rpcRequest, chain: testnetBradbury, source });
    show('wallet-state', `Account ${prepared.account} on chain ${BRADBURY.chainIdHex}; block ${prepared.sameChain.height} hash ${prepared.sameChain.hash} matches Bradbury's RPC; consensus contracts have code (main ${prepared.consensus.main.codeBytes} bytes, data ${prepared.consensus.data.codeBytes} bytes).`);
    $('wallet-state').className = 'ok';
    log(`Ready. Switched: ${prepared.wallet.switched}, network added: ${prepared.wallet.added}. Nothing signed yet.`);
  } catch (err) {
    show('wallet-state', err.message);
    $('wallet-state').className = 'bad';
    log(`Stopped: ${err.message}`);
  } finally {
    $('connect').disabled = false;
    refreshDeployButton();
  }
});

$('confirm').addEventListener('change', refreshDeployButton);

$('deploy').addEventListener('click', async () => {
  $('deploy').disabled = true;
  $('connect').disabled = true;
  let broadcast = false; // once the wallet has sent, no message may say "nothing was sent"
  try {
    log('Opening MetaMask for ONE deploy signature. Check that its "to" is Bradbury\'s consensus contract.');
    const result = await deployAndVerify({
      prepared,
      provider: window.ethereum,
      makeClient,
      chain: testnetBradbury,
      confirmed: $('confirm').checked,
      onStep: (step, r) => {
        if (step === 'sent') { broadcast = true; log(`Sent. GenLayer transaction ${r.txId}. Waiting for consensus (up to 20 min)…`); }
        if (step === 'decided') log(`Decided: ${r.statusName}, execution ${r.executionResult}.`);
        setRecord({ ...r });
      },
    });
    setRecord(result);
    log(`Outcome: ${result.outcome}${result.evmTxHash ? ` — EVM tx ${result.evmTxHash}` : ''}${result.contractAddress ? ` — contract ${result.contractAddress}` : ''}`);
    if (result.contractAddress) $('recheck-address').value = result.contractAddress;
  } catch (err) {
    log(broadcast ? `Stopped after the transaction was sent — keep the record above: ${err.message}` : `Stopped before anything was sent: ${err.message}`);
  } finally {
    prepared = null; // one deploy per Connect: a second deploy needs a fresh Connect and a fresh tick
    $('confirm').checked = false;
    $('connect').disabled = false;
    refreshDeployButton();
  }
});

$('recheck').addEventListener('click', async () => {
  const address = $('recheck-address').value.trim();
  try {
    const client = createClient({ chain: testnetBradbury });
    const sha = await sha256Hex(lfNormalise(source));
    const code = await verifyCode(client, address, sha);
    log(`Code at ${address}: sha256 ${code.sha256 ?? '(unreadable)'} — ${code.matches ? 'MATCHES the source' : 'does not match'}${code.error ? ` (${code.error})` : ''}`);
    // Only a code outcome can change here: the address in the record already passed the status, execution and
    // recipient checks. Any other outcome (failed, not decided) stays as it was.
    const codeOutcome = ['CODE_UNREADABLE', 'CODE_MISMATCH', 'DEPLOYED_VERIFIED'].includes(record?.outcome);
    if (codeOutcome && record.contractAddress?.toLowerCase() === address.toLowerCase()) {
      setRecord({ ...record, code, outcome: code.matches ? 'DEPLOYED_VERIFIED' : (code.sha256 ? 'CODE_MISMATCH' : 'CODE_UNREADABLE'), recheckedAt: new Date().toISOString() });
    }
  } catch (err) {
    log(`Re-check stopped: ${err.message}`);
  }
});

$('copy').addEventListener('click', async () => {
  if (!record) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(record, null, 2));
    log('Record copied.');
  } catch {
    log('Copy failed; select the record text instead.');
  }
});

init().catch((err) => log(`Page failed to start: ${err.message}`));
