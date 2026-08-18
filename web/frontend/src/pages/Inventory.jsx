// src/pages/Inventory.jsx
import React, { useState, useEffect } from 'react';
import { stockService, productService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Inventory = () => {
  const [products, setProducts] = useState([]);
  const [mouvements, setMouvements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState('inventory');
  
  const [showMovementModal, setShowMovementModal] = useState(false);
  const [movementData, setMovementData] = useState({
    produit_id: '',
    quantite: 1,
    type_mouvement: 'entree',
    raison: '',
  });

  const [filterLowStock, setFilterLowStock] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [stockStats, setStockStats] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [productsResponse, mouvementsResponse] = await Promise.allSettled([
        productService.getAll({}),
        stockService.getMouvements({}),
      ]);
      setProducts((productsResponse.status === 'fulfilled' ? productsResponse.value?.data?.produits || productsResponse.value?.data || [] : []));
      setMouvements((mouvementsResponse.status === 'fulfilled' ? mouvementsResponse.value?.data?.mouvements || mouvementsResponse.value?.data || [] : []));

      const failed = [productsResponse, mouvementsResponse].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
        toast.warning(`Chargement partiel: ${msgs.join(', ')}`);
      }

      try {
        const statsResponse = await stockService.getStats();
        setStockStats(statsResponse.data);
      } catch (e) {
        console.log('Stats endpoint not available');
      }
    } catch (err) {
      console.error('Error fetching inventory:', err);
      const msg = err.response?.data?.message || "Échec du chargement de l'inventaire";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleMovementChange = (e) => {
    const { name, value } = e.target;
    setMovementData(prev => ({
      ...prev,
      [name]: name === 'quantite' ? parseInt(value, 10) || 1 : value
    }));
  };

  const openMovementModal = (product = null) => {
    setMovementData({
      produit_id: product?.id || '',
      quantite: 1,
      type_mouvement: 'entree',
      raison: '',
    });
    setShowMovementModal(true);
  };

  const closeMovementModal = () => {
    setShowMovementModal(false);
  };

  const handleMovementSubmit = async (e) => {
    e.preventDefault();
    
    if (!movementData.produit_id) {
      toast.error('Veuillez sélectionner un produit');
      return;
    }
    
    if (movementData.quantite <= 0) {
      toast.error('La quantité doit être supérieure à 0');
      return;
    }
    
    try {
      await stockService.createMouvement(movementData);
      toast.success(`Mouvement de stock enregistré: ${movementData.type_mouvement === 'entree' ? 'Entrée' : 'Sortie'} de ${movementData.quantite} unités`);
      fetchData();
      closeMovementModal();
    } catch (err) {
      console.error('Error recording movement:', err);
      const msg = err.response?.data?.message || 'Échec du mouvement de stock';
      toast.error(msg);
    }
  };

  const getStockStatus = (quantite, seuil) => {
    if (!seuil || seuil === 0) {
      return quantite === 0 ? 'danger' : 'success';
    }
    if (quantite <= seuil) return 'danger';
    if (quantite <= seuil * 1.5) return 'warning';
    return 'success';
  };

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.code_barre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.categorie?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStockFilter = !filterLowStock ||
                              (product.seuil_alerte && (product.quantite_stock || 0) <= product.seuil_alerte);
    
    return matchesSearch && matchesStockFilter;
  });

  const lowStockProducts = products.filter(p => (p.quantite_stock || 0) <= (p.seuil_alerte || 0));

  const formatCurrency = (amount) => {
    const value = Number(amount) || 0;
    return value.toFixed(2) + ' Ar';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('mg-MG');
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
            <div className="stat-value">
              {products.filter(p => (p.quantite_stock || 0) <= (p.seuil_alerte || 0)).length}
            </div>
            <div className="stat-label">Stocks critiques</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: '#48bb78' }}></div>
          <div className="stat-content">
            <div className="stat-value">
              {formatCurrency(products.reduce((sum, p) => {
                return sum + ((p.prix_vente_ht || 0) * (p.quantite_stock || 0));
              }, 0))}
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
            {lowStockProducts.map(p => (
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
              placeholder="Rechercher un produit..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          <label className="filter-checkbox">
            <input 
              type="checkbox" 
              checked={filterLowStock}
              onChange={(e) => setFilterLowStock(e.target.checked)}
            />
            <span>Afficher uniquement les stocks critiques</span>
          </label>
          <div className="view-toggle">
            <button 
              className={`btn-small ${view === 'inventory' ? 'btn-view' : 'btn-secondary'}`}
              onClick={() => setView('inventory')}
            >
              Inventaire
            </button>
            <button 
              className={`btn-small ${view === 'mouvements' ? 'btn-view' : 'btn-secondary'}`}
              onClick={() => setView('mouvements')}
            >
              Mouvements
            </button>
          </div>
        </div>
      </div>

      {view === 'inventory' ? (
        <div className="card full-width">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Produit</th>
                  <th>Catégorie</th>
                  <th>Stock actuel</th>
                  <th>Seuil min.</th>
                  <th>Valeur stock</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center">
                      Aucun produit trouvé
                    </td>
                  </tr>
                ) : (
                  filteredProducts.map(product => {
                    const quantite = product.quantite_stock || 0;
                    const seuil = product.seuil_alerte || 0;
                    const status = getStockStatus(quantite, seuil);
                    const valeurStock = (product.prix_vente_ht || 0) * quantite;
                    
                    return (
                      <tr key={product.id}>
                        <td>{product.code_barre || product.id}</td>
                        <td>{product.nom}</td>
                        <td>{product.categorie || 'N/A'}</td>
                        <td>
                          <span className={`badge ${status}`}>
                            {quantite}
                          </span>
                        </td>
                        <td>{seuil}</td>
                        <td>{formatCurrency(valeurStock)}</td>
                        <td>
                          <button 
                            onClick={() => openMovementModal(product)} 
                            className="btn-small btn-primary"
                            title="Mouvement de stock"
                          >
                            Mouvement
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card full-width">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Produit</th>
                  <th>Type</th>
                  <th>Quantité</th>
                  <th>Raison</th>
                </tr>
              </thead>
              <tbody>
                {mouvements.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center">
                      Aucun mouvement enregistré
                    </td>
                  </tr>
                ) : (
                  mouvements.map((mouvement, index) => (
                    <tr key={index}>
                      <td>{formatDate(mouvement.created_at)}</td>
                      <td>{mouvement.produit_nom || mouvement.produit_id}</td>
                      <td>
                        <span className={`badge ${mouvement.type_mouvement === 'entree' ? 'success' : 'danger'}`}>
                          {mouvement.type_mouvement === 'entree' ? 'Entrée' : 'Sortie'}
                        </span>
                      </td>
                      <td>{mouvement.quantite}</td>
                      <td>{mouvement.raison || 'N/A'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showMovementModal && (
        <div className="modal-overlay" onClick={closeMovementModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Mouvement de stock</h2>
              <button onClick={closeMovementModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleMovementSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Produit *</label>
                  <select 
                    name="produit_id" 
                    value={movementData.produit_id}
                    onChange={handleMovementChange}
                    required
                  >
                    <option value="">Sélectionnez un produit</option>
                    {products.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.nom} (Stock: {p.quantite_stock || 0})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Type de mouvement *</label>
                  <select 
                    name="type_mouvement" 
                    value={movementData.type_mouvement}
                    onChange={handleMovementChange}
                    required
                  >
                    <option value="entree">Entrée (Approvisionnement)</option>
                    <option value="sortie">Sortie (Retrait)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Quantité *</label>
                  <input 
                    type="number" 
                    name="quantite" 
                    value={movementData.quantite}
                    onChange={handleMovementChange}
                    min="1"
                    required
                  />
                </div>
                <div className="form-group full-width">
                  <label>Raison</label>
                  <textarea 
                    name="raison" 
                    value={movementData.raison}
                    onChange={handleMovementChange}
                    placeholder="Ex: Livraison fournisseur, Retrait pour vente, etc."
                    rows="2"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeMovementModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={!movementData.produit_id}>
                  Enregistrer le mouvement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Inventory;
