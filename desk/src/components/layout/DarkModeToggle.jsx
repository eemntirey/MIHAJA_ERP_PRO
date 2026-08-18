// src/components/layout/DarkModeToggle.jsx
import React from 'react';
import './DarkModeToggle.css';

const DarkModeToggle = ({ enabled, onChange }) => {
  return (
    <button
      type="button"
      className={`dark-mode-toggle ${enabled ? 'active' : ''}`}
      onClick={() => onChange(!enabled)}
      aria-label={enabled ? 'Désactiver le mode sombre' : 'Activer le mode sombre'}
      title={enabled ? 'Mode clair' : 'Mode sombre'}
    >
      <span className="dark-mode-icon"><i className={`ti ${enabled ? 'ti-sun' : 'ti-moon'}`} aria-hidden="true" /></span>
      <span className="dark-mode-label">{enabled ? 'Clair' : 'Sombre'}</span>
    </button>
  );
};

export default DarkModeToggle;
