// shared/websockets/socketClient.js
// Client Socket.IO partagÃ© pour web et desktop.
// NÃ©cessite le paquet npm: socket.io-client

import { io } from 'socket.io-client';
import { tokenStore } from '../storage/tokenStore';

const SOCKET_URL =
  process.env.REACT_APP_SOCKET_URL ||
  (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL
    ? process.env.REACT_APP_API_URL.replace(/\/api\/v1\/?$/, '')
    : 'http://localhost:5000');

let socket = null;
const listeners = new Map();

const getSocket = () => {
  if (!socket) {
    const token = tokenStore.getAccessToken();
    socket = io(SOCKET_URL, {
      transports: ['polling', 'websocket'],
        upgrade: false,
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 500,
      reconnectionDelayMax: 10000,
      auth: token ? { token } : undefined,
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
