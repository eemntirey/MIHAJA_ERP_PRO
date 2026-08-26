// shared/websockets/socketClient.js
// Client Socket.IO partagé pour web et desktop.
// Nécessite le paquet npm: socket.io-client

import { io } from 'socket.io-client';

const SOCKET_URL =
  process.env.REACT_APP_SOCKET_URL ||
  (typeof window !== 'undefined' ? window.location.origin : '');

let socket = null;
const listeners = new Map();

const getSocket = () => {
  if (!socket) {
    socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 500,
      reconnectionDelayMax: 10000,
    });

    socket.on('connect', () => {
      console.log('[Socket] Connecté:', socket.id);
      const token = typeof window !== 'undefined' ? window.localStorage.getItem('access_token') : null;
      if (token) {
        socket.emit('authenticate', { token });
      }
    });

    socket.on('disconnect', () => {
      console.log('[Socket] Déconnecté');
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
