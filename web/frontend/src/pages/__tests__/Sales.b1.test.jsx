/**
 * Test de non-régression B1 — formulaire de vente (Sales.jsx).
 *
 * Historique : le <select> produit écrasait l'onChange de register() avec un
 * handler custom, donc `lignes.X.produit_id` restait undefined, la validation
 * yup échouait (« Produit requis ») et la vente n'était jamais créée.
 *
 * Ce test rend le vrai <SaleModal>, coche « client passager », sélectionne un
 * produit, soumet, et vérifie que saleService.create reçoit bien produit_id.
 */
import React, { act } from 'react';

// Environnement act() requis par react-dom 18 en test.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
import { createRoot } from 'react-dom/client';
import { saleService } from '../../services/api';
import { SaleModal } from '../Sales';

jest.mock('../../services/api', () => ({
  saleService: {
    create: jest.fn(() => Promise.resolve({ data: { id: 99 } })),
    update: jest.fn(() => Promise.resolve({})),
  },
  productService: {},
  clientService: {},
  devisService: {},
  bonLivraisonService: {},
  avoirService: {},
  factureService: {},
}));

// La chaîne d'imports d'AccessButton remonte vers shared/ (code Vite avec
// import.meta.env, incompatible avec jest CJS). Ces composants sont hors
// périmètre du test : on les remplace par des stubs neutres.
jest.mock('../../components/common/AccessButton', () => ({
  __esModule: true,
  default: () => <button type="button">stub</button>,
}));
jest.mock('../../components/common/ConfirmModal', () => ({
  __esModule: true,
  default: () => null,
}));

const PRODUCTS = [
  {
    id: 1,
    nom: 'Riz Makaliokely 1kg',
    prix_vente_ht: 1000,
    prix_grossiste: 900,
    prix_demi_gros: 950,
    prix_revendeur: 920,
    taux_tva: 20,
  },
  { id: 2, nom: 'Huile 1L', prix_vente_ht: 2000, taux_tva: 20 },
];

const CLIENTS = [{ id: 5, nom_complet: 'Client Bazar', type: 'detail' }];

const flushMicrotasks = async () => {
  for (let i = 0; i < 6; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    await act(async () => {
      await Promise.resolve();
      await new Promise((r) => setTimeout(r, 0));
    });
  }
};

const setNativeValue = (el, value) => {
  const proto = el instanceof HTMLInputElement ? HTMLInputElement : HTMLSelectElement;
  const prop = el instanceof HTMLInputElement ? 'checked' : 'value';
  Object.getOwnPropertyDescriptor(proto.prototype, prop).set.call(el, value);
};

const fireEvent = (el, type) => {
  act(() => {
    el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
  });
};

const renderModal = () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(
      <SaleModal
        products={PRODUCTS}
        clients={CLIENTS}
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    );
  });
  return { container, root };
};

describe('B1 — formulaire de vente : produit_id capturé', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    jest.clearAllMocks();
  });

  test('la sélection d’un produit écrit produit_id et la vente se crée', async () => {
    const { container } = renderModal();

    // 1. Client passager : évite de devoir sélectionner un client.
    //    (React écoute 'click' — pas 'change' — pour les checkboxes.)
    const passagerToggle = container.querySelector('input[type="checkbox"]');
    expect(passagerToggle).toBeTruthy();
    setNativeValue(passagerToggle, true);
    fireEvent(passagerToggle, 'click');

    // 2. Sélection du produit dans la première ligne de vente.
    const produitSelect = container.querySelector('tbody select');
    expect(produitSelect).toBeTruthy();
    setNativeValue(produitSelect, '1');
    fireEvent(produitSelect, 'change');

    // 3. Soumission : sans le fix, la validation yup échoue (« Produit requis »)
    //    et create n'est jamais appelé.
    const form = container.querySelector('form');
    fireEvent(form, 'submit');
    await flushMicrotasks();

    expect(saleService.create).toHaveBeenCalledTimes(1);
    const payload = saleService.create.mock.calls[0][0];
    expect(payload.lignes[0].produit_id).toBe(1);
    expect(payload.lignes[0].quantite).toBe(1);
    // Prix auto-rempli par handleProduitChange (détail → prix_vente_ht).
    expect(payload.lignes[0].prix_unitaire).toBe(1000);
    expect(payload.lignes[0].taux_tva).toBe(20);
    expect(payload.client_passager).toBe(true);
    expect(payload.client_id).toBeNull();
  });

  test('sans produit sélectionné, la vente est refusée (validation)', async () => {
    const { container } = renderModal();

    const passagerToggle = container.querySelector('input[type="checkbox"]');
    setNativeValue(passagerToggle, true);
    fireEvent(passagerToggle, 'click');

    const form = container.querySelector('form');
    fireEvent(form, 'submit');
    await flushMicrotasks();

    expect(saleService.create).not.toHaveBeenCalled();
    // Message yup affiché pour un produit_id vide (cast number échoué)
    // ou « Produit requis » selon le chemin de validation.
    expect(container.textContent).toMatch(/produit_id must be a `number` type|Produit requis/);
  });
});
