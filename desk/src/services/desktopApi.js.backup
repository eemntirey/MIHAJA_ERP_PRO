// src/services/desktopApi.js

import api from './api';
import { buildKey, readJSON, writeJSON, removeKey } from '../utils/localStore';

export const notificationService = {
  getAll: () => api.get('/notifications'),
  markAsRead: (id) => api.post(`/notifications/${id}/read`),
  markAllAsRead: () => api.post('/notifications/read-all'),
  delete: (id) => api.delete(`/notifications/${id}`),
};

export const favoriteService = {
  getAll: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('desk_favorites') || '[]');
      return Promise.resolve({ data: Array.isArray(stored) ? stored : [] });
    } catch {
      return Promise.resolve({ data: [] });
    }
  },
  add: (item) => {
    try {
      const stored = JSON.parse(localStorage.getItem('desk_favorites') || '[]');
      const list = Array.isArray(stored) ? stored : [];
      const exists = list.some((f) => f.path === item.path);
      if (!exists) {
        list.push({ ...item, id: item.id || item.path });
        localStorage.setItem('desk_favorites', JSON.stringify(list));
      }
      return Promise.resolve({ data: list });
    } catch {
      return Promise.resolve({ data: [] });
    }
  },
  remove: (id) => {
    try {
      const stored = JSON.parse(localStorage.getItem('desk_favorites') || '[]');
      const list = Array.isArray(stored) ? stored.filter((f) => f.id !== id && f.path !== id) : [];
      localStorage.setItem('desk_favorites', JSON.stringify(list));
      return Promise.resolve({ data: list });
    } catch {
      return Promise.resolve({ data: [] });
    }
  },
};


const CONFIG_VERSION = 1;

const nowIso = () => new Date().toISOString();

const genId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const normalizeModule = (module) => String(module || 'default').trim().toLowerCase();

/**
 * Configuration des colonnes (largeurs + colonnes masquées) par module.
 * Tente d'abord le backend (`/desk/columns/:module`), puis replie sur localStorage.
 */
export const columnConfigService = {
  get: (module) => {
    const m = normalizeModule(module);
    return api.get(`/desk/columns/${m}`).catch(() => {
      const key = buildKey('columns', m);
      const stored = readJSON(key, null);
      const config = stored && typeof stored === 'object'
        ? { widths: stored.widths || {}, hidden: Array.isArray(stored.hidden) ? stored.hidden : [], sort: Array.isArray(stored.sort) ? stored.sort : [] }
        : { widths: {}, hidden: [], sort: [] };
      return Promise.resolve({ data: { module: m, config } });
    });
  },

  save: (module, config = {}) => {
    const m = normalizeModule(module);
    const payload = {
      version: CONFIG_VERSION,
      updatedAt: nowIso(),
      widths: config.widths && typeof config.widths === 'object' ? config.widths : {},
      hidden: Array.isArray(config.hidden) ? config.hidden : [],
      sort: Array.isArray(config.sort) ? config.sort : [],
    };
    return api.post(`/desk/columns/${m}`, payload).catch(() => {
      const key = buildKey('columns', m);
      writeJSON(key, payload);
      return Promise.resolve({ data: { module: m, config: payload, persisted: true } });
    });
  },

  reset: (module) => {
    const m = normalizeModule(module);
    return api.delete(`/desk/columns/${m}`).catch(() => {
      removeKey(buildKey('columns', m));
      return Promise.resolve({ data: { module: m, config: { widths: {}, hidden: [], sort: [] } } });
    });
  },
};

const readPresets = (module) => {
  const stored = readJSON(buildKey('filters', normalizeModule(module)), null);
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

const writePresets = (module, presets) => {
  const key = buildKey('filters', normalizeModule(module));
  return writeJSON(key, { version: CONFIG_VERSION, updatedAt: nowIso(), presets });
};

/**
 * Presets de filtres personnalisés par module (ventes, produits, stocks, ...).
 * Persistés en localStorage : aucun endpoint `/desk/filters` n'existe côté backend.
 * L'API reste promise-based afin de pouvoir basculer vers le backend sans toucher l'UI.
 */
export const filterPresetService = {
  getAll: (module) =>
    Promise.resolve({ data: { module: normalizeModule(module), presets: readPresets(module) } }),

  /**
   * Crée ou met à jour un preset (upsert par `id`, sinon par `name`).
   * @param {string} module
   * @param {{id?:string,name:string,filters:Array,isDefault?:boolean}} preset
   */
  save: (module, preset = {}) => {
    const name = String(preset.name || '').trim();
    if (!name) {
      return Promise.reject(new Error('Le nom du filtre est obligatoire'));
    }
    const presets = readPresets(module);
    const filters = Array.isArray(preset.filters) ? preset.filters : [];
    const existingIndex = presets.findIndex(
      (p) => (preset.id && p.id === preset.id) || p.name.toLowerCase() === name.toLowerCase()
    );

    let saved;
    if (existingIndex >= 0) {
      saved = { ...presets[existingIndex], name, filters, isDefault: !!preset.isDefault, updatedAt: nowIso() };
      presets[existingIndex] = saved;
    } else {
      saved = {
        id: preset.id || genId(),
        name,
        filters,
        isDefault: !!preset.isDefault,
        createdAt: nowIso(),
        updatedAt: nowIso(),
      };
      presets.push(saved);
    }

    if (saved.isDefault) {
      presets.forEach((p) => {
        if (p.id !== saved.id) p.isDefault = false;
      });
    }

    const persisted = writePresets(module, presets);
    return Promise.resolve({ data: { module: normalizeModule(module), preset: saved, presets, persisted } });
  },

  delete: (module, id) => {
    const presets = readPresets(module).filter((p) => p.id !== id);
    writePresets(module, presets);
    return Promise.resolve({ data: { module: normalizeModule(module), presets } });
  },

  setDefault: (module, id) => {
    const presets = readPresets(module).map((p) => ({ ...p, isDefault: p.id === id ? !p.isDefault : false }));
    writePresets(module, presets);
    return Promise.resolve({ data: { module: normalizeModule(module), presets } });
  },

  clear: (module) => {
    removeKey(buildKey('filters', normalizeModule(module)));
    return Promise.resolve({ data: { module: normalizeModule(module), presets: [] } });
  },
};
