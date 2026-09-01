
// shared/hooks/useRealtime.js
// Hook temps-rÃ©el pour les mises Ã  jour (favoris, colonnes, filtres, notifications).
// Utilise le polling par dÃ©faut (via /api/v1/desk/events).
// Support optionnel de WebSocket via socket.io-client si disponible.

import { useState, useEffect, useCallback, useRef } from 'react';
import { syncService } from '../services/api';

const POLL_INTERVAL_MS = 5000;
const USE_WEBSOCKET = false;

export function useRealtime(options = {}) {
  const { onFavoriteUpdate, onColumnUpdate, onFilterUpdate, onNotification, pollInterval = POLL_INTERVAL_MS } = options;
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const intervalRef = useRef(null);
  const sinceRef = useRef(Date.now());

  const processEvent = useCallback((event) => {
    setLastEvent(event);
    const entity = event.entity || event.type || '';

    if (entity.includes('favorite') && typeof onFavoriteUpdate === 'function') {
      onFavoriteUpdate(event);
    }
    if (entity.includes('column') && typeof onColumnUpdate === 'function') {
      onColumnUpdate(event);
    }
    if (entity.includes('filter') && typeof onFilterUpdate === 'function') {
      onFilterUpdate(event);
    }
    if (entity.includes('notification') && typeof onNotification === 'function') {
      onNotification(event);
    }
  }, [onFavoriteUpdate, onColumnUpdate, onFilterUpdate, onNotification]);

  useEffect(() => {
    if (USE_WEBSOCKET && typeof window !== 'undefined') {
      let socket = null;
      try {
        const { io } = require('socket.io-client');
        const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null;
        if (token) {
          socket = io(window.location.origin, {
            path: '/socket.io',
            query: { token },
            transports: ['polling', 'websocket'],
        upgrade: false,
          });

          socket.on('connect', () => setConnected(true));
          socket.on('disconnect', () => setConnected(false));
          socket.on('favorite:updated', (data) => processEvent({ entity: 'favorite', data }));
          socket.on('column:updated', (data) => processEvent({ entity: 'column', data }));
          socket.on('filter:updated', (data) => processEvent({ entity: 'filter', data }));
          socket.on('notification:new', (data) => processEvent({ entity: 'notification', data }));
        }
      } catch {
        // socket.io-client non disponible, on utilisera le polling
      }

      return () => {
        if (socket) {
          socket.disconnect();
        }
      };
    }

    return () => {};
  }, [processEvent]);

  useEffect(() => {
    if (USE_WEBSOCKET) return;

    const poll = async () => {
      try {
        const since = sinceRef.current;
        const response = await syncService.events(since);
        const events = response.data?.events || [];
        if (events.length > 0) {
          sinceRef.current = response.data?.now || Date.now();
          events.forEach(processEvent);
        }
        setConnected(true);
      } catch {
        setConnected(false);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, pollInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [processEvent, pollInterval]);

  return {
    connected,
    lastEvent,
    reconnect: () => {
      sinceRef.current = Date.now();
    },
  };
}

export default useRealtime;
