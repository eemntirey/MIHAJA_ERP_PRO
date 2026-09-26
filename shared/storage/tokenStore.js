// shared/storage/tokenStore.js
// Point unique de vérité pour les jetons + données de session.
//
// A1 FIX : Sur web, les JWT sont dans des cookies HttpOnly (XSS-safe).
// getAccessToken/getRefreshToken retournent null sur web — le navigateur
// envoie les cookies automatiquement. Sur Electron (secureStore), les tokens
// restent gérés ici comme auparavant.
//
// Rétro-compatible : lit/écrit AUSSI les clés legacy ('access_token', 'user'...)
// afin de ne pas invalider les sessions existantes pendant la migration.

import { getString, setString, removeKey, readJSON, writeJSON } from './storageAdapter';

const NEW = {
  access: 'erp.auth.access_token',
  refresh: 'erp.auth.refresh_token',
  user: 'erp.auth.user',
  tenant: 'erp.auth.tenant',
  subscription: 'erp.auth.subscription',
};
const LEGACY = {
  access: 'access_token',
  refresh: 'refresh_token',
  user: 'user',
  tenant: 'tenant',
  subscription: 'subscription',
};

// Desktop : double session sécurisée. Les jetons centraux servent lorsque
// le serveur central est joignable ; les jetons locaux servent uniquement
// au backend SQLite embarqué en mode hors-ligne.
const DESKTOP = {
  centralAccess: 'erp.desk.central_access_token',
  centralRefresh: 'erp.desk.central_refresh_token',
  offlineAccess: 'erp.desk.offline_access_token',
  offlineRefresh: 'erp.desk.offline_refresh_token',
};

// Electron = secureStore disponible ; web = localStorage (tokens en cookies HttpOnly)
const isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);

export const tokenStore = {
  // A1 : web retourne null (les cookies HttpOnly gèrent les tokens)
  getAccessToken: () => isElectron ? (getString(NEW.access) || getString(LEGACY.access)) : null,
  getRefreshToken: () => isElectron ? (getString(NEW.refresh) || getString(LEGACY.refresh)) : null,

  getCentralAccessToken: () => isElectron ? getString(DESKTOP.centralAccess) : null,
  getCentralRefreshToken: () => isElectron ? getString(DESKTOP.centralRefresh) : null,
  getOfflineAccessToken: () => isElectron ? getString(DESKTOP.offlineAccess) : null,
  getOfflineRefreshToken: () => isElectron ? getString(DESKTOP.offlineRefresh) : null,

  setCentralTokens: ({ access_token, refresh_token }) => {
    if (!isElectron) return;
    if (access_token) setString(DESKTOP.centralAccess, access_token);
    if (refresh_token) setString(DESKTOP.centralRefresh, refresh_token);
  },

  setOfflineTokens: ({ access_token, refresh_token }) => {
    if (!isElectron) return;
    if (access_token) setString(DESKTOP.offlineAccess, access_token);
    if (refresh_token) setString(DESKTOP.offlineRefresh, refresh_token);
  },

  // A1 : web — no-op (les tokens sont en cookies, gérés par le backend)
  // Electron — stocke dans secureStore comme auparavant
  setTokens: ({ access_token, refresh_token }) => {
    if (!isElectron) return;
    if (access_token) {
      setString(NEW.access, access_token);
      setString(LEGACY.access, access_token);
    }
    if (refresh_token) {
      setString(NEW.refresh, refresh_token);
      setString(LEGACY.refresh, refresh_token);
    }
  },

  setSession: ({ access_token, refresh_token, user, tenant, subscription }) => {
    tokenStore.setTokens({ access_token, refresh_token });
    // User/tenant sont stockés en localStorage sur web (pas sensible, pas de secret)
    if (user) {
      const u = JSON.stringify(user);
      setString(NEW.user, u);
      setString(LEGACY.user, u);
    }
    if (tenant) {
      const t = JSON.stringify(tenant);
      setString(NEW.tenant, t);
      setString(LEGACY.tenant, t);
    }
    if (subscription !== undefined) {
      if (subscription) {
        setString(NEW.subscription, JSON.stringify(subscription));
        setString(LEGACY.subscription, JSON.stringify(subscription));
      } else {
        removeKey(NEW.subscription);
        removeKey(LEGACY.subscription);
      }
    }
  },

  getUser: () => readJSON(NEW.user) || readJSON(LEGACY.user),
  getTenant: () => readJSON(NEW.tenant) || readJSON(LEGACY.tenant),
  getSubscription: () => readJSON(NEW.subscription) || readJSON(LEGACY.subscription),

  setSubscription: (sub) => {
    const v = sub ? JSON.stringify(sub) : null;
    if (v) {
      setString(NEW.subscription, v);
      setString(LEGACY.subscription, v);
    } else {
      removeKey(NEW.subscription);
      removeKey(LEGACY.subscription);
    }
  },

  clear: () => {
    Object.values(NEW).forEach(removeKey);
    Object.values(LEGACY).forEach(removeKey);
    Object.values(DESKTOP).forEach(removeKey);
  },
};

export default tokenStore;
