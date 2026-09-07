// web/frontend/src/__tests__/navPermissions.test.js
// Re-export du test partagé (shared/utils/__tests__/navPermissions.test.js)
// via l'alias @shared configuré dans package.json -> jest.moduleNameMapper.

import {
  canAccessNavItem,
  filterNavGroups,
  canAccessRoute,
  isModuleAllowed,
} from '@shared/utils/navPermissions';

describe('@shared/utils/navPermissions (alias web)', () => {
  test('helpers disponibles', () => {
    expect(typeof canAccessNavItem).toBe('function');
    expect(typeof filterNavGroups).toBe('function');
    expect(typeof canAccessRoute).toBe('function');
    expect(typeof isModuleAllowed).toBe('function');
  });

  test('isModuleAllowed — module absent du plan', () => {
    expect(isModuleAllowed('ventes', ['produits'])).toBe(false);
  });

  test('isModuleAllowed — module present du plan', () => {
    expect(isModuleAllowed('ventes', ['ventes', 'produits'])).toBe(true);
  });

  test('canAccessNavItem — sans permission -> false', () => {
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

  test('canAccessNavItem — avec permission -> true', () => {
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

  test('canAccessNavItem — super_admin -> true', () => {
    const ctx = {
      hasPermission: () => false,
      hasAnyPermission: () => false,
      hasRole: () => false,
      allowedModules: [],
      isSuperAdmin: true,
    };
    expect(canAccessNavItem({ path: '/any' }, ctx)).toBe(true);
  });

  test('filterNavGroups — groupe vide retire', () => {
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

  test('canAccessRoute — acces direct sans permission -> false', () => {
    const ctx = {
      isSuperAdmin: false,
      hasAnyPermission: () => false,
      hasPermission: () => false,
      hasRole: () => false,
      allowedModules: null,
    };
    const pathPerms = { '/sales': ['sale.view'] };
    const pathModules = { '/sales': 'ventes' };
    expect(
      canAccessRoute('/sales', pathPerms, ctx, { pathModuleMap: pathModules })
    ).toBe(false);
  });
});