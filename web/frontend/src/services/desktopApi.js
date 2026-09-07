// src/services/desktopApi.js
// API desktop avec synchronisation hors-ligne vers le backend partagé.

import api from '@shared/services/api';
import { buildKey, readJSON, writeJSON, removeKey } from '../utils/localStore';
import { syncEngine } from '@shared/utils/syncEngine';

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

const writeLocalNotifications = (list) => {
  writeJSON(NOTIF_STORAGE_KEY, list);
};

const genId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const nowIso = () => new Date().toISOString();

const normalizeModule = (module) => String(module || 'default').trim().toLowerCase();

const enqueueMutation = (entity, op, payload) => {
  const entry = {
    entity,
    op,
    payload,
    createdAt: nowIso(),
  };
  syncEngine.enqueue(entry);
};

export const notificationService = {
  readAll: () => readLocalNotifications(),

  getAll: () => Promise.resolve({ data: readLocalNotifications() }),

  add: (item) => {
    const list = readLocalNotifications();
    const id = item.id || genId();
    const exists = list.some((n) => n.id === id);
    if (!exists) {
      const formatted = {
        id,
        title: item.title || 'Notification',
        message: item.message || '',
        time: item.time || '',
        read: !!item.read,
      };
      list.unshift(formatted);
      writeLocalNotifications(list);
    }
    return Promise.resolve({ data: list });
  },

  markAsRead: (id) => {
    let list = readLocalNotifications();
    list = list.map((n) => (n.id === id ? { ...n, read: true } : n));
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },

  markAllAsRead: () => {
    let list = readLocalNotifications();
    list = list.map((n) => ({ ...n, read: true }));
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },

  delete: (id) => {
    let list = readLocalNotifications();
    list = list.filter((n) => n.id !== id);
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },

  triggerNative: (title, body) => {
    if (typeof window !== 'undefined' && window.electron?.notify) {
      return Promise.resolve(window.electron.notify(title, body));
    }
    return Promise.resolve(true);
  },

  setBadge: (count) => {
    if (typeof window !== 'undefined' && window.electron?.setBadge) {
      return Promise.resolve(window.electron.setBadge(count));
    }
    return Promise.resolve(true);
  },

  clear: () => {
    writeLocalNotifications([]);
    return Promise.resolve({ data: [] });
  },

  save: (list) => {
    writeLocalNotifications(list);
    return Promise.resolve({ data: list });
  },
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
      enqueueMutation('favorite', 'upsert', item);
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
      enqueueMutation('favorite', 'delete', { key: id });
      return Promise.resolve({ data: list });
    } catch {
      return Promise.resolve({ data: [] });
    }
  },
};

const CONFIG_VERSION = 1;

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
      enqueueMutation('column', 'upsert', { module: m, config: payload });
      return Promise.resolve({ data: { module: m, config: payload, persisted: true } });
    });
  },

  reset: (module) => {
    const m = normalizeModule(module);
    return api.delete(`/desk/columns/${m}`).catch(() => {
      removeKey(buildKey('columns', m));
      enqueueMutation('column', 'delete', { module: m });
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

export const filterPresetService = {
  getAll: (module) =>
    Promise.resolve({ data: { module: normalizeModule(module), presets: readPresets(module) } }),

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
    enqueueMutation('filter', 'upsert', { module: normalizeModule(module), preset: saved });
    return Promise.resolve({ data: { module: normalizeModule(module), preset: saved, presets, persisted } });
  },

  delete: (module, id) => {
    const presets = readPresets(module).filter((p) => p.id !== id);
    writePresets(module, presets);
    enqueueMutation('filter', 'delete', { module: normalizeModule(module), id });
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

export const syncService = {
  flushQueue: async () => {
    return syncEngine.flush(async (entry) => {
      await api.post('/desk/sync/mutations', {
        mutations: [{
          entity: entry.entity,
          op: entry.op,
          payload: entry.payload,
        }],
      });
    });
  },

  getQueue: () => syncEngine.getQueue(),

  clearQueue: () => syncEngine.clear(),

  isOnline: () => syncEngine.isOnline(),

  getLastSyncedAt: () => syncEngine.getLastSyncedAt(),

  hydrate: async () => {
    return syncEngine.hydrate(async (entry) => {
      await api.post('/desk/sync/mutations', {
        mutations: [{
          entity: entry.entity,
          op: entry.op,
          payload: entry.payload,
        }],
      });
    });
  },
};
