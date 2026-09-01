// shared/storage/authStorage.js
// Stockage unifie de l'authentification pour web et desktop.

import { getString, setString, removeKey, readJSON, writeJSON } from './storageAdapter';
import { tokenStore } from './tokenStore';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';
const TENANT_KEY = 'tenant';
const SUBSCRIPTION_KEY = 'subscription';

const NEW = {
  access: 'erp.auth.access_token',
  refresh: 'erp.auth.refresh_token',
  user: 'erp.auth.user',
  tenant: 'erp.auth.tenant',
  subscription: 'erp.auth.subscription',
};

export const authStorage = {
  getAccessToken: () => getString(ACCESS_TOKEN_KEY),
  getRefreshToken: () => getString(REFRESH_TOKEN_KEY),
  getUser: () => readJSON(USER_KEY),
  getTenant: () => readJSON(TENANT_KEY),
  getSubscription: () => readJSON(SUBSCRIPTION_KEY),

  setAccessToken: (token) => {
    setString(ACCESS_TOKEN_KEY, token);
    setString(NEW.access, token);
  },
  setRefreshToken: (token) => {
    setString(REFRESH_TOKEN_KEY, token);
    setString(NEW.refresh, token);
  },
  setUser: (user) => {
    const v = JSON.stringify(user);
    writeJSON(USER_KEY, user);
    setString(NEW.user, v);
  },
  setTenant: (tenant) => {
    const v = JSON.stringify(tenant);
    writeJSON(TENANT_KEY, tenant);
    setString(NEW.tenant, v);
  },
  setSubscription: (sub) => {
    const v = sub ? JSON.stringify(sub) : null;
    writeJSON(SUBSCRIPTION_KEY, sub);
    if (v) {
      setString(NEW.subscription, v);
    } else {
      removeKey(NEW.subscription);
    }
  },

  remove: (key) => removeKey(key),

  clear: () => {
    tokenStore.clear();
  },
};

export const AUTH_KEYS = {
  ACCESS_TOKEN: ACCESS_TOKEN_KEY,
  REFRESH_TOKEN: REFRESH_TOKEN_KEY,
  USER: USER_KEY,
  TENANT: TENANT_KEY,
  SUBSCRIPTION: SUBSCRIPTION_KEY,
};
