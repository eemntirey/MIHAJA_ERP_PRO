// src/services/api.js

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

console.log('API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(
  (config) => {
    config.headers = config.headers || {};
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!error.response) return Promise.reject(error);

    const requestUrl = originalRequest?.url || '';
    const isLoginRequest = requestUrl.includes('/auth/login');
    const isRefreshRequest = requestUrl.includes('/auth/refresh');

    if (error.response.status === 401 && !isLoginRequest && !isRefreshRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('Refresh token absent');

        const refreshResponse = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          { headers: { Authorization: `Bearer ${refreshToken}`, 'Content-Type': 'application/json' } }
        );

        const newAccessToken = refreshResponse.data.access_token;
        if (!newAccessToken) throw new Error('Nouveau access_token absent');

        localStorage.setItem('access_token', newAccessToken);
        if (refreshResponse.data.user) localStorage.setItem('user', JSON.stringify(refreshResponse.data.user));
        if (refreshResponse.data.tenant) localStorage.setItem('tenant', JSON.stringify(refreshResponse.data.tenant));
        if (refreshResponse.data.refresh_token) localStorage.setItem('refresh_token', refreshResponse.data.refresh_token);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        api.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;

        return api(originalRequest);
      } catch (refreshError) {
        console.error('Échec du renouvellement:', refreshError);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');
        window.dispatchEvent(new Event('auth:logout'));
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export const tenantService = {
  getAll: () => api.get('/tenants/'),
  getById: (id) => api.get(`/tenants/${id}`),
  create: (data) => api.post('/tenants/', data),
  update: (id, data) => api.put(`/tenants/${id}`, data),
  suspend: (id) => api.post(`/tenants/${id}/suspend`),
};

export const superAdminService = {
  getMe: () => api.get('/auth/super-admin/me'),
  updateMe: (data) => api.put('/auth/super-admin/me', data),
};

export const authService = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (data) => api.post('/auth/register', data),
  refresh: (refreshToken) => axios.post(`${API_BASE_URL}/auth/refresh`, null, { headers: { Authorization: `Bearer ${refreshToken}` } }),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
  updateMe: (data) => api.put('/auth/me', data),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
};

export const productService = {
  getAll: (params) => api.get('/produits', { params }),
  getById: (id) => api.get(`/produits/${id}`),
  create: (data) => api.post('/produits', data),
  update: (id, data) => api.put(`/produits/${id}`, data),
  delete: (id) => api.delete(`/produits/${id}`),
};

export const clientService = {
  getAll: (params) => api.get('/clients', { params }),
  getById: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
};

export const fournisseurService = {
  getAll: (params) => api.get('/fournisseurs', { params }),
  getById: (id) => api.get(`/fournisseurs/${id}`),
  create: (data) => api.post('/fournisseurs', data),
  update: (id, data) => api.put(`/fournisseurs/${id}`, data),
  delete: (id) => api.delete(`/fournisseurs/${id}`),
};

export const saleService = {
  getAll: (params) => api.get('/ventes', { params }),
  getById: (id) => api.get(`/ventes/${id}`),
  create: (data) => api.post('/ventes', data),
  update: (id, data) => api.put(`/ventes/${id}`, data),
  delete: (id) => api.delete(`/ventes/${id}`),
  getSummary: () => api.get('/ventes/summary'),
};

export const factureService = {
  getAll: (params) => api.get('/factures', { params }),
  getById: (id) => api.get(`/factures/${id}`),
  create: (data) => api.post('/factures', data),
  update: (id, data) => api.put(`/factures/${id}`, data),
  delete: (id) => api.delete(`/factures/${id}`),
};

export const paiementService = {
  getAll: (params) => api.get('/paiements', { params }),
  getById: (id) => api.get(`/paiements/${id}`),
  create: (data) => api.post('/paiements', data),
  update: (id, data) => api.put(`/paiements/${id}`, data),
  delete: (id) => api.delete(`/paiements/${id}`),
  getByFacture: (factureId) => api.get(`/paiements/facture/${factureId}`),
};

export const stockService = {
  getAll: (params) => api.get('/stocks', { params }),
  getById: (id) => api.get(`/stocks/${id}`),
  getMouvements: (params) => api.get('/stocks/mouvements', { params }),
  createMouvement: (data) => api.post('/stocks/mouvements', data),
  getStats: () => api.get('/stocks/stats'),
  updateStock: (productId, quantity, movementType, reason) => api.post('/stocks', { produit_id: productId, quantite: quantity, type_mouvement: movementType, raison: reason }),
  getAlerts: () => api.get('/stocks/alerts'),
};

