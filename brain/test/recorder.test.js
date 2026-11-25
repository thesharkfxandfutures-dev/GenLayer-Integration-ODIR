import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DirSink, Recorder, RecordError } from '../src/recorder.js';
import { LeaseLock, MemoryRefStore } from '../src/lock.js';
import { clock } from './helpers.js';

test('a run record file is never overwritten', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'brain-sink-'));
  const sink = new DirSink(dir);
  await sink.write('r1.json', 'first');
  await assert.rejects(sink.write('r1.json', 'second'), /EEXIST/);
  assert.equal(fs.readFileSync(path.join(dir, 'r1.json'), 'utf8'), 'first');
  await assert.rejects(sink.write('../escape.json', 'x'), RecordError);
});

test('the Recorder refuses a record that fails its schema, before any write', async () => {
  const store = new MemoryRefStore(); const c = clock();
  const lock = new LeaseLock({ store, runId: 'run-a', clock: c.now });
  await lock.acquire();
  const writes = [];
  const rec = new Recorder({ lock, sink: { write: async (n) => writes.push(n) } });
  await assert.rejects(rec.writeRunRecord({ schema: 'odir-brain-run/1', run_id: 'run-a' }), RecordError);
  assert.deepEqual(writes, []);
});
