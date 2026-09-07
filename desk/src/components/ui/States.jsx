import React from 'react';
import './ui.css';

export const EmptyState = ({ icon = 'ti-folders', title, description, action }) => (
  <div className="state-block">
    <span className="state-block__icon" aria-hidden="true"><i className={icon} /></span>
    <span className="state-block__title">{title}</span>
    {description && <span className="state-block__desc">{description}</span>}
    {action && <div className="state-block__actions">{action}</div>}
  </div>
);

export const ErrorState = ({ icon = 'ti-alert-triangle', title = 'Impossible de charger les données.', action }) => (
  <div className="state-block state-block--error">
    <span className="state-block__icon" aria-hidden="true"><i className={icon} /></span>
    <span className="state-block__title">{title}</span>
    {action && <div className="state-block__actions">{action}</div>}
  </div>
);