export const dashboardService = {
  getStats: () => api.get('/dashboard'),
  getSalesStats: () => api.get('/dashboard/sales-stats'),
  getTopProducts: () => api.get('/dashboard/top-products'),
  getTopClients: () => api.get('/dashboard/top-clients'),
  getAlerts: () => api.get('/dashboard/alerts'),
  getPublicStats: () => api.get('/dashboard/public'),
};

export const subscriptionService = {
  getAll: () => api.get('/abonnements/'),
  demander: (data) => api.post('/abonnements/demander', data),
  getMonAbonnement: () => api.get('/abonnements/mon-abonnement'),
  getMonHistorique: () => api.get('/abonnements/mon-historique'),
  payer: (id, data) => api.post(`/abonnements/${id}/payer`, data),
  renouveler: (id) => api.post(`/abonnements/${id}/renouveler`),
  getHistoriqueByTenant: (tenantId) => api.get(`/abonnements/historique/${tenantId}`),
};

export const aiService = {
  getHealth: () => api.get('/ai/health'),
  getPrevisions: (params) => api.get('/ai/previsions', { params }),
  getAnomalies: (params) => api.get('/ai/anomalies', { params }),
  getRecommendations: (params) => api.get('/ai/recommendations', { params }),
  getStockRuptures: () => api.get('/ai/stock-ruptures'),
  askAssistant: (data) => api.post('/ai/assistant', data),
  trainModels: (data) => api.post('/ai/train', data),
};

export const livreurService = {
  getAll: (params) => api.get('/livreurs', { params }),
  getById: (id) => api.get(`/livreurs/${id}`),
  create: (data) => api.post('/livreurs', data),
  update: (id, data) => api.put(`/livreurs/${id}`, data),
  delete: (id) => api.delete(`/livreurs/${id}`),
};

export const vehiculeService = {
  getAll: (params) => api.get('/vehicules', { params }),
  getById: (id) => api.get(`/vehicules/${id}`),
  create: (data) => api.post('/vehicules', data),
  update: (id, data) => api.put(`/vehicules/${id}`, data),
  delete: (id) => api.delete(`/vehicules/${id}`),
};

export const itineraireService = {
  getAll: (params) => api.get('/itineraires', { params }),
  getById: (id) => api.get(`/itineraires/${id}`),
  create: (data) => api.post('/itineraires', data),
  update: (id, data) => api.put(`/itineraires/${id}`, data),
  delete: (id) => api.delete(`/itineraires/${id}`),
};

export const livraisonService = {
  getAll: (params) => api.get('/livraisons', { params }),
  getById: (id) => api.get(`/livraisons/${id}`),
  create: (data) => api.post('/livraisons', data),
  update: (id, data) => api.put(`/livraisons/${id}`, data),
  delete: (id) => api.delete(`/livraisons/${id}`),
  addSuivi: (id, data) => api.post(`/livraisons/${id}/suivi`, data),
  getSuivis: (id) => api.get(`/livraisons/${id}/suivis`),
};

export const employeService = {
  getAll: (params) => api.get('/employes', { params }),
  getById: (id) => api.get(`/employes/${id}`),
  create: (data) => api.post('/employes', data),
  update: (id, data) => api.put(`/employes/${id}`, data),
  delete: (id) => api.delete(`/employes/${id}`),
};

export const presenceService = {
  getAll: (params) => api.get('/presences', { params }),
  getById: (id) => api.get(`/presences/${id}`),
  create: (data) => api.post('/presences', data),
  update: (id, data) => api.put(`/presences/${id}`, data),
  delete: (id) => api.delete(`/presences/${id}`),
};

export const salaireService = {
  getAll: (params) => api.get('/salaires', { params }),
  getById: (id) => api.get(`/salaires/${id}`),
  create: (data) => api.post('/salaires', data),
  update: (id, data) => api.put(`/salaires/${id}`, data),
  delete: (id) => api.delete(`/salaires/${id}`),
};

export const primeService = {
  getAll: (params) => api.get('/primes', { params }),
  getById: (id) => api.get(`/primes/${id}`),
  create: (data) => api.post('/primes', data),
  update: (id, data) => api.put(`/primes/${id}`, data),
  delete: (id) => api.delete(`/primes/${id}`),
};

