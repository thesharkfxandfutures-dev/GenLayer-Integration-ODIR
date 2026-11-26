# Wallet deploy spike — ODIR Brain slice B1 (pilot step 2)

One static page that deploys a trivial storage contract (`contract/storage.py`) to **GenLayer testnet
Bradbury** from the owner's MetaMask. Not part of SnapLink. **Testnet only.** The page holds no key, never
signs anything itself, and sends at most one transaction per Connect, after the owner ticks a confirmation.

> **Status on 26 Nov 2026: the page will refuse to deploy.** genlayer-js 1.1.8 (the version the plan pins)
> carries Bradbury contract addresses that have **no code on chain** today (OBSERVED: `eth_getCode` → 0 bytes
> for its consensus, data, staking and fee contracts; genlayer-js 2.1.0's addresses have code). A deploy would
> spend gas, call an empty address and deploy nothing, so `Connect` stops at `CONSENSUS_NOT_DEPLOYED` before any
> signature. Choosing the genlayer-js version for Bradbury is the owner's call (blocker B-B1-1 in the
> SnapLink autopilot record). Moving to 2.x touches A1 and C3 as well; see "Moving to another genlayer-js".

## Run it

```bash
cd spikes/wallet-deploy
npm ci          # genlayer-js 1.1.8 and esbuild, exactly as package-lock.json pins them
npm test        # node --test, no network, no wallet
npm start       # builds dist/app.js and serves http://127.0.0.1:5173 (MetaMask does not inject into file://)
```

Node 22 or later. Fund the MetaMask account from the faucet yourself (https://testnet-faucet.genlayer.foundation);
the page never asks for funds.

## What the page does

1. **Pinned network.** Shows Bradbury's chain id (4221), RPC, explorer, and the **consensus main contract** the
   transaction goes to. Bradbury and Asimov share chain id 4221 and the same underlying L2 (A1); what makes a
   deploy a Bradbury deploy is that `to` address. MetaMask shows it again in its confirmation.
2. **Source hash.** The contract source is bundled into `dist/app.js` at build time. The page LF-normalises it,
   shows its SHA-256 and compares it with the pinned hash (`99ad9c8f…bff294`). Any other bytes: no deploy.
3. **Connect (no signature).** `eth_requestAccounts`; `wallet_switchEthereumChain` to `0x107d`, adding Bradbury
   with `wallet_addEthereumChain` if the wallet does not know it (4902); then two checks that a chain id cannot fake:
   - the wallet's chain has the **same block hash** at a recent height as Bradbury's RPC;
   - the **consensus contract has code** on chain.
   It never calls `client.connect()` (in 1.1.8 that installs a MetaMask Snap and swaps `client.chain`).
4. **Deploy (one signature).** Only after the tick. Re-checks the wallet's chain and account, builds
   `createClient({ chain: testnetBradbury, account, provider: window.ethereum })` and calls `deployContract`
   once. A rejected signature stops there: nothing sent, no retry.
5. **Verify.** Waits up to 20 minutes for consensus. Requires `ACCEPTED`/`FINALIZED` and
   `FINISHED_WITH_RETURN`; takes the contract address **only** from the receipt's `recipient`; reads the code
   back with `gen_getContractCode` and compares its SHA-256 with the source hash.
6. **Record.** A JSON record (`odir.b1-wallet-deploy-record.v1`) with the network, account, source hash, block-hash
   check, consensus code size, transaction id, status, execution result, address and code hash. Copy it into the
   B1 ODIR record. A slow or failed deploy still produces a record (`NOT_DECIDED`, `FAILED_CONSENSUS`,
   `FAILED_EXECUTION`, `NO_ADDRESS`, `CODE_UNREADABLE`, `CODE_MISMATCH`); only `DEPLOYED_VERIFIED` meets the plan.

## Acceptance (plan, B1)

Your deploy reaches `FINISHED_WITH_RETURN`, the address comes from the receipt's recipient, and the code read
back from chain matches the source hash — all OBSERVED, with the transaction id in the record. The page stops at
your signature; faucet funding stays manual.

## Files

| Path | What |
|---|---|
| `contract/storage.py` | the contract (pinned GenVM runner, as the other ODIR contracts); genskill lint 0/0/0 |
| `src/bradbury.js` | pinned network facts, source hash, chain guard; tested against the library's own `testnetBradbury` |
| `src/core.js` | all decisions; wallet, RPC and client are injected |
| `src/main.js` | browser glue: DOM (text only), `window.ethereum`, `fetch` to Bradbury's RPC |
| `index.html`, `styles.css` | the page; CSP allows only itself and `rpc-bradbury.genlayer.com`; no inline script |
| `build.mjs` | esbuild, not minified, reproducible; prints the bundle's SHA-256 |
| `serve.mjs` | loopback-only server for four files |
| `test/` | 56 tests: guard, helpers, every outcome of the flow, the real genlayer-js 1.1.8 client against a mock wallet and a stubbed RPC, static checks, reproducible bundle |

## Moving to another genlayer-js

`src/bradbury.js` pins every fact the page relies on, and `test/bradbury.test.mjs` compares each with the installed
library's `testnetBradbury`, so changing the pin fails the tests until the facts are updated on purpose. Facts seen on
26 Nov for genlayer-js 2.1.0 (released 25 Nov): Bradbury consensus main `0x0f4F0e05475723790E4a2ed0598370783C300926`
(has code); its RPC is `https://rpc.testnet-chain.genlayer.com`, which does **not** serve `gen_getContractCode`
(`rpc-bradbury.genlayer.com` does), so the code read-back would need the GenLayer RPC explicitly; Bradbury and Asimov
still share chain id 4221.
