// The fixed vocabulary of SnapLink role contracts (slice A3). Every template, the resolver and the
// parchment viewer agree on these lists; changing one is a schema change (a new v2), not an edit.
//
// 13 clause categories (design doc "ODIR Brain — SnapLink Role-Contract System", Contract model).
// Each category is drawn in one of the parchment's standard sections (SnapLink slice C1,
// src/components/parchment/parchmentModel.js SECTION_ORDER), in this order.

export const CATEGORIES = Object.freeze([
  { key: 'parties_authority', title: 'Parties and authority', section: 'cover' },
  { key: 'role_duties', title: 'Role and duties', section: 'duties' },
  { key: 'place', title: 'Place', section: 'place_time' },
  { key: 'time_hours', title: 'Time and hours', section: 'place_time' },
  { key: 'pay', title: 'Pay', section: 'pay' },
  { key: 'expenses_equipment', title: 'Expenses and equipment', section: 'pay' },
  { key: 'usage_licence', title: 'Usage licence', section: 'terms' },
  { key: 'copyright_moral_rights', title: 'Copyright assignment and moral rights', section: 'terms' },
  { key: 'safety_licences', title: 'Safety and licences', section: 'terms' },
  { key: 'cancellation_no_show', title: 'Cancellation and no-show', section: 'terms' },
  { key: 'confidentiality_consent', title: 'Confidentiality and consent', section: 'terms' },
  { key: 'proof_of_completion', title: 'Proof of completion', section: 'proof_disputes' },
  { key: 'disputes_record', title: 'Disputes and record', section: 'proof_disputes' },
]);
export const CATEGORY_KEYS = Object.freeze(CATEGORIES.map((c) => c.key));
export const CATEGORY_INDEX = new Map(CATEGORY_KEYS.map((k, i) => [k, i]));

// The parchment's standard sections, in reading order (C1 SECTION_ORDER, same keys and titles).
export const SECTIONS = Object.freeze([
  { key: 'cover', title: 'Cover' },
  { key: 'duties', title: 'Role and duties' },
  { key: 'place_time', title: 'Place and time' },
  { key: 'pay', title: 'Pay' },
  { key: 'terms', title: 'Terms' },
  { key: 'proof_disputes', title: 'Proof and disputes' },
  { key: 'acceptance', title: 'Acceptance and seal' },
]);
// A clause may be moved to "Acceptance and seal" only from these categories (signing, age and
// authority confirmation, freezing the terms, the record).
export const ACCEPTANCE_CATEGORIES = Object.freeze(['parties_authority', 'disputes_record']);

export const BASES = Object.freeze({
  P2P: { engager: 'person', provider: 'person' },
  P2B: { engager: 'person', provider: 'organisation' },
  B2P: { engager: 'organisation', provider: 'person' },
  B2B: { engager: 'organisation', provider: 'organisation' },
  STAFF: { engager: 'organisation', provider: 'person' },
});

export const JURISDICTIONS = Object.freeze({
  EW: { name: 'England and Wales', courts: 'the courts of England and Wales' },
  SC: { name: 'Scotland', courts: 'the Scottish courts' },
  NI: { name: 'Northern Ireland', courts: 'the courts of Northern Ireland' },
});

export const FAMILIES = Object.freeze(['DIRECTION', 'TALENT', 'MAKER', 'CRAFT', 'OPERATION']);
export const SLOTS = Object.freeze(['engager', 'provider']);
export const FIELD_TYPES = Object.freeze(['text', 'date', 'time', 'money', 'number', 'duration']);
export const PAY_TYPES = Object.freeze(['hourly', 'day', 'fixed', 'tf', 'expenses_only']);

export const SCHEMA_IDS = Object.freeze({
  base: 'odir.base-template.v1',
  module: 'odir.role-template.v1',
  agreement: 'odir.agreement.v1',
});

// Provider duty modules carry 5 to 10 checkable statements (design doc, "A role duty module holds").
export const CHECKABLE_MIN = 5;
export const CHECKABLE_MAX = 10;
