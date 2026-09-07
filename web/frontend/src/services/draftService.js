// src/services/draftService.js
// Sauvegarde locale des brouillons de formulaires (auto-save toutes les 5 secondes).
// Aucun appel réseau : les brouillons restent sur le poste de travail.

import { buildKey, readJSON, writeJSON, removeKey, listKeys, getScopeId, STORE_NAMESPACE } from '../utils/localStore';

const DRAFT_VERSION = 1;
const DEFAULT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 jours

const draftKey = (key) => buildKey('draft', String(key));

export const draftService = {
  /**
   * @param {string} key identifiant du formulaire, ex: 'produits:new'
   * @returns {{data:Object, savedAt:string}|null}
   */
  get(key) {
    const stored = readJSON(draftKey(key), null);
    if (!stored || typeof stored !== 'object' || !('data' in stored)) return null;
    return { data: stored.data, savedAt: stored.savedAt || null };
  },

  save(key, data) {
    const payload = { version: DRAFT_VERSION, key: String(key), savedAt: new Date().toISOString(), data };
    const persisted = writeJSON(draftKey(key), payload);
    return { ...payload, persisted };
  },

  remove(key) {
    return removeKey(draftKey(key));
  },

  /** Liste les brouillons du scope courant. */
  list() {
    const prefix = `${STORE_NAMESPACE}.draft.${getScopeId()}.`;
    return listKeys(prefix)
      .map((fullKey) => {
        const stored = readJSON(fullKey, null);
        if (!stored || typeof stored !== 'object') return null;
        return { key: fullKey.slice(prefix.length), savedAt: stored.savedAt || null, data: stored.data };
      })
      .filter(Boolean);
  },

  /** Supprime les brouillons trop anciens (appelé au montage du hook). */
  prune(maxAgeMs = DEFAULT_MAX_AGE_MS) {
    const limit = Date.now() - maxAgeMs;
    let removed = 0;
    this.list().forEach((entry) => {
      const time = entry.savedAt ? new Date(entry.savedAt).getTime() : 0;
      if (!Number.isFinite(time) || time < limit) {
        if (this.remove(entry.key)) removed += 1;
      }
    });
    return removed;
  },
};

export default draftService;
