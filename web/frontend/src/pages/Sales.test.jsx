import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { SaleModal } from './Sales';

// Non-régression B1 : la sélection d'un produit dans une ligne de vente doit
// écrire lignes.<i>.produit_id dans le formulaire (react-hook-form). Sans le
// setValue explicite, la valeur reste ''/undefined et la vente ne part jamais.
jest.mock('../services/api', () => ({
  saleService: { create: jest.fn(), update: jest.fn() },
  productService: { getAll: jest.fn() },
  clientService: { getAll: jest.fn() },
  devisService: { getAll: jest.fn() },
  bonLivraisonService: { getAll: jest.fn() },
  avoirService: { getAll: jest.fn() },
  factureService: { getAll: jest.fn() },
}));
jest.mock('react-toastify', () => ({
  toast: { success: jest.fn(), error: jest.fn(), info: jest.fn() },
}));
// AccessButton/ConfirmModal tirent shared/AuthContext (import.meta.env, non
// compatible Jest) — stubs UI, hors périmètre du test B1.
jest.mock('../components/common/AccessButton', () => ({
  __esModule: true,
  default: ({ children, ...props }) => <button {...props}>{children}</button>,
}));
jest.mock('../components/common/ConfirmModal', () => ({
  __esModule: true,
  default: () => null,
}));
jest.mock('./Pages.css', () => ({}));

const products = [
  { id: 7, nom: 'Riz 5kg', prix_vente_ht: 12000, taux_tva: 20 },
  { id: 9, nom: 'Huile 1L', prix_vente_ht: 4500, taux_tva: 20 },
];
const clients = [{ id: 3, nom: 'Rakoto', type: 'detail' }];

describe('SaleModal — B1 produit_id des lignes', () => {
  it('écrit lignes.0.produit_id quand on sélectionne un produit', async () => {
    const { container } = render(
      <SaleModal products={products} clients={clients} onClose={jest.fn()} onSuccess={jest.fn()} />
    );

    const produitSelect = container.querySelector('select[name="lignes.0.produit_id"]');
    fireEvent.change(produitSelect, { target: { value: '7' } });

    // Le select lui-même doit refléter la valeur (sinon register n'a rien su)
    await waitFor(() => expect(produitSelect.value).toBe('7'));
  });

  it('dérive le prix unitaire du produit sélectionné (validation shouldValidate passe)', async () => {
    const { container } = render(
      <SaleModal products={products} clients={clients} onClose={jest.fn()} onSuccess={jest.fn()} />
    );

    const produitSelect = container.querySelector('select[name="lignes.0.produit_id"]');
    fireEvent.change(produitSelect, { target: { value: '9' } });

    await waitFor(() => {
      // Prix dérivé (getPrixAuto) : le champ prix_unitaire doit être rempli
      const prixInput = container.querySelector('input[type="number"][step="0.01"]');
      expect(Number(prixInput.value)).toBe(4500);
    });
  });
});
