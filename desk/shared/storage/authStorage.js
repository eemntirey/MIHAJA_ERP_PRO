// shared/storage/authStorage.js
// Stockage unifie de l'authentification pour web et desktop.

import { getString, setString, removeKey, readJSON, writeJSON } from './storageAdapter';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';
const TENANT_KEY = 'tenant';
const SUBSCRIPTION_KEY = 'subscription';

export const authStorage = {
  getAccessToken: () => getString(ACCESS_TOKEN_KEY),
  getRefreshToken: () => getString(REFRESH_TOKEN_KEY),
  getUser: () => readJSON(USER_KEY),
  getTenant: () => readJSON(TENANT_KEY),
  getSubscription: () => readJSON(SUBSCRIPTION_KEY),

  setAccessToken: (token) => setString(ACCESS_TOKEN_KEY, token),
  setRefreshToken: (token) => setString(REFRESH_TOKEN_KEY, token),
  setUser: (user) => writeJSON(USER_KEY, user),
  setTenant: (tenant) => writeJSON(TENANT_KEY, tenant),
  setSubscription: (sub) => writeJSON(SUBSCRIPTION_KEY, sub),

  remove: (key) => removeKey(key),

  clear: () => {
    removeKey(ACCESS_TOKEN_KEY);
    removeKey(REFRESH_TOKEN_KEY);
    removeKey(USER_KEY);
    removeKey(TENANT_KEY);
    removeKey(SUBSCRIPTION_KEY);
  },
};

export const AUTH_KEYS = {
  ACCESS_TOKEN: ACCESS_TOKEN_KEY,
  REFRESH_TOKEN: REFRESH_TOKEN_KEY,
  USER: USER_KEY,
  TENANT: TENANT_KEY,
  SUBSCRIPTION: SUBSCRIPTION_KEY,
};
