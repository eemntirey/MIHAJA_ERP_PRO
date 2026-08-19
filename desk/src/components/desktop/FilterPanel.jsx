// src/components/desktop/FilterPanel.jsx
//
// Panneau de filtres avancés connecté au `filterPresetService` :
// l'utilisateur peut enregistrer, charger, marquer par défaut et supprimer
// ses filtres personnalisés, module par module (ventes, produits, stocks…).
//
// Exemple :
//   <FilterPanel
//     module="produits"
//     fields={FILTER_FIELDS}
//     filters={filters}
//     onFiltersChange={setFilters}
//     onApply={(f) => setAppliedFilters(f)}
//     onReset={() => setAppliedFilters([])}
//   />

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { filterPresetService } from '../../services/desktopApi';
import {
  FILTER_OPERATORS,
  countActiveFilters,
  defaultOperatorForType,
  operatorRequiresValue,
  operatorsForType,
} from '../../utils/filterUtils';
import './FilterPanel.css';

const emptyFilter = (fields) => {
  const field = fields?.[0];
  return {
    field: field?.key || '',
    operator: defaultOperatorForType(field?.type),
    value: '',
  };
};

const inputTypeForField = (type) => {
  if (type === 'number') return 'number';
  if (type === 'date') return 'date';
  return 'text';
};

