// shared/realtime/socketClient.js
// Client temps-réel (Socket.IO) pour pousser les MAJ backend -> clients.
// Repli automatique sur un polling long (SSE-like) si le serveur n'expose pas
// de socket, afin de ne rien casser si flask-socketio n'est pas déployé.
//
// Événements émis par le backend (voir web/backend/app/realtime/socket_server.py) :
//   'preferences:updated' { entity, module?, payload }
//   'favorite:updated' / 'column:updated' / 'filter:updated' / 'notification:updated'

import { API_BASE_URL } from '../services/apiClient';
import { tokenStore } from '../storage/tokenStore';

const SOCKET_URL = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_WS_URL) || API_BASE_URL.replace('/api/v1', '');

let socket = null;
let pollTimer = null;
let fallbackActive = false;
const handlers = new Map(); // event -> Set<fn>

const emitLocal = (event, payload) => {
  (handlers.get(event) || []).forEach((fn) => {
    try { fn(payload); } catch (e) { /* ignore handler error */ }
  });
};

export const on = (event, fn) => {
  if (!handlers.has(event)) handlers.set(event, new Set());
  handlers.get(event).add(fn);
  return () => handlers.get(event)?.delete(fn);
};

export const connect = () => {
  if (socket || typeof window === 'undefined') return;
  import('socket.io-client')
    .then(({ io }) => {
      socket = io(SOCKET_URL, {
        auth: { token: tokenStore.getAccessToken() },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 8000,
      });
      socket.on('connect', () => { fallbackActive = false; stopPolling(); });
      socket.on('disconnect', () => startPolling());
      ['preferences:updated', 'favorite:updated', 'column:updated', 'filter:updated', 'notification:updated']
        .forEach((evt) => socket.on(evt, (p) => emitLocal(evt, p)));
      setTimeout(() => { if (!socket?.connected) { startPolling(); } }, 4000);
    })
    .catch(() => startPolling());
};

window.addEventListener('pageshow', (event) => {
  if (event.persisted && socket) {
    socket.disconnect();
    socket = null;
    stopPolling();
    connect();
  }
});

const startPolling = () => {
  if (pollTimer || fallbackActive) return;
  fallbackActive = true;
  // Polling long : le backend renvoie les changements depuis `since`.
  let since = Date.now() - 60000;
  const tick = async () => {
    if (!tokenStore.getAccessToken()) return;
    try {
      const res = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/api/v1/desk/events?since=${since}`, {
        headers: { Authorization: `Bearer ${tokenStore.getAccessToken()}` },
      });
      if (res.ok) {
        const body = await res.json();
        (body.events || []).forEach((e) => emitLocal(e.type, e.payload));
        since = body.now || Date.now();
      }
    } catch { /* hors-ligne : on réessayera */ }
    pollTimer = setTimeout(tick, 15000);
  };
  tick();
};

const stopPolling = () => {
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
  fallbackActive = false;
};

export const disconnect = () => {
  stopPolling();
  if (socket) { socket.disconnect(); socket = null; }
};

export const notifyMutation = (entity, payload) => {
  // Le client qui vient de muter émet localement pour mise à jour immédiate de l'autre vue.
  emitLocal(`${entity}:updated`, payload);
};

export default { on, connect, disconnect, notifyMutation };
