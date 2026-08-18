import React, { useState, useEffect, useRef } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { NAV_ITEMS, NAV_GROUPS } from './navConfig';
import './DesktopSidebar.css';

const FAVORITES_KEY = 'desktop_favorites';
const MAX_FAVORITES = 6;

const getInitials = (user) =>
  `${user?.prenom?.[0] || ''}${user?.nom?.[0] || ''}`.trim() || 'U';

const getDisplayName = (user) =>
  `${user?.prenom || ''} ${user?.nom || ''}`.trim() || 'Utilisateur';

const formatRole = (role) => (role ? String(role).replace(/_/g, ' ') : 'Utilisateur');

const readFavorites = () => {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const DesktopSidebar = ({
  collapsed,
  counters,
  onToggleCollapse,
  onOpenPalette,
  onLogout,
  darkMode,
  onToggleDarkMode,
}) => {
  const { user, hasRole } = useAuth();
  const location = useLocation();
  const isSuperAdmin = hasRole('SUPER_ADMIN');

  const [favorites, setFavorites] = useState(readFavorites);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
    } catch {
      // ignore
    }
  }, [favorites]);

  useEffect(() => {
    const onClick = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const toggleFavorite = (path) => {
    setFavorites((prev) => {
      if (prev.includes(path)) return prev.filter((p) => p !== path);
      if (prev.length >= MAX_FAVORITES) return prev;
      return [...prev, path];
    });
  };

  const badgeValue = (item) => {
    if (!item.badge) return null;
    if (item.badge === 'sales') return counters.sales;
    if (item.badge === 'stock') return counters.stock;
    if (item.badge === 'invoices') return counters.invoices;
    return null;
  };

  const favoriteItems = NAV_ITEMS.filter((item) => favorites.includes(item.path));
  const visibleGroups = NAV_GROUPS.filter((g) =>
    NAV_ITEMS.some((i) => i.group === g && (g !== 'Admin' || isSuperAdmin))
  );

  const renderNavItem = (item) => {
    const badge = badgeValue(item);
    const isFav = favorites.includes(item.path);
    return (
      <div className="desktop-sidebar__row" key={item.path}>
        <NavLink
          to={item.path}
          end={item.path === '/dashboard'}
          className={({ isActive }) =>
            `desktop-sidebar__item${isActive ? ' is-active' : ''}`
          }
          title={collapsed ? item.label : undefined}
        >
          <i className={`ti ${item.icon}`} aria-hidden="true" />
          {!collapsed && <span className="desktop-sidebar__label">{item.label}</span>}
          {!collapsed && badge > 0 && <span className="desktop-sidebar__badge">{badge}</span>}
          {collapsed && badge > 0 && <span className="desktop-sidebar__badge desktop-sidebar__badge--dot" />}
        </NavLink>
        {!collapsed && (
          <button
            type="button"
            className={`desktop-sidebar__star${isFav ? ' is-active' : ''}`}
            onClick={() => toggleFavorite(item.path)}
            title={isFav ? 'Retirer des favoris' : 'Épingler aux favoris'}
            aria-label={isFav ? 'Retirer des favoris' : 'Épingler aux favoris'}
          >
            <i className="ti ti-star" aria-hidden="true" />
          </button>
        )}
      </div>
    );
  };

  return (
    <aside className={`desktop-sidebar${collapsed ? ' collapsed' : ''}`} aria-label="Navigation principale">
      <div className="desktop-sidebar__header">
        <Link to="/" className="desktop-sidebar__brand" aria-label="ERP Pro accueil">
          <span className="desktop-sidebar__brand-mark" aria-hidden="true">ERP</span>
          {!collapsed && <span className="desktop-sidebar__wordmark">PRO</span>}
        </Link>
        <button
          type="button"
          className="desktop-sidebar__collapse"
          onClick={onToggleCollapse}
          title={collapsed ? 'Déplier la barre' : 'Réduire la barre'}
          aria-label={collapsed ? 'Déplier la barre' : 'Réduire la barre'}
        >
          <i className={`ti ti-${collapsed ? 'chevrons-right' : 'chevrons-left'}`} aria-hidden="true" />
        </button>
      </div>

      {!collapsed && (
        <button type="button" className="desktop-sidebar__search" onClick={onOpenPalette}>
          <i className="ti ti-search" aria-hidden="true" />
          <span>Rechercher…</span>
          <kbd>⌘K</kbd>
        </button>
      )}

      <div className="desktop-sidebar__scroll">
        {!collapsed && favoriteItems.length > 0 && (
          <div className="desktop-sidebar__group">
            <span className="desktop-sidebar__group-label">
              <i className="ti ti-pin" aria-hidden="true" /> Favoris
            </span>
            <div className="desktop-sidebar__items">
              {favoriteItems.map(renderNavItem)}
            </div>
          </div>
        )}

        {visibleGroups.map((group) => (
          <div className="desktop-sidebar__group" key={group}>
            {!collapsed && <span className="desktop-sidebar__group-label">{group}</span>}
            <div className="desktop-sidebar__items">
              {NAV_ITEMS.filter(
                (item) => item.group === group && (group !== 'Admin' || isSuperAdmin)
              ).map(renderNavItem)}
            </div>
          </div>
        ))}
      </div>

      <div className="desktop-sidebar__footer" ref={profileRef}>
        <button
          type="button"
          className="desktop-sidebar__profile"
          onClick={() => setProfileOpen((o) => !o)}
          title={`${getDisplayName(user)} — ${formatRole(user?.role)}`}
        >
          <span className="desktop-sidebar__avatar" aria-hidden="true">{getInitials(user)}</span>
          {!collapsed && (
            <span className="desktop-sidebar__profile-copy">
              <strong>{getDisplayName(user)}</strong>
              <span>{formatRole(user?.role)}</span>
            </span>
          )}
          {!collapsed && <i className="ti ti-chevron-up" aria-hidden="true" />}
        </button>

        {profileOpen && (
          <div className="desktop-sidebar__menu" role="menu">
            {isSuperAdmin && (
              <Link to="/super-admin/profile" className="desktop-sidebar__menu-item" role="menuitem" onClick={() => setProfileOpen(false)}>
                <i className="ti ti-user" aria-hidden="true" /> Profil
              </Link>
            )}
            <button
              type="button"
              className="desktop-sidebar__menu-item"
              role="menuitem"
              onClick={() => { setProfileOpen(false); onToggleDarkMode(!darkMode); }}
            >
              <i className={`ti ti-${darkMode ? 'sun' : 'moon'}`} aria-hidden="true" />
              {darkMode ? 'Mode clair' : 'Mode sombre'}
            </button>
            <button
              type="button"
              className="desktop-sidebar__menu-item desktop-sidebar__menu-item--danger"
              role="menuitem"
              onClick={onLogout}
            >
              <i className="ti ti-logout" aria-hidden="true" /> Se déconnecter
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};

export default DesktopSidebar;
