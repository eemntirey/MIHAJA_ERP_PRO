import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { buildBreadcrumb, findNavItem } from './navConfig';
import { useAuth } from '../../contexts/AuthContext';
import './TopBar.css';

const CONTEXT_ACTIONS = {
  '/products': { label: 'Nouveau produit', icon: 'ti-package', to: '/products' },
  '/clients': { label: 'Nouveau client', icon: 'ti-user-plus', to: '/clients' },
  '/sales': { label: 'Nouvelle vente', icon: 'ti-shopping-cart', to: '/sales' },
  '/invoices': { label: 'Nouvelle facture', icon: 'ti-file-text', to: '/invoices' },
  '/inventory': { label: 'Entrée de stock', icon: 'ti-box', to: '/inventory' },
  '/suppliers': { label: 'Nouveau fournisseur', icon: 'ti-truck', to: '/suppliers' },
  '/purchases': { label: 'Nouvel achat', icon: 'ti-shopping-cart-plus', to: '/purchases' },
  '/accounting': { label: 'Nouvelle écriture', icon: 'ti-calculator', to: '/accounting' },
  '/documents': { label: 'Nouveau document', icon: 'ti-file-description', to: '/documents' },
  '/hr': { label: 'Nouvel employé', icon: 'ti-users-group', to: '/hr' },
  '/delivery': { label: 'Nouvelle livraison', icon: 'ti-truck-delivery', to: '/delivery' },
};

const describeNotification = (n) => {
  if (!n) return { title: 'Notification', detail: '' };
  return {
    title: n.titre || n.title || n.message || n.type || 'Alerte',
    detail: n.detail || n.description || n.montant || '',
  };
};

const TopBar = ({ counters, notifications, onOpenPalette, onToggleSidebar, collapsed, darkMode, onToggleDarkMode, onLogout }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const breadcrumb = buildBreadcrumb(location.pathname);
  const current = findNavItem(location.pathname);
  const action = current ? CONTEXT_ACTIONS[current.path] : null;

  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    const onClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const handleScrollDrag = (e) => {
    const container = scrollRef.current;
    if (!container) return;
    const startX = e.pageX - container.offsetLeft;
    const scrollLeft = container.scrollLeft;
    const handleMouseMove = (ev) => {
      const x = ev.pageX - container.offsetLeft;
      container.scrollLeft = scrollLeft - (x - startX);
    };
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      container.style.cursor = 'grab';
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    container.style.cursor = 'grabbing';
  };

  const indicators = [
    { key: 'stock', label: 'Stock critique', value: counters.stock, icon: 'ti-alert-triangle', to: '/inventory', tone: 'critical' },
    { key: 'invoices', label: 'Impayés', value: counters.invoices, icon: 'ti-file-text', to: '/invoices', tone: 'warn' },
    { key: 'sales', label: 'Ventes du jour', value: counters.salesToday, icon: 'ti-receipt', to: '/sales', tone: 'ok' },
  ].filter((i) => i.value > 0);

  return (
    <header className="desktop-topbar">
      <div className="desktop-topbar__left">
        <button
          type="button"
          className="desktop-topbar__toggle"
          onClick={onToggleSidebar}
          title={collapsed ? 'Déplier la barre' : 'Réduire la barre'}
          aria-label="Basculer la barre latérale"
        >
          <i className="ti ti-menu-2" aria-hidden="true" />
        </button>

        <nav className="desktop-breadcrumb" aria-label="Fil d'Ariane">
          {breadcrumb.map((crumb, idx) => (
            <span className="desktop-breadcrumb__item" key={idx}>
              {crumb.to && idx < breadcrumb.length - 1 ? (
                <Link to={crumb.to}>{crumb.label}</Link>
              ) : (
                <span className="desktop-breadcrumb__current">{crumb.label}</span>
              )}
              {idx < breadcrumb.length - 1 && <i className="ti ti-chevron-right" aria-hidden="true" />}
            </span>
          ))}
        </nav>
      </div>

      <div className="desktop-topbar__scroll" ref={scrollRef} onMouseDown={handleScrollDrag}>
        <button type="button" className="topbar-icon" onClick={onOpenPalette} title="Recherche globale (⌘K)" aria-label="Recherche">
          <i className="ti ti-search" aria-hidden="true" />
        </button>

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

        <div className="desktop-topbar__notif" ref={notifRef}>
          <button
            type="button"
            className="topbar-icon"
            onClick={() => setNotifOpen((o) => !o)}
            title="Notifications"
            aria-label="Notifications"
          >
            <i className="ti ti-bell" aria-hidden="true" />
            {notifications.length > 0 && <span className="topbar-icon__badge">{notifications.length}</span>}
          </button>

          {notifOpen && (
            <div className="desktop-topbar__dropdown" role="menu">
              <div className="desktop-topbar__dropdown-head">
                <strong>Notifications</strong>
                <span>{notifications.length} récente(s)</span>
              </div>
              {notifications.length === 0 ? (
                <div className="desktop-topbar__dropdown-empty">Aucune notification</div>
              ) : (
                <ul className="desktop-topbar__notif-list">
                  {notifications.map((n, i) => {
                    const { title, detail } = describeNotification(n);
                    return (
                      <li key={i} className="desktop-topbar__notif-item">
                        <i className="ti ti-alert-circle" aria-hidden="true" />
                        <span>
                          <strong>{title}</strong>
                          {detail && <small>{detail}</small>}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </div>

        {hasRole('super_admin') && (
          <button type="button" className="topbar-icon" onClick={() => navigate('/super-admin/profile')} title="Profil utilisateur" aria-label="Profil utilisateur">
            <i className="ti ti-user" aria-hidden="true" />
          </button>
        )}

        <button
          type="button"
          className="topbar-icon"
          onClick={() => onToggleDarkMode(!darkMode)}
          title={darkMode ? 'Mode clair' : 'Mode sombre'}
          aria-label={darkMode ? 'Mode clair' : 'Mode sombre'}
        >
          <i className={`ti ${darkMode ? 'ti-sun' : 'ti-moon'}`} aria-hidden="true" />
        </button>

        {action && (
          <button type="button" className="topbar-icon" onClick={() => navigate(action.to)} title={action.label} aria-label={action.label}>
            <i className={`ti ${action.icon}`} aria-hidden="true" />
          </button>
        )}

        <button type="button" className="topbar-icon" onClick={onLogout} title="Déconnexion" aria-label="Déconnexion">
          <i className="ti ti-logout" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
};

export default TopBar;
