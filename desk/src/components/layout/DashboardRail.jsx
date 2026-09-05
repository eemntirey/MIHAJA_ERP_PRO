import React, { useState, useRef, useEffect } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import { NAV_ITEMS, buildNavGroups } from './navConfig';
import { filterNavGroups } from '@shared/utils/navPermissions';
import './DashboardRail.css';

// Groupes dérivés de NAV_ITEMS (navConfig) : une seule déclaration des
// permissions, filtrage RBAC centralisé via shared/utils/navPermissions.js.
const NAV_GROUPS = buildNavGroups();

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

const formatNotifTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`;
  return date.toLocaleDateString();
};

const DashboardRail = ({ user, onLogout, isSuperAdmin, isEditingName, onStartEditName, onSaveName, nameForm, onUpdateNameField, darkMode, onToggleDarkMode, counters, notifications, unreadCount, onMarkAsRead, onMarkAllAsRead }) => {
  const { hasPermission, hasAnyPermission, hasRole, getAllowedModules } = useAuth();
  const navigate = useNavigate();
  const { refresh: refreshNotifications } = useNotifications();
  const [mobileProfileOpen, setMobileProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const mobileProfileRef = useRef(null);
  const notifRef = useRef(null);
  const notifButtonRef = useRef(null);
  const notifPosition = useRef({ top: 0, left: 0 });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const allowedModules = getAllowedModules();

  // Contexte RBAC effectif : permissions réelles de l'utilisateur (rôle ENUM
  // ou rôle custom) + modules autorisés par le plan. La visibilité n'est plus
  // décidée par le nom du rôle mais par les permissions déclaratives.
  const authCtx = {
    hasPermission,
    hasAnyPermission,
    hasRole,
    allowedModules,
    isSuperAdmin: hasRole('super_admin') || hasRole('SUPER_ADMIN'),
  };

  // Groupes automatiquement masqués si aucun enfant n'est accessible.
  const filteredNavGroups = filterNavGroups(NAV_GROUPS, authCtx);

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
            if (!notifOpen) {
              // Rafraîchit la liste à chaque ouverture du box.
              refreshNotifications();
              if (notifButtonRef.current) {
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
                  const detail = n.message || n.detail || n.description || n.montant || '';
                  const time = formatNotifTime(n.created_at);
                  return (
                    <li
                      key={n.id || i}
                      className={`dashboard-rail__notif-item${!n.read ? ' is-unread' : ''}`}
                      onClick={() => {
                        onMarkAsRead(n.id);
                        // Navigue vers le module concerné si la notification a un lien.
                        if (n.link) {
                          setNotifOpen(false);
                          navigate(n.link);
                        }
                      }}
                      title={n.link ? 'Cliquer pour ouvrir' : undefined}
                    >
                      <i className="ti ti-alert-circle" aria-hidden="true" />
                      <span>
                        <strong>{title}</strong>
                        {detail && <small>{detail}</small>}
                        {time && <small>{time}</small>}
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
                    key={item.path}
                    to={item.path}
                    end={item.path === '/dashboard'}
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
                      key={item.path}
                      to={item.path}
                      end={item.path === '/dashboard'}
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
