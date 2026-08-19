// src/utils/localStore.js
// Accès localStorage tolérant aux pannes (mode privé, quota dépassé, Electron sandbox).
// Toutes les préférences Desktop (colonnes, filtres, brouillons) passent par ce module.

const NAMESPACE = 'erp.desk';

const memoryFallback = new Map();

const hasStorage = () => {
  try {
    return typeof window !== 'undefined' && !!window.localStorage;
  } catch {
    return false;
  }
};

/**
 * Identifiant de scope (utilisateur + tenant) pour éviter que deux comptes
 * partagent les mêmes préférences sur un même poste.
 */
export const getScopeId = () => {
  if (!hasStorage()) return 'anon';
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

/**
 * Construit une clé de stockage complète.
 * @param {string} area  ex: 'columns' | 'filters' | 'draft'
 * @param {string} name  ex: 'produits'
 * @param {boolean} [scoped=true] inclure le scope utilisateur/tenant
 */
export const buildKey = (area, name, scoped = true) =>
  scoped ? `${NAMESPACE}.${area}.${getScopeId()}.${name}` : `${NAMESPACE}.${area}.${name}`;

export const readJSON = (key, fallback = null) => {
  if (!hasStorage()) {
    return memoryFallback.has(key) ? memoryFallback.get(key) : fallback;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null || raw === undefined) return fallback;
    const parsed = JSON.parse(raw);
    return parsed === null || parsed === undefined ? fallback : parsed;
  } catch {
    // Valeur corrompue : on la purge pour ne pas boucler sur l'erreur.
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
    return fallback;
  }
};

export const writeJSON = (key, value) => {
  if (!hasStorage()) {
    memoryFallback.set(key, value);
    return true;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    // Quota dépassé ou stockage indisponible : on garde la valeur en mémoire.
    memoryFallback.set(key, value);
    return false;
  }
};

export const removeKey = (key) => {
  memoryFallback.delete(key);
  if (!hasStorage()) return true;
  try {
    window.localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
};

/** Liste les clés du namespace commençant par un préfixe donné. */
export const listKeys = (prefix) => {
  const found = new Set();
  memoryFallback.forEach((_value, key) => {
    if (key.startsWith(prefix)) found.add(key);
  });
  if (hasStorage()) {
    try {
      for (let i = 0; i < window.localStorage.length; i += 1) {
        const key = window.localStorage.key(i);
        if (key && key.startsWith(prefix)) found.add(key);
      }
    } catch {
      /* ignore */
    }
  }
  return Array.from(found);
};

export const STORE_NAMESPACE = NAMESPACE;
