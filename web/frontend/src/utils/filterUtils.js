// src/utils/filterUtils.js
// Moteur de filtres avancés partagé par FilterPanel et les pages Desktop.

export const FILTER_OPERATORS = [
  { value: 'contains', label: 'Contient', types: ['text', 'select'] },
  { value: 'equals', label: 'Égal à', types: ['text', 'number', 'date', 'select', 'boolean'] },
  { value: 'not_equals', label: 'Différent de', types: ['text', 'number', 'date', 'select', 'boolean'] },
  { value: 'gt', label: 'Supérieur à', types: ['number', 'date'] },
  { value: 'lt', label: 'Inférieur à', types: ['number', 'date'] },
  { value: 'gte', label: 'Supérieur ou égal', types: ['number', 'date'] },
  { value: 'lte', label: 'Inférieur ou égal', types: ['number', 'date'] },
  { value: 'starts_with', label: 'Commence par', types: ['text', 'select'] },
  { value: 'ends_with', label: 'Finit par', types: ['text', 'select'] },
  { value: 'is_null', label: 'Est vide', types: ['text', 'number', 'date', 'select', 'boolean'], noValue: true },
  { value: 'is_not_null', label: "N'est pas vide", types: ['text', 'number', 'date', 'select', 'boolean'], noValue: true },
];

const OPERATOR_MAP = FILTER_OPERATORS.reduce((acc, op) => {
  acc[op.value] = op;
  return acc;
}, {});

export const operatorRequiresValue = (operator) => !OPERATOR_MAP[operator]?.noValue;

export const operatorsForType = (type = 'text') => {
  const normalized = type || 'text';
  const list = FILTER_OPERATORS.filter((op) => op.types.includes(normalized));
  return list.length ? list : FILTER_OPERATORS;
};

export const defaultOperatorForType = (type = 'text') => operatorsForType(type)[0]?.value || 'contains';

const isNil = (value) => value === null || value === undefined || value === '';

const toNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (isNil(value)) return null;
  const parsed = Number(String(value).replace(/\s/g, '').replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
};

const toTime = (value) => {
  if (isNil(value)) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.getTime();
  const parsed = new Date(value);
  const time = parsed.getTime();
  return Number.isNaN(time) ? null : time;
};

const toBool = (value) => {
  if (typeof value === 'boolean') return value;
  if (isNil(value)) return null;
  const text = String(value).trim().toLowerCase();
  if (['true', '1', 'oui', 'yes'].includes(text)) return true;
  if (['false', '0', 'non', 'no'].includes(text)) return false;
  return null;
};

const toText = (value) => {
  if (isNil(value)) return '';
  return String(value)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
};

/** Récupère la valeur brute d'un champ pour une ligne. */
export const resolveFieldValue = (row, field) => {
  if (!row) return undefined;
  if (field && typeof field.accessor === 'function') return field.accessor(row);
  const key = typeof field === 'string' ? field : field?.key;
  if (!key) return undefined;
  if (key.includes('.')) {
    return key.split('.').reduce((acc, part) => (acc == null ? acc : acc[part]), row);
  }
  return row[key];
};

const compareTyped = (rowValue, filterValue, type) => {
  if (type === 'number') {
    const a = toNumber(rowValue);
    const b = toNumber(filterValue);
    return a === null || b === null ? null : a - b;
  }
  if (type === 'date') {
    const a = toTime(rowValue);
    const b = toTime(filterValue);
    return a === null || b === null ? null : a - b;
  }
  const a = toText(rowValue);
  const b = toText(filterValue);
  return a === b ? 0 : a > b ? 1 : -1;
};

/** Évalue un filtre unitaire sur une ligne. */
export const matchFilter = (row, filter, fields = []) => {
  if (!filter || !filter.field) return true;
  const field = fields.find((f) => f.key === filter.field) || { key: filter.field, type: 'text' };
  const type = field.type || 'text';
  const rowValue = resolveFieldValue(row, field);
  const { operator } = filter;

  if (operator === 'is_null') return isNil(rowValue);
  if (operator === 'is_not_null') return !isNil(rowValue);

  if (isNil(filter.value)) return true; // filtre incomplet => ignoré

  switch (operator) {
    case 'contains':
      return toText(rowValue).includes(toText(filter.value));
    case 'starts_with':
      return toText(rowValue).startsWith(toText(filter.value));
    case 'ends_with':
      return toText(rowValue).endsWith(toText(filter.value));
    case 'equals': {
      if (type === 'boolean') return toBool(rowValue) === toBool(filter.value);
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp === 0;
    }
    case 'not_equals': {
      if (type === 'boolean') return toBool(rowValue) !== toBool(filter.value);
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp !== 0;
    }
    case 'gt': {
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp !== null && cmp > 0;
    }
    case 'gte': {
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp !== null && cmp >= 0;
    }
    case 'lt': {
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp !== null && cmp < 0;
    }
    case 'lte': {
      const cmp = compareTyped(rowValue, filter.value, type);
      return cmp !== null && cmp <= 0;
    }
    default:
      return true;
  }
};

/**
 * Applique une liste de filtres à un jeu de données.
 * @param {Array} rows
 * @param {Array<{field:string,operator:string,value:any}>} filters
 * @param {Array<{key:string,label:string,type?:string,accessor?:Function}>} fields
 * @param {'and'|'or'} [logic='and']
 */
export const applyFilters = (rows, filters, fields = [], logic = 'and') => {
  if (!Array.isArray(rows) || !Array.isArray(filters) || filters.length === 0) return rows || [];
  const active = filters.filter(
    (f) => f && f.field && (!operatorRequiresValue(f.operator) || !isNil(f.value))
  );
  if (active.length === 0) return rows;
  if (logic === 'or') {
    return rows.filter((row) => active.some((filter) => matchFilter(row, filter, fields)));
  }
  return rows.filter((row) => active.every((filter) => matchFilter(row, filter, fields)));
};

/** Nombre de filtres réellement appliqués (utile pour le badge du panneau). */
export const countActiveFilters = (filters = []) =>
  filters.filter((f) => f && f.field && (!operatorRequiresValue(f.operator) || !isNil(f.value))).length;

/** Recherche plein texte simple sur une liste de champs. */
export const applySearch = (rows, term, searchFields = []) => {
  if (!term || !Array.isArray(rows) || searchFields.length === 0) return rows || [];
  const needle = toText(term);
  if (!needle) return rows;
  return rows.filter((row) =>
    searchFields.some((field) => toText(resolveFieldValue(row, field)).includes(needle))
  );
};
