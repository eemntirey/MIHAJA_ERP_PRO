// shared/websockets/socketClient.js
// Client Socket.IO partagÃ© pour web et desktop.
// NÃ©cessite le paquet npm: socket.io-client

import { io } from 'socket.io-client';
import { tokenStore } from '../storage/tokenStore';

const PRODUCTION_SOCKET_URL = 'https://mihaja-erp-pro.onrender.com';

const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL ||
  (import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '')
    // Same-origin par défaut : en dev, Vite relaie /socket.io vers le
    // backend (ws: true) ; en prod, reverse-proxy same-origin. Un fallback
    // absolu http://localhost:5000 serait bloqué par la CSP de l'app
    // Electron (connect-src 'self') dès que la page est servie autrement.
    : (typeof window !== 'undefined' ? window.location.origin : PRODUCTION_SOCKET_URL));

let socket = null;
const listeners = new Map();

const getSocket = () => {
  if (!socket) {
    const token = tokenStore.getAccessToken();
    // A1 : web — withCredentials envoie le cookie HttpOnly au handshake.
    // Electron — le token est dans secureStore et passé via auth dict.
    const isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);
    socket = io(SOCKET_URL, {
      transports: ['polling', 'websocket'],
        upgrade: true,
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 500,
      reconnectionDelayMax: 10000,
      withCredentials: !isElectron,
      auth: isElectron && token ? { token } : undefined,
    });

    socket.on('connect', () => {
      console.log('[Socket] Connecte:', socket.id);
    });

    socket.on('disconnect', () => {
      console.log('[Socket] Deconnecte');
    });

    socket.on('connect_error', (err) => {
      console.warn('[Socket] Erreur de connexion:', err.message);
    });
  }
  return socket;
};

export const socketClient = {
  connect: () => getSocket(),

  disconnect: () => {
    if (socket) {
      socket.disconnect();
      socket = null;
    }
  },

  on: (event, callback) => {
    const s = getSocket();
    s.on(event, callback);
    if (!listeners.has(event)) {
      listeners.set(event, new Set());
    }
    listeners.get(event).add(callback);
  },

  off: (event, callback) => {
    const s = getSocket();
    if (callback) {
      s.off(event, callback);
      listeners.get(event)?.delete(callback);
    } else {
      s.off(event);
      listeners.delete(event);
    }
  },

  emit: (event, data) => {
    const s = getSocket();
    s.emit(event, data);
  },

  authenticate: (token) => {
    const s = getSocket();
    s.emit('authenticate', { token });
  },

  subscribeFavorites: (tenantId) => {
    const s = getSocket();
    s.emit('subscribe:favorites', { tenant_id: tenantId });
  },

  subscribeColumns: (tenantId, module) => {
    const s = getSocket();
    s.emit('subscribe:columns', { tenant_id: tenantId, module });
  },

  subscribeFilters: (tenantId, module) => {
    const s = getSocket();
    s.emit('subscribe:filters', { tenant_id: tenantId, module });
  },

  subscribeNotifications: (userId) => {
    const s = getSocket();
    s.emit('subscribe:notifications', { user_id: userId });
  },
};

export default socketClient;
