
// src/services/api.js
// Réexport du shared avec remplacement des services opérationnels
// par leurs versions offline-aware du desktop.

export { default } from '../../shared/services/api';
export * from '../../shared/services/api';

// Remplacer par versions offline-aware (écrase le shared)
export {
  saleService,
  stockService,
  clientService,
  factureService,
  dashboardService,
  productService,
  notificationService,
  favoriteService,
  columnConfigService,
  filterPresetService,
  syncService,
  employeService,
  presenceService,
  salaireService,
  primeService,
  stagiaireService,
  compteService,
  ecritureService,
  tresorerieService,
  documentService,
  devisService,
  tenantService,
} from './desktopApi';
