// shared/storage/authStorage.js
// Stockage unifié de l'authentification pour web et desktop.

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';
const TENANT_KEY = 'tenant';
const SUBSCRIPTION_KEY = 'subscription';

const safeGet = (key) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = (key, value) => {
  try {
    localStorage.setItem(key, value);
  } catch {
    // quota dépassé ou stockage indisponible
  }
};

const safeRemove = (key) => {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
};

export const authStorage = {
  getAccessToken: () => safeGet(ACCESS_TOKEN_KEY),
  getRefreshToken: () => safeGet(REFRESH_TOKEN_KEY),
  getUser: () => {
    const raw = safeGet(USER_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  getTenant: () => {
    const raw = safeGet(TENANT_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  getSubscription: () => {
    const raw = safeGet(SUBSCRIPTION_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setAccessToken: (token) => safeSet(ACCESS_TOKEN_KEY, token),
  setRefreshToken: (token) => safeSet(REFRESH_TOKEN_KEY, token),
  setUser: (user) => safeSet(USER_KEY, JSON.stringify(user)),
  setTenant: (tenant) => safeSet(TENANT_KEY, JSON.stringify(tenant)),
  setSubscription: (sub) => safeSet(SUBSCRIPTION_KEY, JSON.stringify(sub)),

  remove: (key) => safeRemove(key),

  clear: () => {
    safeRemove(ACCESS_TOKEN_KEY);
    safeRemove(REFRESH_TOKEN_KEY);
    safeRemove(USER_KEY);
    safeRemove(TENANT_KEY);
    safeRemove(SUBSCRIPTION_KEY);
  },
};

export const AUTH_KEYS = {
  ACCESS_TOKEN: ACCESS_TOKEN_KEY,
  REFRESH_TOKEN: REFRESH_TOKEN_KEY,
  USER: USER_KEY,
  TENANT: TENANT_KEY,
  SUBSCRIPTION: SUBSCRIPTION_KEY,
};
