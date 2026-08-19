// src/components/desktop/__tests__/FilterPanel.test.jsx
import React, { useState } from 'react';
import FilterPanel from '../FilterPanel';
import { filterPresetService } from '../../../services/desktopApi';
import { setupVirtualEnvironment, mountComponent, clickNode, changeInput, submitForm, act } from '../../../test-helpers/renderDom';

setupVirtualEnvironment();

const FIELDS = [
  { key: 'name', label: 'Nom', type: 'text' },
  { key: 'price', label: 'Prix', type: 'number' },
];

const flush = async () => {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
};

const Harness = ({ initialFilters = [], onApply, onFiltersChange }) => {
  const [filters, setFilters] = useState(initialFilters);
  return (
    <FilterPanel
      module="produits"
      fields={FIELDS}
      filters={filters}
      onFiltersChange={onFiltersChange || setFilters}
      onApply={onApply}
    />
  );
};

beforeEach(() => {
  localStorage.clear();
  window.confirm = () => true;
});

describe('FilterPanel — presets', () => {
  test('enregistre un preset puis le recharge depuis le service', async () => {
    let applied = null;
    const { container } = mountComponent(
      <Harness initialFilters={[{ field: 'name', operator: 'contains', value: 'abc' }]} onApply={(f) => { applied = f; }} />
    );

    clickNode(container.querySelector('.filter-panel-toggle'));
    clickNode(Array.from(container.querySelectorAll('button')).find((b) => b.textContent.includes('Enregistrer le filtre')));
    changeInput(container.querySelector('.filter-save-form input'), 'Mon filtre');
    submitForm(container.querySelector('.filter-save-form'));

    await flush();

    const stored = await filterPresetService.getAll('produits');
    expect(stored.data.presets.length).toBe(1);
    expect(stored.data.presets[0].name).toBe('Mon filtre');

    // Le chip apparaît et l'application recharge les critères.
    expect(container.querySelectorAll('.filter-preset-chip').length).toBe(1);
    clickNode(container.querySelector('.filter-preset-chip-label'));
    expect(applied).not.toBeNull();
    expect(applied[0].field).toBe('name');
  });

  test('supprime un preset (confirmation acceptée)', async () => {
    await filterPresetService.save('produits', { name: 'A', filters: [{ field: 'name', operator: 'contains', value: 'x' }] });
    const { container } = mountComponent(<Harness />);
    await flush();
    expect(container.querySelectorAll('.filter-preset-chip').length).toBe(1);

    clickNode(container.querySelector('.filter-preset-chip-action.is-danger'));
    await flush();
    expect(container.querySelectorAll('.filter-preset-chip').length).toBe(0);
    const stored = await filterPresetService.getAll('produits');
    expect(stored.data.presets.length).toBe(0);
  });

  test('marque un preset par défaut (étoile)', async () => {
    await filterPresetService.save('produits', { name: 'Def', filters: [{ field: 'name', operator: 'contains', value: 'x' }] });
    const { container } = mountComponent(<Harness />);
    await flush();
    clickNode(container.querySelector('.filter-preset-chip-action:not(.is-danger)'));
    await flush();
    const stored = await filterPresetService.getAll('produits');
    expect(stored.data.presets[0].isDefault).toBe(true);
  });
});

describe('FilterPanel — critères', () => {
  test('ajout et retrait de critères', () => {
    const onFiltersChange = jest.fn();
    const { container } = mountComponent(<Harness onFiltersChange={onFiltersChange} />);
    clickNode(container.querySelector('.filter-panel-toggle'));
    clickNode(Array.from(container.querySelectorAll('button')).find((b) => b.textContent.includes('Ajouter un critère')));
    expect(onFiltersChange).toHaveBeenCalled();
    expect(onFiltersChange.mock.calls.at(-1)[0].length).toBe(1);
  });

  test('saisir une valeur émet le filtre mis à jour', () => {
    const onFiltersChange = jest.fn();
    const { container } = mountComponent(
      <Harness initialFilters={[{ field: 'name', operator: 'contains', value: '' }]} onFiltersChange={onFiltersChange} />
    );
    clickNode(container.querySelector('.filter-panel-toggle'));
    changeInput(container.querySelector('.filter-value'), 'toto');
    expect(onFiltersChange.mock.calls.at(-1)[0][0].value).toBe('toto');
  });
});
