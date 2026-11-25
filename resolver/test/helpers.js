// SYNTHETIC templates for the resolver's unit tests. The wording is filler, not a template.
import { CATEGORY_KEYS } from '../src/categories.js';

export const clone = (v) => JSON.parse(JSON.stringify(v));

export function makeBase(key = 'P2P', { consumer: wanted = true } = {}) {
  const p = key.toLowerCase();
  const engagerIsOrg = key.startsWith('B') || key === 'STAFF';
  const consumer = wanted && !engagerIsOrg;
  const clauses = CATEGORY_KEYS.map((c) => ({ id: `${p}.${c}.1`, category: c, text: `Base ${c} clause for [[Engager]] and [[provider]].` }));
  clauses.find((c) => c.category === 'pay').text = '[[Engager]] pays {{fee}} within {{pay_days}} days.';
  clauses.find((c) => c.category === 'parties_authority').locked = true;
  clauses.push({ id: `${p}.disputes_record.law`, category: 'disputes_record', text: 'The law of [[jurisdiction]] applies and [[courts]] decide.' });
  clauses.push({ id: `${p}.acceptance.sign`, category: 'parties_authority', section: 'acceptance', text: 'Each party confirms they are 18 or over and signs below.', locked: true });
  clauses.push({ id: `${p}.cancel.sc`, category: 'cancellation_no_show', text: 'A Scottish-only cancellation clause.', when: { jurisdictions: ['SC'] } });
  if (consumer) {
    clauses.push({ id: `${p}.cancel.consumer`, category: 'cancellation_no_show', text: 'A consumer may cancel within 14 days.', locked: true, when: { consumer: true } });
    clauses.push({ id: `${p}.cancel.business`, category: 'cancellation_no_show', text: 'A business engager cancels on {{notice_hours}} hours’ notice.', when: { consumer: false } });
  }
  return {
    schema: 'odir.base-template.v1',
    key,
    version: 1,
    title: `Synthetic ${key} base`,
    engager_kind: engagerIsOrg ? 'organisation' : 'person',
    provider_kind: key.endsWith('B') ? 'organisation' : 'person',
    consumer_variant: consumer,
    jurisdictions: ['EW', 'SC', 'NI'],
    notice: 'Synthetic test template. Not legal advice.',
    party_labels: { engager: 'the Client', provider: 'the Provider' },
    clauses,
    fields: [
      { key: 'fee', label: 'Fee', category: 'pay', type: 'money' },
      { key: 'pay_days', label: 'Days to pay', category: 'pay', type: 'number', default: '14' },
      ...(consumer ? [{ key: 'notice_hours', label: 'Notice (hours)', category: 'cancellation_no_show', type: 'number', default: '48' }] : []),
    ],
    style: { paper: 'waxed-parchment', ink: 'sepia' },
  };
}

export function makeModule(key = 'tester', { bases = ['P2P', 'B2P'], engagerBases = ['P2P'] } = {}) {
  const slot = (s, n) => {
    const clauses = CATEGORY_KEYS.map((c) => ({ id: `${key}.${s}.${c}.1`, category: c, text: `${s} ${c} duty of [[${s}]].` }));
    for (let i = 0; i < n; i++) clauses.push({ id: `${key}.${s}.duty.${i + 1}`, category: 'role_duties', text: `Checkable ${s} duty ${i + 1}: deliver {{item_count}} items.`, checkable: true });
    return clauses;
  };
  return {
    schema: 'odir.role-template.v1',
    role_key: key,
    role_label: 'Tester',
    family: 'MAKER',
    version: 1,
    drafted_against: Object.fromEntries([...new Set([...bases, ...engagerBases])].map((b) => [b, 1])),
    defaults: { pay_type: 'day' },
    risk_flags: ['image_rights'],
    engager: { bases: engagerBases, party_label: 'the Tester', clauses: slot('engager', 0), fields: [{ key: 'item_count', label: 'Items', category: 'role_duties', type: 'number', default: '3' }] },
    provider: { bases, party_label: 'the Tester', clauses: slot('provider', 5), fields: [{ key: 'item_count', label: 'Items', category: 'role_duties', type: 'number', default: '3' }] },
    style: { ink: 'navy' },
  };
}

export const allClauses = (doc) => doc.sections.flatMap((s) => s.clauses);
export const clause = (doc, id) => allClauses(doc).find((c) => c.id === id);
