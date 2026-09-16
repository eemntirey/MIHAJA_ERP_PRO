// web/frontend/src/components/layout/LanguageSwitcher.jsx
// Sélecteur de langue FR / MG — intégré à la TopBar.
// Réutilise la classe existante `topbar-icon` (TopBar.css) pour conserver
// exactement le design actuel. Le menu est positionné en `fixed` (comme le
// dropdown des notifications) afin de ne pas être rogné par le conteneur
// scrollable `.desktop-topbar__scroll` (overflow-x).

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from '../../i18n';
import './LanguageSwitcher.css';

const LanguageSwitcher = () => {
  const { language, setLanguage, languages, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, right: 10 });
  const rootRef = useRef(null);
  const triggerRef = useRef(null);

  const openMenu = () => {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const margin = 8;
      const right = Math.max(margin, window.innerWidth - rect.right);
      setPos({ top: rect.bottom + 8, right });
    }
    setOpen((o) => !o);
  };

  useEffect(() => {
    if (!open) return undefined;
    const onOutside = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    const onKey = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onReflow = () => setOpen(false);
    document.addEventListener('mousedown', onOutside);
    document.addEventListener('keydown', onKey);
    window.addEventListener('scroll', onReflow, true);
    window.addEventListener('resize', onReflow);
    return () => {
      document.removeEventListener('mousedown', onOutside);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('scroll', onReflow, true);
      window.removeEventListener('resize', onReflow);
    };
  }, [open]);

  const current = languages.find((l) => l.code === language) || languages[0];

  return (
    <div className="language-switcher" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="topbar-icon language-switcher__trigger"
        onClick={openMenu}
        title={t('common.language')}
        aria-label={t('common.language')}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <i className="ti ti-language" aria-hidden="true" />
        <span className="language-switcher__code">{current.short}</span>
      </button>

      {open && (
        <div
          className="language-switcher__dropdown"
          role="listbox"
          aria-label={t('common.language')}
          style={{ position: 'fixed', top: pos.top, right: pos.right }}
        >
          {languages.map((lang) => (
            <button
              key={lang.code}
              type="button"
              role="option"
              aria-selected={lang.code === language}
              className={`language-switcher__option${lang.code === language ? ' is-active' : ''}`}
              onClick={() => {
                setLanguage(lang.code);
                setOpen(false);
              }}
            >
              <span className="language-switcher__flag" aria-hidden="true">{lang.flag}</span>
              <span>{lang.label}</span>
              {lang.code === language && <i className="ti ti-check" aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;