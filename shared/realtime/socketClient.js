// shared/realtime/socketClient.js
// Client temps-rÃ©el (Socket.IO) pour pousser les MAJ backend -> clients.
// Repli automatique sur un polling long (SSE-like) si le serveur n'expose pas
// de socket, afin de ne rien casser si flask-socketio n'est pas dÃ©ployÃ©.
//
// Ã‰vÃ©nements Ã©mis par le backend (voir web/backend/app/realtime/socket_server.py) :
//   'preferences:updated' { entity, module?, payload }
//   'favorite:updated' / 'column:updated' / 'filter:updated' / 'notification:updated'

import { API_BASE_URL } from '../services/apiClient';
import { tokenStore } from '../storage/tokenStore';

const SOCKET_URL =
  import.meta.env.VITE_WS_URL ||
  (import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '')
    : API_BASE_URL.replace(/\/api\/v1\/?$/, ''));

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
      // A1 : web — withCredentials envoie le cookie HttpOnly au handshake.
      // Electron — le token est dans secureStore et passé via auth dict.
      const token = tokenStore.getAccessToken();
      const isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);
      socket = io(SOCKET_URL, {
        auth: isElectron && token ? { token } : undefined,
        withCredentials: !isElectron,
        transports: ['polling', 'websocket'],
        upgrade: false,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 8000,
      });
      socket.on('connect', () => { fallbackActive = false; stopPolling(); });
      socket.on('disconnect', () => startPolling());
      socket.io.on('error', (err) => {
        // "Session is disconnected" (HTTP 400 sur le polling suivant)
        // signifie que le serveur a purgé le sid. On détruit l'instance
        // pour forcer un nouveau handshake au prochain connect().
        if (err && /Session is disconnected/i.test(err.message || '')) {
          try { socket.disconnect(); } catch {}
          socket = null;
          connect();
        }
      });
      ['preferences:updated', 'favorite:updated', 'column:updated', 'filter:updated', 'notification:updated']
        .forEach((evt) => socket.on(evt, (p) => emitLocal(evt, p)));
      setTimeout(() => { if (!socket?.connected) { startPolling(); } }, 4000);
    })
    .catch(() => startPolling());
};

if (typeof window !== 'undefined') {
  window.addEventListener('pageshow', (event) => {
    if (event.persisted && socket) {
      socket.disconnect();
      socket = null;
      stopPolling();
      connect();
    }
  });
}

const startPolling = () => {
  if (pollTimer || fallbackActive) return;
  fallbackActive = true;
  // Polling long : le backend renvoie les changements depuis `since`.
  let since = Date.now() - 60000;
  const tick = async () => {
    // A1 : web — le cookie HttpOnly est envoyé automatiquement avec credentials.
    // Electron — le token est dans secureStore et passé via le header.
    const isElectron = !!(typeof window !== 'undefined' && window.electron && window.electron.secureStore);
    const token = isElectron ? tokenStore.getAccessToken() : null;
    if (!isElectron && typeof window === 'undefined') return;
    try {
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/api/v1/desk/events?since=${since}`, {
        credentials: isElectron ? 'omit' : 'include',
        headers,
      });
      if (res.ok) {
        const body = await res.json();
        (body.events || []).forEach((e) => emitLocal(e.type, e.payload));
        since = body.now || Date.now();
      }
    } catch { /* hors-ligne : on rÃ©essayera */ }
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
  // Le client qui vient de muter Ã©met localement pour mise Ã  jour immÃ©diate de l'autre vue.
  emitLocal(`${entity}:updated`, payload);
};

export default { on, connect, disconnect, notifyMutation };
