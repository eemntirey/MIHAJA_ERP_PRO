// Configuration centralisée de navigation (Plan Desktop §2.1, §4.2, §4.3).
// Partagée entre DesktopSidebar, TopBar (breadcrumbs) et CommandPalette.

export const NAV_ITEMS = [
  { path: '/dashboard', label: 'Tableau de bord', icon: 'ti-layout-dashboard', group: 'Piloter' },
  { path: '/products', label: 'Produits', icon: 'ti-package', group: 'Piloter', badge: 'products' },
  { path: '/clients', label: 'Clients', icon: 'ti-users', group: 'Piloter' },
  { path: '/sales', label: 'Ventes', icon: 'ti-shopping-cart', group: 'Piloter', badge: 'sales' },
  { path: '/invoices', label: 'Factures', icon: 'ti-file-text', group: 'Piloter', badge: 'invoices' },
  { path: '/payments', label: 'Paiements', icon: 'ti-credit-card', group: 'Piloter' },
  { path: '/inventory', label: 'Stock', icon: 'ti-box', group: 'Opérations', badge: 'stock' },
  { path: '/suppliers', label: 'Fournisseurs', icon: 'ti-truck', group: 'Opérations' },
  { path: '/purchases', label: 'Achats', icon: 'ti-shopping-cart-plus', group: 'Opérations' },
  { path: '/delivery', label: 'Livraisons', icon: 'ti-truck-delivery', group: 'Opérations' },
  { path: '/hr', label: 'Ressources Humaines', icon: 'ti-users-group', group: 'Gestion' },
  { path: '/accounting', label: 'Comptabilité', icon: 'ti-calculator', group: 'Gestion' },
  { path: '/documents', label: 'Documents', icon: 'ti-file-description', group: 'Gestion' },
  { path: '/ai', label: 'Assistant IA', icon: 'ti-robot', group: 'Gestion' },
  { path: '/super-admin', label: 'Administration', icon: 'ti-settings', group: 'Admin' },
  { path: '/users', label: 'Utilisateurs', icon: 'ti-users', group: 'Admin' },
  { path: '/roles', label: 'Rôles', icon: 'ti-user-cog', group: 'Admin' },
  { path: '/permissions', label: 'Permissions', icon: 'ti-key', group: 'Admin' },
];

export const NAV_GROUPS = ['Piloter', 'Opérations', 'Gestion', 'Admin'];

export const findNavItem = (pathname) =>
  NAV_ITEMS.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`));

// Construit un fil d'Ariane cliquable à partir de l'URL (Plan §4.3).
export const buildBreadcrumb = (pathname, isAuthenticated = true) => {
  const segments = pathname.split('/').filter(Boolean);
  const crumbs = isAuthenticated
    ? [{ label: 'Accueil', to: '/dashboard' }]
    : [{ label: 'Connexion', to: '/login' }];

  const root = segments[0] ? `/${segments[0]}` : (isAuthenticated ? '/dashboard' : '/login');
  const navItem = NAV_ITEMS.find((item) => item.path === root);

  if (navItem) {
    crumbs.push({ label: navItem.label, to: navItem.path });
  }

  segments.slice(1).forEach((segment) => {
    const isId = /^\d+$/.test(segment);
    const label = isId ? `#${segment}` : segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    crumbs.push({ label, to: null });
  });

  return crumbs;
};

export default NAV_ITEMS;
