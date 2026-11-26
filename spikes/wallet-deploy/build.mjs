// Builds dist/app.js: src/main.js + genlayer-js 1.1.8 (from package-lock.json) + the contract source as text.
// Not minified, so the bundle the owner runs can be read. Prints the bundle's SHA-256; two builds from the
// same lockfile give the same bytes (test/static.test.mjs checks this).
import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outfile = process.argv[2] ? resolve(process.argv[2]) : join(here, 'dist', 'app.js');

await build({
  absWorkingDir: here,
  entryPoints: ['src/main.js'],
  bundle: true,
  format: 'esm',
  platform: 'browser',
  target: 'es2022',
  outfile,
  loader: { '.py': 'text' },
  minify: false,
  sourcemap: false,
  legalComments: 'eof',
  charset: 'utf8',
  logLevel: 'warning',
});

const bytes = await readFile(outfile);
console.log(`${outfile.startsWith(here) ? outfile.slice(here.length + 1) : outfile}  ${bytes.length} bytes  sha256 ${createHash('sha256').update(bytes).digest('hex')}`);
