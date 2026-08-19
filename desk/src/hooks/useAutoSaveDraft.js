// src/hooks/useAutoSaveDraft.js
import { useState, useEffect, useCallback, useRef } from 'react';

const STORAGE_PREFIX = 'erp_draft_';

export const useAutoSaveDraft = (key, initialData) => {
  const storageKey = `${STORAGE_PREFIX}${key}`;

  const [draft, setDraft] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...initialData, ...parsed };
      }
    } catch {
      // ignore parse errors
    }
    return initialData;
  });

  const draftRef = useRef(draft);
  draftRef.current = draft;

  useEffect(() => {
    const interval = setInterval(() => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(draftRef.current));
      } catch {
        // storage full or unavailable
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [storageKey]);

  const clearDraft = useCallback(() => {
    localStorage.removeItem(storageKey);
    setDraft(initialData);
  }, [storageKey, initialData]);

  const updateDraft = useCallback((updater) => {
    setDraft((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : { ...prev, ...updater };
      return next;
    });
  }, []);

  return { draft, setDraft: updateDraft, clearDraft };
};

export default useAutoSaveDraft;
