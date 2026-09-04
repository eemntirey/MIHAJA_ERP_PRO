// shared/utils/__tests__/navPermissions.test.js
// Tests unitaires des helpers de visibilité dynamique RBAC.
// Couvre les cas 1 a 8 du cahier RBAC + cas super_admin + cas plan/tenant.

import {
  canAccessNavItem,
  filterNavGroups,
  canAccessRoute,
  isModuleAllowed,
} from '../navPermissions';

const makeHas = (userPerms) => {
  const set = new Set(userPerms || []);
  const hasPermission = (p) => set.has(p);
  const hasAnyPermission = (arr) =>
    Array.isArray(arr) && arr.length > 0 && arr.some(hasPermission);
  return { hasPermission, hasAnyPermission };
};

const makeCtx = (overrides = {}) => ({
  hasPermission: () => false,
  hasAnyPermission: () => false,
  hasRole: () => false,
  allowedModules: null,
  isSuperAdmin: false,
  ...overrides,
});

describe('navPermissions', () => {
  describe('isModuleAllowed', () => {
    test('autorise si module vide (pas de gating)', () => {
      expect(isModuleAllowed(null, ['ventes'])).toBe(true);
      expect(isModuleAllowed(undefined, ['ventes'])).toBe(true);
      expect(isModuleAllowed('', ['ventes'])).toBe(true);
    });

    test('autorise si allowedModules inconnu (null/undefined)', () => {
      expect(isModuleAllowed('ventes', null)).toBe(true);
      expect(isModuleAllowed('ventes', undefined)).toBe(true);
    });

    test('rejette si module absent de la liste du plan', () => {
      expect(isModuleAllowed('ventes', ['produits', 'clients'])).toBe(false);
    });

    test('autorise si module present dans la liste du plan', () => {
      expect(isModuleAllowed('ventes', ['ventes', 'produits'])).toBe(true);
    });
  });

  describe('canAccessNavItem', () => {
    const saleItem = {
      path: '/sales',
      permissions: ['sale.view', 'sale.create', 'sale.update', 'sale.delete'],
      module: 'ventes',
    };

    test('cas 1 — utilisateur sans permission -> module masque', () => {
      const ctx = makeCtx({ ...makeHas([]), allowedModules: ['ventes'] });
      expect(canAccessNavItem(saleItem, ctx)).toBe(false);
    });

    test('cas 2 — sale.view seulement -> module visible', () => {
      const ctx = makeCtx({ ...makeHas(['sale.view']), allowedModules: ['ventes'] });
      expect(canAccessNavItem(saleItem, ctx)).toBe(true);
    });

    test('cas 3 — sale.view + sale.create (sans delete) -> visible', () => {
      const ctx = makeCtx({
        ...makeHas(['sale.view', 'sale.create']),
        allowedModules: ['ventes'],
      });
      expect(canAccessNavItem(saleItem, ctx)).toBe(true);
    });

    test('create sans view -> NON visible (module.view requis)', () => {
      const ctx = makeCtx({ ...makeHas(['sale.create']), allowedModules: ['ventes'] });
      expect(canAccessNavItem(saleItem, ctx)).toBe(false);
    });

    test('module absent du plan -> masque meme avec permissions', () => {
      const ctx = makeCtx({
        ...makeHas(['sale.view', 'sale.create']),
        allowedModules: ['produits'], // 'ventes' absent
      });
      expect(canAccessNavItem(saleItem, ctx)).toBe(false);
    });

    test('permissions declarees vides -> non visible', () => {
      const item = { path: '/foo', permissions: [], module: null };
      const ctx = makeCtx({ ...makeHas(['anything']) });
      expect(canAccessNavItem(item, ctx)).toBe(false);
    });

    test('roleFallback declenche si permissions refusees', () => {
      const adminItem = {
        path: '/users',
        permissions: ['user.view'],
        roleFallback: ['admin', 'super_admin'],
        module: null,
      };
      const ctx = makeCtx({
        ...makeHas([]),
        hasRole: (r) => r === 'admin',
      });
      expect(canAccessNavItem(adminItem, ctx)).toBe(true);
    });

    test('super_admin -> acces total', () => {
      const ctx = makeCtx({ isSuperAdmin: true });
      expect(canAccessNavItem(saleItem, ctx)).toBe(true);
    });

    test('ctx manquant -> false', () => {
      expect(canAccessNavItem(saleItem, null)).toBe(false);
      expect(canAccessNavItem(null, makeCtx({}))).toBe(false);
    });
  });

  describe('filterNavGroups — groupes jamais vides', () => {
    const vente = {
      path: '/sales',
      group: 'Commercial',
      permissions: ['sale.view'],
      module: 'ventes',
    };
    const client = {
      path: '/clients',
      group: 'Commercial',
      permissions: ['client.view'],
      module: 'clients',
    };
    const rh = {
      path: '/hr',
      group: 'Gestion',
      permissions: ['employe.view'],
      module: 'rh',
    };
    const groups = [
      { label: 'Commercial', items: [vente, client] },
      { label: 'Gestion', items: [rh] },
    ];

    test('cas 5 — aucune permission -> tous les groupes vides -> []', () => {
      const out = filterNavGroups(groups, makeCtx({ ...makeHas([]) }));
      expect(out).toEqual([]);
    });

    test('cas 6 — permission sur un seul enfant -> groupe visible avec 1 item', () => {
      const out = filterNavGroups(
        groups,
        makeCtx({ ...makeHas(['order.view']), allowedModules: ['clients'] })
      );
      // Aucune permission ici -> tout vide.
      expect(out).toEqual([]);

      const out2 = filterNavGroups(
        groups,
        makeCtx({ ...makeHas(['client.view']), allowedModules: ['clients'] })
      );
      expect(out2).toHaveLength(1);
      expect(out2[0].label).toBe('Commercial');
      expect(out2[0].items.map((i) => i.path)).toEqual(['/clients']);
    });

    test('groupe vide filtre (jamais affiche sans enfant)', () => {
      const out = filterNavGroups(
        groups,
        makeCtx({ ...makeHas(['employe.view']), allowedModules: ['rh'] })
      );
      expect(out).toHaveLength(1);
      expect(out[0].label).toBe('Gestion');
    });
  });

  describe('canAccessRoute — garde d acces direct par URL', () => {
    const PATH_PERMISSION_MAP = {
      '/sales': ['sale.view'],
      '/users': ['user.view'],
      '/roles': ['admin.access'],
    };
    const PATH_MODULE_MAP = {
      '/sales': 'ventes',
      '/users': null,
      '/roles': null,
    };

    test('cas 7 — sans permission -> refuse', () => {
      const ctx = makeCtx({ ...makeHas([]) });
      expect(
        canAccessRoute('/sales', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
        })
      ).toBe(false);
    });

    test('cas 7 — avec permission -> autorise', () => {
      const ctx = makeCtx({ ...makeHas(['sale.view']) });
      expect(
        canAccessRoute('/sales', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
        })
      ).toBe(true);
    });

    test('module du plan bloque l acces', () => {
      const ctx = makeCtx({
        ...makeHas(['sale.view']),
        allowedModules: ['produits'], // ventes absent
      });
      expect(
        canAccessRoute('/sales', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
        })
      ).toBe(false);
    });

    test('skipModuleGatePaths : /users jamais gate par plan', () => {
      const ctx = makeCtx({
        ...makeHas(['user.view']),
        allowedModules: [], // aucun module -> tout refuse par defaut
      });
      expect(
        canAccessRoute('/users', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
          skipModuleGatePaths: ['/users'],
        })
      ).toBe(true);
    });

    test('super_admin -> acces direct autorise meme sans permission', () => {
      const ctx = makeCtx({ isSuperAdmin: true });
      expect(
        canAccessRoute('/roles', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
        })
      ).toBe(true);
    });
  });

  describe('integration — cas 1 a 8 du cahier RBAC', () => {
    const PATH_PERMISSION_MAP = {
      '/sales': ['sale.view'],
      '/clients': ['client.view'],
      '/products': ['product.view'],
    };
    const PATH_MODULE_MAP = {
      '/sales': 'ventes',
      '/clients': 'clients',
      '/products': 'produits',
    };

    const navItems = [
      { path: '/sales', group: 'Commercial', permissions: ['sale.view'], module: 'ventes' },
      { path: '/clients', group: 'Commercial', permissions: ['client.view'], module: 'clients' },
      { path: '/products', group: 'Catalogue', permissions: ['product.view'], module: 'produits' },
    ];
    const groups = [
      { label: 'Commercial', items: navItems.filter((i) => i.group === 'Commercial') },
      { label: 'Catalogue', items: navItems.filter((i) => i.group === 'Catalogue') },
    ];

    test('cas 1+5 — sans permission, aucun item ni groupe visible', () => {
      const ctx = makeCtx({ ...makeHas([]) });
      const visibleItems = navItems.filter((i) => canAccessNavItem(i, ctx));
      expect(visibleItems).toEqual([]);
      const visibleGroups = filterNavGroups(groups, ctx);
      expect(visibleGroups).toEqual([]);
    });

    test('cas 2+6 — un seul enfant -> son groupe apparait avec un seul item', () => {
      const ctx = makeCtx({
        ...makeHas(['client.view']),
        allowedModules: ['clients', 'produits', 'ventes'],
      });
      const visibleGroups = filterNavGroups(groups, ctx);
      expect(visibleGroups).toHaveLength(1);
      expect(visibleGroups[0].label).toBe('Commercial');
      expect(visibleGroups[0].items.map((i) => i.path)).toEqual(['/clients']);
    });

    test('cas 3 — view + create (sans delete) -> visible', () => {
      const item = navItems.find((i) => i.path === '/sales');
      const ctx = makeCtx({
        ...makeHas(['sale.view', 'sale.create']),
        allowedModules: ['ventes'],
      });
      expect(canAccessNavItem(item, ctx)).toBe(true);
    });

    test('cas 4 — view sans delete -> visible (boutons caches au composant)', () => {
      const item = navItems.find((i) => i.path === '/sales');
      const ctx = makeCtx({ ...makeHas(['sale.view']), allowedModules: ['ventes'] });
      expect(canAccessNavItem(item, ctx)).toBe(true);
    });

    test('cas 7 — acces direct sans permission -> refuse', () => {
      const ctx = makeCtx({ ...makeHas([]) });
      expect(
        canAccessRoute('/sales', PATH_PERMISSION_MAP, ctx, {
          pathModuleMap: PATH_MODULE_MAP,
        })
      ).toBe(false);
    });

    test('cas 8 — tenant A n a pas les modules du tenant B (plan vide)', () => {
      // Le plan du tenant A n inclut pas 'ventes' : on simule allowedModules=[].
      const ctx = makeCtx({
        ...makeHas(['sale.view', 'client.view', 'product.view']),
        allowedModules: ['produits'], // ventes et clients absents
      });
      const visible = navItems.filter((i) => canAccessNavItem(i, ctx));
      expect(visible.map((i) => i.path)).toEqual(['/products']);
    });
  });

  describe('integration — NAV_ITEMS reels (source unique de verite)', () => {
    // On charge la config reelle partagee entre web et desk. Toute
    // regression de la config ou de navPermissions sera detectee ici.
    // eslint-disable-next-line global-require
    const { NAV_ITEMS, NAV_GROUPS, buildNavGroups, PATH_PERMISSION_MAP, PATH_MODULE_MAP } = require('../../navConfig');

    test('NAV_ITEMS expose des permissions non vides pour chaque item', () => {
      expect(NAV_ITEMS.length).toBeGreaterThan(0);
      for (const item of NAV_ITEMS) {
        expect(Array.isArray(item.permissions)).toBe(true);
        expect(item.permissions.length).toBeGreaterThan(0);
      }
    });

    test('PATH_PERMISSION_MAP et PATH_MODULE_MAP derives de NAV_ITEMS', () => {
      for (const item of NAV_ITEMS) {
        expect(PATH_PERMISSION_MAP[item.path]).toEqual(item.permissions);
        expect(PATH_MODULE_MAP[item.path]).toEqual(item.module || null);
      }
    });

    test('aucun groupe vide : filterNavGroups ne renvoie jamais items=[]', () => {
      // Utilisateur SANS aucune permission effective.
      const ctx = makeCtx({ ...makeHas([]) });
      const groups = buildNavGroups();
      const out = filterNavGroups(groups, ctx);
      for (const g of out) {
        expect(g.items.length).toBeGreaterThan(0);
      }
      // Avec zero permission, on attend une liste vide (groupes tous masques).
      expect(out).toEqual([]);
    });

    test('NAV_GROUPS contient tous les groupes declares dans NAV_ITEMS', () => {
      const declared = new Set(NAV_ITEMS.map((i) => i.group).filter(Boolean));
      for (const g of declared) {
        expect(NAV_GROUPS).toContain(g);
      }
    });
  });
});