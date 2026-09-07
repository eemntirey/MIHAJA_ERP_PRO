import React from 'react';
import './ui.css';

const VARIANTS = {
  primary: 'btn--primary',
  secondary: 'btn--secondary',
  ghost: 'btn--ghost',
  danger: 'btn--danger',
  success: 'btn--success',
};

/**
 * Bouton cohérent (variantes Primary / Secondary / Ghost / Danger / Success).
 * `loading` affiche un spinner et désactive le bouton.
 */
const Button = ({
  variant = 'primary',
  size,
  icon,
  iconOnly = false,
  block = false,
  loading = false,
  type = 'button',
  className = '',
  children,
  disabled,
  ...rest
}) => {
  const classes = [
    'btn',
    VARIANTS[variant] || VARIANTS.primary,
    size === 'sm' && 'btn--sm',
    size === 'lg' && 'btn--lg',
    iconOnly && 'btn--icon',
    block && 'btn--block',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading ? <span className="btn__spinner" aria-hidden="true" /> : icon && <i className={icon} aria-hidden="true" />}
      {!iconOnly && children}
    </button>
  );
};

export default Button;
