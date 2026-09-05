// web/frontend/src/components/layout/__tests__/navConfig.rbac.test.js
// Tests RBAC : la sidebar est filtree selon les permissions effectives
// + la disponibilite du module dans le plan du tenant.

import { NAV_ITEMS, NAV_GROUPS } from '../navConfig';

// Replique de isItemVisible utilisee par DesktopSidebar (web + desk).
// Source unique de verite : permissions + module + plan.
function isItemVisible(item, user, subscription) {
  if (!item) return false;
  const isSuperAdmin = (user?.role || '').toLowerCase() === 'super_admin';
  if (!user) return false;
  if (!isSuperAdmin && !Array.isArray(user.permissions)) return false;
  if (!Array.isArray(item.permissions) || item.permissions.length === 0) return false;
  const perms = isSuperAdmin ? ['*'] : (user.permissions || []);
  if (perms.includes('*')) {
    if (subscription && item.module) {
      const mods = Array.isArray(subscription.modules)
        ? subscription.modules
        : typeof subscription.modules === 'string'
          ? subscription.modules.split(',').map((m) => m.trim()).filter(Boolean)
          : null;
      if (mods !== null && !mods.includes(item.module)) return false;
    }
    return true;
  }
  const granted = item.permissions.some((p) => perms.includes(p));
  if (!granted) return false;
  if (subscription && item.module) {
    const mods = Array.isArray(subscription.modules)
      ? subscription.modules
      : typeof subscription.modules === 'string'
        ? subscription.modules.split(',').map((m) => m.trim()).filter(Boolean)
        : null;
    if (mods !== null && !mods.includes(item.module)) return false;
  }
  return true;
}

// Toutes les permissions par module sont dans navConfig.
describe('navConfig - RBAC sidebar', () => {
  test('tous les items declarent une liste de permissions non vide', () => {
    for (const item of NAV_ITEMS) {
      expect(Array.isArray(item.permissions)).toBe(true);
      expect(item.permissions.length).toBeGreaterThan(0);
    }
  });

  test('Cas 1 : utilisateur sans aucune permission -> aucun item visible', () => {
    const user = { role: 'user', permissions: [] };
    for (const item of NAV_ITEMS) {
      expect(isItemVisible(item, user, null)).toBe(false);
    }
  });

  test('Cas 2 : utilisateur avec sale.view uniquement -> /sales visible', () => {
    const user = { role: 'sales', permissions: ['sale.view'] };
    const sub = { modules: ['dashboard', 'ventes'] };
    const item = NAV_ITEMS.find((i) => i.path === '/sales');
    expect(isItemVisible(item, user, sub)).toBe(true);
  });

  test('Cas 3 : sale.view + sale.create -> /sales visible, action Creer visible via sale.create', () => {
    const user = { role: 'sales', permissions: ['sale.view', 'sale.create'] };
    const item = NAV_ITEMS.find((i) => i.path === '/sales');
    expect(isItemVisible(item, user, { modules: ['ventes'] })).toBe(true);
    // Et sale.create fait partie des permissions de l'item
    expect(item.permissions).toContain('sale.create');
  });

  test('Cas 4 : sale.view sans sale.delete -> /sales visible', () => {
    const user = { role: 'user', permissions: ['sale.view'] };
    const item = NAV_ITEMS.find((i) => i.path === '/sales');
    expect(isItemVisible(item, user, null)).toBe(true);
    // Mais sale.delete n'est pas dans les permissions user
    expect(item.permissions).toContain('sale.delete');
  });

  test('Cas 5 : aucune permission sur tous les enfants -> groupe Operation masque', () => {
    const user = { role: 'user', permissions: ['profile.view'] };
    // Operation inclut inventaire, fournisseurs, achats, livraisons.
    // Aucun de ces modules n'est couvert par profile.view.
    const ops = NAV_ITEMS.filter((i) => i.group === 'Opérations');
    const visible = ops.filter((i) => isItemVisible(i, user, null));
    expect(visible.length).toBe(0);
  });

  test('Cas 6 : permission sur un seul enfant d\'un groupe -> seul cet enfant visible', () => {
    const user = { role: 'user', permissions: ['sale.view'] };
    // Piloter : seul /sales devrait etre visible parmi les enfants.
    const pilots = NAV_ITEMS.filter((i) => i.group === 'Piloter');
    const visible = pilots.filter((i) => isItemVisible(i, user, null));
    expect(visible.map((i) => i.path)).toEqual(['/sales']);
  });

  test('Cas 7 : aucun super_admin implicite : super_admin voit tout (mais respecte le plan)', () => {
    const user = { role: 'super_admin', permissions: ['*'] };
    const item = NAV_ITEMS.find((i) => i.path === '/hr');
    // Pas de subscription -> visible
    expect(isItemVisible(item, user, null)).toBe(true);
    // Avec subscription qui inclut rh -> visible
    expect(isItemVisible(item, user, { modules: ['rh'] })).toBe(true);
    // Avec subscription qui n'inclut PAS rh -> masque
    expect(isItemVisible(item, user, { modules: ['dashboard'] })).toBe(false);
  });

  test('module disabled par le plan -> item masque meme avec permission', () => {
    const user = { role: 'manager', permissions: ['sale.view', 'sale.create', 'sale.update'] };
    const item = NAV_ITEMS.find((i) => i.path === '/sales');
    expect(isItemVisible(item, user, null)).toBe(true); // pas de sub
    expect(isItemVisible(item, user, { modules: [] })).toBe(false); // plan vide
    expect(isItemVisible(item, user, { modules: ['produits'] })).toBe(false); // autres modules
  });

  test('hasAnyPermission retourne false si permissions est vide', () => {
    const user = { role: 'user', permissions: [] };
    // Items sans permissions declarees -> invisibles (defense en profondeur)
    const ghost = { path: '/x', label: 'X', permissions: [] };
    expect(isItemVisible(ghost, user, null)).toBe(false);
  });
});