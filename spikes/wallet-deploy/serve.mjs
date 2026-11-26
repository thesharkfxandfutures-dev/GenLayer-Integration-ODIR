// Serves the spike on http://127.0.0.1:5173 (MetaMask does not inject into file:// pages).
// Loopback only, four files only, no directory listing, no other path.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 5173);
const CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src https://rpc-bradbury.genlayer.com; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";

export const ROUTES = Object.freeze({
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/index.html': ['index.html', 'text/html; charset=utf-8'],
  '/styles.css': ['styles.css', 'text/css; charset=utf-8'],
  '/dist/app.js': ['dist/app.js', 'text/javascript; charset=utf-8'],
});

export function handler(req, res) {
  const path = new URL(req.url, 'http://127.0.0.1').pathname;
  const route = req.method === 'GET' || req.method === 'HEAD' ? ROUTES[path] : undefined;
  if (!route) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('not found');
    return;
  }
  readFile(join(here, route[0])).then((body) => {
    res.writeHead(200, {
      'Content-Type': route[1],
      'Content-Security-Policy': CSP,
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
      'Cache-Control': 'no-store',
    });
    res.end(req.method === 'HEAD' ? undefined : body);
  }, () => {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end(route[0] === 'dist/app.js' ? 'run npm run build first' : 'not found');
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  createServer(handler).listen(PORT, '127.0.0.1', () => {
    console.log(`Wallet deploy spike: http://127.0.0.1:${PORT}/  (testnet Bradbury only; Ctrl+C to stop)`);
  });
}
