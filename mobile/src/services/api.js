// src/services/api.js
// Client HTTP unique de l'application mobile.
// Reprend la logique de shared/services/api.js (web/desktop) adaptée à
// React Native :
// - attachement du jeton d'accès (SecureStore) à chaque requête
// - rafraîchissement automatique du jeton sur 401 (file d'attente)
// - déconnexion propagée via setUnauthorizedHandler (pas de window en RN)

import axios from 'axios';
import { API_BASE_URL } from '../config/env';
import { session } from '../storage/session';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Callback déclenché quand la session doit être purgée (refresh impossible).
let unauthorizedHandler = null;
export const setUnauthorizedHandler = (fn) => {
  unauthorizedHandler = typeof fn === 'function' ? fn : null;
};

// ======================================================
// INTERCEPTEUR REQUEST — jeton d'accès
// ======================================================

api.interceptors.request.use(async (config) => {
  const token = await session.getAccessToken();
  if (token && !(config.headers && config.headers.Authorization)) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ======================================================
// INTERCEPTEUR RESPONSE — rafraîchissement JWT
// ======================================================

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((pending) => {
    if (error) {
      pending.reject(error);
    } else {
      pending.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    // Pas de réponse du serveur (réseau, timeout, URL invalide...)
    if (!error.response) {
      error.friendlyMessage =
        'Impossible de joindre le serveur. Vérifiez que le backend est démarré et que EXPO_PUBLIC_API_URL pointe vers la bonne adresse.';
      return Promise.reject(error);
    }

    const requestUrl = originalRequest?.url || '';
    const isLoginRequest = requestUrl.includes('/auth/login');
    const isRefreshRequest = requestUrl.includes('/auth/refresh');

    if (
      error.response.status === 401 &&
      !isLoginRequest &&
      !isRefreshRequest &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      const refreshToken = await session.getRefreshToken();

      // Aucun refresh token : purge + déconnexion.
      if (!refreshToken) {
        await session.clear();
        unauthorizedHandler?.();
        return Promise.reject(error);
      }

      // Un rafraîchissement est déjà en cours : mettre la requête en file.
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      isRefreshing = true;

      try {
        const refreshResponse = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          {
            timeout: 20000,
            headers: {
              Authorization: `Bearer ${refreshToken}`,
              'Content-Type': 'application/json',
            },
          }
        );

        const newAccessToken = refreshResponse.data?.access_token;
        if (!newAccessToken) {
          throw new Error('Nouveau access_token absent');
        }

        await session.setTokens({
          access_token: newAccessToken,
          refresh_token: refreshResponse.data.refresh_token,
        });
        if (refreshResponse.data.user) {
          await session.setUser(refreshResponse.data.user);
        }
        if (refreshResponse.data.tenant) {
          await session.setTenant(refreshResponse.data.tenant);
        }

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        processQueue(null, newAccessToken);

        return api(originalRequest);
      } catch (refreshError) {
        const refreshStatus = refreshError.response?.status;
        const isAuthFailure = refreshStatus === 401 || refreshStatus === 403;

        if (isAuthFailure) {
          await session.clear();
          unauthorizedHandler?.();
        }

        processQueue(refreshError);
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ======================================================
// HELPERS
// ======================================================

// Message d'erreur lisible à partir d'une erreur axios/RN.
export const getErrorMessage = (error, fallback = 'Une erreur est survenue') =>
  error?.friendlyMessage ||
  error?.response?.data?.message ||
  error?.response?.data?.error ||
  error?.message ||
  fallback;

// Extraction défensive des listes renvoyées par le backend
// ({produits: [...]} / {ventes: [...]} / tableau nu / {data: [...]}).
export const extractList = (data, keys) => {
  if (!data) return [];
  for (const key of keys) {
    if (Array.isArray(data[key])) return data[key];
  }
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.data)) return data.data;
  return [];
};

export default api;
