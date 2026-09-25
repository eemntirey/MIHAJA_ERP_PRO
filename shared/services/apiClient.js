// shared/services/apiClient.js
// Instance axios partagée (web + desktop) avec :
//  - injection du Bearer access_token (depuis tokenStore, Electron seul)
//  - refresh automatique sur 401 (cookies HttpOnly sur web, header sur Electron)
//  - émission de l'événement 'auth:logout' en cas d'échec de refresh
// Remplace la duplication des intercepteurs présents dans les deux api.js.

import axios from 'axios';
import { tokenStore } from '../storage/tokenStore';

const _viteEnv = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};
const _isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);
export const API_BASE_URL =
  _viteEnv.VITE_API_URL || (_isElectron ? 'https://mihaja-erp-pro.onrender.com/api/v1' : '/api/v1');

// A1 : Electron = secureStore + header ; web = cookies HttpOnly
const isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(
  (config) => {
    config.headers = config.headers || {};
    config.withCredentials = true;
    // A1 : web n'a pas besoin du header — le navigateur envoie les cookies
    if (isElectron) {
      const token = tokenStore.getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest) return Promise.reject(error);

    const url = originalRequest.url || '';
    const isAuthCall =
      url.includes('/auth/login') || url.includes('/auth/refresh');

    if (
      error.response &&
      error.response.status === 401 &&
      !isAuthCall &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;
      try {
        // A1 : web — le refresh token est en cookie HttpOnly (envoyé automatiquement).
        // Electron — le token est dans secureStore et passé via le header.
        const refreshToken = isElectron ? tokenStore.getRefreshToken() : null;

        const refreshHeaders = { 'Content-Type': 'application/json' };
        if (isElectron && refreshToken) {
          refreshHeaders.Authorization = `Bearer ${refreshToken}`;
        }

        const { data } = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          { headers: refreshHeaders, withCredentials: true }
        );

        const newAccess = data.access_token;
        if (!newAccess && isElectron) throw new Error('Nouveau access_token absent');

        tokenStore.setSession({
          access_token: newAccess,
          refresh_token: data.refresh_token,
          user: data.user,
          tenant: data.tenant,
        });

        if (isElectron && newAccess) {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        tokenStore.clear();
        delete api.defaults.headers.common.Authorization;
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('auth:logout'));
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
