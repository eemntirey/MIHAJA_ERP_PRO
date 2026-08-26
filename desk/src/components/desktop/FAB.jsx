// src/components/desktop/FAB.jsx
import React, { useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './FAB.css';

// Actions rapides contextuelles par module actif (Plan §5.3).
const MODULE_ACTIONS = {
  '/products': [
    { label: 'Nouveau produit', icon: 'ti-package', to: '/products' },
    { label: 'Entrée de stock', icon: 'ti-box', to: '/inventory' },
  ],
  '/clients': [{ label: 'Nouveau client', icon: 'ti-user-plus', to: '/clients' }],
  '/sales': [{ label: 'Nouvelle vente', icon: 'ti-shopping-cart', to: '/sales' }],
  '/invoices': [{ label: 'Nouvelle facture', icon: 'ti-file-text', to: '/invoices' }],
  '/inventory': [
    { label: 'Entrée de stock', icon: 'ti-box', to: '/inventory' },
    { label: 'Nouveau fournisseur', icon: 'ti-truck', to: '/suppliers' },
  ],
  '/suppliers': [
    { label: 'Nouveau fournisseur', icon: 'ti-truck', to: '/suppliers' },
    { label: 'Nouvel achat', icon: 'ti-shopping-cart-plus', to: '/purchases' },
  ],
  '/purchases': [{ label: 'Nouvel achat', icon: 'ti-shopping-cart-plus', to: '/purchases' }],
  '/delivery': [{ label: 'Nouvelle livraison', icon: 'ti-truck-delivery', to: '/delivery' }],
  '/accounting': [{ label: 'Nouvelle écriture', icon: 'ti-calculator', to: '/accounting' }],
  '/documents': [{ label: 'Nouveau document', icon: 'ti-file-description', to: '/documents' }],
  '/hr': [{ label: 'Nouvel employé', icon: 'ti-users-group', to: '/hr' }],
};

const DEFAULT_ACTIONS = [
  { label: 'Nouvelle vente', icon: 'ti-shopping-cart', to: '/sales' },
  { label: 'Nouveau client', icon: 'ti-user-plus', to: '/clients' },
  { label: 'Nouvelle facture', icon: 'ti-file-text', to: '/invoices' },
  { label: 'Demande de stock', icon: 'ti-box', to: '/inventory' },
];

// FAB flottant déclenchant des actions contextuelles selon le module actif.
// `actions` permet de surcharger le mapping par défaut ; `module` force le module.
const FAB = ({ actions, module: moduleProp }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  const activeModule = moduleProp || `/${location.pathname.split('/')[1] || ''}`;

  const contextualActions = useMemo(
    () => (actions && actions.length ? actions : MODULE_ACTIONS[activeModule] || DEFAULT_ACTIONS),
    [actions, activeModule]
  );

  if (!contextualActions.length) return null;

  const handle = (action) => {
    if (action.to) navigate(action.to);
    if (action.onClick) action.onClick();
    setIsOpen(false);
  };

  return (
    <div className="fab-container">
      {isOpen && (
        <div className="fab-menu" role="menu" aria-label="Actions rapides">
          {contextualActions.map((action, index) => (
            <button
              key={index}
              type="button"
              className="fab-menu-item"
              role="menuitem"
              onClick={() => handle(action)}
            >
              <i className={`ti ${action.icon}`} aria-hidden="true" />
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        className="fab-main"
        aria-expanded={isOpen}
        aria-label="Actions rapides"
        onClick={() => setIsOpen(!isOpen)}
      >
        <i className={`ti ${isOpen ? 'ti-x' : 'ti-plus'}`} aria-hidden="true" />
      </button>
    </div>
  );
};

export default FAB;
