// desk/src/components/layout/navConfig.js
// Shim de compatibilité — la définition canonique vit désormais dans
// `shared/navConfig.js` (utilisée par web et desk). Ce fichier ré-exporte
// pour préserver les imports existants `./navConfig`.

import {
  NAV_ITEMS as _NAV_ITEMS,
  NAV_GROUPS,
  buildNavGroups,
  findNavItem,
  buildBreadcrumb,
} from '@shared/navConfig';

export const NAV_ITEMS = _NAV_ITEMS;
export { NAV_GROUPS, buildNavGroups, findNavItem, buildBreadcrumb };
export default _NAV_ITEMS;