const FilterPanel = ({
  fields = [],
  filters = [],
  onFiltersChange,
  onApply,
  onReset,
  module,
  defaultOpen = false,
  autoLoadDefaultPreset = true,
  title = 'Filtres avancés',
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [presets, setPresets] = useState([]);
  const [presetsLoading, setPresetsLoading] = useState(false);
  const [presetError, setPresetError] = useState(null);
  const [activePresetId, setActivePresetId] = useState(null);
  const [presetName, setPresetName] = useState('');
  const [showSaveForm, setShowSaveForm] = useState(false);
  const saveInputRef = useRef(null);
  const autoLoadedRef = useRef(false);

  const activeCount = useMemo(() => countActiveFilters(filters), [filters]);

  const emitFilters = useCallback(
    (next) => {
      if (onFiltersChange) onFiltersChange(next);
    },
    [onFiltersChange]
  );

  /* ------------------------------------------------------------- presets */

  const loadPresets = useCallback(async () => {
    if (!module) return [];
    setPresetsLoading(true);
    setPresetError(null);
    try {
      const response = await filterPresetService.getAll(module);
      const list = response?.data?.presets || response?.data || [];
      const normalized = Array.isArray(list) ? list : [];
      setPresets(normalized);
      return normalized;
    } catch (err) {
      setPresetError('Impossible de charger les filtres enregistrés');
      return [];
    } finally {
      setPresetsLoading(false);
    }
  }, [module]);

  const applyPreset = useCallback(
    (preset) => {
      if (!preset) return;
      const nextFilters = Array.isArray(preset.filters) ? preset.filters.map((f) => ({ ...f })) : [];
      setActivePresetId(preset.id);
      setPresetName(preset.name || '');
      emitFilters(nextFilters);
      if (onApply) onApply(nextFilters);
      if (nextFilters.length > 0) setIsOpen(true);
    },
    [emitFilters, onApply]
  );

  // Chargement initial + application éventuelle du preset marqué par défaut.
  useEffect(() => {
    if (!module) return;
    let cancelled = false;
    autoLoadedRef.current = false;
    loadPresets().then((list) => {
      if (cancelled || !autoLoadDefaultPreset || autoLoadedRef.current) return;
      const preferred = list.find((p) => p.isDefault);
      if (preferred) {
        autoLoadedRef.current = true;
        applyPreset(preferred);
      }
    });
    return () => {
      cancelled = true;
    };
    // applyPreset dépend de callbacks parents : on ne rejoue que sur changement de module.

  }, [module, loadPresets]);

  useEffect(() => {
    if (showSaveForm && saveInputRef.current) saveInputRef.current.focus();
  }, [showSaveForm]);

  const handleSavePreset = useCallback(
    async (event) => {
      event?.preventDefault?.();
      const name = presetName.trim();
      if (!module || !name) return;
      setPresetsLoading(true);
      setPresetError(null);
      try {
        const response = await filterPresetService.save(module, { name, filters });
        const saved = response?.data?.preset;
        setPresets(response?.data?.presets || []);
        setActivePresetId(saved?.id || null);
        setShowSaveForm(false);
      } catch (err) {
        setPresetError(err?.message || "Échec de l'enregistrement du filtre");
      } finally {
        setPresetsLoading(false);
      }
    },
    [filters, module, presetName]
  );

  const handleDeletePreset = useCallback(
    async (preset) => {
      if (!module || !preset) return;
      if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
        if (!window.confirm(`Supprimer le filtre « ${preset.name} » ?`)) return;
      }
      setPresetsLoading(true);
      try {
        const response = await filterPresetService.delete(module, preset.id);
        setPresets(response?.data?.presets || []);
        if (activePresetId === preset.id) setActivePresetId(null);
      } catch (err) {
        setPresetError('Échec de la suppression du filtre');
      } finally {
        setPresetsLoading(false);
      }
    },
    [activePresetId, module]
  );

  const handleToggleDefaultPreset = useCallback(
    async (preset) => {
      if (!module || !preset) return;
      setPresetsLoading(true);
      try {
        const response = await filterPresetService.setDefault(module, preset.id);
        setPresets(response?.data?.presets || []);
      } catch (err) {
        setPresetError('Échec de la mise à jour du filtre par défaut');
      } finally {
        setPresetsLoading(false);
      }
    },
    [module]
  );

  /* ------------------------------------------------------------- filtres */

  const handleAddFilter = useCallback(() => {
    emitFilters([...filters, emptyFilter(fields)]);
    setIsOpen(true);
  }, [emitFilters, fields, filters]);

  const handleRemoveFilter = useCallback(
    (index) => {
      emitFilters(filters.filter((_, i) => i !== index));
    },
    [emitFilters, filters]
  );

  const handleFilterChange = useCallback(
    (index, patch) => {
      const updated = filters.map((filter, i) => (i === index ? { ...filter, ...patch } : filter));
      emitFilters(updated);
    },
    [emitFilters, filters]
  );

  const handleFieldChange = useCallback(
    (index, fieldKey) => {
      const field = fields.find((f) => f.key === fieldKey);
      const current = filters[index];
      const allowed = operatorsForType(field?.type).map((op) => op.value);
      const operator = allowed.includes(current?.operator) ? current.operator : defaultOperatorForType(field?.type);
      handleFilterChange(index, { field: fieldKey, operator, value: '' });
    },
    [fields, filters, handleFilterChange]
  );

  const handleApply = useCallback(() => {
    if (onApply) onApply(filters);
  }, [filters, onApply]);

  const handleReset = useCallback(() => {
    emitFilters([]);
    setActivePresetId(null);
    if (onReset) onReset();
    else if (onApply) onApply([]);
  }, [emitFilters, onApply, onReset]);

  const renderValueInput = (filter, index) => {
    const field = fields.find((f) => f.key === filter.field);
    const type = field?.type || 'text';
    const disabled = !operatorRequiresValue(filter.operator);

    if (disabled) {
      return <input type="text" className="filter-input" value="" placeholder="—" disabled readOnly />;
    }

    if (type === 'boolean') {
      return (
        <select
          className="filter-select filter-value"
          value={filter.value ?? ''}
          onChange={(event) => handleFilterChange(index, { value: event.target.value })}
        >
          <option value="">—</option>
          <option value="true">Oui</option>
          <option value="false">Non</option>
        </select>
      );
    }

    if (Array.isArray(field?.options) && field.options.length > 0) {
      return (
        <select
          className="filter-select filter-value"
          value={filter.value ?? ''}
          onChange={(event) => handleFilterChange(index, { value: event.target.value })}
        >
          <option value="">—</option>
          {field.options.map((option) => {
            const value = typeof option === 'object' ? option.value : option;
            const label = typeof option === 'object' ? option.label : option;
            return (
              <option key={String(value)} value={value}>
                {label}
              </option>
            );
          })}
        </select>
      );
    }

    return (
      <input
        type={inputTypeForField(type)}
        className="filter-input filter-value"
        value={filter.value ?? ''}
        placeholder={field?.placeholder || 'Valeur'}
        step={type === 'number' ? 'any' : undefined}
        onChange={(event) => handleFilterChange(index, { value: event.target.value })}
      />
    );
  };

  return (
    <div className="filter-panel">
      <div className="filter-panel-head">
        <button
          type="button"
          className="filter-panel-toggle"
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
        >
          <i className="ti ti-filter" aria-hidden="true" />
          <span>{title}</span>
          {activeCount > 0 && <span className="filter-panel-count">{activeCount}</span>}
          <i className={`ti ti-chevron-${isOpen ? 'up' : 'down'}`} aria-hidden="true" />
        </button>

        {module && presets.length > 0 && (
          <div className="filter-preset-chips" role="group" aria-label="Filtres enregistrés">
            {presets.map((preset) => (
              <span
                key={preset.id}
                className={`filter-preset-chip${activePresetId === preset.id ? ' is-active' : ''}`}
              >
                <button
                  type="button"
                  className="filter-preset-chip-label"
                  onClick={() => applyPreset(preset)}
                  title={`Charger « ${preset.name} » (${preset.filters?.length || 0} critère(s))`}
                >
                  {preset.isDefault && <i className="ti ti-star-filled" aria-hidden="true" />}
                  {preset.name}
                </button>
                <button
                  type="button"
                  className="filter-preset-chip-action"
                  onClick={() => handleToggleDefaultPreset(preset)}
                  title={preset.isDefault ? 'Retirer des filtres par défaut' : 'Définir par défaut'}
                  aria-label={preset.isDefault ? 'Retirer des filtres par défaut' : 'Définir par défaut'}
                >
                  <i className={`ti ti-${preset.isDefault ? 'star-off' : 'star'}`} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="filter-preset-chip-action is-danger"
                  onClick={() => handleDeletePreset(preset)}
                  title={`Supprimer « ${preset.name} »`}
                  aria-label={`Supprimer le filtre ${preset.name}`}
                >
                  <i className="ti ti-x" aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {isOpen && (
        <div className="filter-panel-body">
          {presetError && <div className="filter-panel-error">{presetError}</div>}

          {filters.length === 0 && (
            <p className="filter-panel-empty">
              Aucun critère. Ajoutez un critère ou chargez un filtre enregistré.
            </p>
          )}

          {filters.map((filter, index) => {
            const field = fields.find((f) => f.key === filter.field);
            const availableOperators = operatorsForType(field?.type);
            return (
              <div key={index} className="filter-row">
                <span className="filter-row-prefix">{index === 0 ? 'Où' : 'Et'}</span>
                <select
                  className="filter-select"
                  value={filter.field || ''}
                  onChange={(event) => handleFieldChange(index, event.target.value)}
                  aria-label="Champ"
                >
                  {fields.map((f) => (
                    <option key={f.key} value={f.key}>
                      {f.label}
                    </option>
                  ))}
                </select>
                <select
                  className="filter-select"
                  value={filter.operator || ''}
                  onChange={(event) => handleFilterChange(index, { operator: event.target.value })}
                  aria-label="Opérateur"
                >
                  {availableOperators.map((op) => (
                    <option key={op.value} value={op.value}>
                      {op.label}
                    </option>
                  ))}
                </select>
                {renderValueInput(filter, index)}
                <button
                  type="button"
                  className="filter-remove-btn"
                  onClick={() => handleRemoveFilter(index)}
                  title="Retirer ce critère"
                  aria-label="Retirer ce critère"
                >
                  <i className="ti ti-x" aria-hidden="true" />
                </button>
              </div>
            );
          })}

          <div className="filter-actions">
            <div className="filter-actions-left">
              <button type="button" className="btn-secondary" onClick={handleAddFilter}>
                <i className="ti ti-plus" aria-hidden="true" /> Ajouter un critère
              </button>
              {module && (
                showSaveForm ? (
                  <form className="filter-save-form" onSubmit={handleSavePreset}>
                    <input
                      ref={saveInputRef}
                      type="text"
                      className="filter-input"
                      value={presetName}
                      placeholder="Nom du filtre"
                      onChange={(event) => setPresetName(event.target.value)}
                      aria-label="Nom du filtre"
                    />
                    <button type="submit" className="btn-primary" disabled={!presetName.trim() || presetsLoading}>
                      Enregistrer
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => setShowSaveForm(false)}>
                      Annuler
                    </button>
                  </form>
                ) : (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowSaveForm(true)}
                    disabled={filters.length === 0}
                    title="Enregistrer les critères courants comme filtre réutilisable"
                  >
                    <i className="ti ti-bookmark" aria-hidden="true" /> Enregistrer le filtre
                  </button>
                )
              )}
            </div>
            <div className="filter-actions-right">
              <button type="button" className="btn-secondary" onClick={handleReset}>
                Réinitialiser
              </button>
              <button type="button" className="btn-primary" onClick={handleApply}>
                Appliquer{activeCount > 0 ? ` (${activeCount})` : ''}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export { FILTER_OPERATORS };
export default FilterPanel;
