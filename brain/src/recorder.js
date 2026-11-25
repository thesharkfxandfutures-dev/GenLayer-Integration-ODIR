// The Recorder: a plain script, no LLM. Every write it makes is preceded by lock.assertHeld(),
// so a run that has lost its lease writes nothing more. In A2 it writes the run record and
// (outside dry runs) the brain-blocked issue; branches, commits, PRs and labels come in later
// slices through the same guard. It has no merge operation and touches no other repository.
import fs from 'node:fs';
import path from 'node:path';
import { validate } from './jsonschema.js';

export const RUN_SCHEMA = 'odir-brain-run/1';
export const runSchema = JSON.parse(fs.readFileSync(new URL('../../schema/brain-run.v1.json', import.meta.url), 'utf8'));

export class RecordError extends Error {}

export class MemorySink {
  constructor() { this.files = new Map(); }
  async write(name, text) { this.files.set(name, text); }
}

export class DirSink {
  constructor(dir) { this.dir = dir; }
  async write(name, text) {
    if (!/^[A-Za-z0-9._:-]+$/.test(name)) throw new RecordError(`bad record name ${name}`);
    fs.mkdirSync(this.dir, { recursive: true });
    const file = path.join(this.dir, name);
    fs.writeFileSync(file, text, { flag: 'wx' });
    return file;
  }
}

export class Recorder {
  constructor({ lock, sink, issues = null, dryRun = true }) {
    this.lock = lock; this.sink = sink; this.issues = issues; this.dryRun = dryRun; this.writes = [];
  }

  async writeRunRecord(record) {
    const v = validate(runSchema, record);
    if (!v.ok) throw new RecordError(`run record fails its schema: ${v.problems.join('; ')}`);
    await this.lock.assertHeld('run record');
    const name = `${record.run_id}.json`;
    await this.sink.write(name, `${JSON.stringify(record, null, 2)}\n`);
    this.writes.push(`record:${name}`);
    return name;
  }

  async applyIssuePlan(plan) {
    if (this.dryRun) return { applied: false, why: 'dry run' };
    if (!this.issues) throw new RecordError('no issue store');
    const done = [];
    for (const n of plan.close_duplicates || []) {
      await this.lock.assertHeld(`comment on duplicate issue #${n}`);
      await this.issues.comment(n, 'Duplicate brain-blocked issue; the oldest open one is kept.');
      await this.lock.assertHeld(`close duplicate issue #${n}`);
      await this.issues.close(n);
      done.push(`close_duplicate:${n}`);
    }
    if (plan.action === 'create') {
      await this.lock.assertHeld('create brain-blocked issue');
      const r = await this.issues.create({ title: plan.title, body: plan.body, labels: plan.labels });
      done.push(`create:${r.number}`);
    } else if (plan.action === 'update') {
      await this.lock.assertHeld('update brain-blocked issue');
      await this.issues.update(plan.number, { body: plan.body });
      await this.lock.assertHeld('comment on brain-blocked issue');
      await this.issues.comment(plan.number, plan.comment);
      done.push(`update:${plan.number}`);
    } else if (plan.action === 'close') {
      await this.lock.assertHeld('comment on brain-blocked issue');
      await this.issues.comment(plan.number, plan.comment);
      await this.lock.assertHeld('close brain-blocked issue');
      await this.issues.close(plan.number);
      done.push(`close:${plan.number}`);
    }
    this.writes.push(...done.map((d) => `issue:${d}`));
    return { applied: true, done };
  }
}
