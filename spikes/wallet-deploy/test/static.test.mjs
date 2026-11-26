// Static guarantees: what the page's own code never does, the page's CSP, the server's routes, and a
// reproducible bundle that carries the exact contract source.
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { BRADBURY } from '../src/bradbury.js';
import { handler, ROUTES } from '../serve.mjs';
import { ROOT, SOURCE } from './helpers.mjs';

const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const code = (p) => read(p).split('\n').filter((l) => !l.trim().startsWith('//')).join('\n'); // comments may name what is forbidden
const OWN = ['src/bradbury.js', 'src/core.js', 'src/main.js', 'build.mjs', 'serve.mjs'];

test('the page\'s own code never calls connect(), never holds a key, never names mainnet', () => {
  for (const f of OWN) {
    const c = code(f);
    assert.ok(!/\.connect\b|\[\s*['"`]connect['"`]\s*\]/.test(c), `${f}: no client.connect() in any spelling`);
    assert.ok(!/privateKey|private_key|mnemonic|generatePrivateKey|createAccount|privateKeyToAccount|signTransaction/i.test(c), `${f}: no key handling`);
    assert.ok(!/mainnet/i.test(c), `${f}: no mainnet`);
    assert.ok(!/wallet_requestSnaps|wallet_getSnaps/.test(c), `${f}: no Snaps`);
  }
});

test('main.js builds the client exactly as the plan says and writes the DOM as text only', () => {
  const c = code('src/main.js');
  assert.match(c, /createClient\(\{ chain, account, provider \}\)/);
  assert.match(c, /chain: testnetBradbury/);
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function/.test(c));
  assert.ok(!/testnetAsimov|studionet|localnet/.test(c), 'no other chain is imported');
});

test('index.html: no inline script, CSP allows only this origin and Bradbury\'s RPC, the tick names the consensus contract', () => {
  const html = read('index.html');
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length, 1);
  assert.match(scripts[0][0], /src="dist\/app\.js"/);
  assert.equal(scripts[0][1].trim(), '');
  assert.ok(!/\son[a-z]+=/i.test(html), 'no inline event handlers');
  const csp = html.match(/Content-Security-Policy" content="([^"]+)"/)[1];
  assert.match(csp, /default-src 'none'/);
  assert.match(csp, /script-src 'self'(;|$)/);
  assert.equal(csp.match(/connect-src ([^;]+)/)[1].trim(), BRADBURY.rpcUrl);
  assert.ok(html.includes(BRADBURY.consensusMainContract), 'the confirmation text shows the pinned consensus contract');
  assert.match(html, /TESTNET BRADBURY ONLY/);
});

test('serve.mjs serves four files on loopback and nothing else', async () => {
  assert.deepEqual(Object.keys(ROUTES).sort(), ['/', '/dist/app.js', '/index.html', '/styles.css']);
  assert.match(read('serve.mjs'), /listen\(PORT, '127\.0\.0\.1'/);
  const ask = (method, url) => new Promise((resolve) => {
    const res = { status: 0, headers: {}, writeHead(s, h) { this.status = s; this.headers = h; return this; }, end() { resolve(this); } };
    handler({ method, url }, res);
  });
  for (const url of ['/package.json', '/src/core.js', '/../package.json', '/%2e%2e/package.json', '/node_modules/genlayer-js/package.json', '/contract/storage.py', '/dist/']) {
    assert.equal((await ask('GET', url)).status, 404, url);
  }
  assert.equal((await ask('POST', '/')).status, 404);
  const ok = await ask('GET', '/index.html');
  assert.equal(ok.status, 200);
  assert.match(ok.headers['Content-Security-Policy'], /frame-ancestors 'none'/);
  assert.equal(ok.headers['X-Content-Type-Options'], 'nosniff');
});

test('the bundle is reproducible and carries the exact contract source', () => {
  const dir = mkdtempSync(join(tmpdir(), 'b1-build-'));
  try {
    const a = join(dir, 'a.js'); const b = join(dir, 'b.js');
    execFileSync(process.execPath, [join(ROOT, 'build.mjs'), a], { cwd: dir, stdio: 'pipe' });
    execFileSync(process.execPath, [join(ROOT, 'build.mjs'), b], { cwd: dir, stdio: 'pipe' });
    const ba = readFileSync(a); const bb = readFileSync(b);
    assert.equal(createHash('sha256').update(ba).digest('hex'), createHash('sha256').update(bb).digest('hex'));
    const js = ba.toString('utf8');
    const literal = js.match(/\nvar storage_default = (`[\s\S]*?`);\n/);
    assert.ok(literal, 'the contract source is bundled as one string');
    assert.equal(Function(`return ${literal[1]};`)(), SOURCE, 'the bundled string is the exact source');
    assert.ok(js.includes(BRADBURY.consensusMainContract));
    assert.ok(!js.includes('rpc-asimov.genlayer.com') || js.includes('testnetAsimov'), 'Asimov appears only as the library\'s own chain list');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('nothing key-shaped is committed in the spike (no 0x-prefixed 32-byte hex value anywhere)', () => {
  for (const f of [...OWN, 'index.html', 'styles.css', 'package.json', 'contract/storage.py']) {
    assert.ok(!/0x[0-9a-fA-F]{64}/.test(read(f)), `${f}: no 32-byte hex value`);
  }
});
