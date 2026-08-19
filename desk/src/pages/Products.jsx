// src/pages/Products.jsx
import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { productService } from '../services/api';
import { toast } from 'react-toastify';
import DataTable from '../components/desktop/DataTable';
import FilterPanel from '../components/desktop/FilterPanel';
import FormGrid, { FormField, FormDraftBanner, FormDraftStatus } from '../components/desktop/FormGrid';
import useFormDraft from '../hooks/useFormDraft';
import { applyFilters, applySearch } from '../utils/filterUtils';
import { exportRowsToCsv, timestampedFilename } from '../utils/exportUtils';
import './Pages.css';

const EMPTY_FORM = {
  nom: '',
  reference: '',
  description_courte: '',
  prix_achat_ht: 0,
  prix_vente_ht: 0,
  quantite_stock: 0,
  categorie: '',
  code_barre: '',
  seuil_alerte: 0,
};

const NUMERIC_FIELDS = ['prix_achat_ht', 'prix_vente_ht', 'quantite_stock', 'seuil_alerte'];

const formatCurrency = (value) => `${(Number(value) || 0).toFixed(2)} Ar`;

const marginOf = (product) => {
  const achat = Number(product?.prix_achat_ht) || 0;
  const vente = Number(product?.prix_vente_ht) || 0;
  if (achat <= 0) return 0;
  return ((vente - achat) / achat) * 100;
};

const stockValueOf = (product) => (Number(product?.prix_achat_ht) || 0) * (Number(product?.quantite_stock) || 0);

