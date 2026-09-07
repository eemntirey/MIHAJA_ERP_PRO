
// shared/utils/migrateLocalStorage.js
// Migration des données localStorage existantes vers le nouveau format partagé.
// À appeler au démarrage de l'application (dans AuthContext ou App.js).

import { authStorage, AUTH_KEYS } from '../storage/authStorage';
import { buildKey, readJSON, writeJSON, removeKey, listKeys } from './localStore';
import { syncEngine } from './syncEngine';
import { favoriteService, columnConfigService, filterPresetService, syncService } from '../services/api';

const LEGACY_DESK_FAVORITES_KEY = 'desk_favorites';
const LEGACY_DESK_COLUMNS_PREFIX = 'erp.desk.columns.';
const LEGACY_DESK_FILTERS_PREFIX = 'erp.desk.filters.';
const MIGRATION_FLAG_KEY = 'erp.migration.completed';

/**
 * Vérifie si la migration a déjà été effectuée.
 */
export const isMigrationCompleted = () => {
  try {
    return localStorage.getItem(MIGRATION_FLAG_KEY) === 'true';
  } catch {
    return false;
  }
};

/**
 * Marque la migration comme terminée.
 */
export const markMigrationCompleted = () => {
  try {
    localStorage.setItem(MIGRATION_FLAG_KEY, 'true');
  } catch {
    // ignore
  }
};

/**
 * Migre les favoris depuis l'ancienne clé localStorage `desk_favorites`
 * vers le format partagé.
 */
export async function migrateFavorites() {
  try {
    const raw = localStorage.getItem(LEGACY_DESK_FAVORITES_KEY);
    if (!raw) return { migrated: 0 };

    const legacy = JSON.parse(raw);
    if (!Array.isArray(legacy)) return { migrated: 0 };

    let migrated = 0;
    for (const fav of legacy) {
      try {
        await favoriteService.add(fav);
        migrated++;
      } catch {
        // skip individual failures
      }
    }

    localStorage.removeItem(LEGACY_DESK_FAVORITES_KEY);
    return { migrated };
  } catch {
    return { migrated: 0 };
  }
}

/**
 * Migre les configurations de colonnes depuis l'ancien format localStorage
 * vers le nouveau format partagé.
 */
export async function migrateColumnConfigs() {
  try {
    const keys = listKeys(LEGACY_DESK_COLUMNS_PREFIX);
    let migrated = 0;

    for (const key of keys) {
      try {
        const module = key.replace(LEGACY_DESK_COLUMNS_PREFIX, '');
        const stored = readJSON(key, null);
        if (stored && typeof stored === 'object') {
          await columnConfigService.save(module, stored);
          removeKey(key);
          migrated++;
        }
      } catch {
        // skip individual failures
      }
    }

    return { migrated };
  } catch {
    return { migrated: 0 };
  }
}

/**
 * Migre les presets de filtres depuis l'ancien format localStorage
 * vers le nouveau format partagé.
 */
export async function migrateFilterPresets() {
  try {
    const keys = listKeys(LEGACY_DESK_FILTERS_PREFIX);
    let migrated = 0;

    for (const key of keys) {
      try {
        const module = key.replace(LEGACY_DESK_FILTERS_PREFIX, '');
        const stored = readJSON(key, null);
        if (stored && stored.presets && Array.isArray(stored.presets)) {
          for (const preset of stored.presets) {
            try {
              await filterPresetService.save(module, preset);
            } catch {
              // skip individual failures
            }
          }
          removeKey(key);
          migrated++;
        }
      } catch {
        // skip individual failures
      }
    }

    return { migrated };
  } catch {
    return { migrated: 0 };
  }
}

/**
 * Exécute toutes les migrations nécessaires.
 * À appeler une seule fois au premier démarrage après mise à jour.
 */
export async function runMigration() {
  if (isMigrationCompleted()) {
    return { skipped: true };
  }

  const results = {
    favorites: await migrateFavorites(),
    columns: await migrateColumnConfigs(),
    filters: await migrateFilterPresets(),
  };

  markMigrationCompleted();

  return {
    skipped: false,
    ...results,
  };
}

export default runMigration;
