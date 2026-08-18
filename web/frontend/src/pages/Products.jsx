// src/pages/Products.jsx
import React, { useState, useEffect } from 'react';
import { productService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [currentProduct, setCurrentProduct] = useState(null);
  const [formData, setFormData] = useState({
    nom: '',
    reference: '',
    description_courte: '',
    prix_achat_ht: 0,
    prix_vente_ht: 0,
    quantite_stock: 0,
    categorie: '',
    code_barre: '',
    seuil_alerte: 0,
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const fetchProducts = async () => {
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
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: ['prix_achat_ht', 'prix_vente_ht', 'quantite_stock', 'seuil_alerte'].includes(name)
        ? parseFloat(value) || 0
        : value
    }));
  };

  const openModal = (product = null) => {
    setCurrentProduct(product);
    setFormData(product ? {
      nom: product.nom || '',
      reference: product.reference || '',
      description_courte: product.description_courte || product.description || '',
      prix_achat_ht: product.prix_achat_ht || 0,
      prix_vente_ht: product.prix_vente_ht || 0,
      quantite_stock: product.quantite_stock || 0,
      categorie: product.categorie || '',
      code_barre: product.code_barre || '',
      seuil_alerte: product.seuil_alerte || 0,
    } : {
      nom: '',
      reference: '',
      description_courte: '',
      prix_achat_ht: 0,
      prix_vente_ht: 0,
      quantite_stock: 0,
      categorie: '',
      code_barre: '',
      seuil_alerte: 0,
    });
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

  const getStockStatus = (quantite, seuil) => {
    if (quantite <= seuil) return 'danger';
    if (quantite <= seuil * 1.5) return 'warning';
    return 'success';
  };

  const categories = [...new Set(products.map(p => p.categorie).filter(Boolean))];

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.code_barre?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !categoryFilter || product.categorie === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const totalStockValue = products.reduce((sum, p) => sum + ((p.prix_achat_ht || 0) * (p.quantite_stock || 0)), 0);

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
            {products.filter(p => p.quantite_stock <= (p.seuil_alerte || 0)).length}
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
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card full-width">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Nom</th>
                <th>Catégorie</th>
                <th>Prix d'achat</th>
                <th>Prix de vente</th>
                <th>Marge</th>
                <th>Valeur stock</th>
                <th>Stock</th>
                <th>Seuil min.</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan="10" className="text-center">
                    Aucun produit trouvé
                  </td>
                </tr>
              ) : (
                filteredProducts.map(product => {
                  const margin = product.prix_vente_ht && product.prix_achat_ht && product.prix_achat_ht > 0
                    ? ((product.prix_vente_ht - product.prix_achat_ht) / product.prix_achat_ht * 100).toFixed(1)
                    : 0;
                  const stockValue = (product.prix_achat_ht || 0) * (product.quantite_stock || 0);
                  return (
                    <tr key={product.id}>
                      <td>{product.code_barre || product.id}</td>
                      <td>{product.nom}</td>
                      <td>{product.categorie || 'N/A'}</td>
                      <td>{product.prix_achat_ht?.toFixed(2) || '0.00'} Ar</td>
                      <td>{product.prix_vente_ht?.toFixed(2) || '0.00'} Ar</td>
                      <td>{margin}%</td>
                      <td>{stockValue.toFixed(2)} Ar</td>
                      <td>
                        <span className={`badge ${getStockStatus(product.quantite_stock || 0, product.seuil_alerte || 0)}`}>
                          {product.quantite_stock || 0}
                        </span>
                      </td>
                      <td>{product.seuil_alerte || 0}</td>
                      <td>
                        <button 
                          onClick={() => openModal(product)} 
                          className="btn-small btn-edit"
                          title="Modifier"
                        >
                          <i className="ti ti-edit" aria-hidden="true" />
                        </button>
                        <button 
                          onClick={() => handleDelete(product.id)} 
                          className="btn-small btn-delete"
                          title="Supprimer"
                        >
                          <i className="ti ti-trash" aria-hidden="true" />
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

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{currentProduct ? 'Modifier le produit' : 'Ajouter un nouveau produit'}</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Nom *</label>
                  <input 
                    type="text" 
                    name="nom" 
                    value={formData.nom}
                    onChange={handleChange}
                    required
                    placeholder="Nom du produit"
                  />
                </div>
                <div className="form-group">
                  <label>Référence *</label>
                  <input 
                    type="text" 
                    name="reference" 
                    value={formData.reference}
                    onChange={handleChange}
                    required
                    placeholder="Référence produit"
                  />
                </div>
                <div className="form-group">
                  <label>Code barre</label>
                  <input 
                    type="text" 
                    name="code_barre" 
                    value={formData.code_barre}
                    onChange={handleChange}
                    placeholder="Code barre"
                  />
                </div>
                <div className="form-group">
                  <label>Catégorie</label>
                  <input 
                    type="text" 
                    name="categorie" 
                    value={formData.categorie}
                    onChange={handleChange}
                    placeholder="Catégorie"
                    list="categories"
                  />
                  <datalist id="categories">
                    {categories.map(cat => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </div>
                <div className="form-group">
                  <label>Description courte</label>
                  <textarea 
                    name="description_courte" 
                    value={formData.description_courte}
                    onChange={handleChange}
                    placeholder="Description courte du produit"
                    rows="2"
                  />
                </div>
                <div className="form-group">
                  <label>Prix d'achat HT (Ar)</label>
                  <input 
                    type="number" 
                    name="prix_achat_ht" 
                    value={formData.prix_achat_ht}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>Prix de vente HT (Ar)</label>
                  <input 
                    type="number" 
                    name="prix_vente_ht" 
                    value={formData.prix_vente_ht}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>Quantité en stock</label>
                  <input 
                    type="number" 
                    name="quantite_stock" 
                    value={formData.quantite_stock}
                    onChange={handleChange}
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label>Seuil alerte</label>
                  <input 
                    type="number" 
                    name="seuil_alerte" 
                    value={formData.seuil_alerte}
                    onChange={handleChange}
                    min="0"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={!formData.nom}>
                  {currentProduct ? 'Mettre à jour' : 'Ajouter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Products;
