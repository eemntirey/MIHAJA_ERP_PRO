// src/storage/session.js
// Stockage de session mobile :
// - jetons (access/refresh) → expo-secure-store (stockage chiffré natif)
//   et fallback window.localStorage sur le web (Expo web, port 8081) :
//   expo-secure-store n'a aucune implémentation web (ExpoSecureStore.web.js
//   est vide) → sans fallback, les jetons étaient perdus et toute requête
//   authentifiée finissait en 401.
// - données non sensibles (user, tenant) → AsyncStorage (JSON)
// Équivalent mobile de shared/storage/tokenStore.js (web/desktop).

import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  access: 'erp.auth.access_token',
  refresh: 'erp.auth.refresh_token',
  deviceId: 'erp.auth.device_id',
  user: 'erp.auth.user',
  tenant: 'erp.auth.tenant',
};

// Sur le web, on utilise localStorage (le module natif est absent).
const HAS_WEB_STORAGE =
  Platform.OS === 'web' && typeof window !== 'undefined' && !!window.localStorage;

const readJSON = async (key) => {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const writeJSON = async (key, value) => {
  try {
    if (value == null) {
      await AsyncStorage.removeItem(key);
    } else {
      await AsyncStorage.setItem(key, JSON.stringify(value));
    }
  } catch {
    // stockage indisponible : on ignore silencieusement
  }
};

// Helpers de stockage chiffré (natifs) avec repli localStorage sur le web.
const readSecure = (key) => {
  if (HAS_WEB_STORAGE) {
    try {
      return Promise.resolve(window.localStorage.getItem(key));
    } catch {
      return Promise.resolve(null);
    }
  }
  return SecureStore.getItemAsync(key).catch(() => null);
};

const writeSecure = (key, value) => {
  if (HAS_WEB_STORAGE) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // stockage indisponible : on ignore silencieusement
    }
    return Promise.resolve();
  }
  return SecureStore.setItemAsync(key, value).catch(() => {});
};

const deleteSecure = (key) => {
  if (HAS_WEB_STORAGE) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      // stockage indisponible : on ignore silencieusement
    }
    return Promise.resolve();
  }
  return SecureStore.deleteItemAsync(key).catch(() => {});
};

export const session = {
  // ---- Jetons (chiffrés en natif, localStorage sur le web) ----
  getAccessToken: () => readSecure(KEYS.access),
  setAccessToken: (token) => {
    if (!token) return deleteSecure(KEYS.access);
    return writeSecure(KEYS.access, token);
  },
  getRefreshToken: () => readSecure(KEYS.refresh),
  setRefreshToken: (token) => {
    if (!token) return deleteSecure(KEYS.refresh);
    return writeSecure(KEYS.refresh, token);
  },
  setTokens: async ({ access_token, refresh_token }) => {
    await session.setAccessToken(access_token);
    await session.setRefreshToken(refresh_token);
  },

  // ---- Données de session (JSON) ----
  getUser: () => readJSON(KEYS.user),
  setUser: (user) => writeJSON(KEYS.user, user),
  getTenant: () => readJSON(KEYS.tenant),
  setTenant: (tenant) => writeJSON(KEYS.tenant, tenant),

  // ---- Purge complète ----
  clear: async () => {
    await Promise.all([
      deleteSecure(KEYS.access),
      deleteSecure(KEYS.refresh),
      AsyncStorage.multiRemove([KEYS.user, KEYS.tenant]).catch(() => {}),
    ]);
  },

  // ---- Identifiant d'appareil (traçabilité / audit backend) ----
  getDeviceId: async () => {
    let id = await readSecure(KEYS.deviceId);
    if (!id) {
      id = `mob-${Math.random().toString(36).slice(2, 12)}-${Date.now().toString(36)}`;
      await writeSecure(KEYS.deviceId, id);
    }
    return id;
  },
};

export default session;
