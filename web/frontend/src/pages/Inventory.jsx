// src/pages/Inventory.jsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { stockService, productService } from '../services/api';
import { toast } from 'react-toastify';
import DataTable from '../components/desktop/DataTable';
import FilterPanel from '../components/desktop/FilterPanel';
import FormGrid, { FormField, FormDraftBanner, FormDraftStatus } from '../components/desktop/FormGrid';
import useFormDraft from '../hooks/useFormDraft';
import { applyFilters, applySearch } from '../utils/filterUtils';
import { exportRowsToCsv, timestampedFilename } from '../utils/exportUtils';
import './Pages.css';

const EMPTY_MOVEMENT = {
  produit_id: '',
  quantite: 1,
  type_mouvement: 'entree',
  raison: '',
};

const formatCurrency = (amount) => `${(Number(amount) || 0).toFixed(2)} Ar`;

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString('mg-MG');
};

const getStockStatus = (quantite, seuil) => {
  if (!seuil || seuil === 0) return quantite === 0 ? 'danger' : 'success';
  if (quantite <= seuil) return 'danger';
  if (quantite <= seuil * 1.5) return 'warning';
  return 'success';
};

const stockValueOf = (product) => (Number(product?.prix_vente_ht) || 0) * (Number(product?.quantite_stock) || 0);

