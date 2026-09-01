
// src/services/api.js
// Réexport en une seule passe de tous les services de la bibliothèque
// partagée (shared/services/api), y compris l'export par défaut `api`.

export * from '../../shared/services/api';
export { default } from '../../shared/services/api';
