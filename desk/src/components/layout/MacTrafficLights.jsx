import React, { useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';
import './MacTrafficLights.css';

const IS_ELECTRON = typeof window !== 'undefined' && !!window.electron;

const MacTrafficLights = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [minimized, setMinimized] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  React.useEffect(() => {
    if (!IS_ELECTRON) return undefined;
    if (typeof window.electron.isMaximized === 'function') {
      window.electron.isMaximized().then(setIsMaximized).catch(() => {});
    }
    if (typeof window.electron.onMaximizeChanged === 'function') {
      window.electron.onMaximizeChanged(setIsMaximized);
    }
  }, []);

  const handleClose = useCallback(() => {
    if (IS_ELECTRON) {
      window.electron.close();
      return;
    }
    const confirmed = window.confirm('Quitter l\u2019application ? Vous serez d\u00e9connect\u00e9.');
    if (!confirmed) return;
    logout();
    navigate('/');
  }, [logout, navigate]);

  const handleMinimize = useCallback(() => {
    if (IS_ELECTRON) {
      window.electron.minimize();
      return;
    }
    setMinimized((prev) => {
      const next = !prev;
      toast.info(next ? 'Fen\u00eatre r\u00e9duite' : 'Fen\u00eatre restaur\u00e9e');
      return next;
    });
  }, []);

  const handleMaximize = useCallback(() => {
    if (IS_ELECTRON) {
      if (isMaximized) {
        window.electron.unmaximize();
      } else {
        window.electron.maximize();
      }
      return;
    }
    const docEl = document.documentElement;
    const isFs = document.fullscreenElement || document.webkitFullscreenElement;
    if (isFs) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen;
      if (exit) exit.call(document);
    } else if (docEl.requestFullscreen) {
      docEl.requestFullscreen().catch(() => toast.error('Plein \u00e9cran refus\u00e9'));
    } else {
      toast.warning('Plein \u00e9cran non support\u00e9');
    }
  }, [isMaximized]);

  // Render under <body> via a portal so the element escapes any ancestor
  // with `transform`, `perspective`, `filter` or `backdrop-filter` that
  // would otherwise create a containing block for fixed-positioned
  // descendants (e.g. .desktop-topbar with `backdrop-filter` + `sticky`).
  return createPortal(
    <div
      className={`mac-traffic-lights ${minimized ? 'is-minimized' : ''}`}
      role="toolbar"
      aria-label="Contr\u00f4les de fen\u00eatre macOS"
    >
      <button
        type="button"
        className="mac-btn mac-close"
        onClick={handleClose}
        aria-label="Fermer"
        title={IS_ELECTRON ? 'Fermer la fen\u00eatre' : 'D\u00e9connexion'}
      >
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path d="M3 3l6 6M9 3l-6 6" />
        </svg>
      </button>
      <button
        type="button"
        className="mac-btn mac-minimize"
        onClick={handleMinimize}
        aria-label="R\u00e9duire"
        title="R\u00e9duire"
      >
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path d="M3 6h6" />
        </svg>
      </button>
      <button
        type="button"
        className="mac-btn mac-maximize"
        onClick={handleMaximize}
        aria-label="Plein \u00e9cran"
        title="Plein \u00e9cran"
      >
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path d="M3 3h6v6H3z" />
        </svg>
      </button>
    </div>,
    document.body
  );
};

export default MacTrafficLights;