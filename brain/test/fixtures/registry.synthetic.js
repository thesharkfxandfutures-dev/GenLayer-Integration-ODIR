/**
 * SYNTHETIC fixture in the shape of SnapLink's base44/shared/taxonomy/registry.js.
 * Not the app's file: four roles, three sectors, enough to exercise the Inspector.
 */

export const KEY_PATTERN = /^[a-z][a-z0-9_]{1,59}$/;

/** Bumped whenever any definition below changes. */
export const TAXONOMY_REVISION = 1;

export const LIFECYCLE = Object.freeze({ ACTIVE: 'ACTIVE' });

export const ROLE_FAMILIES = Object.freeze(['MAKER', 'CRAFT', 'TALENT', 'DIRECTION', 'OPERATION', 'GENERIC']);

const freezeAll = (rows) => Object.freeze(rows.map((row) => Object.freeze({ ...row })));

/* ── SECTORS (3) ── */

const sector = (key, label) => ({ key, label, lifecycle: LIFECYCLE.ACTIVE });

export const SECTORS = freezeAll([
  sector('photography', 'Photography'),
  sector('hair_beauty_makeup', 'Hair, Beauty, Makeup & SFX'),
  sector('modelling_talent', 'Modelling & Commercial Talent'),
]);

/* ── ROLES (4) ── */

const role = (key, label, legacyGroup, family, sectors, synonyms = []) => ({
  key, label, legacyGroup, family, sectors: Object.freeze([...sectors]),
  synonyms: Object.freeze([...synonyms]), lifecycle: LIFECYCLE.ACTIVE, mergedInto: null,
});

export const ROLES = freezeAll([
  role('photographer', 'Photographer', 'Visual Arts', 'MAKER', ['photography']),
  // a comment between rows is allowed
  role('makeup_artist', 'Makeup Artist', 'Beauty & Grooming', 'CRAFT', ['hair_beauty_makeup'], ['mua', 'make-up artist']),
  role('model_fashion', "Fashion Model", 'Talent', 'TALENT', ['modelling_talent']),
  role('retoucher', 'Retoucher', 'Post-Production', 'MAKER', ['photography'], []),
]);
