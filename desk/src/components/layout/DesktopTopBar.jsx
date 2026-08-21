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

const DesktopTopBar = ({ darkMode, onToggleDarkMode, counters = {}, onOpenPalette, onToggleSidebar, collapsed, isMobile, onLogout }) => {
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const { setCommandPaletteOpen, notifications, unreadCount } = useDesktop();
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef(null);

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
    <header className="desktop-topbar">
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
        <button className="topbar-search-btn" onClick={openCommandPalette} title="Recherche globale (CMD+K)">
          <i className="ti ti-search" aria-hidden="true" />
          <span>Rechercher...</span>
          <kbd>⌘K</kbd>
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
