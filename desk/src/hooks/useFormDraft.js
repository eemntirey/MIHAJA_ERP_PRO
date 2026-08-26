// src/hooks/useFormDraft.js
// Auto-save local des brouillons de formulaire (par défaut toutes les 5 secondes).
//
// Utilisation :
//   const draft = useFormDraft('produits:new', formData, { enabled: showModal });
//   ...
//   {draft.hasStoredDraft && <FormDraftBanner draft={draft} onRestore={(data) => setFormData(data)} />}
//   // après un submit réussi :
//   draft.clear();

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { draftService } from '../services/draftService';

export const DRAFT_AUTOSAVE_INTERVAL = 5000;

/** JSON déterministe (clés triées) pour comparer deux états de formulaire. */
const stableStringify = (value) => {
  const seen = new WeakSet();
  const walk = (input) => {
    if (input === null || typeof input !== 'object') {
      return typeof input === 'function' || input === undefined ? null : input;
    }
    if (seen.has(input)) return null;
    seen.add(input);
    if (Array.isArray(input)) return input.map(walk);
    return Object.keys(input)
      .sort()
      .reduce((acc, key) => {
        acc[key] = walk(input[key]);
        return acc;
      }, {});
  };
  try {
    return JSON.stringify(walk(value));
  } catch {
    return '';
  }
};

const omitKeys = (values, keys) => {
  if (!keys?.length || !values || typeof values !== 'object' || Array.isArray(values)) return values;
  const clone = { ...values };
  keys.forEach((key) => delete clone[key]);
  return clone;
};

/**
 * @param {string|null} key identifiant du brouillon ('produits:new', 'ventes:42'...). `null` désactive le hook.
 * @param {Object} values état courant du formulaire
 * @param {Object} [options]
 * @param {boolean} [options.enabled=true] active l'auto-save (ex: modale ouverte)
 * @param {number} [options.interval=5000] période d'auto-save en ms
 * @param {string[]} [options.exclude] champs à ne pas persister
 * @param {boolean} [options.saveOnUnmount=true] flush au démontage / fermeture de fenêtre
 */
const useFormDraft = (key, values, options = {}) => {
  const {
    enabled = true,
    interval = DRAFT_AUTOSAVE_INTERVAL,
    exclude,
    saveOnUnmount = true,
  } = options;

  const active = enabled && !!key;

  const [status, setStatus] = useState('idle');
  const [savedAt, setSavedAt] = useState(null);
  const [storedDraft, setStoredDraft] = useState(null);

  const valuesRef = useRef(values);
  const baselineRef = useRef(null);
  const lastSavedRef = useRef(null);
  const excludeRef = useRef(exclude);

  valuesRef.current = values;
  excludeRef.current = exclude;

  const buildPayload = useCallback(() => omitKeys(valuesRef.current, excludeRef.current), []);

  /** Écrit le brouillon immédiatement. Retourne true si une écriture a eu lieu. */
  const saveNow = useCallback(
    (force = false) => {
      if (!key) return false;
      const payload = buildPayload();
      const signature = stableStringify(payload);
      if (!force) {
        // Rien à sauvegarder : formulaire non modifié depuis l'ouverture ou depuis la dernière sauvegarde.
        if (signature === baselineRef.current || signature === lastSavedRef.current) return false;
      }
      const result = draftService.save(key, payload);
      lastSavedRef.current = signature;
      setSavedAt(result.savedAt);
      setStatus(result.persisted === false ? 'error' : 'saved');
      return true;
    },
    [buildPayload, key]
  );

  // (Ré)initialisation quand le formulaire s'ouvre ou change de cible.
  useEffect(() => {
    if (!active) {
      setStatus('idle');
      return;
    }
    baselineRef.current = stableStringify(omitKeys(valuesRef.current, excludeRef.current));
    lastSavedRef.current = null;
    setStatus('idle');
    setSavedAt(null);
    draftService.prune();
    const existing = draftService.get(key);
    setStoredDraft(existing);
  }, [active, key]);

  // Minuteur d'auto-save : indépendant des frappes clavier (aucun re-render inutile).
  useEffect(() => {
    if (!active) return undefined;
    const timer = setInterval(() => {
      saveNow(false);
    }, Math.max(1000, interval));
    return () => clearInterval(timer);
  }, [active, interval, saveNow]);

  // Flush au démontage et à la fermeture de la fenêtre.
  useEffect(() => {
    if (!active || !saveOnUnmount) return undefined;
    const flush = () => saveNow(false);
    window.addEventListener('beforeunload', flush);
    return () => {
      window.removeEventListener('beforeunload', flush);
      flush();
    };
  }, [active, saveOnUnmount, saveNow]);

  const restore = useCallback(() => {
    const existing = storedDraft || (key ? draftService.get(key) : null);
    if (!existing) return null;
    lastSavedRef.current = stableStringify(existing.data);
    baselineRef.current = null;
    setStoredDraft(null);
    setSavedAt(existing.savedAt);
    setStatus('restored');
    return existing.data;
  }, [key, storedDraft]);

  const discard = useCallback(() => {
    if (key) draftService.remove(key);
    setStoredDraft(null);
    lastSavedRef.current = null;
    setSavedAt(null);
    setStatus('idle');
  }, [key]);

  const clear = useCallback(() => {
    if (key) draftService.remove(key);
    setStoredDraft(null);
    baselineRef.current = null;
    lastSavedRef.current = null;
    setSavedAt(null);
    setStatus('idle');
  }, [key]);

  return useMemo(
    () => ({
      status,
      savedAt,
      storedDraft,
      hasStoredDraft: !!storedDraft,
      interval,
      restore,
      discard,
      clear,
      saveNow,
    }),
    [status, savedAt, storedDraft, interval, restore, discard, clear, saveNow]
  );
};

export { stableStringify };
export default useFormDraft;
