// src/hooks/useSplitView.js
import { useState, useEffect, useCallback } from 'react';

const LS_KEY = 'desk_split_view_state';

export const useSplitView = (module) => {
  const [state, setState] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
      return stored[module] || { enabled: false, leftWidth: 40 };
    } catch {
      return { enabled: false, leftWidth: 40 };
    }
  });

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
      stored[module] = state;
      localStorage.setItem(LS_KEY, JSON.stringify(stored));
    } catch {}
  }, [state, module]);

  const toggle = useCallback(() => setState((prev) => ({ ...prev, enabled: !prev.enabled })), []);
  const setLeftWidth = useCallback((width) => setState((prev) => ({ ...prev, leftWidth: Math.max(20, Math.min(60, width)) })), []);

  return { ...state, toggle, setLeftWidth };
};
