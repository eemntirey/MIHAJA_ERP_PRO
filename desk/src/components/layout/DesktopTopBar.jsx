// src/components/layout/DesktopTopBar.jsx
import React, { useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useDesktop } from '../../contexts/DesktopContext';
import CommandPalette from './CommandPalette';
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

const DesktopTopBar = ({ darkMode, onToggleDarkMode }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { setCommandPaletteOpen, unreadCount } = useDesktop();
  const [showNotifications, setShowNotifications] = useState(false);

  const path = location.pathname;
  const crumbs = useMemo(() => {
    const base = BREADCRUMB_MAP[path] || ['Page'];
    return base;
  }, [path]);

  const quickStats = useMemo(() => {
    if (path === '/inventory') return [
      { label: 'Stock critique', value: '2', tone: 'danger' },
    ];
    if (path === '/invoices') return [
      { label: 'Impayés', value: '12 450 Ar', tone: 'warning' },
    ];
    if (path === '/sales') return [
      { label: 'Ventes du jour', value: '3', tone: 'success' },
    ];
    return [];
  }, [path]);

  const openCommandPalette = () => setCommandPaletteOpen(true);

  return (
    <header className="desktop-topbar">
      <div className="topbar-left">
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
        {quickStats.map((stat, i) => (
          <span key={i} className={`topbar-pill ${stat.tone}`}>
            {stat.label}: {stat.value}
          </span>
        ))}
      </div>

      <div className="topbar-right">
        <button className="topbar-search-btn" onClick={openCommandPalette} title="Recherche globale (CMD+K)">
          <i className="ti ti-search" aria-hidden="true" />
          <span>Rechercher...</span>
          <kbd>⌘K</kbd>
        </button>

        <div className="topbar-notifications" style={{ position: 'relative' }}>
          <button className="topbar-icon-btn" onClick={() => setShowNotifications(!showNotifications)} title="Notifications">
            <i className="ti ti-bell" aria-hidden="true" />
            {unreadCount > 0 && <span className="topbar-notif-badge">{unreadCount}</span>}
          </button>
          {showNotifications && <NotificationDropdown onClose={() => setShowNotifications(false)} />}
        </div>

        <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
      </div>
    </header>
  );
};

export default DesktopTopBar;
