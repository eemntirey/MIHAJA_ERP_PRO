// desk/src/shared/utils/__tests__/navPermissions.test.js
// Re-export du test partagé pour intégration à la suite de tests CRA du desk.
// Les assertions vivent dans shared/utils/__tests__/navPermissions.test.js
// (chemin absolu) — ce fichier vérifie que l'alias @shared est correctement
// câblé pour les imports depuis l'app desk.

import {
  canAccessNavItem,
  filterNavGroups,
  canAccessRoute,
} from '@shared/utils/navPermissions';

describe('@shared/utils/navPermissions (alias desk)', () => {
  test('l alias @shared est fonctionnel', () => {
    expect(typeof canAccessNavItem).toBe('function');
    expect(typeof filterNavGroups).toBe('function');
    expect(typeof canAccessRoute).toBe('function');
  });

  test('cas 1 — item sans permission', () => {
    const ctx = {
      hasPermission: () => false,
      hasAnyPermission: () => false,
      hasRole: () => false,
      allowedModules: ['ventes'],
      isSuperAdmin: false,
    };
    expect(
      canAccessNavItem(
        { path: '/sales', permissions: ['sale.view'], module: 'ventes' },
        ctx
      )
    ).toBe(false);
  });

  test('cas 2 — item avec permission', () => {
    const ctx = {
      hasPermission: (p) => p === 'sale.view',
      hasAnyPermission: (arr) => arr.includes('sale.view'),
      hasRole: () => false,
      allowedModules: ['ventes'],
      isSuperAdmin: false,
    };
    expect(
      canAccessNavItem(
        { path: '/sales', permissions: ['sale.view'], module: 'ventes' },
        ctx
      )
    ).toBe(true);
  });

  test('cas 5 — groupe vide filtre', () => {
    const ctx = {
      hasPermission: () => false,
      hasAnyPermission: () => false,
      hasRole: () => false,
      allowedModules: null,
      isSuperAdmin: false,
    };
    const groups = [
      { label: 'X', items: [{ path: '/a', permissions: ['a.view'], module: null }] },
    ];
    expect(filterNavGroups(groups, ctx)).toEqual([]);
  });
});