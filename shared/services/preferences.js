// shared/services/preferences.js
// ============================================================================
// Services de préférences partagés (web + desktop) remplaçant
// desk/src/services/desktopApi.js. Stratégie "backend-first" avec cache local
// et file de synchronisation hors-ligne (syncEngine). Garantit la cohérence
// favoris / colonnes / filtres / notifications entre web et desktop.
//
// Réexporte les mêmes noms que l'ancien desktopApi :
//   notificationService, favoriteService, columnConfigService, filterPresetService
// ============================================================================

import api from './apiClient';
import { favoriteApi, filterApi, columnApi, syncApi } from './syncApi';
import * as sync from '../utils/syncEngine';
import { readJSON, writeJSON, buildKey, getString } from '../storage/storageAdapter';

const CONFIG_VERSION = 1;
const nowIso = () => new Date().toISOString();
const genId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const normalizeModule = (m) => String(m || 'default').trim().toLowerCase();

// Cache local (scoped user+tenant)
const cacheKey = (area, name) => buildKey(area, name);
const readCache = (area, name) => readJSON(cacheKey(area, name), null);

/**
 * Applique une mutation optimiste (cache local) puis l'envoie au backend.
 * En cas d'échec réseau, l'opération est enqueueée et rejouée par flush().
 */
const applyWithSync = async (localMutator, buildMutation, networkCall) => {
  const result = localMutator(); // mise à jour synchrone du cache local
  try {
    await networkCall();
  } catch (err) {
    // Hors-ligne ou erreur : on planifie le rejeu.
    sync.enqueue(buildMutation());
  }
  return result;
};

// ============================================================================
// NOTIFICATIONS (reste majoritairement locale sur desktop, pont vers backend)
// ============================================================================
const NOTIF_STORAGE_KEY = buildKey('notifications', 'list', false);
const DEFAULT_NOTIFICATIONS = [
  { id: 1, title: 'Nouvelle commande', message: 'Commande #1042 reçue', time: "il y a 2 min", read: false },
  { id: 2, title: 'Stock critique', message: 'Produit XYZ sous le seuil', time: "il y a 15 min", read: false },
  { id: 3, title: 'Paiement reçu', message: 'Facture #89 payée', time: "il y a 1 h", read: true },
];

const readLocalNotifications = () => {
  const stored = readJSON(NOTIF_STORAGE_KEY, null);
  return Array.isArray(stored) ? stored : [...DEFAULT_NOTIFICATIONS];
};
const writeLocalNotifications = (list) => writeJSON(NOTIF_STORAGE_KEY, list);

export const notificationService = {
  readAll: () => readLocalNotifications(),
  getAll: () => Promise.resolve({ data: readLocalNotifications() }),
  add: (item) => {
    const list = readLocalNotifications();
    const id = item.id || genId();
    if (!list.some((n) => n.id === id)) {
      list.unshift({ id, title: item.title || 'Notification', message: item.message || '', time: item.time || '', read: !!item.read });
      writeLocalNotifications(list);
    }
    return Promise.resolve({ data: list });
  },
  markAsRead: (id) => {
    const list = readLocalNotifications().map((n) => (n.id === id ? { ...n, read: true } : n));
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },
  markAllAsRead: () => {
    const list = readLocalNotifications().map((n) => ({ ...n, read: true }));
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },
  delete: (id) => {
    const list = readLocalNotifications().filter((n) => n.id !== id);
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },
  triggerNative: (title, body) =>
    typeof window !== 'undefined' && window.electron?.notify
      ? Promise.resolve(window.electron.notify(title, body))
      : Promise.resolve(true),
  setBadge: (count) =>
    typeof window !== 'undefined' && window.electron?.setBadge
      ? Promise.resolve(window.electron.setBadge(count))
      : Promise.resolve(true),
  clear: () => {
    writeLocalNotifications([]);
    return Promise.resolve({ data: [] });
  },
  save: (list) => {
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },
};

