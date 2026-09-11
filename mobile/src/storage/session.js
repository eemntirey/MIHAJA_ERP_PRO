// src/storage/session.js
// Stockage de session mobile :
// - jetons (access/refresh) → expo-secure-store (stockage chiffré natif)
// - données non sensibles (user, tenant) → AsyncStorage (JSON)
// Équivalent mobile de shared/storage/tokenStore.js (web/desktop).

import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  access: 'erp.auth.access_token',
  refresh: 'erp.auth.refresh_token',
  deviceId: 'erp.auth.device_id',
  user: 'erp.auth.user',
  tenant: 'erp.auth.tenant',
};

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

const deleteSecure = (key) => SecureStore.deleteItemAsync(key).catch(() => {});

export const session = {
  // ---- Jetons (chiffrés) ----
  getAccessToken: () => SecureStore.getItemAsync(KEYS.access).catch(() => null),
  setAccessToken: (token) => {
    if (!token) return deleteSecure(KEYS.access);
    return SecureStore.setItemAsync(KEYS.access, token).catch(() => {});
  },
  getRefreshToken: () => SecureStore.getItemAsync(KEYS.refresh).catch(() => null),
  setRefreshToken: (token) => {
    if (!token) return deleteSecure(KEYS.refresh);
    return SecureStore.setItemAsync(KEYS.refresh, token).catch(() => {});
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
    let id = await SecureStore.getItemAsync(KEYS.deviceId).catch(() => null);
    if (!id) {
      id = `mob-${Math.random().toString(36).slice(2, 12)}-${Date.now().toString(36)}`;
      await SecureStore.setItemAsync(KEYS.deviceId, id).catch(() => {});
    }
    return id;
  },
};

export default session;
