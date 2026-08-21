// desk/src/components/layout/ThemeToggle.jsx
// Bouton de bascule instantanée Light / Dark.
//
// Aucune couleur hexadécimale ou RGB n'est codée en dur dans le JSX.
// Toutes les couleurs proviennent de variables CSS sémantiques du design
// system (définies dans index.css → :root / .dark) ou de classes Tailwind
// sémantiques (bg-background, text-foreground, …).
//
import React from 'react';
import './ThemeToggle.css';

/**
 * @param {Object} props
 * @param {boolean} props.enabled   — true = mode sombre actif.
 * @param {(next: boolean) => void} props.onChange
 * @param {boolean} [props.label=true]      — afficher le libellé "Clair"/"Sombre".
 * @param {boolean} [props.compact=false]   — variante icône uniquement.
 * @param {boolean} [props.menuItem=false]  — style adapté aux menus contextuels.
 * @param {string}  [props.className]       — classes additionnelles.
 * @param {function} [props.onClick]        — callback additionnel (ex: fermer un menu).
 */
const ThemeToggle = ({
  enabled,
  onChange,
  label = true,
  compact = false,
  menuItem = false,
  className = '',
  onClick,
}) => {
  const dark = Boolean(enabled);

  const handleClick = (e) => {
    if (typeof onChange === 'function') {
      onChange(!dark);
    }
    if (typeof onClick === 'function') {
      onClick(e);
    }
  };

  const baseClass = 'theme-toggle';
  const variantClass = compact
    ? 'theme-toggle--compact'
    : menuItem
      ? 'theme-toggle--menuitem'
      : '';
  const stateClass = dark ? 'theme-toggle--dark' : 'theme-toggle--light';

  return (
    <button
      type="button"
      className={`${baseClass} ${variantClass} ${stateClass} ${className}`.trim()}
      onClick={handleClick}
      aria-label={dark ? 'Passer au mode clair' : 'Passer au mode sombre'}
      title={dark ? 'Mode clair' : 'Mode sombre'}
    >
      <span className="theme-toggle__icon" aria-hidden="true">
        <i className={`ti ${dark ? 'ti-sun' : 'ti-moon'}`} />
      </span>
      {label && <span className="theme-toggle__label">{dark ? 'Clair' : 'Sombre'}</span>}
    </button>
  );
};

export default ThemeToggle;
