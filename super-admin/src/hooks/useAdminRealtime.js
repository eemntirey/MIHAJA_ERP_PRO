import { useEffect, useRef } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL =
  process.env.REACT_APP_SOCKET_URL ||
  (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL
    ? process.env.REACT_APP_API_URL.replace(/\/api\/v1\/?$/, '')
    : (typeof window !== 'undefined' ? window.location.origin : ''));

let socket = null;
const listeners = new Set();

const getSocket = () => {
  if (!socket) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('super_admin_access_token') : null;
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
      console.log('[Socket] Super-admin connectÃ©:', socket.id);
    });

    socket.on('disconnect', () => {
      console.log('[Socket] Super-admin dÃ©connectÃ©');
    });

    socket.on('connect_error', (err) => {
      console.warn('[Socket] Erreur connexion super-admin:', err.message);
    });
  }
  return socket;
};

export const useAdminRealtime = () => {
  const subscribedRef = useRef(false);

  useEffect(() => {
    const s = getSocket();

    const handleUserUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:user:updated', { detail: data })
      );
    };

    const handleTenantUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:tenant:updated', { detail: data })
      );
    };

    const handleSubscriptionUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:subscription:updated', { detail: data })
      );
    };

    const handlePlanUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:plan:updated', { detail: data })
      );
    };

    s.on('user:updated', handleUserUpdated);
    s.on('tenant:updated', handleTenantUpdated);
    s.on('subscription:updated', handleSubscriptionUpdated);
    s.on('plan:updated', handlePlanUpdated);
    listeners.add(handleUserUpdated);
    listeners.add(handleTenantUpdated);
    listeners.add(handleSubscriptionUpdated);
    listeners.add(handlePlanUpdated);
    subscribedRef.current = true;

    return () => {
      s.off('user:updated', handleUserUpdated);
      s.off('tenant:updated', handleTenantUpdated);
      s.off('subscription:updated', handleSubscriptionUpdated);
      s.off('plan:updated', handlePlanUpdated);
      listeners.delete(handleUserUpdated);
      listeners.delete(handleTenantUpdated);
      listeners.delete(handleSubscriptionUpdated);
      listeners.delete(handlePlanUpdated);
    };
  }, []);
};

export default useAdminRealtime;