export const compteService = {
  getAll: (params) => api.get('/comptes', { params }),
  getById: (id) => api.get(`/comptes/${id}`),
  create: (data) => api.post('/comptes', data),
  update: (id, data) => api.put(`/comptes/${id}`, data),
  delete: (id) => api.delete(`/comptes/${id}`),
  import: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/comptes/import', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const ecritureService = {
  getAll: (params) => api.get('/ecritures', { params }),
  getById: (id) => api.get(`/ecritures/${id}`),
  create: (data) => api.post('/ecritures', data),
  update: (id, data) => api.put(`/ecritures/${id}`, data),
  delete: (id) => api.delete(`/ecritures/${id}`),
  valider: (id) => api.post(`/ecritures/${id}/valider`),
  annuler: (id) => api.post(`/ecritures/${id}/annuler`),
  import: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/ecritures/import', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const tresorerieService = {
  getAll: (params) => api.get('/tresorerie', { params }),
  getById: (id) => api.get(`/tresorerie/${id}`),
  create: (data) => api.post('/tresorerie', data),
  update: (id, data) => api.put(`/tresorerie/${id}`, data),
  delete: (id) => api.delete(`/tresorerie/${id}`),
  getSolde: (params) => api.get('/tresorerie/solde', { params }),
  import: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/tresorerie/import', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
};

export const modeleDocumentService = {
  getAll: (params) => api.get('/modeles-documents', { params }),
  getById: (id) => api.get(`/modeles-documents/${id}`),
  create: (data) => api.post('/modeles-documents', data),
  update: (id, data) => api.put(`/modeles-documents/${id}`, data),
  delete: (id) => api.delete(`/modeles-documents/${id}`),
};

export const documentService = {
  getAll: (params) => api.get('/documents', { params }),
  getById: (id) => api.get(`/documents/${id}`),
  create: (data) => api.post('/documents', data),
  delete: (id) => api.delete(`/documents/${id}`),
  generer: (data) => api.post('/documents/generer', data),
};

export const commandeAchatService = {
  getAll: (params) => api.get('/commandes-achat', { params }),
  getById: (id) => api.get(`/commandes-achat/${id}`),
  create: (data) => api.post('/commandes-achat', data),
  update: (id, data) => api.put(`/commandes-achat/${id}`, data),
  delete: (id) => api.delete(`/commandes-achat/${id}`),
};

export const receptionService = {
  getAll: (params) => api.get('/receptions', { params }),
  getById: (id) => api.get(`/receptions/${id}`),
  create: (data) => api.post('/receptions', data),
  update: (id, data) => api.put(`/receptions/${id}`, data),
  delete: (id) => api.delete(`/receptions/${id}`),
};

export const devisService = {
  getAll: (params) => api.get('/devis', { params }),
  getById: (id) => api.get(`/devis/${id}`),
  create: (data) => api.post('/devis', data),
  update: (id, data) => api.put(`/devis/${id}`, data),
  delete: (id) => api.delete(`/devis/${id}`),
  convertir: (id) => api.post(`/devis/${id}/convertir`),
};

export const bonLivraisonService = {
  getAll: (params) => api.get('/bons-livraison', { params }),
  getById: (id) => api.get(`/bons-livraison/${id}`),
  create: (data) => api.post('/bons-livraison', data),
  update: (id, data) => api.put(`/bons-livraison/${id}`, data),
  delete: (id) => api.delete(`/bons-livraison/${id}`),
};

export const avoirService = {
  getAll: (params) => api.get('/avoirs', { params }),
  getById: (id) => api.get(`/avoirs/${id}`),
  create: (data) => api.post('/avoirs', data),
  update: (id, data) => api.put(`/avoirs/${id}`, data),
  delete: (id) => api.delete(`/avoirs/${id}`),
};

export const roleService = {
  getAll: (params) => api.get('/roles', { params }),
  getById: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post('/roles', data),
  update: (id, data) => api.put(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
  addPermission: (roleId, permissionId) => api.post(`/roles/permissions`, { role_id: roleId, permission_id: permissionId }),
  removePermission: (roleId, permissionId) => api.delete(`/roles/permissions/${roleId}/${permissionId}`),
};

export const permissionService = {
  getAll: (params) => api.get('/permissions', { params }),
  getById: (id) => api.get(`/permissions/${id}`),
  create: (data) => api.post('/permissions', data),
  update: (id, data) => api.put(`/permissions/${id}`, data),
  delete: (id) => api.delete(`/permissions/${id}`),
};

export const userService = {
  getAll: (params) => api.get('/users', { params }),
  getById: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
};

export default api;
