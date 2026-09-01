import React, { useState, useRef, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './DashboardRail.css';

const NAV_GROUPS = [
  {
    label: 'Piloter',
    items: [
      { label: 'Tableau de bord', to: '/dashboard', icon: 'ti-layout-dashboard', module: 'dashboard' },
      { label: 'Produits', to: '/products', icon: 'ti-package', module: 'produits', badge: 'products' },
      { label: 'Clients', to: '/clients', icon: 'ti-users', module: 'clients' },
      { label: 'Ventes', to: '/sales', icon: 'ti-shopping-cart', module: 'ventes', badge: 'sales' },
      { label: 'Factures', to: '/invoices', icon: 'ti-file-text', module: 'factures', badge: 'invoices' },
      { label: 'Paiements', to: '/payments', icon: 'ti-credit-card', module: 'paiements' },
    ],
  },
  {
    label: 'Opérations',
    items: [
      { label: 'Stock', to: '/inventory', icon: 'ti-box', module: 'stocks', badge: 'stock' },
      { label: 'Fournisseurs', to: '/suppliers', icon: 'ti-truck' },
      { label: 'Achats', to: '/purchases', icon: 'ti-shopping-cart-plus', module: 'achats' },
      { label: 'Livraisons', to: '/delivery', icon: 'ti-truck-delivery', module: 'livraison' },
    ],
  },
  {
    label: 'Gestion',
    items: [
      { label: 'Ressources Humaines', to: '/hr', icon: 'ti-users-group', module: 'rh' },
      { label: 'Comptabilité', to: '/accounting', icon: 'ti-calculator', module: 'comptabilite' },
      { label: 'Documents', to: '/documents', icon: 'ti-file-description', module: 'documents' },
      { label: 'IA', to: '/ai', icon: 'ti-robot', module: 'ia' },
    ],
  },
  {
    label: 'Admin',
    items: [
      { label: 'Administration', to: '/super-admin', icon: 'ti-settings' },
      { label: 'Utilisateurs', to: '/users', icon: 'ti-users' },
      { label: 'Rôles', to: '/roles', icon: 'ti-user-cog' },
      { label: 'Permissions', to: '/permissions', icon: 'ti-key' },
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

const DashboardRail = ({ user, onLogout, isSuperAdmin, isEditingName, onStartEditName, onSaveName, nameForm, onUpdateNameField, darkMode, onToggleDarkMode, counters, notifications, unreadCount, onMarkAsRead, onMarkAllAsRead }) => {
  const { hasRole, getAllowedModules } = useAuth();
  const [mobileProfileOpen, setMobileProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const mobileProfileRef = useRef(null);
  const notifRef = useRef(null);
  const notifButtonRef = useRef(null);
  const notifPosition = useRef({ top: 0, left: 0 });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const hasAccountingAccess = hasRole('super_admin') || hasRole('admin') || hasRole('manager') || hasRole('accountant');
  const allowedModules = getAllowedModules();
  const isAdmin = hasRole('super_admin') || hasRole('admin');

  const filteredNavGroups = NAV_GROUPS.map(group => ({
    ...group,
    items: group.items.filter(item => {
      if (item.to === '/accounting') return hasAccountingAccess;
      if (item.to === '/super-admin') return hasRole('super_admin');
      if (item.to === '/users' || item.to === '/roles' || item.to === '/permissions') return isAdmin;
      if (!isSuperAdmin && item.module && allowedModules !== null && !allowedModules.includes(item.module)) return false;
      return true;
    })
  })).filter(group => group.items.length > 0);

  const badgeValue = (item) => {
    if (!item.badge || !counters) return null;
    if (item.badge === 'sales') return counters.sales;
    if (item.badge === 'stock') return counters.stock;
    if (item.badge === 'invoices') return counters.invoices;
    if (item.badge === 'products') return counters.products;
    return null;
  };

  useEffect(() => {
    const onClick = (event) => {
      if (mobileProfileRef.current && !mobileProfileRef.current.contains(event.target)) {
        setMobileProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleCommandPalette = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true }));
  };

  // Close mobile nav on Escape + lock body scroll
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setMobileNavOpen(false);
    };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [mobileNavOpen]);

  return (
    <>
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

      <div className="dashboard-rail__notif-wrapper" ref={notifRef}>
        <button
          ref={notifButtonRef}
          type="button"
          className="dashboard-rail__notif"
          onClick={() => {
            if (!notifOpen && notifButtonRef.current) {
              const rect = notifButtonRef.current.getBoundingClientRect();
              const dropdownWidth = window.innerWidth <= 760 ? Math.min(window.innerWidth - 32, 300) : 300;
              let left = rect.left;
              if (left + dropdownWidth > window.innerWidth - 8) {
                left = window.innerWidth - dropdownWidth - 8;
              }
              left = Math.max(8, left);
              notifPosition.current = {
                top: rect.bottom + 10,
                left,
              };
            }
            setNotifOpen((o) => !o);
          }}
          title="Notifications"
          aria-label={`${unreadCount > 0 ? unreadCount : notifications.length} notifications`}
        >
          <i className="ti ti-bell" aria-hidden="true" />
          {(unreadCount > 0 || notifications.length > 0) && (
            <span className="dashboard-rail__notif-count">{unreadCount > 0 ? (unreadCount > 99 ? '99+' : unreadCount) : (notifications.length > 99 ? '99+' : notifications.length)}</span>
          )}
        </button>
        {notifOpen && (
          <div className="dashboard-rail__notif-dropdown" role="menu" style={{ position: 'fixed', top: notifPosition.current.top, left: notifPosition.current.left, width: window.innerWidth <= 760 ? 'calc(100vw - 32px)' : '300px', maxWidth: '300px' }}>
            <div className="dashboard-rail__notif-dropdown-head">
              <strong>Notifications</strong>
              {unreadCount > 0 && (
                <button
                  type="button"
                  className="dashboard-rail__notif-action"
                  onClick={(e) => { e.stopPropagation(); onMarkAllAsRead(); }}
                >
                  Tout marquer comme lu
                </button>
              )}
            </div>
            {notifications.length === 0 ? (
              <div className="dashboard-rail__notif-empty">Aucune notification</div>
            ) : (
              <ul className="dashboard-rail__notif-list">
                {notifications.map((n, i) => {
                  const title = n.titre || n.title || n.message || n.type || 'Alerte';
                  const detail = n.detail || n.description || n.montant || '';
                  return (
                    <li
                      key={n.id || i}
                      className={`dashboard-rail__notif-item${!n.read ? ' is-unread' : ''}`}
                      onClick={() => onMarkAsRead(n.id)}
                    >
                      <i className="ti ti-alert-circle" aria-hidden="true" />
                      <span>
                        <strong>{title}</strong>
                        {detail && <small>{detail}</small>}
                      </span>
                      {!n.read && <span className="dashboard-rail__notif-dot" />}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>

      <button
        type="button"
        className="dashboard-rail__menu-btn"
        onClick={() => setMobileNavOpen(true)}
        title="Menu des modules"
        aria-label="Menu des modules"
        aria-expanded={mobileNavOpen}
      >
        <i className="ti ti-menu" aria-hidden="true" />
      </button>

      <nav className="dashboard-rail__nav">
        {filteredNavGroups.map((group) => (
          <div className="dashboard-rail__group" key={group.label}>
            <span className="dashboard-rail__group-label">{group.label}</span>
            <div className="dashboard-rail__items">
              {group.items.map((item) => {
                const badge = badgeValue(item);
                return (
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
                    {badge > 0 && <span className="dashboard-rail__badge">{badge > 99 ? '99+' : badge}</span>}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
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
              <Link to="/subscription" className="dashboard-rail__mobile-menu-item" role="menuitem" onClick={() => setMobileProfileOpen(false)}>
                <i className="ti ti-credit-card" aria-hidden="true" /> Abonnement
              </Link>
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

    {/* Mobile navigation overlay: full module list with labels */}
    <div
      className={`dashboard-rail__mobile-nav-overlay${mobileNavOpen ? ' is-open' : ''}`}
      role="presentation"
      onClick={() => setMobileNavOpen(false)}
    >
      <nav
        className="dashboard-rail__mobile-nav"
        onClick={(e) => e.stopPropagation()}
        aria-label="Menu des modules"
      >
        <div className="dashboard-rail__mobile-nav-header">
          <span className="dashboard-rail__mobile-nav-title">Modules</span>
          <button
            type="button"
            className="dashboard-rail__mobile-nav-close"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Fermer le menu"
          >
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>
        <div className="dashboard-rail__mobile-nav-groups">
          {filteredNavGroups.map((group) => (
            <div className="dashboard-rail__mobile-nav-group" key={group.label}>
              <div className="dashboard-rail__mobile-nav-group-label">{group.label}</div>
              <div className="dashboard-rail__mobile-nav-items">
                {group.items.map((item) => {
                  const badge = badgeValue(item);
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === '/dashboard'}
                      className={({ isActive }) =>
                        `dashboard-rail__mobile-nav-item${isActive ? ' is-active' : ''}`
                      }
                      onClick={() => setMobileNavOpen(false)}
                      aria-label={item.label}
                    >
                      <i className={`ti ${item.icon}`} aria-hidden="true" />
                      <span>{item.label}</span>
                      {badge > 0 && (
                        <span className="dashboard-rail__mobile-nav-badge">
                          {badge > 99 ? '99+' : badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="dashboard-rail__mobile-nav-footer">
          <button
            type="button"
            className="dashboard-rail__mobile-nav-item dashboard-rail__mobile-nav-item--footer"
            onClick={() => { setMobileNavOpen(false); onToggleDarkMode?.(!darkMode); }}
          >
            <i className={`ti ti-${darkMode ? 'sun' : 'moon'}`} aria-hidden="true" />
            <span>{darkMode ? 'Mode clair' : 'Mode sombre'}</span>
          </button>
          <button
            type="button"
            className="dashboard-rail__mobile-nav-item dashboard-rail__mobile-nav-item--footer dashboard-rail__mobile-nav-item--danger"
            onClick={() => { setMobileNavOpen(false); onLogout(); }}
          >
            <i className="ti ti-logout" aria-hidden="true" />
            <span>Se déconnecter</span>
          </button>
        </div>
      </nav>
    </div>

    </>
  );
};

export default DashboardRail;