// ============================================================================
// FAVORIS (backend-first, cache local, queue hors-ligne)
// ============================================================================
const readLocalFavorites = () => {
  // Migration : ancienne clé non-scoped `desk_favorites`.
  const legacy = (() => {
    try {
      const raw = getString('desk_favorites');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();
  const cached = readCache('favorites', 'list');
  if (Array.isArray(cached)) return cached;
  if (Array.isArray(legacy)) return legacy;
  return [];
};

export const favoriteService = {
  getAll: async () => {
    try {
      const { data } = await favoriteApi.getAll();
      const remote = Array.isArray(data?.favorites) ? data.favorites : [];
      const merged = sync.mergeCollections(readLocalFavorites(), remote, (f) => f.path || f.id).merged;
      writeJSON(cacheKey('favorites', 'list'), merged);
      return { data: merged };
    } catch {
      return { data: readLocalFavorites() };
    }
  },
  add: (item) =>
    applyWithSync(
      () => {
        const list = readLocalFavorites();
        const fav = { ...item, id: item.id || item.path, path: item.path, updatedAt: nowIso() };
        const exists = list.some((f) => (f.path || f.id) === (fav.path || fav.id));
        const next = exists ? list.map((f) => ((f.path || f.id) === (fav.path || fav.id) ? fav : f)) : [...list, fav];
        writeJSON(cacheKey('favorites', 'list'), next);
        return { data: next };
      },
      () => ({ entity: 'favorite', op: 'upsert', payload: item }),
      () => favoriteApi.upsert(item)
    ),
  remove: (id) =>
    applyWithSync(
      () => {
        const next = readLocalFavorites().filter((f) => f.id !== id && f.path !== id);
        writeJSON(cacheKey('favorites', 'list'), next);
        return { data: next };
      },
      () => ({ entity: 'favorite', op: 'delete', payload: { key: id } }),
      () => favoriteApi.remove(id)
    ),
};

// ============================================================================
// CONFIGURATION DES COLONNES (backend-first)
// ============================================================================
export const columnConfigService = {
  get: async (module) => {
    const m = normalizeModule(module);
    try {
      const { data } = await columnApi.get(m);
      const cfg = data?.config || data;
      writeJSON(cacheKey('columns', m), cfg);
      return { data: { module: m, config: cfg } };
    } catch {
      const stored = readCache('columns', m) || { widths: {}, hidden: [], sort: [] };
      return { data: { module: m, config: stored } };
    }
  },
  save: async (module, config = {}) => {
    const m = normalizeModule(module);
    const payload = {
      version: CONFIG_VERSION,
      updatedAt: nowIso(),
      widths: config.widths && typeof config.widths === 'object' ? config.widths : {},
      hidden: Array.isArray(config.hidden) ? config.hidden : [],
      sort: Array.isArray(config.sort) ? config.sort : [],
    };
    writeJSON(cacheKey('columns', m), payload);
    try {
      await columnApi.save(m, payload);
      return { data: { module: m, config: payload, persisted: true } };
    } catch {
      sync.enqueue({ entity: 'column', op: 'upsert', payload: { module: m, config: payload } });
      return { data: { module: m, config: payload, persisted: false } };
    }
  },
  reset: async (module) => {
    const m = normalizeModule(module);
    const empty = { widths: {}, hidden: [], sort: [] };
    writeJSON(cacheKey('columns', m), empty);
    try {
      await columnApi.reset(m);
    } catch {
      sync.enqueue({ entity: 'column', op: 'delete', payload: { module: m } });
    }
    return { data: { module: m, config: empty } };
  },
};

// ============================================================================
// PRESETS DE FILTRES (backend-first désormais)
// ============================================================================
const readPresets = (module) => {
  const stored = readCache('filters', normalizeModule(module));
  const list = Array.isArray(stored) ? stored : stored?.presets;
  if (!Array.isArray(list)) return [];
  return list
    .filter((p) => p && typeof p === 'object')
    .map((p) => ({
      id: p.id || genId(),
      name: String(p.name || 'Sans nom'),
      filters: Array.isArray(p.filters) ? p.filters : [],
      isDefault: !!p.isDefault,
      createdAt: p.createdAt || nowIso(),
      updatedAt: p.updatedAt || p.createdAt || nowIso(),
    }));
};
const writePresets = (module, presets) =>
  writeJSON(cacheKey('filters', normalizeModule(module)), presets);

export const filterPresetService = {
  getAll: async (module) => {
    const m = normalizeModule(module);
    try {
      const { data } = await filterApi.getAll(m);
      const remote = Array.isArray(data?.presets) ? data.presets : [];
      const merged = sync.mergeCollections(readPresets(m), remote, (p) => p.id).merged;
      writePresets(m, merged);
      return { data: { module: m, presets: merged } };
    } catch {
      return { data: { module: m, presets: readPresets(m) } };
    }
  },
  save: async (module, preset = {}) => {
    const m = normalizeModule(module);
    const name = String(preset.name || '').trim();
    if (!name) return Promise.reject(new Error('Le nom du filtre est obligatoire'));
    const presets = readPresets(m);
    const saved = { ...preset, id: preset.id || genId(), name, updatedAt: nowIso(), createdAt: preset.createdAt || nowIso() };
    const idx = presets.findIndex((p) => (saved.id && p.id === saved.id) || p.name.toLowerCase() === name.toLowerCase());
    if (idx >= 0) presets[idx] = { ...presets[idx], ...saved };
    else presets.push(saved);
    if (saved.isDefault) presets.forEach((p) => { if (p.id !== saved.id) p.isDefault = false; });
    writePresets(m, presets);
    try {
      await filterApi.upsert(m, saved);
    } catch {
      sync.enqueue({ entity: 'filter', op: 'upsert', payload: { module: m, preset: saved } });
    }
    return { data: { module: m, preset: saved, presets } };
  },
  delete: async (module, id) => {
    const m = normalizeModule(module);
    const presets = readPresets(m).filter((p) => p.id !== id);
    writePresets(m, presets);
    try {
      await filterApi.remove(m, id);
    } catch {
      sync.enqueue({ entity: 'filter', op: 'delete', payload: { module: m, id } });
    }
    return { data: { module: m, presets } };
  },
  setDefault: async (module, id) => {
    const m = normalizeModule(module);
    const presets = readPresets(m).map((p) => ({ ...p, isDefault: p.id === id ? !p.isDefault : false }));
    writePresets(m, presets);
    const def = presets.find((p) => p.id === id);
    if (def) {
      try { await filterApi.upsert(m, def); } catch { /* queue */ }
    }
    return { data: { module: m, presets } };
  },
  clear: (module) => {
    const m = normalizeModule(module);
    writePresets(m, []);
    return Promise.resolve({ data: { module: m, presets: [] } });
  },
};

// ============================================================================
// HYDRATATION + REJEU (à appeler au démarrage de l'app, une fois authentifié)
// ============================================================================
export const hydrateAndSync = async () => {
  // 1) Rejeu de la file hors-ligne (mutations en attente).
  await sync.flush(async (entry) => {
    switch (entry.entity) {
      case 'favorite':
        return entry.op === 'delete'
          ? favoriteApi.remove(entry.payload.key)
          : favoriteApi.upsert(entry.payload);
      case 'column':
        return entry.op === 'delete'
          ? columnApi.reset(entry.payload.module)
          : columnApi.save(entry.payload.module, entry.payload.config);
      case 'filter':
        return entry.op === 'delete'
          ? filterApi.remove(entry.payload.module, entry.payload.id)
          : filterApi.upsert(entry.payload.module, entry.payload.preset);
      default:
        throw new Error(`Entité inconnue: ${entry.entity}`);
    }
  });

  // 2) Pull incrémental pour récupérer les modifs faites sur l'autre client.
  try {
    const { data } = await syncApi.pull(readJSON(cacheKey('sync', 'revision'), 0) || 0);
    const rev = data?.revision ?? 0;
    if (Array.isArray(data?.favorites)) {
      writeJSON(cacheKey('favorites', 'list'), sync.mergeCollections(readLocalFavorites(), data.favorites, (f) => f.path || f.id).merged);
    }
    if (Array.isArray(data?.filters)) {
      data.filters.forEach(({ module, presets }) => {
        writeJSON(cacheKey('filters', module), sync.mergeCollections(readPresets(module), presets, (p) => p.id).merged);
      });
    }
    if (Array.isArray(data?.columns)) {
      data.columns.forEach(({ module, config }) => writeJSON(cacheKey('columns', module), config));
    }
    writeJSON(cacheKey('sync', 'revision'), rev);
  } catch {
    /* hors-ligne : on garde le cache local + la file */
  }
};

export default {
  notificationService,
  favoriteService,
  columnConfigService,
  filterPresetService,
  hydrateAndSync,
};
