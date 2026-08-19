// src/components/desktop/__tests__/DataTable.component.test.jsx
import React from 'react';
import DataTable, {
  DEFAULT_COLUMN_WIDTH,
} from '../DataTable';
import {
  setupVirtualEnvironment,
  mountComponent,
  clickNode,
  flushFrames,
  rowTexts,
  textOf,
  act,
} from '../../../test-helpers/renderDom';

setupVirtualEnvironment({ viewportHeight: 600, viewportWidth: 1000 });

const COLUMNS = [
  { key: 'id', label: 'ID', sortable: true },
  { key: 'name', label: 'Nom', sortable: true },
  { key: 'price', label: 'Prix', sortable: true, type: 'number' },
];

const makeData = (n = 5) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: ['Banane', 'Abricot', 'Citron', 'Pomme', 'Datte', 'Figue'][i % 6],
    price: [3, 1, 2, 5, 4, 6][i % 6],
  }));

const fireChange = (node, { shiftKey = false } = {}) => {
  // React maps checkbox onChange to the native 'click' event.
  // eslint-disable-next-line no-param-reassign
  node.checked = !node.checked;
  node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, shiftKey }));
};

const headerButton = (container, label) =>
  Array.from(container.querySelectorAll('th.is-sortable button.dt-th-btn')).find((btn) =>
    btn.textContent.includes(label)
  );

beforeEach(() => {
  localStorage.clear();
});

describe('DataTable — rendu et tri', () => {
  test('affiche les lignes et respecte l’ordre de tri initial', () => {
    const { container } = mountComponent(
      <DataTable module="test-render" columns={COLUMNS} data={makeData(3)} virtualized={false} />
    );
    const rows = container.querySelectorAll('tbody tr.dt-row');
    expect(rows.length).toBe(3);
    expect(rowTexts(container, 1)).toEqual(['Banane', 'Abricot', 'Citron']);
  });

  test('clic sur un en-tête trie la colonne', () => {
    const { container } = mountComponent(
      <DataTable module="test-sort" columns={COLUMNS} data={makeData(5)} virtualized={false} />
    );
    clickNode(headerButton(container, 'Nom')); // asc
    expect(rowTexts(container, 1)).toEqual(['Abricot', 'Banane', 'Citron', 'Datte', 'Pomme']);
    clickNode(headerButton(container, 'Nom')); // desc
    expect(rowTexts(container, 1)).toEqual(['Pomme', 'Datte', 'Citron', 'Banane', 'Abricot']);
  });

  test('Maj+clic construit un tri multi-critères (badge de rang + pied de page)', () => {
    // Données avec des prix en double pour que le 2e critère soit décisif.
    const multiData = [
      { id: 1, name: 'Pomme', price: 10 },
      { id: 2, name: 'Abricot', price: 10 },
      { id: 3, name: 'Citron', price: 5 },
      { id: 4, name: 'Banane', price: 20 },
      { id: 5, name: 'Datte', price: 20 },
    ];
    const { container } = mountComponent(
      <DataTable module="test-multi" columns={COLUMNS} data={multiData} virtualized={false} multiSort />
    );
    clickNode(headerButton(container, 'Prix')); // 1er critère : prix asc
    clickNode(headerButton(container, 'Nom'), { shiftKey: true }); // 2e critère : nom asc

    expect(container.textContent).toContain('Tri multi-critères');
    // Nom est le 2e critère : son badge de rang vaut "2".
    const nameTh = headerButton(container, 'Nom').closest('th');
    expect(textOf(nameTh.querySelector('.dt-sort-rank'))).toBe('2');
    // Prix asc, puis nom asc pour départager les ex-aequo (10→Abricot,Pomme ; 20→Banane,Datte).
    expect(rowTexts(container, 1)).toEqual(['Citron', 'Abricot', 'Pomme', 'Banane', 'Datte']);
  });
});

