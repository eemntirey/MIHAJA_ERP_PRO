// src/components/desktop/FAB.jsx
import React, { useState } from 'react';
import './FAB.css';

const FAB = ({ actions }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fab-container">
      {isOpen && (
        <div className="fab-menu">
          {actions.map((action, index) => (
            <button
              key={index}
              className="fab-menu-item"
              onClick={() => {
                action.onClick();
                setIsOpen(false);
              }}
            >
              <i className={`ti ${action.icon}`} aria-hidden="true" />
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}
      <button className="fab-main" onClick={() => setIsOpen(!isOpen)} aria-label="Actions rapides">
        <i className={`ti ${isOpen ? 'ti-x' : 'ti-plus'}`} aria-hidden="true" />
      </button>
    </div>
  );
};

export default FAB;
