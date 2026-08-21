import React from 'react';
import './ui.css';

const Card = ({ title, actions, footer, children, className = '', bodyClassName = '' }) => (
  <section className={`ui-card ${className}`}>
    {(title || actions) && (
      <div className="ui-card__header">
        {title && <span className="ui-card__title">{title}</span>}
        {actions}
      </div>
    )}
    <div className={`ui-card__body ${bodyClassName}`}>{children}</div>
    {footer && <div className="ui-card__footer">{footer}</div>}
  </section>
);

export default Card;
