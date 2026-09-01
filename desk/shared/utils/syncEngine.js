
// shared/utils/syncEngine.js
// Moteur de synchronisation hors-ligne / en-ligne pour desktop et web.
//
// Stratégie:
// - Toutes les mutations (POST/PUT/DELETE) en mode hors-ligne sont
//   enregistrées dans une file d'attente (syncQueue) stockée en localStorage.
// - Au retour de la connexion, la file est rejouée séquentiellement.
// - Un timestamp "lastSyncedAt" permet de détecter les modifications
//   locales plus récentes que le backend (hydration au démarrage).
// - En cas de conflit (dernière écriture gagne), la mutation locale
//   écrase le backend si son timestamp est plus récent.

const SYNC_QUEUE_KEY = 'erp.sync.queue';
const LAST_SYNCED_KEY = 'erp.sync.lastSyncedAt';
const MAX_RETRIES = 3;
const RETRY_DELAYS = [1000, 5000, 30000];

const isOnline = () => typeof navigator !== 'undefined' ? navigator.onLine : true;

export const nowIso = () => new Date().toISOString();

/**
 * Compare deux items et renvoie le "gagnant" (Last-Write-Wins).
 */
export const pickLatest = (localItem, remoteItem) => {
  const lt = localItem?.updatedAt ? new Date(localItem.updatedAt).getTime() : 0;
  const rt = remoteItem?.updatedAt ? new Date(remoteItem.updatedAt).getTime() : 0;
  if (rt > lt) return remoteItem;
  if (lt > rt) return localItem;
  return remoteItem || localItem;
};

/**
 * Fusionne deux collections indexées par `keyFn`.
 * - Items des deux côtés -> résolus par LWW.
 * - Items d'un seul côté -> conservés (fusion manuelle).
 * @returns {{merged:Array, conflicts:Array}}
 */
export const mergeCollections = (localList, remoteList, keyFn = (x) => x.id) => {
  const local = Array.isArray(localList) ? localList : [];
  const remote = Array.isArray(remoteList) ? remoteList : [];
  const map = new Map();
  const conflicts = [];

  local.forEach((item) => map.set(keyFn(item), { item, source: 'local' }));

  remote.forEach((item) => {
    const k = keyFn(item);
    const existing = map.get(k);
    if (!existing) {
      map.set(k, { item, source: 'remote' });
    } else {
      const winner = pickLatest(existing.item, item);
      if (winner === item && winner !== existing.item) {
        conflicts.push({ key: k, local: existing.item, remote: item, winner: 'remote' });
      } else if (winner === existing.item) {
        conflicts.push({ key: k, local: existing.item, remote: item, winner: 'local' });
      }
      map.set(k, { item: winner, source: 'merged' });
    }
  });

  return { merged: Array.from(map.values()).map((v) => v.item), conflicts };
};

const memoryQueue = [];

const getQueue = () => {
  try {
    const raw = localStorage.getItem(SYNC_QUEUE_KEY);
    if (raw === null) return memoryQueue.slice();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : memoryQueue.slice();
  } catch {
    return memoryQueue.slice();
  }
};

const persistQueue = (queue) => {
  try {
    localStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(queue));
    memoryQueue.length = 0;
  } catch {
    memoryQueue.length = 0;
    memoryQueue.push(...queue);
  }
};

const getLastSyncedAt = () => {
  try {
    const raw = localStorage.getItem(LAST_SYNCED_KEY);
    return raw ? new Date(raw).getTime() : 0;
  } catch {
    return 0;
  }
};

