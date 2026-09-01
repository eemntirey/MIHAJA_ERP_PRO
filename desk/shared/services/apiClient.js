// shared/services/apiClient.js
// Instance axios partagée (web + desktop) avec :
//  - injection du Bearer access_token (depuis tokenStore)
//  - refresh automatique sur 401 (logique identique web/desktop)
//  - émission de l'événement 'auth:logout' en cas d'échec de refresh
// Remplace la duplication des intercepteurs présents dans les deux api.js.

import axios from 'axios';
import { tokenStore } from '../storage/tokenStore';

export const API_BASE_URL =
  (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(
  (config) => {
    config.headers = config.headers || {};
    const token = tokenStore.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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
        const refreshToken = tokenStore.getRefreshToken();
        if (!refreshToken) throw new Error('Refresh token absent');

        const { data } = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          { headers: { Authorization: `Bearer ${refreshToken}`, 'Content-Type': 'application/json' } }
        );

        const newAccess = data.access_token;
        if (!newAccess) throw new Error('Nouveau access_token absent');

        tokenStore.setSession({
          access_token: newAccess,
          refresh_token: data.refresh_token,
          user: data.user,
          tenant: data.tenant,
        });

        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
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
