import axios from 'axios';
import { toast } from 'react-toastify';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

let isRefreshing = false;
let failedQueue = [];
const processQueue = (error, token = null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue = [];
};

const api = axios.create({
  baseURL: API_BASE_URL,
  // Timeout anti-blocage : sans lui, une requete qui ne repond jamais
  // (backend injoignable, mauvaise URL) fige le bouton sur "Connexion...".
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  const token = localStorage.getItem('super_admin_access_token');
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const requestUrl = originalRequest.url || '';
    // Les appels d'authentification eux-memes ne doivent jamais declencher
    // ni refresh ni redirection : l'erreur doit remonter a l'ecran de login.
    // Avant, un 401 sur /auth/login provoquait un rechargement complet de la
    // page (toast d'erreur perdu + impression de bouton "Connexion..." fige).
    const isAuthCall =
      requestUrl.includes('/auth/login') || requestUrl.includes('/auth/refresh');

    const redirectToLogin = () => {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    };

    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      !isAuthCall
    ) {
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
      originalRequest._retry = true;
      isRefreshing = true;
      const refreshToken = localStorage.getItem('super_admin_refresh_token');
      if (refreshToken) {
        try {
          const refreshResponse = await axios.post(
            `${API_BASE_URL}/auth/refresh`,
            null,
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
                'Content-Type': 'application/json',
              },
            }
          );
          const newAccessToken = refreshResponse.data.access_token;
          if (newAccessToken) {
            localStorage.setItem('super_admin_access_token', newAccessToken);
            if (refreshResponse.data.refresh_token) {
              localStorage.setItem('super_admin_refresh_token', refreshResponse.data.refresh_token);
            }
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            processQueue(null, newAccessToken);
            return api(originalRequest);
          }
          throw new Error('refresh sans token');
        } catch (e) {
          processQueue(e);
          localStorage.removeItem('super_admin_access_token');
          localStorage.removeItem('super_admin_refresh_token');
          localStorage.removeItem('super_admin_user');
          redirectToLogin();
        } finally {
          isRefreshing = false;
        }
      } else {
        isRefreshing = false;
        processQueue(new Error('no refresh token'));
        redirectToLogin();
      }
    }

    if (error.response?.status === 403) {
      toast.error("Accès refusé");
    }

    return Promise.reject(error);
  }
);

export const superAdminApi = api;

export const superAdminAuthService = {
  login: (email, password) =>
    api.post('/auth/login', { username: email, password }),

  logout: () =>
    api.post('/auth/logout'),

  getMe: () =>
    api.get('/auth/super-admin/me'),

  updateMe: (data) =>
    api.put('/auth/super-admin/me', data),

  confirmSession: () =>
    api.get('/auth/super-admin/me'),
};

export const superAdminTenantService = {
  getAll: (params) =>
    api.get('/super-admin/tenants', { params }),

  getById: (id) =>
    api.get(`/super-admin/tenants/${id}`),

  create: (data) =>
    api.post('/tenants/', data),

  update: (id, data) =>
    api.put(`/tenants/${id}`, data),

  suspend: (id) =>
    api.post(`/super-admin/tenants/${id}/suspend`),

  activate: (id) =>
    api.post(`/super-admin/tenants/${id}/activate`),

  reactivate: (id) =>
    api.post(`/super-admin/tenants/${id}/reactivate`),

  delete: (id) =>
    api.delete(`/super-admin/tenants/${id}`),

  extendSubscription: (id, days) =>
    api.post(`/super-admin/tenants/${id}/subscription/extend`, { days }),

  changeSubscription: (id, plan, days) =>
    api.post(`/super-admin/tenants/${id}/subscription/change`, { plan, days }),
};

export const superAdminSubscriptionService = {
  getAll: (params) =>
    api.get('/super-admin/subscriptions', { params }),

  getHistoriqueByTenant: (tenantId, params) =>
    api.get(`/abonnements/historique/${tenantId}`, { params }),

  getToggle: () =>
    api.get('/super-admin/subscription-toggle'),

  setToggle: (active) =>
    api.put('/super-admin/subscription-toggle', { subscription_active: active }),

  notifyActivation: () =>
    api.post('/super-admin/subscriptions/notify-activation'),

  sendReminder3j: () =>
    api.post('/super-admin/subscriptions/send-reminder-3j'),
};

export const superAdminDashboardService = {
  getStats: () =>
    api.get('/super-admin/dashboard'),
};

export const superAdminAuditService = {
  getLogs: (params) =>
    api.get('/super-admin/audit', { params }),
};

export const superAdminPlanService = {
  getAll: () =>
    api.get('/super-admin/plans'),
  update: (code, data) =>
    api.put('/super-admin/plans', { code, ...data }),
};

export const superAdminUserService = {
  getAll: (params) =>
    api.get('/super-admin/users', { params }),

  getById: (id) =>
    api.get(`/super-admin/users/${id}`),

  delete: (id) =>
    api.delete(`/super-admin/users/${id}`),
};

export default api;