const getStockStatus = (quantite, seuil) => {
  if (quantite <= seuil) return 'danger';
  if (quantite <= seuil * 1.5) return 'warning';
  return 'success';
};

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);
  const [currentProduct, setCurrentProduct] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [filters, setFilters] = useState([]);
  const [appliedFilters, setAppliedFilters] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);

  const draftKey = showModal ? `produits:${currentProduct?.id || 'new'}` : null;
  const draft = useFormDraft(draftKey, formData, { enabled: showModal });

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await productService.getAll({});
      setProducts(response.data?.produits || response.data || []);
    } catch (err) {
      console.error('Error fetching products:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des produits';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: NUMERIC_FIELDS.includes(name) ? parseFloat(value) || 0 : value,
    }));
  };

  const openModal = (product = null) => {
    setCurrentProduct(product);
    setFormData(
      product
        ? {
            nom: product.nom || '',
            reference: product.reference || '',
            description_courte: product.description_courte || product.description || '',
            prix_achat_ht: product.prix_achat_ht || 0,
            prix_vente_ht: product.prix_vente_ht || 0,
            quantite_stock: product.quantite_stock || 0,
            categorie: product.categorie || '',
            code_barre: product.code_barre || '',
            seuil_alerte: product.seuil_alerte || 0,
          }
        : { ...EMPTY_FORM }
    );
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentProduct(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentProduct) {
        await productService.update(currentProduct.id, formData);
        toast.success('Produit mis à jour avec succès');
      } else {
        await productService.create(formData);
        toast.success('Produit créé avec succès');
      }
      draft.clear(); // brouillon inutile après un enregistrement réussi
      fetchProducts();
      closeModal();
    } catch (err) {
      console.error('Error saving product:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde du produit';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')) {
      try {
        await productService.delete(id);
        toast.success('Produit supprimé avec succès');
        fetchProducts();
      } catch (err) {
        console.error('Error deleting product:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression du produit';
        toast.error(msg);
      }
    }
  };

  const categories = useMemo(
    () => [...new Set(products.map((p) => p.categorie).filter(Boolean))],
    [products]
  );

  /* ------------------------------------------------------ colonnes DataTable */

  const columns = useMemo(
    () => [
      { key: 'code_barre', label: 'Code', width: 130, accessor: (row) => row.code_barre || row.id },
      { key: 'nom', label: 'Nom', width: 220 },
      { key: 'categorie', label: 'Catégorie', width: 150, render: (value) => value || 'N/A' },
      {
        key: 'prix_achat_ht',
        label: "Prix d'achat",
        type: 'number',
        align: 'right',
        width: 120,
        render: (value) => formatCurrency(value),
      },
      {
        key: 'prix_vente_ht',
        label: 'Prix de vente',
        type: 'number',
        align: 'right',
        width: 120,
        render: (value) => formatCurrency(value),
      },
      {
        key: 'marge',
        label: 'Marge',
        type: 'number',
        align: 'right',
        width: 100,
        accessor: marginOf,
        render: (value) => `${(Number(value) || 0).toFixed(1)}%`,
      },
      {
        key: 'valeur_stock',
        label: 'Valeur stock',
        type: 'number',
        align: 'right',
        width: 130,
        accessor: stockValueOf,
        render: (value) => formatCurrency(value),
      },
      {
        key: 'quantite_stock',
        label: 'Stock',
        type: 'number',
        align: 'center',
        width: 90,
        render: (value, row) => (
          <span className={`badge ${getStockStatus(Number(value) || 0, Number(row.seuil_alerte) || 0)}`}>
            {Number(value) || 0}
          </span>
        ),
      },
      {
        key: 'seuil_alerte',
        label: 'Seuil min.',
        type: 'number',
        align: 'center',
        width: 100,
        render: (value) => Number(value) || 0,
      },
      {
        key: 'actions',
        label: 'Actions',
        width: 110,
        sortable: false,
        resizable: false,
        exportable: false,
        align: 'center',
        render: (_value, row) => (
          <span className="dt-actions">
            <button onClick={() => openModal(row)} className="btn-small btn-edit" title="Modifier">
              <i className="ti ti-edit" aria-hidden="true" />
            </button>
            <button onClick={() => handleDelete(row.id)} className="btn-small btn-delete" title="Supprimer">
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </span>
        ),
      },
    ],
    // openModal/handleDelete sont stables au sein d'un rendu de page

    []
  );

  const filterFields = useMemo(
    () => [
      { key: 'nom', label: 'Nom', type: 'text' },
      { key: 'reference', label: 'Référence', type: 'text' },
      { key: 'code_barre', label: 'Code barre', type: 'text' },
      { key: 'categorie', label: 'Catégorie', type: 'select', options: categories },
      { key: 'prix_achat_ht', label: "Prix d'achat", type: 'number' },
      { key: 'prix_vente_ht', label: 'Prix de vente', type: 'number' },
      { key: 'marge', label: 'Marge (%)', type: 'number', accessor: marginOf },
      { key: 'quantite_stock', label: 'Stock', type: 'number' },
      { key: 'seuil_alerte', label: 'Seuil alerte', type: 'number' },
    ],
    [categories]
  );

  const filteredProducts = useMemo(() => {
    let rows = products;
    rows = applySearch(rows, searchTerm, [{ key: 'nom' }, { key: 'code_barre' }, { key: 'reference' }]);
    if (categoryFilter) rows = rows.filter((p) => p.categorie === categoryFilter);
    return applyFilters(rows, appliedFilters, filterFields);
  }, [products, searchTerm, categoryFilter, appliedFilters, filterFields]);

  const bulkActions = useMemo(
    () => [
      {
        key: 'export',
        label: 'Exporter CSV',
        icon: 'ti-download',
        onClick: (ids, rows) => {
          const ok = exportRowsToCsv(timestampedFilename('produits'), columns, rows);
          if (ok) toast.success(`${rows.length} produit(s) exporté(s)`);
          else toast.error("Échec de l'export CSV");
        },
      },
      {
        key: 'delete',
        label: 'Supprimer',
        icon: 'ti-trash',
        variant: 'danger',
        confirm: (count) => `Supprimer définitivement ${count} produit(s) ?`,
        onClick: async (ids) => {
          const results = await Promise.allSettled(ids.map((id) => productService.delete(id)));
          const failed = results.filter((r) => r.status === 'rejected').length;
          const done = results.length - failed;
          if (done > 0) toast.success(`${done} produit(s) supprimé(s)`);
          if (failed > 0) toast.error(`${failed} suppression(s) en échec`);
          fetchProducts();
        },
      },
    ],
    [columns, fetchProducts]
  );

  const totalStockValue = useMemo(
    () => products.reduce((sum, p) => sum + stockValueOf(p), 0),
    [products]
  );

  if (loading && products.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des produits...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchProducts} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Produits</h1>
          <p>Catalogue produits et suivi des stocks</p>
        </div>
        <div className="header-actions">
          <button onClick={() => openModal()} className="btn-primary">
            + Ajouter un produit
          </button>
          <button onClick={fetchProducts} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-value">{products.length}</div>
          <div className="stat-label">Total des produits</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {products.filter((p) => (p.quantite_stock || 0) <= (p.seuil_alerte || 0)).length}
          </div>
          <div className="stat-label">Stock critique</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {products.reduce((sum, p) => sum + (p.quantite_stock || 0), 0)}
          </div>
          <div className="stat-label">Stock total</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totalStockValue.toFixed(2)} Ar</div>
          <div className="stat-label">Valeur du stock</div>
        </div>
      </div>

      <div className="card filter-card">
        <div className="filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder="Rechercher un produit..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="form-select"
          >
            <option value="">Toutes les catégories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        <FilterPanel
          module="produits"
          fields={filterFields}
          filters={filters}
          onFiltersChange={setFilters}
          onApply={setAppliedFilters}
          onReset={() => setAppliedFilters([])}
        />
      </div>

      <div className="card full-width">
        <DataTable
          module="produits"
          columns={columns}
          data={filteredProducts}
          rowKey="id"
          loading={loading}
          emptyMessage="Aucun produit trouvé"
          selectable
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          bulkActions={bulkActions}
          rowHeight={46}
          maxHeight={560}
        />
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{currentProduct ? 'Modifier le produit' : 'Ajouter un nouveau produit'}</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <FormDraftBanner draft={draft} onRestore={(data) => setFormData((prev) => ({ ...prev, ...data }))} />
              <FormGrid columns={3}>
                <FormField label="Nom" required htmlFor="produit-nom">
                  <input
                    id="produit-nom"
                    type="text"
                    name="nom"
                    value={formData.nom}
                    onChange={handleChange}
                    required
                    placeholder="Nom du produit"
                  />
                </FormField>
                <FormField label="Référence" required htmlFor="produit-reference">
                  <input
                    id="produit-reference"
                    type="text"
                    name="reference"
                    value={formData.reference}
                    onChange={handleChange}
                    required
                    placeholder="Référence produit"
                  />
                </FormField>
                <FormField label="Code barre" htmlFor="produit-code-barre">
                  <input
                    id="produit-code-barre"
                    type="text"
                    name="code_barre"
                    value={formData.code_barre}
                    onChange={handleChange}
                    placeholder="Code barre"
                  />
                </FormField>
                <FormField label="Catégorie" htmlFor="produit-categorie">
                  <input
                    id="produit-categorie"
                    type="text"
                    name="categorie"
                    value={formData.categorie}
                    onChange={handleChange}
                    placeholder="Catégorie"
                    list="categories"
                  />
                  <datalist id="categories">
                    {categories.map((cat) => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </FormField>
                <FormField label="Prix d'achat HT (Ar)" htmlFor="produit-prix-achat">
                  <input
                    id="produit-prix-achat"
                    type="number"
                    name="prix_achat_ht"
                    value={formData.prix_achat_ht}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                  />
                </FormField>
                <FormField
                  label="Prix de vente HT (Ar)"
                  htmlFor="produit-prix-vente"
                  hint={`Marge : ${marginOf(formData).toFixed(1)}%`}
                >
                  <input
                    id="produit-prix-vente"
                    type="number"
                    name="prix_vente_ht"
                    value={formData.prix_vente_ht}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                  />
                </FormField>
                <FormField label="Quantité en stock" htmlFor="produit-stock">
                  <input
                    id="produit-stock"
                    type="number"
                    name="quantite_stock"
                    value={formData.quantite_stock}
                    onChange={handleChange}
                    min="0"
                  />
                </FormField>
                <FormField label="Seuil alerte" htmlFor="produit-seuil">
                  <input
                    id="produit-seuil"
                    type="number"
                    name="seuil_alerte"
                    value={formData.seuil_alerte}
                    onChange={handleChange}
                    min="0"
                  />
                </FormField>
                <FormField label="Description courte" span="full" htmlFor="produit-description">
                  <textarea
                    id="produit-description"
                    name="description_courte"
                    value={formData.description_courte}
                    onChange={handleChange}
                    placeholder="Description courte du produit"
                    rows="2"
                  />
                </FormField>
              </FormGrid>
              <div className="modal-footer">
                <FormDraftStatus draft={draft} />
                <div className="modal-footer-actions">
                  <button type="button" onClick={closeModal} className="btn-secondary">
                    Annuler
                  </button>
                  <button type="submit" className="btn-primary" disabled={!formData.nom}>
                    {currentProduct ? 'Mettre à jour' : 'Ajouter'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Products;
