// scripts/migrate_localStorage_sync.js
// Migration des données localStorage existantes vers la nouvelle architecture.
// À exécuter une seule fois lors du déploiement de la version synchronisée.

const MIGRATION_VERSION_KEY = 'erp.migration.version';
const CURRENT_VERSION = 1;

const legacyKeys = [
  'desk_favorites',
  'erp.desk.columns.',
  'erp.desk.filters.',
];

export const runMigration = () => {
  if (typeof window === 'undefined') return;

  const storedVersion = localStorage.getItem(MIGRATION_VERSION_KEY);
  if (storedVersion && Number(storedVersion) >= CURRENT_VERSION) {
    return;
  }

  console.log('[Migration] Début de la migration localStorage...');

  const migratedFavorites = [];

  legacyKeys.forEach((prefix) => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(prefix)) {
        try {
          const value = JSON.parse(localStorage.getItem(key));
          if (prefix === 'desk_favorites') {
            migratedFavorites.push(...(Array.isArray(value) ? value : []));
          }
          localStorage.removeItem(key);
        } catch {
          // ignore corrupted data
        }
      }
    }
  });

  if (migratedFavorites.length > 0) {
    const seen = new Set();
    const unique = migratedFavorites.filter((f) => {
      const id = f.id || f.path;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });

    localStorage.setItem('desk_favorites', JSON.stringify(unique));
    console.log(`[Migration] ${unique.length} favoris migrés.`);
  }

  localStorage.setItem(MIGRATION_VERSION_KEY, String(CURRENT_VERSION));
  console.log('[Migration] Terminée.');
};

export default runMigration;
