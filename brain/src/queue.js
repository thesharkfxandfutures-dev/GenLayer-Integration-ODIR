// brain/QUEUE.md on main: the owner's queue order and the pinned registry hash.
//
//   registry_sha256: <64 hex> | unpinned     (exactly once)
//   order: registry | listed                 (exactly once; default registry)
//   ## Queue
//   - <role_key>                             (one per line, in order)
//
// order: registry  -> the listed roles first, then every other registry role in registry order.
// order: listed    -> only the listed roles.
// A missing file means: unpinned, registry order, nothing listed.
export class QueueFormatError extends Error {}

const KEY = /^[a-z][a-z0-9_]{1,59}$/;

export function parseQueue(text) {
  if (text === null || text === undefined) return { exists: false, pinned_registry_sha256: null, order: 'registry', listed: [] };
  const lines = String(text).split(/\r?\n/);
  let pin, order, inQueue = false;
  const listed = [];
  for (const raw of lines) {
    const line = raw.trim();
    let m;
    if ((m = /^registry_sha256:\s*(\S+)$/.exec(line))) {
      if (pin !== undefined) throw new QueueFormatError('registry_sha256 appears twice');
      if (m[1] === 'unpinned') pin = null;
      else if (/^[0-9a-f]{64}$/.test(m[1])) pin = m[1];
      else throw new QueueFormatError('registry_sha256 must be 64 lowercase hex or "unpinned"');
    } else if ((m = /^order:\s*(\S+)$/.exec(line))) {
      if (order !== undefined) throw new QueueFormatError('order appears twice');
      if (m[1] !== 'registry' && m[1] !== 'listed') throw new QueueFormatError('order must be registry or listed');
      order = m[1];
    } else if (/^##\s+/.test(line)) {
      inQueue = /^##\s+Queue\s*$/i.test(line);
    } else if (inQueue && (m = /^[-*]\s+(\S+)\s*$/.exec(line))) {
      const key = m[1].replace(/^`|`$/g, '');
      if (!KEY.test(key)) throw new QueueFormatError(`queue item ${JSON.stringify(key)} is not a role key`);
      if (listed.includes(key)) throw new QueueFormatError(`queue item ${key} listed twice`);
      listed.push(key);
    }
  }
  if (pin === undefined) throw new QueueFormatError('registry_sha256 line missing');
  return { exists: true, pinned_registry_sha256: pin, order: order || 'registry', listed };
}

export function queueOrder(queue, snapshot) {
  const registryKeys = snapshot.roles.map((r) => r.key);
  const known = new Set(registryKeys);
  const unknown = queue.listed.filter((k) => !known.has(k));
  const first = queue.listed.filter((k) => known.has(k));
  const order = queue.order === 'listed' ? first : [...first, ...registryKeys.filter((k) => !first.includes(k))];
  return { order, unknown, source: queue.exists ? `QUEUE.md (${queue.order})` : 'registry (no QUEUE.md)' };
}
