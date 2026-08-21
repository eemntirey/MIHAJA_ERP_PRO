import React from 'react';
import './ui.css';

/**
 * En-tête de page standard (titre + description + actions).
 * Remplace le <div className="page-header"> dupliqué sur chaque page.
 */
const PageHeader = ({ title, description, icon, actions, compact = false, className = '' }) => (
  <header className={`page-header ${compact ? 'page-header--compact' : ''} ${className}`}>
    <div>
      <div className="page-header__title">
        {icon && <span className="page-header__icon" aria-hidden="true"><i className={icon} /></span>}
        <h1>{title}</h1>
      </div>
      {description && <p>{description}</p>}
    </div>
    {actions && <div className="page-header__actions">{actions}</div>}
  </header>
);

export default PageHeader;
