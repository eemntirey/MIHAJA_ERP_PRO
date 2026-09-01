import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
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
    const originalRequest = error.config;

    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
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
            return api(originalRequest);
          }
        } catch {
          localStorage.removeItem('super_admin_access_token');
          localStorage.removeItem('super_admin_refresh_token');
          localStorage.removeItem('super_admin_user');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
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
