// src/components/layout/Breadcrumbs.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { buildBreadcrumb } from './navConfig';
import { useAuth } from '../../contexts/AuthContext';
import './Breadcrumbs.css';

// Fil d'Ariane dynamique synchronisé avec l'URL courante (Plan §4.3).
// La racine pointe vers le dashboard si authentifié, vers la connexion sinon.
const Breadcrumbs = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const crumbs = buildBreadcrumb(location.pathname, isAuthenticated);

  if (!crumbs.length) return null;

  return (
    <nav className="desktop-breadcrumb" aria-label="Fil d'Ariane">
      {crumbs.map((crumb, idx) => {
        const isLast = idx === crumbs.length - 1;
        return (
          <span className="desktop-breadcrumb__item" key={`${crumb.label}-${idx}`}>
            {crumb.to && !isLast ? (
              <Link to={crumb.to}>{crumb.label}</Link>
            ) : (
              <span
                className={isLast ? 'desktop-breadcrumb__current' : undefined}
                aria-current={isLast ? 'page' : undefined}
              >
                {crumb.label}
              </span>
            )}
            {!isLast && <i className="ti ti-chevron-right" aria-hidden="true" />}
          </span>
        );
      })}
    </nav>
  );
};

export default Breadcrumbs;
