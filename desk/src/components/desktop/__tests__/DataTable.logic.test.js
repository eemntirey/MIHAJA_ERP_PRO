// src/components/desktop/__tests__/DataTable.logic.test.js
import {
  nextSortState,
  sortRows,
  compareValues,
  getCellValue,
  VIRTUALIZATION_THRESHOLD,
} from '../DataTable';

const buildColumnMap = (columns) => {
  const map = new Map();
  columns.forEach((column) => map.set(column.key, column));
  return map;
};

describe('DataTable — logique de tri', () => {
  const columns = [
    { key: 'name', label: 'Nom' },
    { key: 'price', label: 'Prix', type: 'number' },
  ];
  const columnMap = buildColumnMap(columns);

  test('nextSortState : clic simple asc → desc → aucun', () => {
    expect(nextSortState([], 'name')).toEqual([{ key: 'name', direction: 'asc' }]);
    expect(nextSortState([{ key: 'name', direction: 'asc' }], 'name')).toEqual([
      { key: 'name', direction: 'desc' },
    ]);
    expect(nextSortState([{ key: 'name', direction: 'desc' }], 'name')).toEqual([]);
  });

  test('nextSortState : clic simple sur une nouvelle colonne réinitialise les autres critères', () => {
    const state = [{ key: 'name', direction: 'asc' }];
    expect(nextSortState(state, 'price')).toEqual([{ key: 'price', direction: 'asc' }]);
  });

  test('nextSortState : Maj+clic cumule les critères puis les retire', () => {
    const one = nextSortState([], 'name', true);
    expect(one).toEqual([{ key: 'name', direction: 'asc' }]);
    const two = nextSortState(one, 'price', true);
    expect(two).toEqual([
      { key: 'name', direction: 'asc' },
      { key: 'price', direction: 'asc' },
    ]);
    const three = nextSortState(two, 'price', true);
    expect(three).toEqual([
      { key: 'name', direction: 'asc' },
      { key: 'price', direction: 'desc' },
    ]);
    const four = nextSortState(three, 'price', true);
    expect(four).toEqual([{ key: 'name', direction: 'asc' }]);
  });

  test('compareValues : numérique, date, booléen, texte FR (tri naturel + accents)', () => {
    expect(compareValues(2, 10, 'number')).toBeLessThan(0);
    expect(compareValues('10', '2', 'number')).toBeGreaterThan(0);
    expect(compareValues('2020-01-01', '2021-01-01', 'date')).toBeLessThan(0);
    expect(compareValues(true, false)).toBeGreaterThan(0);
    expect(compareValues('abc2', 'abc10')).toBeLessThan(0); // tri naturel
    expect(compareValues('café', 'cache')).toBeGreaterThan(0); // insensible aux accents
  });

  test('getCellValue supporte accessor et clés imbriquées', () => {
    const row = { name: 'X', meta: { sku: 'S1' } };
    expect(getCellValue(row, { key: 'name' })).toBe('X');
    expect(getCellValue(row, { key: 'meta.sku' })).toBe('S1');
    expect(getCellValue(row, { accessor: (r) => r.name.toUpperCase() })).toBe('X');
  });

  test('sortRows : tri simple ascendant sur texte', () => {
    const rows = [{ name: 'Banane' }, { name: 'Abricot' }, { name: 'Citron' }];
    const sorted = sortRows(rows, [{ key: 'name', direction: 'asc' }], columnMap);
    expect(sorted.map((r) => r.name)).toEqual(['Abricot', 'Banane', 'Citron']);
  });

  test('sortRows : tri multi-critères (prix desc, puis nom asc)', () => {
    const rows = [
      { name: 'A', price: 10 },
      { name: 'B', price: 20 },
      { name: 'C', price: 20 },
      { name: 'D', price: 5 },
    ];
    const sorted = sortRows(
      rows,
      [
        { key: 'price', direction: 'desc' },
        { key: 'name', direction: 'asc' },
      ],
      columnMap
    );
    expect(sorted.map((r) => r.name)).toEqual(['B', 'C', 'A', 'D']);
  });

  test('sortRows : les valeurs vides sont reléguées en fin quelle que soit la direction', () => {
    const rows = [{ name: 'Z' }, { name: '' }, { name: 'A' }];
    const asc = sortRows(rows, [{ key: 'name', direction: 'asc' }], columnMap);
    expect(asc[asc.length - 1].name).toBe('');
    const desc = sortRows(rows, [{ key: 'name', direction: 'desc' }], columnMap);
    expect(desc[desc.length - 1].name).toBe('');
  });

  test('sortRows : garde l ordre stable quand critères égaux', () => {
    const rows = [{ name: 'A', price: 1 }, { name: 'B', price: 1 }, { name: 'C', price: 1 }];
    const sorted = sortRows(rows, [{ key: 'price', direction: 'asc' }], columnMap);
    expect(sorted.map((r) => r.name)).toEqual(['A', 'B', 'C']);
  });

  test('seuil de virtualisation par défaut > 80', () => {
    expect(VIRTUALIZATION_THRESHOLD).toBe(80);
  });
});
