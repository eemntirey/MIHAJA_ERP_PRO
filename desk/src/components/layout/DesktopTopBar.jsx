// src/components/layout/DesktopTopBar.jsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useDesktop } from '../../contexts/DesktopContext';
import NotificationDropdown from './NotificationDropdown';
import DarkModeToggle from './DarkModeToggle';
import './DesktopTopBar.css';

const BREADCRUMB_MAP = {
  '/dashboard': ['Tableau de bord'],
  '/products': ['Produits'],
  '/clients': ['Piloter', 'Clients'],
  '/sales': ['Piloter', 'Ventes'],
  '/invoices': ['Piloter', 'Factures'],
  '/payments': ['Piloter', 'Paiements'],
  '/inventory': ['Opérations', 'Stock'],
  '/suppliers': ['Opérations', 'Fournisseurs'],
  '/purchases': ['Opérations', 'Achats'],
  '/delivery': ['Opérations', 'Livraisons'],
  '/hr': ['Gestion', 'Ressources Humaines'],
  '/accounting': ['Gestion', 'Comptabilité'],
  '/documents': ['Gestion', 'Documents'],
  '/ai': ['Gestion', 'Assistant IA'],
  '/subscription': ['Compte', 'Abonnement'],
  '/super-admin': ['Admin', 'Administration'],
};

const DesktopTopBar = ({ darkMode, onToggleDarkMode, counters = {}, onOpenPalette, onToggleSidebar, collapsed, onLogout }) => {
  const location = useLocation();
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

  const path = location.pathname;
  const crumbs = useMemo(() => {
    const base = BREADCRUMB_MAP[path] || ['Page'];
    return base;
  }, [path]);

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
            title={collapsed ? 'Déplier la barre' : 'Réduire la barre'}
            aria-label="Basculer la barre latérale"
          >
            <i className="ti ti-menu-2" aria-hidden="true" />
          </button>
        )}
        <nav className="topbar-breadcrumb" aria-label="Fil d'Ariane">
          {crumbs.map((crumb, i) => (
            <span key={i} className="topbar-crumb">
              {i > 0 && <i className="ti ti-chevron-right" aria-hidden="true" />}
              {i === crumbs.length - 1 ? <strong>{crumb}</strong> : <span>{crumb}</span>}
            </span>
          ))}
        </nav>
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

        <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />

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
