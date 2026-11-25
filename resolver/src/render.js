// Two views of a resolved document:
//   toParchment(doc, { names })  → the input SnapLink's parchment viewer takes today (slice C1,
//                                  src/components/parchment/parchmentModel.js): fields and values as
//                                  maps, clauses as { id, text }, plus the replacement marks.
//   renderMarkdown(doc)          → plain text for review and CI, one numbered clause per line,
//                                  every replacement marked.
// Neither view is hashed; terms_hash is carried through unchanged.

const SOURCE_LABEL = { base: 'base', engager_module: 'engager module', provider_module: 'provider module', override: 'parties’ override' };

export function toParchment(doc, { names = {} } = {}) {
  const fields = {};
  const values = {};
  for (const f of doc.fields) {
    fields[f.key] = { label: f.label, ...(f.default !== null ? { default: f.default } : {}) };
    if (f.value !== null) values[f.key] = f.value;
  }
  return {
    title: doc.title,
    notice: doc.notice,
    base: doc.base,
    jurisdiction: doc.jurisdiction,
    parties: doc.parties.map((p) => ({
      slot: p.slot,
      name: names[p.slot] ?? p.label.replace(/^the /, ''),
      role: p.role_label ?? null,
    })),
    sections: doc.sections.map((s) => ({
      key: s.key,
      title: s.title,
      clauses: s.clauses.map((c) => ({
        id: c.id,
        text: c.text,
        ...(c.replaces ? { marked: `replaces ${SOURCE_LABEL[c.replaces.source]} clause ${c.replaces.id}`, source: c.source } : {}),
      })),
    })),
    fields,
    values,
    terms_hash: doc.terms_hash,
    seal: null,
  };
}

export function renderMarkdown(doc) {
  const out = [];
  out.push(`# ${doc.title}`, '');
  out.push(`> ${doc.notice}`, '');
  out.push(`- Base: ${doc.base} · Law: ${doc.jurisdiction_name} · ${doc.consumer ? 'Consumer engager' : 'Business engager'} · Mode: ${doc.mode}`);
  for (const p of doc.parties) out.push(`- ${p.slot === 'engager' ? 'Engager' : 'Provider'}: ${p.label}${p.role_label ? ` (${p.role_label})` : ''}, ${p.kind}`);
  const src = doc.sources;
  out.push(`- Base ${src.base.key} v${src.base.version} \`${src.base.sha256}\``);
  for (const k of ['engager_module', 'provider_module']) if (src[k]) out.push(`- ${SOURCE_LABEL[k]} ${src[k].role_key} v${src[k].version} \`${src[k].sha256}\`${src[k].stale ? ' **STALE**' : ''}`);
  if (src.overrides.count) out.push(`- Overrides: ${src.overrides.count} \`${src.overrides.sha256}\``);
  out.push(`- Terms hash: \`${doc.terms_hash}\``, '');
  doc.sections.forEach((s, i) => {
    out.push(s.key === 'cover' ? `## ${s.title}` : `## ${i}. ${s.title}`, '');
    if (!s.clauses.length) out.push('_Nothing under this heading._', '');
    s.clauses.forEach((c, j) => {
      const no = s.key === 'cover' ? '-' : `${i}.${j + 1}`;
      const marks = [c.category, c.checkable ? 'checkable' : null, c.locked ? 'locked' : null, c.source !== 'base' ? SOURCE_LABEL[c.source] : null]
        .filter(Boolean).join(', ');
      out.push(`${no} ${c.text} _[${marks}]_${c.replaces ? ` **(replaces ${SOURCE_LABEL[c.replaces.source]} clause ${c.replaces.id})**` : ''}`);
    });
    out.push('');
  });
  if (doc.fields.length) {
    out.push('## Blanks', '');
    for (const f of doc.fields) out.push(`- \`{{${f.key}}}\` ${f.label} (${f.type}, ${f.category})${f.default !== null ? ` — default: ${f.default}` : ''}${f.value !== null ? ` — value: ${f.value}` : ''}`);
    out.push('');
  }
  return `${out.join('\n').trimEnd()}\n`;
}