const Inventory = () => {
  const [products, setProducts] = useState([]);
  const [mouvements, setMouvements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState('inventory');

  const [showMovementModal, setShowMovementModal] = useState(false);
  const [movementData, setMovementData] = useState(EMPTY_MOVEMENT);
  const [batchTargets, setBatchTargets] = useState([]);

  const [filterLowStock, setFilterLowStock] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState([]);
  const [appliedFilters, setAppliedFilters] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);

  const isBatch = batchTargets.length > 0;
  const draftKey = showMovementModal ? (isBatch ? 'stocks:mouvement-groupe' : 'stocks:mouvement') : null;
  const draft = useFormDraft(draftKey, movementData, { enabled: showMovementModal });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [productsResponse, mouvementsResponse] = await Promise.allSettled([
        productService.getAll({}),
        stockService.getMouvements({}),
      ]);
      setProducts((productsResponse.status === 'fulfilled' ? productsResponse.value?.data?.produits : undefined) || []);
      setMouvements((mouvementsResponse.status === 'fulfilled' ? mouvementsResponse.value?.data?.mouvements : undefined) || []);
    } catch (err) {
      const msg = err.response?.data?.message || "Échec du chargement de l'inventaire";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleMovementChange = (e) => {
    const { name, value } = e.target;
    setMovementData((prev) => ({
      ...prev,
      [name]: name === 'quantite' ? parseInt(value, 10) || 1 : value,
    }));
  };

  const openMovementModal = useCallback((product = null) => {
    setBatchTargets([]);
    setMovementData({ ...EMPTY_MOVEMENT, produit_id: product?.id || '' });
    setShowMovementModal(true);
  }, []);

  const openBatchMovementModal = useCallback((ids) => {
    setBatchTargets(ids);
    setMovementData({ ...EMPTY_MOVEMENT, produit_id: '' });
    setShowMovementModal(true);
  }, []);

  const closeMovementModal = () => {
    setShowMovementModal(false);
    setBatchTargets([]);
  };

  const handleMovementSubmit = async (e) => {
    e.preventDefault();

    if (!isBatch && !movementData.produit_id) {
      toast.error('Veuillez sélectionner un produit');
      return;
    }
    if (movementData.quantite <= 0) {
      toast.error('La quantité doit être supérieure à 0');
      return;
    }

    const typeLabel = movementData.type_mouvement === 'entree' ? 'Entrée' : 'Sortie';

    try {
      if (isBatch) {
        const results = await Promise.allSettled(
          batchTargets.map((produitId) =>
            stockService.createMouvement({ ...movementData, produit_id: produitId })
          )
        );
        const failed = results.filter((r) => r.status === 'rejected').length;
        const done = results.length - failed;
        if (done > 0) toast.success(`${typeLabel} de ${movementData.quantite} unités sur ${done} produit(s)`);
        if (failed > 0) toast.error(`${failed} mouvement(s) en échec`);
        setSelectedIds([]);
      } else {
        await stockService.createMouvement(movementData);
        toast.success(`Mouvement de stock enregistré: ${typeLabel} de ${movementData.quantite} unités`);
      }
      draft.clear();
      fetchData();
      closeMovementModal();
    } catch (err) {
      console.error('Error recording movement:', err);
      const msg = err.response?.data?.message || 'Échec du mouvement de stock';
      toast.error(msg);
    }
  };

  /* ---------------------------------------------------------------- colonnes */

  const inventoryColumns = useMemo(
    () => [
      { key: 'code_barre', label: 'Code', width: 130, accessor: (row) => row.code_barre || row.id },
      { key: 'nom', label: 'Produit', width: 240 },
      { key: 'categorie', label: 'Catégorie', width: 150, render: (value) => value || 'N/A' },
      {
        key: 'quantite_stock',
        label: 'Stock actuel',
        type: 'number',
        align: 'center',
        width: 120,
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
        key: 'valeur_stock',
        label: 'Valeur stock',
        type: 'number',
        align: 'right',
        width: 140,
        accessor: stockValueOf,
        render: (value) => formatCurrency(value),
      },
      {
        key: 'actions',
        label: 'Actions',
        width: 130,
        sortable: false,
        resizable: false,
        exportable: false,
        align: 'center',
        render: (_value, row) => (
          <span className="dt-actions">
            <button
              onClick={() => openMovementModal(row)}
              className="btn-small btn-primary"
              title="Mouvement de stock"
            >
              Mouvement
            </button>
          </span>
        ),
      },
    ],
    [openMovementModal]
  );

  const movementColumns = useMemo(
    () => [
      {
        key: 'created_at',
        label: 'Date',
        type: 'date',
        width: 130,
        render: (value) => formatDate(value),
      },
      {
        key: 'produit_nom',
        label: 'Produit',
        width: 260,
        accessor: (row) => row.produit_nom || row.produit_id,
      },
      {
        key: 'type_mouvement',
        label: 'Type',
        width: 110,
        align: 'center',
        render: (value) => (
          <span className={`badge ${value === 'entree' ? 'success' : 'danger'}`}>
            {value === 'entree' ? 'Entrée' : 'Sortie'}
          </span>
        ),
      },
      { key: 'quantite', label: 'Quantité', type: 'number', align: 'center', width: 100 },
      { key: 'raison', label: 'Raison', width: 280, render: (value) => value || 'N/A' },
    ],
    []
  );

  /* ----------------------------------------------------------------- filtres */

  const categories = useMemo(
    () => [...new Set(products.map((p) => p.categorie).filter(Boolean))],
    [products]
  );

  const inventoryFilterFields = useMemo(
    () => [
      { key: 'nom', label: 'Produit', type: 'text' },
      { key: 'code_barre', label: 'Code barre', type: 'text' },
      { key: 'categorie', label: 'Catégorie', type: 'select', options: categories },
      { key: 'quantite_stock', label: 'Stock actuel', type: 'number' },
      { key: 'seuil_alerte', label: 'Seuil alerte', type: 'number' },
      { key: 'valeur_stock', label: 'Valeur stock', type: 'number', accessor: stockValueOf },
    ],
    [categories]
  );

  const movementFilterFields = useMemo(
    () => [
      { key: 'produit_nom', label: 'Produit', type: 'text' },
      {
        key: 'type_mouvement',
        label: 'Type',
        type: 'select',
        options: [
          { value: 'entree', label: 'Entrée' },
          { value: 'sortie', label: 'Sortie' },
        ],
      },
      { key: 'quantite', label: 'Quantité', type: 'number' },
      { key: 'raison', label: 'Raison', type: 'text' },
      { key: 'created_at', label: 'Date', type: 'date' },
    ],
    []
  );

  const filteredProducts = useMemo(() => {
    let rows = applySearch(products, searchTerm, [{ key: 'nom' }, { key: 'code_barre' }, { key: 'categorie' }]);
    if (filterLowStock) {
      rows = rows.filter((p) => p.seuil_alerte && (p.quantite_stock || 0) <= p.seuil_alerte);
    }
    return applyFilters(rows, appliedFilters, inventoryFilterFields);
  }, [products, searchTerm, filterLowStock, appliedFilters, inventoryFilterFields]);

  const filteredMouvements = useMemo(() => {
    const rows = applySearch(mouvements, searchTerm, [{ key: 'produit_nom' }, { key: 'raison' }]);
    return applyFilters(rows, appliedFilters, movementFilterFields);
  }, [mouvements, searchTerm, appliedFilters, movementFilterFields]);

  const inventoryBulkActions = useMemo(
    () => [
      {
        key: 'batch-movement',
        label: 'Mouvement groupé',
        icon: 'ti-transfer',
        clearSelection: false,
        onClick: (ids) => openBatchMovementModal(ids),
      },
      {
        key: 'export',
        label: 'Exporter CSV',
        icon: 'ti-download',
        onClick: (ids, rows) => {
          const ok = exportRowsToCsv(timestampedFilename('stocks'), inventoryColumns, rows);
          if (ok) toast.success(`${rows.length} ligne(s) exportée(s)`);
          else toast.error("Échec de l'export CSV");
        },
      },
    ],
    [inventoryColumns, openBatchMovementModal]
  );

  const movementBulkActions = useMemo(
    () => [
      {
        key: 'export',
        label: 'Exporter CSV',
        icon: 'ti-download',
        onClick: (ids, rows) => {
          const ok = exportRowsToCsv(timestampedFilename('mouvements-stock'), movementColumns, rows);
          if (ok) toast.success(`${rows.length} mouvement(s) exporté(s)`);
          else toast.error("Échec de l'export CSV");
        },
      },
    ],
    [movementColumns]
  );

  const lowStockProducts = useMemo(
    () => products.filter((p) => (p.quantite_stock || 0) <= (p.seuil_alerte || 0)),
    [products]
  );

  const handleViewChange = (nextView) => {
    setView(nextView);
    setSelectedIds([]);
    setFilters([]);
    setAppliedFilters([]);
  };

  if (loading && products.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement de l'inventaire...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchData} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Stock</h1>
          <p>Suivi et gestion de l'inventaire</p>
        </div>
        <div className="header-actions">
          <button onClick={() => openMovementModal()} className="btn-primary">
            + Mouvement de stock
          </button>
          <button onClick={fetchData} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: '#667eea' }}></div>
          <div className="stat-content">
            <div className="stat-value">{products.length}</div>
            <div className="stat-label">Total des produits</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: '#f56565' }}></div>
          <div className="stat-content">
            <div className="stat-value">{lowStockProducts.length}</div>
            <div className="stat-label">Stocks critiques</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: '#48bb78' }}></div>
          <div className="stat-content">
            <div className="stat-value">
              {formatCurrency(products.reduce((sum, p) => sum + stockValueOf(p), 0))}
            </div>
            <div className="stat-label">Valeur totale du stock</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: '#ed8936' }}></div>
          <div className="stat-content">
            <div className="stat-value">
              {products.reduce((sum, p) => sum + (p.quantite_stock || 0), 0)}
            </div>
            <div className="stat-label">Unités totales</div>
          </div>
        </div>
      </div>

      {lowStockProducts.length > 0 && (
        <div className="alert warning">
          <strong> Alerte: {lowStockProducts.length} produit(s) en stock critique</strong>
          <div className="low-stock-list">
            {lowStockProducts.map((p) => (
              <span key={p.id} className="badge danger">{p.nom} (Stock: {p.quantite_stock || 0})</span>
            ))}
          </div>
        </div>
      )}

      <div className="card filter-card">
        <div className="filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder={view === 'inventory' ? 'Rechercher un produit...' : 'Rechercher un mouvement...'}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          {view === 'inventory' && (
            <label className="filter-checkbox">
              <input
                type="checkbox"
                checked={filterLowStock}
                onChange={(e) => setFilterLowStock(e.target.checked)}
              />
              <span>Afficher uniquement les stocks critiques</span>
            </label>
          )}
          <div className="view-toggle">
            <button
              className={`btn-small ${view === 'inventory' ? 'btn-view' : 'btn-secondary'}`}
              onClick={() => handleViewChange('inventory')}
            >
              Inventaire
            </button>
            <button
              className={`btn-small ${view === 'mouvements' ? 'btn-view' : 'btn-secondary'}`}
              onClick={() => handleViewChange('mouvements')}
            >
              Mouvements
            </button>
          </div>
        </div>
        <FilterPanel
          key={view}
          module={view === 'inventory' ? 'stocks' : 'stocks-mouvements'}
          fields={view === 'inventory' ? inventoryFilterFields : movementFilterFields}
          filters={filters}
          onFiltersChange={setFilters}
          onApply={setAppliedFilters}
          onReset={() => setAppliedFilters([])}
        />
      </div>

      <div className="card full-width">
        {view === 'inventory' ? (
          <DataTable
            module="stocks"
            columns={inventoryColumns}
            data={filteredProducts}
            rowKey="id"
            loading={loading}
            emptyMessage="Aucun produit trouvé"
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={inventoryBulkActions}
            rowHeight={46}
            maxHeight={560}
          />
        ) : (
          <DataTable
            module="stocks-mouvements"
            columns={movementColumns}
            data={filteredMouvements}
            rowKey={(row, index) => row.id ?? `${row.produit_id}-${row.created_at}-${index}`}
            loading={loading}
            emptyMessage="Aucun mouvement enregistré"
            defaultSort={[{ key: 'created_at', direction: 'desc' }]}
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={movementBulkActions}
            rowHeight={44}
            maxHeight={560}
          />
        )}
      </div>

      {showMovementModal && (
        <div className="modal-overlay" onClick={closeMovementModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{isBatch ? `Mouvement groupé (${batchTargets.length} produits)` : 'Mouvement de stock'}</h2>
              <button onClick={closeMovementModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleMovementSubmit} className="modal-form">
              <FormDraftBanner draft={draft} onRestore={(data) => setMovementData((prev) => ({ ...prev, ...data }))} />
              <FormGrid columns={2}>
                {isBatch ? (
                  <FormField label="Produits concernés" span="full">
                    <div className="low-stock-list">
                      {batchTargets.map((id) => {
                        const product = products.find((p) => p.id === id);
                        return (
                          <span key={id} className="badge info">
                            {product?.nom || `#${id}`}
                          </span>
                        );
                      })}
                    </div>
                  </FormField>
                ) : (
                  <FormField label="Produit" required htmlFor="mouvement-produit">
                    <select
                      id="mouvement-produit"
                      name="produit_id"
                      value={movementData.produit_id}
                      onChange={handleMovementChange}
                      required
                    >
                      <option value="">Sélectionnez un produit</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.nom} (Stock: {p.quantite_stock || 0})
                        </option>
                      ))}
                    </select>
                  </FormField>
                )}
                <FormField label="Type de mouvement" required htmlFor="mouvement-type">
                  <select
                    id="mouvement-type"
                    name="type_mouvement"
                    value={movementData.type_mouvement}
                    onChange={handleMovementChange}
                    required
                  >
                    <option value="entree">Entrée (Approvisionnement)</option>
                    <option value="sortie">Sortie (Retrait)</option>
                  </select>
                </FormField>
                <FormField
                  label="Quantité"
                  required
                  htmlFor="mouvement-quantite"
                  hint={isBatch ? 'Appliquée à chaque produit sélectionné' : undefined}
                >
                  <input
                    id="mouvement-quantite"
                    type="number"
                    name="quantite"
                    value={movementData.quantite}
                    onChange={handleMovementChange}
                    min="1"
                    required
                  />
                </FormField>
                <FormField label="Raison" span="full" htmlFor="mouvement-raison">
                  <textarea
                    id="mouvement-raison"
                    name="raison"
                    value={movementData.raison}
                    onChange={handleMovementChange}
                    placeholder="Ex: Livraison fournisseur, Retrait pour vente, etc."
                    rows="2"
                  />
                </FormField>
              </FormGrid>
              <div className="modal-footer">
                <FormDraftStatus draft={draft} />
                <div className="modal-footer-actions">
                  <button type="button" onClick={closeMovementModal} className="btn-secondary">
                    Annuler
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={!isBatch && !movementData.produit_id}
                  >
                    {isBatch ? `Enregistrer ${batchTargets.length} mouvements` : 'Enregistrer le mouvement'}
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

export default Inventory;
