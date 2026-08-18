// src/components/desktop/FormGrid.jsx
import React from 'react';
import './FormGrid.css';

const FormGrid = ({ children, columns = 2 }) => {
  return (
    <div className="form-grid-desktop" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {children}
    </div>
  );
};

export default FormGrid;
