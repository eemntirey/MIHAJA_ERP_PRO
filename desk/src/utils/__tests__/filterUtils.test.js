// src/utils/__tests__/filterUtils.test.js
import {
  FILTER_OPERATORS,
  operatorRequiresValue,
  operatorsForType,
  defaultOperatorForType,
  resolveFieldValue,
  matchFilter,
  applyFilters,
  applySearch,
  countActiveFilters,
} from '../filterUtils';

const FIELDS = [
  { key: 'name', label: 'Nom', type: 'text' },
  { key: 'price', label: 'Prix', type: 'number' },
  { key: 'active', label: 'Actif', type: 'boolean' },
  { key: 'created', label: 'Créé le', type: 'date' },
];

const ROW = {
  name: 'Café Noir',
  price: 12,
  active: true,
  created: '2024-03-10',
  meta: { sku: 'SKU-9' },
};

describe('filterUtils — opérateurs', () => {
  test('FILTER_OPERATORS contient les opérateurs clés', () => {
    const values = FILTER_OPERATORS.map((o) => o.value);
    ['contains', 'equals', 'not_equals', 'gt', 'lt', 'gte', 'lte', 'is_null', 'is_not_null'].forEach((v) =>
      expect(values).toContain(v)
    );
  });

  test('operatorRequiresValue : is_null / is_not_null n’exigent pas de valeur', () => {
    expect(operatorRequiresValue('is_null')).toBe(false);
    expect(operatorRequiresValue('is_not_null')).toBe(false);
    expect(operatorRequiresValue('contains')).toBe(true);
  });

  test('operatorsForType / defaultOperatorForType par type', () => {
    expect(defaultOperatorForType('text')).toBe('contains');
    expect(defaultOperatorForType('number')).toBe('equals');
    expect(defaultOperatorForType('boolean')).toBe('equals');
    expect(defaultOperatorForType('date')).toBe('equals');
    expect(operatorsForType('number').map((o) => o.value)).toContain('gt');
    expect(operatorsForType('number').map((o) => o.value)).not.toContain('contains');
  });
});

describe('filterUtils — matching', () => {
  test('resolveFieldValue gère clés simples et imbriquées', () => {
    expect(resolveFieldValue(ROW, 'name')).toBe('Café Noir');
    expect(resolveFieldValue(ROW, 'meta.sku')).toBe('SKU-9');
  });

  test('contains est insensible aux accents et à la casse', () => {
    expect(matchFilter(ROW, { field: 'name', operator: 'contains', value: 'cafe' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'name', operator: 'contains', value: 'noir' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'name', operator: 'contains', value: 'vert' }, FIELDS)).toBe(false);
  });

  test('equals / not_equals booléen', () => {
    expect(matchFilter(ROW, { field: 'active', operator: 'equals', value: 'true' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'active', operator: 'not_equals', value: 'true' }, FIELDS)).toBe(false);
  });

  test('comparaisons numériques', () => {
    expect(matchFilter(ROW, { field: 'price', operator: 'gt', value: '10' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'price', operator: 'lt', value: '10' }, FIELDS)).toBe(false);
    expect(matchFilter(ROW, { field: 'price', operator: 'gte', value: '12' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'price', operator: 'lte', value: '12' }, FIELDS)).toBe(true);
  });

  test('dates via gt/lt', () => {
    expect(matchFilter(ROW, { field: 'created', operator: 'gte', value: '2024-01-01' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'created', operator: 'lt', value: '2024-01-01' }, FIELDS)).toBe(false);
  });

  test('is_null / is_not_null', () => {
    const blank = { name: '' };
    expect(matchFilter(blank, { field: 'name', operator: 'is_null', value: '' }, FIELDS)).toBe(true);
    expect(matchFilter(ROW, { field: 'name', operator: 'is_not_null', value: '' }, FIELDS)).toBe(true);
    expect(matchFilter(blank, { field: 'name', operator: 'is_not_null', value: '' }, FIELDS)).toBe(false);
  });
});

describe('filterUtils — compositions', () => {
  const rows = [
    { name: 'Pomme', price: 5 },
    { name: 'Poire', price: 15 },
    { name: 'Banane', price: 25 },
  ];

  test('applyFilters (ET)', () => {
    const result = applyFilters(
      rows,
      [
        { field: 'price', operator: 'gt', value: '10' },
        { field: 'name', operator: 'contains', value: 'a' },
      ],
      FIELDS,
      'and'
    );
    expect(result.map((r) => r.name)).toEqual(['Banane']);
  });

  test('applyFilters (OU)', () => {
    const result = applyFilters(
      rows,
      [
        { field: 'price', operator: 'lt', value: '10' },
        { field: 'name', operator: 'contains', value: 'oi' },
      ],
      FIELDS,
      'or'
    );
    expect(result.map((r) => r.name).sort()).toEqual(['Poire', 'Pomme']);
  });

  test('applySearch insensible aux accents', () => {
    expect(applySearch(rows, 'pom', ['name']).map((r) => r.name)).toEqual(['Pomme']);
    expect(applySearch([{ name: 'Café' }], 'cafe', ['name']).length).toBe(1);
  });

  test('countActiveFilters ignore les valeurs vides', () => {
    expect(
      countActiveFilters([
        { field: 'name', operator: 'contains', value: 'x' },
        { field: 'price', operator: 'is_null', value: '' },
      ])
    ).toBe(2);
    expect(
      countActiveFilters([
        { field: 'name', operator: 'contains', value: '' },
        { field: 'price', operator: 'gt', value: '' },
      ])
    ).toBe(0);
  });
});
