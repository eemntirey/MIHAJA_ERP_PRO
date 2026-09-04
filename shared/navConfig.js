// shared/navConfig.js
// Configuration centralisée de navigation — SOURCE UNIQUE partagée entre
// l'application web (web/frontend) et l'application desktop (desk).
//
// RBAC (règle fonctionnelle) :
//   VISIBLE(item) = hasAnyPermission(item.permissions)
//                   AND isModuleEnabled(item.module)
//                   ET (item.roleFallback matche si déclaré)
//
//   VISIBLE(group) = AU MOINS UN enfant visible
//                    (un groupe ne reste JAMAIS affiché vide)
//
// Chaque entrée déclare ses permissions EFFECTIVES (alignées avec
// web/backend/app/security/permission_matrix.py). Le champ `module`
// correspond aux modules autorisés par le plan d'abonnement du tenant
// (web/backend/app/security/plans.py::AVAILABLE_MODULES).
//
// IMPORTANT : `module.view` est la permission principale qui autorise
// l'affichage du module dans la sidebar. Les permissions d'écriture
// (create/update/delete) ne rendent PAS le module visible si l'utilisateur
// ne possède pas la permission `module.view` correspondante.
//
// La sidebar n'est qu'une commodité UI : la sécurité réelle reste appliquée
// côté backend par les décorateurs @permission_required + @tenant_required.

export const NAV_ITEMS = [
  {
    path: '/dashboard',
    label: 'Tableau de bord',
    icon: 'ti-layout-dashboard',
    group: 'Piloter',
    module: 'dashboard',
    permissions: ['profile.view', 'dashboard.view'],
  },
  {
    path: '/products',
    label: 'Produits',
    icon: 'ti-package',
    group: 'Piloter',
    module: 'produits',
    badge: 'products',
    permissions: ['product.view', 'product.create', 'product.update', 'product.delete'],
  },
  {
    path: '/clients',
    label: 'Clients',
    icon: 'ti-users',
    group: 'Piloter',
    module: 'clients',
    permissions: ['client.view', 'client.create', 'client.update', 'client.delete'],
  },
  {
    path: '/sales',
    label: 'Ventes',
    icon: 'ti-shopping-cart',
    group: 'Piloter',
    module: 'ventes',
    badge: 'sales',
    permissions: ['sale.view', 'sale.create', 'sale.update', 'sale.delete'],
  },
  {
    path: '/invoices',
    label: 'Factures',
    icon: 'ti-file-text',
    group: 'Piloter',
    module: 'factures',
    badge: 'invoices',
    permissions: ['invoice.view', 'invoice.create', 'invoice.update'],
  },
  {
    path: '/payments',
    label: 'Paiements',
    icon: 'ti-credit-card',
    group: 'Piloter',
    module: 'paiements',
    permissions: ['payment.view', 'payment.create'],
  },
  {
    path: '/inventory',
    label: 'Stock',
    icon: 'ti-box',
    group: 'Opérations',
    module: 'stocks',
    badge: 'stock',
    permissions: ['stock.view', 'stock.update'],
  },
  {
    path: '/suppliers',
    label: 'Fournisseurs',
    icon: 'ti-truck',
    group: 'Opérations',
    module: null,
    permissions: ['supplier.view', 'supplier.create', 'supplier.update'],
  },
  {
    path: '/purchases',
    label: 'Achats',
    icon: 'ti-shopping-cart-plus',
    group: 'Opérations',
    module: 'achats',
    permissions: ['purchase_order.view', 'purchase_order.create'],
  },
  {
    path: '/delivery',
    label: 'Livraisons',
    icon: 'ti-truck-delivery',
    group: 'Opérations',
    module: 'livraison',
    permissions: ['delivery.view', 'delivery.update'],
  },
  {
    path: '/hr',
    label: 'Ressources Humaines',
    icon: 'ti-users-group',
    group: 'Gestion',
    module: 'rh',
    permissions: [
      'employe.view', 'employe.create', 'employe.update', 'employe.delete',
      'presence.view', 'presence.create', 'presence.update', 'presence.delete',
      'salaire.view', 'salaire.create', 'salaire.update', 'salaire.delete',
      'prime.view', 'prime.create', 'prime.update', 'prime.delete',
      'stagiaire.view', 'stagiaire.create', 'stagiaire.update', 'stagiaire.delete',
    ],
  },
  {
    path: '/accounting',
    label: 'Comptabilité',
    icon: 'ti-calculator',
    group: 'Gestion',
    module: 'comptabilite',
    permissions: [
      'compte.view', 'compte.create', 'compte.update', 'compte.delete',
      'ecriture.view', 'ecriture.create', 'ecriture.update', 'ecriture.delete',
      'tresorerie.view', 'tresorerie.create', 'tresorerie.update', 'tresorerie.delete',
    ],
    roleFallback: ['super_admin', 'admin', 'manager', 'accountant'],
  },
  {
    path: '/documents',
    label: 'Documents',
    icon: 'ti-file-description',
    group: 'Gestion',
    module: 'documents',
    permissions: ['quote.view', 'quote.create', 'invoice.view'],
  },
  {
    path: '/ai',
    label: 'Assistant IA',
    icon: 'ti-robot',
    group: 'Gestion',
    module: 'ia',
    permissions: ['report.view', 'profile.view'],
  },
  {
    path: '/super-admin',
    label: 'Administration',
    icon: 'ti-settings',
    group: 'Admin',
    module: null,
    permissions: ['super_admin.access'],
    roleFallback: ['super_admin'],
  },
  {
    path: '/users',
    label: 'Utilisateurs',
    icon: 'ti-users',
    group: 'Admin',
    module: null,
    permissions: ['user.view', 'user.create', 'user.update'],
    roleFallback: ['super_admin', 'admin'],
  },
  {
    path: '/roles',
    label: 'Rôles',
    icon: 'ti-user-cog',
    group: 'Admin',
    module: null,
    permissions: ['admin.access', 'super_admin.access'],
    roleFallback: ['super_admin', 'admin'],
  },
  {
    path: '/permissions',
    label: 'Permissions',
    icon: 'ti-key',
    group: 'Admin',
    module: null,
    permissions: ['admin.access', 'super_admin.access'],
    roleFallback: ['super_admin', 'admin'],
  },
];

export const NAV_GROUPS = ['Piloter', 'Opérations', 'Gestion', 'Admin'];

// Construit la liste de groupes { label, items } à partir de NAV_ITEMS.
export const buildNavGroups = () =>
  NAV_GROUPS.map((label) => ({
    label,
    items: NAV_ITEMS.filter((item) => item.group === label),
  }));

// Trouve l'item de nav correspondant à un pathname (supporte les sous-routes).
export const findNavItem = (pathname) =>
  NAV_ITEMS.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`));

// Construit un fil d'Ariane cliquable à partir de l'URL.
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

// Map déclarative pour les guards frontend (ProtectedRoute).
// Source UNIQUE alignée avec NAV_ITEMS — permissions + module pour chaque
// chemin. Ne PAS dupliquer ailleurs.
export const PATH_PERMISSION_MAP = NAV_ITEMS.reduce((acc, item) => {
  acc[item.path] = item.permissions || [];
  return acc;
}, {});

export const PATH_MODULE_MAP = NAV_ITEMS.reduce((acc, item) => {
  acc[item.path] = item.module || null;
  return acc;
}, {});

// Chemins d'administration — gardés en plus de la vérification de
// permission pour préserver le comportement existant (anti-bypass).
export const ADMIN_PATHS = ['/super-admin', '/users', '/roles', '/permissions'];

export default NAV_ITEMS;