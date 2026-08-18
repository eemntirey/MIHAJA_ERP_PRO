// src/services/desktopApi.js

import api from './api';

export const notificationService = {
  getAll: () => api.get('/notifications'),
  markAsRead: (id) => api.post(`/notifications/${id}/read`),
  markAllAsRead: () => api.post('/notifications/read-all'),
  delete: (id) => api.delete(`/notifications/${id}`),
};

export const favoriteService = {
  getAll: () => api.get('/favorites'),
  add: (item) => api.post('/favorites', item),
  remove: (id) => api.delete(`/favorites/${id}`),
};

export const columnConfigService = {
  get: (module) => api.get(`/desk/columns/${module}`),
  save: (module, columns) => api.post(`/desk/columns/${module}`, { columns }),
};

export const filterPresetService = {
  getAll: (module) => api.get(`/desk/filters/${module}`),
  save: (module, preset) => api.post(`/desk/filters/${module}`, preset),
  delete: (module, id) => api.delete(`/desk/filters/${module}/${id}`),
};
