import React, { useState, useRef, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './DashboardRail.css';

const NAV_GROUPS = [
  {
    label: 'Piloter',
    items: [
      { label: 'Tableau de bord', to: '/dashboard', icon: 'ti-layout-dashboard' },
      { label: 'Produits', to: '/products', icon: 'ti-package' },
      { label: 'Clients', to: '/clients', icon: 'ti-users' },
      { label: 'Ventes', to: '/sales', icon: 'ti-shopping-cart' },
      { label: 'Factures', to: '/invoices', icon: 'ti-file-text' },
      { label: 'Paiements', to: '/payments', icon: 'ti-credit-card' },
    ],
  },
  {
    label: 'Opérations',
    items: [
      { label: 'Stock', to: '/inventory', icon: 'ti-box' },
      { label: 'Fournisseurs', to: '/suppliers', icon: 'ti-truck' },
      { label: 'Achats', to: '/purchases', icon: 'ti-shopping-cart-plus' },
      { label: 'Livraisons', to: '/delivery', icon: 'ti-truck-delivery' },
    ],
  },
  {
    label: 'Gestion',
    items: [
      { label: 'Ressources Humaines', to: '/hr', icon: 'ti-users-group' },
      { label: 'Comptabilité', to: '/accounting', icon: 'ti-calculator' },
      { label: 'Documents', to: '/documents', icon: 'ti-file-description' },
      { label: 'IA', to: '/ai', icon: 'ti-robot' },
    ],
  },
];

const getInitials = (user) => {
  const initials = `${user?.prenom?.[0] || ''}${user?.nom?.[0] || ''}`.trim();
  return initials || 'U';
};

const getDisplayName = (user) => {
  const name = `${user?.prenom || ''} ${user?.nom || ''}`.trim();
  return name || 'Utilisateur';
};

const formatRole = (role) => {
  if (!role) return 'Utilisateur';
  return String(role).replace(/_/g, ' ');
};

const DashboardRail = ({ user, onLogout, isSuperAdmin, isEditingName, onStartEditName, onSaveName, nameForm, onUpdateNameField, darkMode, onToggleDarkMode }) => {
  const [mobileProfileOpen, setMobileProfileOpen] = useState(false);
  const mobileProfileRef = useRef(null);

  useEffect(() => {
    const onClick = (event) => {
      if (mobileProfileRef.current && !mobileProfileRef.current.contains(event.target)) {
        setMobileProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleCommandPalette = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true }));
  };

  return (
    <aside className="dashboard-rail" aria-label="Navigation principale">
      <Link to="/" className="dashboard-rail__brand" aria-label="ERP Pro accueil">
        <span className="dashboard-rail__brand-mark" aria-hidden="true">ERP</span>
        <span className="dashboard-rail__wordmark">PRO</span>
      </Link>

      <button
        type="button"
        className="dashboard-rail__search"
        onClick={handleCommandPalette}
        title="Recherche globale (CMD+K)"
        aria-label="Recherche globale"
      >
        <i className="ti ti-search" aria-hidden="true" />
      </button>

      <nav className="dashboard-rail__nav">
        {NAV_GROUPS.map((group) => (
          <div className="dashboard-rail__group" key={group.label}>
            <span className="dashboard-rail__group-label">{group.label}</span>
            <div className="dashboard-rail__items">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/dashboard'}
                  className={({ isActive }) => (
                    `dashboard-rail__item${isActive ? ' is-active' : ''}`
                  )}
                  title={item.label}
                  aria-label={item.label}
                >
                  <i className={`ti ${item.icon}`} aria-hidden="true" />
                </NavLink>
              ))}
            </div>
          </div>
        ))}
        {isSuperAdmin && (
          <div className="dashboard-rail__group">
            <span className="dashboard-rail__group-label">Admin</span>
            <div className="dashboard-rail__items">
              <NavLink
                to="/super-admin"
                className={({ isActive }) => (
                  `dashboard-rail__item${isActive ? ' is-active' : ''}`
                )}
                title="Administration"
                aria-label="Administration"
              >
                <i className="ti ti-settings" aria-hidden="true" />
              </NavLink>
            </div>
          </div>
        )}
      </nav>

      <div className="dashboard-rail__footer">
        <div
          className="dashboard-rail__user"
          title={`${getDisplayName(user)} — ${formatRole(user?.role)}`}
        >
          <span className="dashboard-rail__avatar" aria-hidden="true">{getInitials(user)}</span>
          <span className="dashboard-rail__user-copy">
            {isEditingName ? (
              <>
                <input
                  type="text"
                  value={nameForm.prenom}
                  onChange={(e) => onUpdateNameField('prenom', e.target.value)}
                  placeholder="Prénom"
                  className="dashboard-rail__name-input"
                />
                <input
                  type="text"
                  value={nameForm.nom}
                  onChange={(e) => onUpdateNameField('nom', e.target.value)}
                  placeholder="Nom"
                  className="dashboard-rail__name-input"
                />
                <button type="button" className="dashboard-rail__save-name" onClick={onSaveName}>
                  OK
                </button>
              </>
            ) : (
              <>
                <strong>{getDisplayName(user)}</strong>
                <span>{formatRole(user?.role)}</span>
                <button type="button" className="dashboard-rail__edit-name" onClick={onStartEditName} title="Modifier mon nom" aria-label="Modifier mon nom">
                  <i className="ti ti-user-edit" aria-hidden="true" />
                </button>
              </>
            )}
          </span>
        </div>
        <div className="dashboard-rail__actions" ref={mobileProfileRef}>
          <button
            type="button"
            className="dashboard-rail__profile"
            onClick={() => setMobileProfileOpen((o) => !o)}
            aria-label="Menu profil"
            title="Menu profil"
          >
            <i className="ti ti-user" aria-hidden="true" />
          </button>
          <button
            type="button"
            className="dashboard-rail__logout"
            onClick={onLogout}
            aria-label="Se déconnecter"
            title="Se déconnecter"
          >
            <i className="ti ti-logout" aria-hidden="true" />
          </button>

          {mobileProfileOpen && (
            <div className="dashboard-rail__mobile-menu" role="menu">
              <div className="dashboard-rail__mobile-menu-header">
                <span className="dashboard-rail__avatar" aria-hidden="true">{getInitials(user)}</span>
                <div>
                  <strong>{getDisplayName(user)}</strong>
                  <span>{formatRole(user?.role)}</span>
                </div>
              </div>
              {isSuperAdmin && (
                <Link to="/super-admin/profile" className="dashboard-rail__mobile-menu-item" role="menuitem" onClick={() => setMobileProfileOpen(false)}>
                  <i className="ti ti-user" aria-hidden="true" /> Profil
                </Link>
              )}
              <button
                type="button"
                className="dashboard-rail__mobile-menu-item"
                role="menuitem"
                onClick={() => { setMobileProfileOpen(false); onToggleDarkMode?.(!darkMode); }}
              >
                <i className={`ti ti-${darkMode ? 'sun' : 'moon'}`} aria-hidden="true" />
                {darkMode ? 'Mode clair' : 'Mode sombre'}
              </button>
              <button
                type="button"
                className="dashboard-rail__mobile-menu-item dashboard-rail__mobile-menu-item--danger"
                role="menuitem"
                onClick={() => { setMobileProfileOpen(false); onLogout(); }}
              >
                <i className="ti ti-logout" aria-hidden="true" /> Se déconnecter
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default DashboardRail;
