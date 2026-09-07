// shared/storage/storageAdapter.js
// Couche de stockage plateforme-agnostique.
// - Web : localStorage (synchrone, compatible mobile/tiers).
// - Desktop (Electron) : window.electron.secureStore (synchronisé via safeStorage + fs
//   dans le preload) -> chiffré au repos, et synchronise les deux clients via le backend.
// Le reste du code (Auth, syncEngine, preferences) ne dépend QUE de cette interface.

const DEFAULT_NAMESPACE = 'erp.desk';

const memoryFallback = new Map();

const hasWindowStorage = () => {
  try {
    return typeof window !== 'undefined' && !!window.localStorage;
  } catch {
    return false;
  }
};

// Le desktop expose un store sécurisé synchrone (voir electron/preload.js).
const secureStore = () => {
  if (typeof window !== 'undefined' && window.electron && window.electron.secureStore) {
    return window.electron.secureStore;
  }
  return null;
};

export const getScopeId = () => {
  if (!hasWindowStorage()) return 'anon';
  try {
    const rawUser = window.localStorage.getItem('user');
    const rawTenant = window.localStorage.getItem('tenant');
    const user = rawUser ? JSON.parse(rawUser) : null;
    const tenant = rawTenant ? JSON.parse(rawTenant) : null;
    const userId = user?.id ?? user?.email ?? 'anon';
    const tenantId = tenant?.id ?? tenant?.slug ?? 'default';
    return `${tenantId}:${userId}`;
  } catch {
    return 'anon';
  }
};

// Construit une clé scoped (utilisateur + tenant) pour éviter le mélange de comptes.
export const buildKey = (area, name, scoped = true) =>
  scoped
    ? `${DEFAULT_NAMESPACE}.${area}.${getScopeId()}.${name}`
    : `${DEFAULT_NAMESPACE}.${area}.${name}`;

export const getString = (key) => {
  const secure = secureStore();
  if (secure) {
    const v = secure.get(key);
    return v === undefined || v === null ? null : v;
  }
  if (hasWindowStorage()) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  return memoryFallback.has(key) ? memoryFallback.get(key) : null;
};

export const setString = (key, value) => {
  const secure = secureStore();
  if (secure) {
    secure.set(key, value);
    return;
  }
  if (hasWindowStorage()) {
    try {
      window.localStorage.setItem(key, value);
      return;
    } catch {
      /* quota / indisponible -> mémoire */
    }
  }
  memoryFallback.set(key, value);
};

export const removeKey = (key) => {
  const secure = secureStore();
  if (secure) {
    secure.remove(key);
    return;
  }
  memoryFallback.delete(key);
  if (hasWindowStorage()) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  }
};

export const readJSON = (key, fallback = null) => {
  const raw = getString(key);
  if (raw === null || raw === undefined) return fallback;
  try {
    const parsed = JSON.parse(raw);
    return parsed === null || parsed === undefined ? fallback : parsed;
  } catch {
    removeKey(key);
    return fallback;
  }
};

export const writeJSON = (key, value) => {
  try {
    setString(key, JSON.stringify(value));
  } catch {
    memoryFallback.set(key, value);
  }
};

// Notifications de changement (pour hydratation croisée entre onglets du navigateur web).
export const subscribe = (key, callback) => {
  if (typeof window === 'undefined' || !window.addEventListener) return () => {};
  const handler = (e) => {
    if (e.key === key) callback(e.newValue);
  };
  window.addEventListener('storage', handler);
  return () => window.removeEventListener('storage', handler);
};

export const listKeys = (prefix) => {
  const found = new Set();
  memoryFallback.forEach((_v, k) => {
    if (k.startsWith(prefix)) found.add(k);
  });
  if (hasWindowStorage()) {
    try {
      for (let i = 0; i < window.localStorage.length; i += 1) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith(prefix)) found.add(k);
      }
    } catch {
      /* ignore */
    }
  }
  return Array.from(found);
};

export const STORE_NAMESPACE = DEFAULT_NAMESPACE;
