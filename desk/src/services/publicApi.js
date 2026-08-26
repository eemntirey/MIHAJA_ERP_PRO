import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const publicApi = axios.create({
  baseURL: process.env.REACT_APP_PUBLIC_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const publicCatalogueService = {
  getProduits: (params) => publicApi.get('/public/produits', { params }),
  getProduit: (id) => publicApi.get(`/public/produits/${id}`),
  getTenant: (id) => publicApi.get(`/public/tenants/${id}`),
  createCommande: (data) => publicApi.post('/public/commandes', data),
  getCommandeTracking: (ref) => publicApi.get(`/public/commandes/tracking/${ref}`),
  getNotifications: (ref) =>
    publicApi.get('/public/notifications', { params: ref ? { ref } : undefined }),
};

export default publicApi;
