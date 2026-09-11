// web/frontend/src/i18n/LanguageContext.jsx
// Contexte React de langue (FR / MG) — i18n léger sans dépendance externe.
// - Persistance dans localStorage (clé 'app_language'), fallback navigator.language.
// - Expose t(clé, vars?, fallback?) : traduction avec interpolation {var}.
// - Expose tNav(path, fallback) / tGroup(label) pour la navigation (navConfig).
// - Met à jour <html lang> pour l'accessibilité.

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  DEFAULT_LANGUAGE,
  LANGUAGES,
  SUPPORTED_LANGUAGES,
  translations,
} from './translations';

const STORAGE_KEY = 'app_language';

const isSupported = (code) => SUPPORTED_LANGUAGES.includes(code);

const resolveInitialLanguage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && isSupported(stored)) return stored;
  } catch {
    // ignore storage errors
  }
  try {
    const nav = (navigator.language || '').toLowerCase();
    if (nav.startsWith('mg')) return 'mg';
  } catch {
    // ignore
  }
  return DEFAULT_LANGUAGE;
};

export const LanguageContext = createContext(null);

const dictFor = (language) => translations[language] || translations[DEFAULT_LANGUAGE];

const translate = (language, key, vars, fallback) => {
  const raw = dictFor(language)[key] ?? dictFor(DEFAULT_LANGUAGE)[key];
  let text = raw != null ? raw : (fallback != null ? fallback : key);
  if (vars) {
    text = text.replace(/\{(\w+)\}/g, (match, name) =>
      vars[name] !== undefined && vars[name] !== null ? String(vars[name]) : match
    );
  }
  return text;
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguageState] = useState(resolveInitialLanguage);

  useEffect(() => {
    try {
      document.documentElement.lang = language;
    } catch {
      // ignore (SSR/tests)
    }
  }, [language]);

  const setLanguage = useCallback((code) => {
    if (!isSupported(code)) return;
    setLanguageState(code);
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // ignore storage errors
    }
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguage(language === 'fr' ? 'mg' : 'fr');
  }, [language, setLanguage]);

  const t = useCallback(
    (key, vars, fallback) => translate(language, key, vars, fallback),
    [language]
  );

  const tNav = useCallback(
    (path, fallback) => translate(language, `nav.${path}`, undefined, fallback),
    [language]
  );

  const tGroup = useCallback(
    (label) => translate(language, `navGroup.${label}`, undefined, label),
    [language]
  );

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      toggleLanguage,
      t,
      tNav,
      tGroup,
      languages: LANGUAGES,
    }),
    [language, setLanguage, toggleLanguage, t, tNav, tGroup]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useTranslation = () => {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useTranslation doit être utilisé dans un <LanguageProvider>');
  }
  return ctx;
};