
// shared/contexts/SyncContext.jsx
// Contexte de synchronisation global pour web et desktop.
// Gère la file d'attente hors-ligne, l'hydratation au démarrage,
// et les mises à jour temps-réel.

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { syncEngine } from '../utils/syncEngine';
import { syncService } from '../services/api';
import { useRealtime } from '../hooks/useRealtime';
import { runMigration } from '../utils/migrateLocalStorage';
import { toast } from 'react-toastify';

const SyncContext = createContext();

export const useSync = () => {
  const context = useContext(SyncContext);
  if (!context) {
    throw new Error('useSync must be used within a SyncProvider');
  }
  return context;
};

export const SyncProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(syncEngine.isOnline());
  const [syncQueue, setSyncQueue] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [migrationReport, setMigrationReport] = useState(null);

  // Ref de garde : le listener 'online' est enregistré une seule fois (deps [])
  // et ne doit pas dépendre d'un state qui peut être stale (closure) au moment
  // où l'événement réseau se déclenche. Un flush simultané est ainsi évité.
  const isSyncingRef = useRef(false);

  const flushQueue = useCallback(async () => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    setIsSyncing(true);

    try {
      const queue = syncEngine.getQueue();
      if (queue.length === 0) return;

      const result = await syncEngine.flush(async (entry) => {
        await syncService.push({
          mutations: [{
            entity: entry.entity,
            op: entry.op,
            payload: entry.payload,
          }],
        });
      });

      if (result.flushed > 0) {
        toast.success(`${result.flushed} modification(s) synchronisée(s)`);
      }

      if (result.failed > 0) {
        toast.error(`${result.failed} modification(s) n'ont pas pu être synchronisées`);
      }

      setLastSync(new Date());
      setSyncQueue(syncEngine.getQueue());
    } catch (error) {
      console.error('Erreur lors de la synchronisation:', error);
    } finally {
      isSyncingRef.current = false;
      setIsSyncing(false);
    }
  }, []);

  // Surveiller l'état du réseau
  useEffect(() => {
    const updateOnlineStatus = () => {
      const online = syncEngine.isOnline();
      setIsOnline(online);

      if (online) {
        flushQueue();
      }
    };

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
    };
  }, [flushQueue]);

  // Migration au premier démarrage
  useEffect(() => {
    runMigration()
      .then((report) => {
        if (report && !report.skipped) {
          setMigrationReport(report);
          const total = (report.favorites?.migrated || 0) +
            (report.columns?.migrated || 0) +
            (report.filters?.migrated || 0);
          if (total > 0) {
            toast.success(`${total} préférences migrées vers le cloud`);
          }
        }
      })
      .catch(() => {
        // migration silencieuse
      });
  }, []);

  // Mettre à jour la queue quand elle change
  useEffect(() => {
    setSyncQueue(syncEngine.getQueue());
  }, [lastSync]);

  const handleRealtimeEvent = useCallback((event) => {
    const entity = event.entity || event.type || '';

    if (entity.includes('favorite') || entity.includes('column') || entity.includes('filter')) {
      setSyncQueue(syncEngine.getQueue());
    }
  }, []);

  useRealtime({
    onFavoriteUpdate: handleRealtimeEvent,
    onColumnUpdate: handleRealtimeEvent,
    onFilterUpdate: handleRealtimeEvent,
    onUserUpdate: handleRealtimeEvent,
    onTenantUpdate: handleRealtimeEvent,
  });

  const value = {
    isOnline,
    syncQueue,
    isSyncing,
    lastSync,
    migrationReport,
    flushQueue,
    getQueue: () => syncEngine.getQueue(),
    clearQueue: () => {
      syncEngine.clear();
      setSyncQueue([]);
    },
    getStats: () => syncEngine.getStats(),
  };

  return (
    <SyncContext.Provider value={value}>
      {children}
    </SyncContext.Provider>
  );
};

export default SyncContext;
