// src/components/layout/TitleBar.jsx
import React, { useEffect, useState } from 'react';
import './TitleBar.css';

// La barre n'est rendue que dans l'environnement Electron (window.electron via preload).
const isElectron = typeof window !== 'undefined' && window.electron;

const MinimizeIcon = () => (
  <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
    <line x1="2" y1="6" x2="10" y2="6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
);

const MaximizeIcon = () => (
  <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
    <rect x="2.2" y="2.2" width="7.6" height="7.6" fill="none" stroke="currentColor" strokeWidth="1.4" />
  </svg>
);

const RestoreIcon = () => (
  <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
    <rect x="2" y="4" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
    <rect x="4" y="2" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
    <line x1="2.5" y1="2.5" x2="9.5" y2="9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    <line x1="9.5" y1="2.5" x2="2.5" y2="9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
);

const TitleBar = () => {
  if (!isElectron) return null;

  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    let active = true;
    window.electron.isMaximized().then((value) => {
      if (active) setIsMaximized(!!value);
    });
    const handler = (value) => setIsMaximized(!!value);
    window.electron.onMaximizeChanged(handler);
    return () => { active = false; };
  }, []);

  const handleMinimize = () => window.electron.minimize();
  const handleMaximizeToggle = () => {
    if (isMaximized) window.electron.unmaximize();
    else window.electron.maximize();
  };
  const handleClose = () => window.electron.close();

  return (
    <header className="app-titlebar">
      <div className="app-titlebar__drag" onDoubleClick={handleMaximizeToggle}>
        <span className="app-titlebar__logo" aria-hidden="true">TIA</span>
        <span className="app-titlebar__brand">
          TIA INFO WHOLESALE
          <em className="app-titlebar__brand-sub">ERP PRO</em>
        </span>
      </div>

      <div className="app-titlebar__controls">
        <button
          type="button"
          className="app-titlebar__btn"
          onClick={handleMinimize}
          title="Minimiser"
          aria-label="Minimiser"
        >
          <MinimizeIcon />
        </button>
        <button
          type="button"
          className="app-titlebar__btn"
          onClick={handleMaximizeToggle}
          title={isMaximized ? 'Restaurer' : 'Maximiser'}
          aria-label={isMaximized ? 'Restaurer' : 'Maximiser'}
        >
          {isMaximized ? <RestoreIcon /> : <MaximizeIcon />}
        </button>
        <button
          type="button"
          className="app-titlebar__btn app-titlebar__btn--close"
          onClick={handleClose}
          title="Fermer"
          aria-label="Fermer"
        >
          <CloseIcon />
        </button>
      </div>
    </header>
  );
};

export default TitleBar;
