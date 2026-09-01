// desk/src/hooks/useTheme.js
// Hook centralisé de gestion du thème clair/sombre.
//
// Responsabilités :
//  - Lecture synchrone de la préférence depuis localStorage (compatible
//    avec le script en ligne critique injecté dans index.html → zéro flash).
//  - Synchronisation de la classe racine `.dark` sur <html> (documentElement)
//    en temps réel, ce qui active les variantes Tailwind `dark:` globalement.
//  - Persistance du choix dans localStorage.
//  - Mise à jour de la balise <meta name="theme-color"> pour Electron / navigateurs.
//
import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'dark_mode';
const THEME_COLORS = { dark: '#0f172a', light: '#fafafa' };

/**
 * @param {boolean|undefined} initialValue - Force un thème initial (utile en tests).
 * @returns {[boolean, (next?: boolean) => void]} [darkMode, toggleDarkMode]
 */
export const useTheme = (initialValue) => {
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof initialValue === 'boolean') return initialValue;
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    try {
      localStorage.setItem(STORAGE_KEY, String(darkMode));
    } catch {
      // ignore storage errors (SSR / restricted mode)
    }

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute('content', darkMode ? THEME_COLORS.dark : THEME_COLORS.light);
    }
  }, [darkMode]);

  const toggleDarkMode = useCallback((next) => {
    setDarkMode((prev) => {
      if (typeof next === 'boolean') return next;
      return !prev;
    });
  }, []);

  return [darkMode, toggleDarkMode];
};

export default useTheme;
