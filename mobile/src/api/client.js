// mobile/src/api/client.js
// Client API central — axios + token persisté via expo-secure-store.

import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL as ENV_API_BASE_URL } from '../config/env';

// En émulateur Android, 10.0.2.2 pointe vers le localhost de la machine hôte.
// L'URL effective vient de EXPO_PUBLIC_API_URL (mobile/.env) via config/env.js :
// en test externe, elle pointe vers le tunnel HTTPS unique
// https://bj470sl0-3000.inc1.devtunnels.ms/api/v1
export const API_BASE_URL = ENV_API_BASE_URL;

export const TOKEN_KEY = 'erp_mobile_token';
export const USER_KEY = 'erp_mobile_user';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// Injecte le token sur chaque requête.
api.interceptors.request.use(async (config) => {
  try {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // token indisponible : requête anonyme
  }
  return config;
});

// Handlers de token utilisés par l'AuthContext.
export const TokenStorage = {
  async getToken() {
    try {
      return await SecureStore.getItemAsync(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  async setToken(token) {
    try {
      await SecureStore.setItemAsync(TOKEN_KEY, token);
    } catch {
      // stockage indisponible
    }
  },
  async clear() {
    try {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      await SecureStore.deleteItemAsync(USER_KEY);
    } catch {
      // rien à faire
    }
  },
};

export const AuthApi = {
  async login(identifier, password) {
    const { data } = await api.post('/auth/login', {
      username: identifier,
      password,
    });
    if (data?.access_token) {
      await TokenStorage.setToken(data.access_token);
    }
    if (data?.user) {
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(data.user));
    }
    return data;
  },

  async me() {
    const { data } = await api.get('/auth/me');
    return data;
  },

  async logout() {
    try {
      await api.post('/auth/logout');
    } catch {
      // la session côté serveur peut déjà être expirée
    }
    await TokenStorage.clear();
  },
};

// Helpers de requête (retour {ok, data, error}).
export const apiGet = async (url, config) => {
  try {
    const { data } = await api.get(url, config);
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: extractError(e) };
  }
};

export const apiPost = async (url, body, config) => {
  try {
    const { data } = await api.post(url, body, config);
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: extractError(e) };
  }
};

export const apiPut = async (url, body, config) => {
  try {
    const { data } = await api.put(url, body, config);
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: extractError(e) };
  }
};

export const apiDelete = async (url, config) => {
  try {
    await api.delete(url, config);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: extractError(e) };
  }
};

function extractError(e) {
  return e?.response?.data?.detail || e?.response?.data?.message || e?.message || 'Erreur réseau';
}
