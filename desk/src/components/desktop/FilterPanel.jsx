// src/components/desktop/FilterPanel.jsx
import React, { useState } from 'react';
import './FilterPanel.css';

const OPERATORS = [
  { value: 'contains', label: 'Contient' },
  { value: 'equals', label: 'Égal à' },
  { value: 'not_equals', label: 'Différent de' },
  { value: 'gt', label: 'Supérieur à' },
  { value: 'lt', label: 'Inférieur à' },
  { value: 'gte', label: 'Supérieur ou égal' },
  { value: 'lte', label: 'Inférieur ou égal' },
  { value: 'starts_with', label: 'Commence par' },
  { value: 'ends_with', label: 'Finit par' },
  { value: 'is_null', label: 'Est vide' },
  { value: 'is_not_null', label: 'N\'est pas vide' },
];

const FilterPanel = ({ fields, filters, onFiltersChange, onApply, onReset }) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleAddFilter = () => {
    onFiltersChange([...filters, { field: fields[0]?.key || '', operator: 'contains', value: '' }]);
  };

  const handleRemoveFilter = (index) => {
    onFiltersChange(filters.filter((_, i) => i !== index));
  };

  const handleFilterChange = (index, field, value) => {
    const updated = [...filters];
    updated[index] = { ...updated[index], [field]: value };
    onFiltersChange(updated);
  };

  return (
    <div className="filter-panel">
      <button className="filter-panel-toggle" onClick={() => setIsOpen(!isOpen)}>
        <i className="ti ti-filter" aria-hidden="true" />
        <span>Filtres avancés</span>
        {filters.length > 0 && <span className="filter-panel-count">{filters.length}</span>}
        <i className={`ti ti-chevron-${isOpen ? 'up' : 'down'}`} aria-hidden="true" />
      </button>
      {isOpen && (
        <div className="filter-panel-body">
          {filters.map((filter, index) => (
            <div key={index} className="filter-row">
              <select
                value={filter.field}
                onChange={(e) => handleFilterChange(index, 'field', e.target.value)}
                className="form-select"
              >
                {fields.map((f) => (
                  <option key={f.key} value={f.key}>{f.label}</option>
                ))}
              </select>
              <select
                value={filter.operator}
                onChange={(e) => handleFilterChange(index, 'operator', e.target.value)}
                className="form-select"
              >
                {OPERATORS.map((op) => (
                  <option key={op.value} value={op.value}>{op.label}</option>
                ))}
              </select>
              <input
                type="text"
                value={filter.value}
                onChange={(e) => handleFilterChange(index, 'value', e.target.value)}
                placeholder="Valeur"
                className="form-input"
                disabled={filter.operator === 'is_null' || filter.operator === 'is_not_null'}
              />
              <button className="filter-remove-btn" onClick={() => handleRemoveFilter(index)}>
                <i className="ti ti-x" aria-hidden="true" />
              </button>
            </div>
          ))}
          <div className="filter-actions">
            <button className="btn-secondary" onClick={handleAddFilter}>
              <i className="ti ti-plus" aria-hidden="true" /> Ajouter
            </button>
            <div className="filter-actions-right">
              <button className="btn-secondary" onClick={onReset}>Réinitialiser</button>
              <button className="btn-primary" onClick={onApply}>Appliquer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterPanel;
