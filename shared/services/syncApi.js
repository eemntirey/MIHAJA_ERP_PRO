// shared/services/syncApi.js
// Client des endpoints de synchronisation backend (namespace /api/v1/desk).
// Toutes les fonctions renvoient des Promises axios (data = corps de réponse).

import api from './apiClient';

// ---------- FAVORIS ----------
export const favoriteApi = {
  getAll: () => api.get('/desk/favorites'),
  upsert: (item) => api.post('/desk/favorites', item),
  remove: (key) => api.delete(`/desk/favorites/${encodeURIComponent(key)}`),
};

// ---------- PRESETS DE FILTRES ----------
export const filterApi = {
  getAll: (module) => api.get(`/desk/filters/${module}`),
  upsert: (module, preset) => api.post(`/desk/filters/${module}`, preset),
  remove: (module, id) => api.delete(`/desk/filters/${module}/${id}`),
};

// ---------- CONFIGURATION DES COLONNES ----------
export const columnApi = {
  get: (module) => api.get(`/desk/columns/${module}`),
  save: (module, config) => api.post(`/desk/columns/${module}`, config),
  reset: (module) => api.delete(`/desk/columns/${module}`),
};

// ---------- SYNC INCERTEMENTAL (révision) ----------
// push : envoie un batch de mutations ; le backend renvoie la nouvelle révision.
// pull : récupère tout l'état au-dessus de `revision` (last-write-wins serveur).
export const syncApi = {
  push: (batch) => api.post('/desk/sync/push', batch),
  pull: (revision = 0) => api.get('/desk/sync/pull', { params: { revision } }),
  status: () => api.get('/desk/sync/status'),
};

export default { favoriteApi, filterApi, columnApi, syncApi };
