// Read-only RPC access to the configured contract through the pinned GenLayer client.
// Only view methods, only the configured chain and address, only when the client is
// installed. The client is an optional dependency loaded on demand so file-mode use of the
// adapter needs no network install at all.
export const PINNED_CLIENT = 'genlayer-js@1.1.8';
export const STATE_SELECTION = 'latest-final';
export const VIEW_METHODS = ['get_slice', 'get_attempt', 'can_consume', 'get_config'];

export class RpcError extends Error {
  constructor(message, { category = 'transport_outage', exit = 3 } = {}) { super(message); this.category = category; this.exit = exit; }
}

async function loadClient() {
  try {
    const [core, chains] = await Promise.all([import('genlayer-js'), import('genlayer-js/chains')]);
    return { core, chains };
  } catch (e) {
    throw new RpcError(`BLOCKED_ENVIRONMENT: ${PINNED_CLIENT} is not installed (run npm install in adapter/): ${e.message}`, { category: 'configuration_failure', exit: 3 });
  }
}

const trimUrl = (u) => String(u).trim().replace(/\/+$/, '');
const normName = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, '');
const chainUrl = (c) => c.rpcUrls?.default?.http?.[0];

// The names a config may use for a chain: the client's export key ("testnetBradbury"), that key
// without its "testnet" prefix ("bradbury"), or the client's display name
// ("Genlayer Bradbury Testnet"). Case, spaces and punctuation are ignored.
function chainNames(key, chain) {
  const k = normName(key);
  const names = new Set([k, k.replace(/^testnet(?=.)/, '')]);
  if (typeof chain.name === 'string') names.add(normName(chain.name));
  return names;
}

// The chain comes from the client's own definition and must agree with the reviewed config;
// a config naming a different chain id, name or RPC URL is a configuration failure, not a
// request to talk to somewhere else.
//
// A chain id alone is not enough: genlayer-js 1.1.8 defines testnetAsimov and testnetBradbury
// both as chain 4221. So the id narrows the client's chains, then `chain_name` (optional) and
// `rpc_url` narrow them further, and exactly one chain must remain. Two left is refused as
// ambiguous; the first match never wins by position.
export function selectChain(chains, config) {
  const fail = (message) => { throw new RpcError(message, { category: 'configuration_failure', exit: 5 }); };
  const known = Object.entries(chains).filter(([, c]) => c && typeof c === 'object' && Number.isInteger(c.id));
  let candidates = known.filter(([, c]) => c.id === config.chain_id);
  if (candidates.length === 0) fail(`config chain_id ${config.chain_id} is not a chain the pinned client knows`);
  const keys = () => candidates.map(([k]) => k).join(', ');

  if (config.chain_name !== undefined && config.chain_name !== null) {
    const wanted = typeof config.chain_name === 'string' ? normName(config.chain_name) : '';
    if (!wanted) fail('config chain_name must be a non-empty string');
    const named = candidates.filter(([k, c]) => chainNames(k, c).has(wanted));
    if (named.length === 0) fail(`config chain_name "${config.chain_name}" is not chain ${config.chain_id} in the pinned client (chain ${config.chain_id} is ${keys()})`);
    candidates = named;
  }

  if (config.rpc_url) {
    const wanted = trimUrl(config.rpc_url);
    // A client chain with no default URL cannot contradict the config, as before.
    const byUrl = candidates.filter(([, c]) => !chainUrl(c) || trimUrl(chainUrl(c)) === wanted);
    if (byUrl.length === 0) fail(`config rpc_url differs from the client's definition for chain ${config.chain_id} (${candidates.map(([k, c]) => `${k}: ${chainUrl(c)}`).join('; ')})`);
    candidates = byUrl;
  }

  if (candidates.length > 1) fail(`config chain_id ${config.chain_id} is shared by ${keys()} in the pinned client; set rpc_url or chain_name to choose one`);
  return candidates[0][1];
}

export async function readView(config, functionName, args, { timeoutMs = 20_000 } = {}) {
  if (!VIEW_METHODS.includes(functionName)) throw new RpcError(`${functionName} is not a permitted view method`, { category: 'configuration_failure', exit: 5 });
  if (Array.isArray(config.permitted_methods) && !config.permitted_methods.includes(functionName)) throw new RpcError(`${functionName} is not in config.permitted_methods`, { category: 'configuration_failure', exit: 5 });
  const { core, chains } = await loadClient();
  const chain = selectChain(chains, config);
  const client = core.createClient({ chain });
  let timer;
  const started = Date.now();
  try {
    const raw = await Promise.race([
      client.readContract({ address: config.contract_address, functionName, args, transactionHashVariant: STATE_SELECTION }),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new RpcError(`read timed out after ${timeoutMs} ms`, { category: 'transport_outage', exit: 3 })), timeoutMs); }),
    ]);
    return {
      raw: typeof raw === 'string' ? raw : JSON.stringify(raw),
      rpc_url: chain.rpcUrls?.default?.http?.[0] || config.rpc_url || null,
      chain_id: chain.id,
      state_selection: STATE_SELECTION,
      client_version: PINNED_CLIENT,
      duration_ms: Date.now() - started,
    };
  } catch (e) {
    if (e instanceof RpcError) throw e;
    const msg = String(e?.message || e);
    // The contract raising UserError (unknown slice, paused) surfaces as "execution failed":
    // a definite answer from the chain, not an outage, so it is classified separately.
    if (/execution failed|UserError/i.test(msg)) throw new RpcError(`contract call failed (unknown slice or refused view): ${msg.split('\n')[0].slice(0, 160)}`, { category: 'execution_error', exit: 3 });
    if (/rate limit|429/i.test(msg)) throw new RpcError(`rate limited: ${msg.slice(0, 160)}`, { category: 'rate_limit', exit: 3 });
    throw new RpcError(`RPC read failed: ${msg.split('\n')[0].slice(0, 200)}`, { category: 'transport_outage', exit: 3 });
  } finally { clearTimeout(timer); }
}
