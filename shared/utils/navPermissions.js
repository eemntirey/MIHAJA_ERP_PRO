// shared/utils/navPermissions.js
// Source unique de vérité pour la visibilité dynamique des modules
// (sidebar + guards de routes), partagée entre l'app web et l'app desktop.
//
// Règle fonctionnelle :
//   VISIBLE(item) = (hasAnyPermission(item.permissions) OU roleFallback)
//                   AND module disponible pour le tenant (plan)
//   VISIBLE(group) = AU MOINS UN enfant visible
//                    (un groupe ne reste JAMAIS affiché vide)
//
// La visibilité UI n'est qu'une commodité : la sécurité réelle reste
// appliquée côté backend (@permission_required + tenant_required).

/**
 * Vérifie qu'un module est disponible pour le tenant courant (plan d'abonnement).
 * `allowedModules === null/undefined` => pas d'info (essai, super_admin...), on autorise.
 *
 * @param {string|null|undefined} moduleName
 * @param {Array<string>|null|undefined} allowedModules
 * @returns {boolean}
 */
export const isModuleAllowed = (moduleName, allowedModules) => {
  if (!moduleName) return true;
  if (allowedModules === null || allowedModules === undefined) return true;
  if (!Array.isArray(allowedModules)) return true;
  return allowedModules.includes(moduleName);
};

/**
 * Évalue la visibilité d'un item de navigation déclaratif.
 *
 * @param {Object} item    Item de nav : { path, label, permissions?, roleFallback?, module? }
 * @param {Object} ctx     Contexte auth : { hasPermission, hasAnyPermission, hasRole, allowedModules, isSuperAdmin }
 * @returns {boolean}
 */
export const canAccessNavItem = (item, ctx) => {
  if (!item) return false;
  if (!ctx) return false;

  // Super admin : accès complet (comportement backend préservé).
  if (ctx.isSuperAdmin) return true;

  // 1. Permission effective (RBAC : rôle ENUM ou rôle custom).
  //    Une liste de permissions VIDE rend l'item NON visible (sécurité par
  //    défaut) — l'item doit déclarer explicitement ses permissions.
  let permOk = true;
  if (Array.isArray(item.permissions) && item.permissions.length > 0) {
    permOk = ctx.hasAnyPermission
      ? ctx.hasAnyPermission(item.permissions)
      : item.permissions.some((p) => ctx.hasPermission && ctx.hasPermission(p));
  } else if (!Array.isArray(item.permissions)) {
    permOk = true;
  } else {
    permOk = false;
  }

  if (!permOk) {
    // Repli déclaratif explicite (ex. section Admin : rôles admin/super_admin,
    // aligné sur les règles backend existantes _ensure_admin / is_admin).
    const fallback = Array.isArray(item.roleFallback) ? item.roleFallback : [];
    if (fallback.length === 0) return false;
    if (!fallback.some((r) => (ctx.hasRole ? ctx.hasRole(r) : false))) return false;
  }

  // 2. Module disponible pour le tenant (plan d'abonnement).
  //    allowedModules === null signifie "aucune restriction connue" (essai, etc.).
  if (!isModuleAllowed(item.module, ctx.allowedModules)) return false;

  return true;
};

/**
 * Filtre des groupes de navigation : chaque groupe ne garde que ses enfants
 * accessibles, et les groupes sans enfant accessible sont supprimés
 * (un groupe ne doit jamais rester affiché avec un menu vide).
 *
 * @param {Array}  groups [{ label, items: [...] }]
 * @param {Object} ctx    Contexte auth (voir canAccessNavItem)
 * @returns {Array} groupes filtrés
 */
export const filterNavGroups = (groups, ctx) =>
  (groups || [])
    .map((group) => ({
      ...group,
      items: (group.items || []).filter((item) => canAccessNavItem(item, ctx)),
    }))
    .filter((group) => group.items.length > 0);

/**
 * Retourne les permissions requises pour une URL directe (guard de route).
 * `permissions` peut être une liste directe ou une fonction (matching par préfixe).
 *
 * @param {string} pathname
 * @param {Object} pathPermissions Map path -> permissions[] (ex. PATH_PERMISSIONS)
 * @returns {Array|null} permissions requises, ou null si la route n'est pas gardée par permission
 */
export const getRequiredPermissions = (pathname, pathPermissions) => {
  if (!pathname || !pathPermissions) return null;
  if (pathPermissions[pathname]) return pathPermissions[pathname];
  // Matching par préfixe (ex. /sales/12)
  const match = Object.keys(pathPermissions).find(
    (p) => p !== '/' && (pathname === p || pathname.startsWith(`${p}/`))
  );
  return match ? pathPermissions[match] : null;
};

/**
 * Décision d'accès à une route directe (URL tapée à la main).
 * Utilisée par les guards frontend ; le backend reste la protection principale.
 *
 * Combine :
 *   - permission effective (any-of)
 *   - roleFallback déclaratif (si fourni via ctx.roleFallbackFor)
 *   - disponibilité du module dans le plan du tenant (si ctx.pathModuleMap fourni)
 *
 * @param {string} pathname
 * @param {Object} pathPermissions  Map path -> permissions[]
 * @param {Object} ctx              Contexte auth (voir canAccessNavItem)
 * @param {Object} [opts]
 * @param {Object} [opts.pathModuleMap]  Map path -> module (pour le gating plan)
 * @param {string[]} [opts.skipModuleGatePaths] Chemins à ne PAS gater par module
 *                                              (ex. ADMIN_PATHS côté web).
 * @returns {boolean}
 */
export const canAccessRoute = (pathname, pathPermissions, ctx, opts = {}) => {
  if (!ctx) return false;
  if (ctx.isSuperAdmin) return true;

  const skipModule = Array.isArray(opts.skipModuleGatePaths)
    && opts.skipModuleGatePaths.includes(pathname);

  const required = getRequiredPermissions(pathname, pathPermissions);
  if (required && required.length > 0) {
    const ok = ctx.hasAnyPermission
      ? ctx.hasAnyPermission(required)
      : required.some((p) => ctx.hasPermission && ctx.hasPermission(p));
    if (!ok) {
      const fallback = ctx.roleFallbackFor
        ? ctx.roleFallbackFor(pathname)
        : null;
      if (Array.isArray(fallback) && fallback.length > 0) {
        if (!fallback.some((r) => (ctx.hasRole ? ctx.hasRole(r) : false))) return false;
      } else {
        return false;
      }
    }
  }

  // Gating par module (plan du tenant), sauf skipModule.
  if (!skipModule && opts.pathModuleMap) {
    const moduleName = opts.pathModuleMap[pathname] || null;
    if (!isModuleAllowed(moduleName, ctx.allowedModules)) return false;
  }

  return true;
};

export default {
  canAccessNavItem,
  filterNavGroups,
  getRequiredPermissions,
  canAccessRoute,
};
