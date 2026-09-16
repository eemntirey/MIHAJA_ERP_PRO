// src/services/services.js
// Services REST de l'application mobile — mêmes contrats que le backend
// /api/v1 et que shared/services/api.js (web/desktop), limités aux
// modules du mobile : Consultation, Vente, Inventaire, Livraison.

import { api } from './api';

// ======================================================
// AUTHENTIFICATION
// ======================================================

export const authService = {
  // POST /auth/login {username, password}
  // → {access_token, refresh_token, user, tenant, must_change_password}
  login: (credentials) => api.post('/auth/login', credentials),

  logout: () => api.post('/auth/logout'),

  // GET /auth/me → {user, tenant}
  me: () => api.get('/auth/me'),

  // Changement obligatoire (première connexion, mot de passe temporaire)
  firstChangePassword: (newPassword) =>
    api.post('/auth/first-login-change', {
      new_password: newPassword,
      confirm_password: newPassword,
    }),

  // Changement volontaire (compte connecté)
  changePassword: (oldPassword, newPassword) =>
    api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
      confirm_password: newPassword,
    }),
};

// ======================================================
// CONSULTATION (accueil / dashboard)
// ======================================================

export const dashboardService = {
  // GET /dashboard → {message, stats: {ca_mois, ventes_aujourdhui,
  //   benefice_mois, alertes_stock, clients_actifs, ...}}
  getStats: () => api.get('/dashboard'),

  // GET /dashboard/top-products → {top_products: [{produit_id, nom,
  //   total_quantite, total_ca}]}
  getTopProducts: () => api.get('/dashboard/top-products'),

  // GET /dashboard/alerts → {alertes_stock: [...], nb_alertes_stock}
  getAlerts: () => api.get('/dashboard/alerts'),
};

// ======================================================
// PRODUITS / CLIENTS (données de support pour la vente)
// ======================================================

export const productService = {
  // GET /produits → {produits: [...], total}
  getAll: (params) => api.get('/produits', { params }),
};

export const clientService = {
  // GET /clients → {clients: [...], total}
  getAll: (params) => api.get('/clients', { params }),
};

// ======================================================
// VENTES
// ======================================================

export const saleService = {
  // GET /ventes → {ventes: [...]} (avec client_nom / commercial_nom)
  getAll: (params) => api.get('/ventes', { params }),

  // POST /ventes {client_id, date?, statut?, mode_paiement?, type_vente?,
  //   remarque?, lignes: [{produit_id, quantite, prix_unitaire, taux_tva?}]}
  create: (data) => api.post('/ventes', data),
};

// ======================================================
// INVENTAIRE (stocks)
// ======================================================

export const stockService = {
  // GET /stocks → {stocks: [produits avec statut stock]}
  getAll: () => api.get('/stocks'),

  // GET /stocks/mouvements → {mouvements: [...]}
  getMouvements: () => api.get('/stocks/mouvements'),

  // POST /stocks {produit_id, quantite, type_mouvement: 'entree'|'sortie',
  //   raison} → 201 produit mis à jour
  createMouvement: (data) => api.post('/stocks', data),
};

// ======================================================
// LIVRAISON
// ======================================================

export const livraisonService = {
  // GET /livraisons → {livraisons: [...], total}
  getAll: (params) => api.get('/livraisons', { params }),

  // GET /livraisons/{id} → livraison détaillée (avec suivis)
  getById: (id) => api.get(`/livraisons/${id}`),

  // POST /livraisons/{id}/avancer → passe au statut suivant autorisé
  avancer: (id) => api.post(`/livraisons/${id}/avancer`),

  // POST /livraisons/{id}/statut {statut, commentaire?}
  changerStatut: (id, data) => api.post(`/livraisons/${id}/statut`, data),
};
