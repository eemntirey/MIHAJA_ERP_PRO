import { useEffect } from 'react';
import { io } from 'socket.io-client';
import { useSuperAdminAuth } from '../contexts/SuperAdminAuthContext';

const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL ||
  (import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '')
    : (typeof window !== 'undefined' ? window.location.origin : ''));

let socket = null;

export const useAdminRealtime = () => {
  const { isAuthenticated } = useSuperAdminAuth();

  useEffect(() => {
    const token =
      isAuthenticated && typeof window !== 'undefined'
        ? localStorage.getItem('super_admin_access_token')
        : null;

    // Ne jamais lancer une connexion Socket.IO anonyme depuis /login :
    // cela provoquait une boucle de 400 avant que l'access token soit disponible.
    if (!isAuthenticated || !token) {
      if (socket) {
        socket.disconnect();
        socket = null;
      }
      return undefined;
    }

    const s = io(SOCKET_URL, {
      transports: ['polling', 'websocket'],
      upgrade: true,
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 500,
      reconnectionDelayMax: 10000,
      withCredentials: true,
      auth: { token },
    });

    socket = s;

    s.on('connect', () => {
      console.log('[Socket] Super-admin connecté:', s.id);
    });

    s.on('disconnect', () => {
      console.log('[Socket] Super-admin déconnecté');
    });

    s.on('connect_error', (err) => {
      console.warn('[Socket] Erreur connexion super-admin:', err.message);
    });

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

    return () => {
      s.off('user:updated', handleUserUpdated);
      s.off('tenant:updated', handleTenantUpdated);
      s.off('subscription:updated', handleSubscriptionUpdated);
      s.off('plan:updated', handlePlanUpdated);
      s.disconnect();

      if (socket === s) {
        socket = null;
      }
    };
  }, [isAuthenticated]);

  return null;
};

export default useAdminRealtime;
