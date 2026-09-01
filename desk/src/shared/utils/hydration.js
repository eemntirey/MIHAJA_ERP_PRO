
// shared/utils/hydration.js
// Hydratation des données au démarrage de l'application.
// Compare les données locales avec le backend et résout les conflits.

import { syncEngine } from './syncEngine';
import { syncService, favoriteService, columnConfigService, filterPresetService } from '../services/api';

const HYDRATION_ENDPOINTS = {
  favorites: () => syncService.pull().then((res) => res.data),
};

/**
 * Hydrate les données locales depuis le backend au démarrage.
 * Stratégie: "dernière écriture gagne" (LWW).
 *
 * @param {Object} options
 * @param {string[]} [options.entities=['favorites','columns','filters']] - entités à hydrater
 * @param {Function} [options.onProgress] - callback de progression
 * @returns {Promise<Object>} rapport d'hydratation
 */
export async function hydrateApp(options = {}) {
  const {
    entities = ['favorites', 'columns', 'filters'],
    onProgress,
  } = options;

  const report = {
    favorites: { pulled: 0, pushed: 0, conflicts: 0 },
    columns: { pulled: 0, pushed: 0, conflicts: 0 },
    filters: { pulled: 0, pushed: 0, conflicts: 0 },
    queue: { hydrated: 0 },
  };

  if (!syncEngine.isOnline()) {
    return { ...report, offline: true };
  }

  try {
    const backendState = await HYDRATION_ENDPOINTS.favorites();
    if (backendState && backendState.favorites) {
      const localFavorites = favoriteService.getAll?.() || [];
      const backendFavorites = backendState.favorites || [];

      const merged = mergeFavorites(localFavorites, backendFavorites);
      report.favorites.pulled = backendFavorites.length;
      report.favorites.conflicts = Math.max(0, localFavorites.length - backendFavorites.length);
    }
  } catch {
    // Backend indisponible, on garde les données locales
  }

  const queueReport = await syncEngine.hydrate(
    async (entry) => {
      await syncService.push({
        mutations: [{
          entity: entry.entity,
          op: entry.op,
          payload: entry.payload,
        }],
      });
    },
    async () => {
      try {
        return await syncService.status().then((res) => res.data);
      } catch {
        return null;
      }
    }
  );

  report.queue.hydrated = queueReport.hydrated || 0;

  if (typeof onProgress === 'function') {
    onProgress(report);
  }

  return report;
}

function mergeFavorites(local, remote) {
  const map = new Map();

  remote.forEach((item) => {
    map.set(item.path || item.id, { ...item, _source: 'remote' });
  });

  local.forEach((item) => {
    const key = item.path || item.id;
    const existing = map.get(key);
    if (!existing) {
      map.set(key, { ...item, _source: 'local' });
    } else {
      const resolved = syncEngine.resolveConflict(item, existing, 'lww');
      map.set(key, { ...resolved, _source: 'merged' });
    }
  });

  return Array.from(map.values());
}

export default hydrateApp;
