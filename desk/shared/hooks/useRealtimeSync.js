// shared/hooks/useRealtimeSync.js
// Hook React pour la synchronisation temps-réel via Socket.IO.

import { useEffect, useCallback, useRef } from 'react';
import { socketClient } from '../websockets/socketClient';
import { useAuth } from '../../shared/hooks/useAuth';

export const useRealtimeSync = () => {
  const { user, tenant } = useAuth();
  const subscribedRef = useRef(new Set());

  useEffect(() => {
    const socket = socketClient.connect();

    const handleFavoriteUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:favorite:updated', { detail: data })
      );
    };

    const handleColumnUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:column:updated', { detail: data })
      );
    };

    const handleFilterUpdated = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:filter:updated', { detail: data })
      );
    };

    const handleNotificationNew = (data) => {
      window.dispatchEvent(
        new CustomEvent('realtime:notification:new', { detail: data })
      );
    };

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

    socketClient.on('favorite:updated', handleFavoriteUpdated);
    socketClient.on('column:updated', handleColumnUpdated);
    socketClient.on('filter:updated', handleFilterUpdated);
    socketClient.on('notification:new', handleNotificationNew);
    socketClient.on('user:updated', handleUserUpdated);
    socketClient.on('tenant:updated', handleTenantUpdated);

    return () => {
      socketClient.off('favorite:updated', handleFavoriteUpdated);
      socketClient.off('column:updated', handleColumnUpdated);
      socketClient.off('filter:updated', handleFilterUpdated);
      socketClient.off('notification:new', handleNotificationNew);
      socketClient.off('user:updated', handleUserUpdated);
      socketClient.off('tenant:updated', handleTenantUpdated);
    };
  }, []);

  const subscribeToFavorites = useCallback(() => {
    if (tenant?.id && !subscribedRef.current.has('favorites')) {
      socketClient.subscribeFavorites(tenant.id);
      subscribedRef.current.add('favorites');
    }
  }, [tenant?.id]);

  const subscribeToColumns = useCallback((module) => {
    if (tenant?.id && module) {
      socketClient.subscribeColumns(tenant.id, module);
      subscribedRef.current.add(`columns:${module}`);
    }
  }, [tenant?.id]);

  const subscribeToFilters = useCallback((module) => {
    if (tenant?.id && module) {
      socketClient.subscribeFilters(tenant.id, module);
      subscribedRef.current.add(`filters:${module}`);
    }
  }, [tenant?.id]);

  const subscribeToNotifications = useCallback(() => {
    if (user?.id && !subscribedRef.current.has('notifications')) {
      socketClient.subscribeNotifications(user.id);
      subscribedRef.current.add('notifications');
    }
  }, [user?.id]);

  useEffect(() => {
    subscribeToFavorites();
    subscribeToNotifications();
  }, [subscribeToFavorites, subscribeToNotifications]);

  return {
    subscribeToFavorites,
    subscribeToColumns,
    subscribeToFilters,
    subscribeToNotifications,
  };
};

export default useRealtimeSync;
