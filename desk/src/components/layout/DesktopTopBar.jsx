// src/components/layout/DesktopTopBar.jsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useDesktop } from '../../contexts/DesktopContext';
import { notificationService } from '../../services/desktopApi';
import Breadcrumbs from './Breadcrumbs';
import NotificationDropdown from './NotificationDropdown';
import ThemeToggle from './ThemeToggle';
import './DesktopTopBar.css';

const IS_ELECTRON = typeof window !== 'undefined' && !!window.electron;

const DesktopTopBar = ({ darkMode, onToggleDarkMode, counters = {}, onOpenPalette, onToggleSidebar, collapsed, isMobile, onLogout }) => {
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const { setCommandPaletteOpen, notifications, unreadCount } = useDesktop();
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef(null);

  const handleTopBarMouseDown = (e) => {
    if (!IS_ELECTRON) return;
    if (e.button !== 0) return;
    if (e.target.closest('button, a, input, select, textarea, [data-no-drag]')) return;
    try {
      window.electron.startDragging();
    } catch {
      /* ignore */
    }
  };

  const handleTopBarDoubleClick = (e) => {
    if (!IS_ELECTRON) return;
    if (e.target.closest('button, a, input, select, textarea, [data-no-drag]')) return;
    try {
      window.electron.isMaximized().then((max) => {
        if (max) window.electron.unmaximize();
        else window.electron.maximize();
      });
    } catch {
      /* ignore */
    }
  };

  // Fermer le dropdown notifications au clic extérieur
  useEffect(() => {
    const onClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setShowNotifications(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  // Synchronisation du badge du dock Electron
  useEffect(() => {
    notificationService.setBadge(unreadCount).catch(() => {});
  }, [unreadCount]);

  const indicators = useMemo(() => [
    { key: 'stock', label: 'Stock critique', value: counters.stock, icon: 'ti-alert-triangle', to: '/inventory', tone: 'critical' },
    { key: 'invoices', label: 'Impayés', value: counters.invoices, icon: 'ti-file-text', to: '/invoices', tone: 'warn' },
    { key: 'sales', label: 'Ventes du jour', value: counters.salesToday, icon: 'ti-receipt', to: '/sales', tone: 'ok' },
  ].filter((i) => i.value > 0), [counters]);

  const openCommandPalette = () => {
    if (onOpenPalette) onOpenPalette();
    else setCommandPaletteOpen(true);
  };

  return (
    <header className="desktop-topbar" onMouseDown={handleTopBarMouseDown} onDoubleClick={handleTopBarDoubleClick}>
      <div className="desktop-topbar__left">
        {onToggleSidebar && (
          <button
            type="button"
            className="desktop-topbar__toggle"
            onClick={onToggleSidebar}
            title={isMobile ? 'Menu' : (collapsed ? 'Déplier la barre' : 'Réduire la barre')}
            aria-label={isMobile ? 'Menu' : 'Basculer la barre latérale'}
          >
            <i className={`ti ${isMobile ? 'ti-menu' : 'ti-menu-2'}`} aria-hidden="true" />
          </button>
        )}
          <Breadcrumbs />
      </div>

      <div className="topbar-center">
        {indicators.map((ind) => (
          <button
            key={ind.key}
            type="button"
            className={`topbar-icon topbar-icon--${ind.tone}`}
            onClick={() => navigate(ind.to)}
            title={ind.label}
            aria-label={ind.label}
          >
            <i className={`ti ${ind.icon}`} aria-hidden="true" />
            <span className="topbar-icon__badge">{ind.value}</span>
          </button>
        ))}
      </div>

      <div className="topbar-right">
        <button
          className="topbar-search-btn"
          onClick={openCommandPalette}
          title="Recherche globale (CMD+K)"
          aria-label="Recherche globale (raccourci Cmd+K)"
        >
          <i className="ti ti-search" aria-hidden="true" />
          <span className="topbar-search-btn__label">Rechercher...</span>
          <kbd className="topbar-search-btn__kbd">⌘K</kbd>
        </button>

        <div className="topbar-notifications" ref={notifRef} style={{ position: 'relative' }}>
          <button className="topbar-icon-btn" onClick={() => setShowNotifications(!showNotifications)} title="Notifications">
            <i className="ti ti-bell" aria-hidden="true" />
            {unreadCount > 0 && <span className="topbar-notif-badge">{unreadCount}</span>}
          </button>
          {showNotifications && <NotificationDropdown onClose={() => setShowNotifications(false)} />}
        </div>

        {hasRole && hasRole('super_admin') && (
          <button type="button" className="topbar-icon-btn" onClick={() => navigate('/super-admin/profile')} title="Profil">
            <i className="ti ti-user" aria-hidden="true" />
          </button>
        )}

                <ThemeToggle enabled={darkMode} onChange={onToggleDarkMode} />

        {onLogout && (
          <button type="button" className="topbar-icon-btn" onClick={onLogout} title="Déconnexion" aria-label="Déconnexion">
            <i className="ti ti-logout" aria-hidden="true" />
          </button>
        )}
      </div>
    </header>
  );
};

export default DesktopTopBar;
