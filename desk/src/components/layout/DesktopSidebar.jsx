import React, { useState, useEffect, useRef } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { favoriteService } from '../../services/desktopApi';
import { NAV_ITEMS, NAV_GROUPS } from './navConfig';
import ThemeToggle from './ThemeToggle';
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
    if (!Array.isArray(parsed)) return [];
    return parsed.map((item) => (typeof item === 'string' ? { path: item } : item));
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
  className,
}) => {
  const { user, hasRole, getAllowedModules } = useAuth();
  const location = useLocation();
  const isSuperAdmin = hasRole('SUPER_ADMIN');
  const isAdminPrincipal = hasRole('admin') || hasRole('super_admin');
  const allowedModules = getAllowedModules();

  const hasAccountingAccess = hasRole('super_admin') || hasRole('admin') || hasRole('manager') || hasRole('accountant');

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

  useEffect(() => {
    let active = true;
    favoriteService.getAll().then((res) => {
      if (!active) return;
      const items = Array.isArray(res.data) ? res.data : [];
      const normalized = items
        .map((item) => ({ id: item.id, path: item.path || item.to }))
        .filter((item) => item.path)
        .slice(0, MAX_FAVORITES);
      setFavorites(normalized);
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  const toggleFavorite = async (path) => {
    setFavorites((prev) => {
      const exists = prev.find((f) => f.path === path);
      if (exists) {
        favoriteService.remove(exists.id).catch(() => {});
        return prev.filter((f) => f.path !== path);
      }
      if (prev.length >= MAX_FAVORITES) return prev;
      const navItem = NAV_ITEMS.find((i) => i.path === path);
      const newItem = { path, label: navItem?.label };
      favoriteService.add(newItem).then((res) => {
        const saved = res.data || newItem;
        setFavorites((p) => {
          if (p.some((f) => f.path === saved.path)) return p;
          return [...p, saved].slice(0, MAX_FAVORITES);
        });
      }).catch(() => {});
      return [...prev, newItem];
    });
  };

  const badgeValue = (item) => {
    if (!item.badge) return null;
    if (item.badge === 'sales') return counters.sales;
    if (item.badge === 'stock') return counters.stock;
    if (item.badge === 'invoices') return counters.invoices;
    return null;
  };

  const favoriteItems = NAV_ITEMS.filter((item) => favorites.some((f) => f.path === item.path));
  const visibleGroups = NAV_GROUPS.filter((g) =>
    NAV_ITEMS.some((i) => i.group === g)
  );

  const renderNavItem = (item) => {
    if (item.path === '/accounting' && !hasAccountingAccess) return null;
    if ((item.path === '/super-admin' || item.path === '/users' || item.path === '/roles' || item.path === '/permissions') && !isSuperAdmin) return null;
    if (!isSuperAdmin && item.module && allowedModules !== null && !allowedModules.includes(item.module)) return null;
    const badge = badgeValue(item);
    const isFav = favorites.some((f) => f.path === item.path);
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
    <aside className={`desktop-sidebar${collapsed ? ' collapsed' : ''} ${className || ''}`} aria-label="Navigation principale">
      <div className="desktop-sidebar__header">
        <Link to="/dashboard" className="desktop-sidebar__brand" aria-label="ERP Pro accueil">
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
                (item) => item.group === group
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
            {isAdminPrincipal && (
              <Link to="/subscription" className="desktop-sidebar__menu-item" role="menuitem" onClick={() => setProfileOpen(false)}>
                <i className="ti ti-credit-card" aria-hidden="true" /> Abonnement
              </Link>
            )}
            <ThemeToggle
              enabled={darkMode}
              onChange={onToggleDarkMode}
              menuItem
              className="desktop-sidebar__menu-item"
              onClick={() => setProfileOpen(false)}
            />
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
