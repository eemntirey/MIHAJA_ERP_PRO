import React from 'react';
import './ui.css';

const TONES = {
  success: 'status-badge--success',
  warning: 'status-badge--warning',
  danger: 'status-badge--danger',
  info: 'status-badge--info',
  neutral: 'status-badge--neutral',
};

/**
 * Badge de statut uniforme. Le statut n'est jamais indiqué par la seule
 * couleur : un point + libellé garantissent l'accessibilité.
 */
const StatusBadge = ({ tone = 'neutral', label, dot = true, icon, className = '' }) => (
  <span className={`status-badge ${TONES[tone] || TONES.neutral} ${className}`}>
    {dot && !icon && <span className="status-badge__dot" aria-hidden="true" />}
    {icon && <i className={icon} aria-hidden="true" />}
    {label}
  </span>
);

export default StatusBadge;