describe('DataTable — sélection et actions groupées', () => {
  test('sélection totale affiche la barre d’actions groupées', () => {
    const { container } = mountComponent(
      <DataTable
        module="test-select-all"
        columns={COLUMNS}
        data={makeData(4)}
        virtualized={false}
        selectable
        bulkActions={[{ key: 'del', label: 'Supprimer', onClick: () => {} }]}
      />
    );
    const selectAll = container.querySelector('thead input[type="checkbox"]');
    fireChange(selectAll);
    expect(container.querySelector('.dt-bulkbar')).toBeTruthy();
    expect(container.textContent).toContain('4 lignes sélectionnées');
  });

  test('Maj+clic étend la sélection sur une plage continue', () => {
    const onClick = jest.fn();
    const { container } = mountComponent(
      <DataTable
        module="test-range"
        columns={COLUMNS}
        data={makeData(5)}
        virtualized={false}
        selectable
        bulkActions={[{ key: 'del', label: 'Supprimer', onClick }]}
      />
    );
    const boxes = () => container.querySelectorAll('tbody tr.dt-row td.dt-cell--select input');
    fireChange(boxes()[0]); // sélectionne la ligne 0
    fireChange(boxes()[3], { shiftKey: true }); // étend 0→3
    expect(container.textContent).toContain('4 lignes sélectionnées');

    clickNode(
      Array.from(container.querySelectorAll('.dt-bulk-btn')).find((btn) =>
        btn.textContent.includes('Supprimer')
      )
    );
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick.mock.calls[0][0].length).toBe(4);
  });
});

describe('DataTable — redimensionnement', () => {
  test('glisser le séparateur met à jour la largeur de colonne', async () => {
    const { container } = mountComponent(
      <DataTable columns={COLUMNS} data={makeData(3)} virtualized={false} />
    );
    const resizer = container.querySelector('[data-resizer="name"]');
    expect(resizer).toBeTruthy();
    act(() => {
      resizer.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: 100 }));
    });
    // Laisse l'effet attacher les écouteurs document après le setResizingKey.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 200 }));
    });
    // Laisse le requestAnimationFrame (throttle) appliquer la largeur AVANT le mouseup
    // (sinon le nettoyage de l'effet annule le rAF planifié).
    await flushFrames();
    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    });

    const nameCol = container.querySelectorAll('colgroup col')[1];
    expect(nameCol.style.width).toBe(`${DEFAULT_COLUMN_WIDTH + 100}px`);
  });

  test('flèches clavier ajustent la largeur par pas de 16', async () => {
    const { container } = mountComponent(
      <DataTable columns={COLUMNS} data={makeData(3)} virtualized={false} />
    );
    const resizer = container.querySelector('[data-resizer="name"]');
    act(() => {
      resizer.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    });
    await flushFrames();
    const nameCol = container.querySelectorAll('colgroup col')[1];
    expect(nameCol.style.width).toBe(`${DEFAULT_COLUMN_WIDTH + 16}px`);
  });
});

describe('DataTable — menu colonnes', () => {
  test('masquer une colonne via le menu la retire du tableau', () => {
    const { container } = mountComponent(
      <DataTable module="test-toggle" columns={COLUMNS} data={makeData(2)} virtualized={false} columnToggle />
    );
    clickNode(container.querySelector('.dt-toolbar-btn')); // ouvre le menu
    const options = container.querySelectorAll('.dt-column-option input');
    // première option = ID, deuxième = Nom, troisième = Prix
    fireChange(options[1]); // décoche "Nom"
    expect(Array.from(container.querySelectorAll('th.is-sortable')).map((t) => t.textContent)).not.toContain(
      'Nom'
    );
  });
});

describe('DataTable — virtualisation', () => {
  test('5000 lignes ne rendent qu’un sous-ensemble DOM et active la virtualisation', async () => {
    const { container } = mountComponent(
      <DataTable module="test-virtual" columns={COLUMNS} data={makeData(5000)} virtualized rowHeight={44} />
    );
    expect(container.querySelector('[data-testid="dt-virtual-tag"]')).toBeTruthy();
    const rendered = container.querySelectorAll('tbody tr.dt-row');
    expect(rendered.length).toBeGreaterThan(0);
    expect(rendered.length).toBeLessThan(5000);

    const firstBefore = textOf(rendered[0].querySelectorAll('td')[1]);
    const viewport = container.querySelector('.dt-viewport');
    await act(async () => {
      viewport.scrollTop = 1500;
      viewport.dispatchEvent(new Event('scroll', { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 40));
    });
    const firstAfter = textOf(container.querySelectorAll('tbody tr.dt-row')[0].querySelectorAll('td')[1]);
    expect(firstAfter).not.toBe(firstBefore);
  });
});