const setLastSyncedAt = () => {
  try {
    localStorage.setItem(LAST_SYNCED_KEY, new Date().toISOString());
  } catch {
    // ignore
  }
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const syncEngine = {
  isOnline,
  mergeCollections,
  pickLatest,
  nowIso,

  getLastSyncedAt,

  getQueue: () => getQueue(),

  enqueue: (operation) => {
    const queue = getQueue();
    const entry = {
      id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      method: operation.method || 'POST',
      url: operation.url,
      payload: operation.payload ?? null,
      headers: operation.headers || {},
      entity: operation.entity || null,
      op: operation.op || null,
      retries: 0,
      createdAt: new Date().toISOString(),
    };
    queue.push(entry);
    persistQueue(queue);
    return entry;
  },

  dequeue: (id) => {
    const queue = getQueue().filter((item) => item.id !== id);
    persistQueue(queue);
  },

  clear: () => {
    persistQueue([]);
    memoryQueue.length = 0;
  },

  /**
   * Rejoue la file d'attente dans l'ordre.
   * @param {Function} fetchFn - (entry) => Promise<response>
   * @param {Function} [onProgress] - (processed, total) => void
   */
  async flush(fetchFn, onProgress) {
    const queue = getQueue();
    if (queue.length === 0) return { flushed: 0, failed: 0 };

    let processed = 0;
    let failed = 0;

    for (let i = 0; i < queue.length; i++) {
      const entry = queue[i];
      try {
        await fetchFn(entry);
        this.dequeue(entry.id);
        processed++;
      } catch (error) {
        entry.retries = (entry.retries || 0) + 1;
        if (entry.retries >= MAX_RETRIES) {
          this.dequeue(entry.id);
          failed++;
        } else {
          const remaining = getQueue();
          persistQueue(remaining);
          await wait(RETRY_DELAYS[Math.min(entry.retries - 1, RETRY_DELAYS.length - 1)]);
        }
      }
      if (typeof onProgress === 'function') {
        onProgress(processed, queue.length);
      }
    }

    if (processed > 0) {
      setLastSyncedAt();
    }

    return { flushed: processed, failed };
  },

  /**
   * Hydratation au démarrage: compare les timestamps locaux vs backend.
   * Si une donnée locale est plus récente, on peut la pousser au backend.
   * @param {Function} fetchFn - (entry) => Promise<response>
   * @param {Function} [pullFn] - () => Promise<backendState> pour comparaison
   */
  async hydrate(fetchFn, pullFn) {
    const lastSynced = getLastSyncedAt();
    const queue = getQueue();

    if (queue.length === 0) {
      return { hydrated: 0, pulled: false };
    }

    let hydrated = 0;

    if (typeof pullFn === 'function') {
      try {
        const backendState = await pullFn();
        if (backendState && backendState.revision) {
          const backendTime = new Date(backendState.revision * 1000).getTime();
          if (backendTime > lastSynced && lastSynced > 0) {
            const staleEntries = queue.filter((entry) => {
              const entryTime = new Date(entry.createdAt).getTime();
              return entryTime < lastSynced;
            });

            for (const entry of staleEntries) {
              try {
                await fetchFn(entry);
                this.dequeue(entry.id);
                hydrated++;
              } catch {
                // on garde l'entrée pour le prochain flush
              }
            }
          }
        }
      } catch {
        // Fallback: si pull échoue, on hydrate tout
        for (const entry of queue) {
          try {
            await fetchFn(entry);
            this.dequeue(entry.id);
            hydrated++;
          } catch {
            // keep for next flush
          }
        }
      }
    } else {
      for (const entry of queue) {
        try {
          await fetchFn(entry);
          this.dequeue(entry.id);
          hydrated++;
        } catch {
          // keep for next flush
        }
      }
    }

    if (hydrated > 0) {
      setLastSyncedAt();
    }

    return { hydrated };
  },

  /**
   * Résout un conflit entre données locales et backend.
   * Stratégie: "dernière écriture gagne" (LWW - Last Write Wins).
   * @param {Object} local - données locales
   * @param {Object} remote - données du backend
   * @param {string} [strategy='lww'] - 'lww' | 'merge' | 'manual'
   * @returns {Object} données résolues
   */
  resolveConflict(local, remote, strategy = 'lww') {
    if (!local) return remote;
    if (!remote) return local;

    const localTime = new Date(local.updatedAt || local.createdAt || 0).getTime();
    const remoteTime = new Date(remote.updatedAt || remote.createdAt || 0).getTime();

    if (strategy === 'lww') {
      return localTime >= remoteTime ? local : remote;
    }

    if (strategy === 'merge') {
      return {
        ...remote,
        ...local,
        updatedAt: localTime >= remoteTime ? local.updatedAt : remote.updatedAt,
      };
    }

    return local;
  },

  /**
   * Statistiques de la file d'attente.
   */
  getStats() {
    const queue = getQueue();
    const byEntity = {};
    queue.forEach((entry) => {
      const key = entry.entity || 'unknown';
      byEntity[key] = (byEntity[key] || 0) + 1;
    });

    return {
      total: queue.length,
      pending: queue.filter((e) => e.retries === 0).length,
      retrying: queue.filter((e) => e.retries > 0 && e.retries < MAX_RETRIES).length,
      failed: queue.filter((e) => e.retries >= MAX_RETRIES).length,
      byEntity,
      lastSyncedAt: getLastSyncedAt(),
    };
  },
};

export default syncEngine;
