// shared/index.js
// Point d'entrée unique de la bibliothèque partagée web/desktop.

export { default as api, API_BASE_URL } from './services/apiClient';
export { default as tokenStore } from './storage/tokenStore';
export * from './storage/storageAdapter';
export * from './utils/syncEngine';
export * from './services/syncApi';
export * from './services/preferences';
export { default as AuthContext, AuthProvider, useAuth } from './contexts/AuthContext';
export * from './realtime/socketClient';
