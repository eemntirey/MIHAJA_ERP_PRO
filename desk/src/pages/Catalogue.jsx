// src/pages/Catalogue.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import { Icon } from '../components/common/Icon';
import './Pages.css';

const Catalogue = () => {
  const { user, isAuthenticated } = useAuth();
  const { addItem } = useCart();
  const [produits, setProduits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isUser = (user?.role || '').toLowerCase() === 'user';
  const canBuy = isUser && isAuthenticated;

  useEffect(() => {
    fetchCatalogue();
  }, []);

  const fetchCatalogue = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await publicCatalogueService.getProduits();
      const data = response.data;
      setProduits(Array.isArray(data) ? data : data?.produits || data?.items || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Impossible de charger le catalogue.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-page">
      <div className="home-content page-container">
        <div className="page-header">
          <div>
            <h1>Catalogue public</h1>
            <p>Découvrez nos produits disponibles</p>
          </div>
          <Link to="/" className="btn-secondary">Retour à l'accueil</Link>
        </div>

        {loading && (
          <div className="loading-screen">
            <div className="spinner-large"></div>
            <p>Chargement du catalogue...</p>
          </div>
        )}

        {error && !loading && (
          <div className="alert error">
            <p>{error}</p>
            <button onClick={fetchCatalogue} className="btn-primary">Réessayer</button>
          </div>
        )}

        {!loading && !error && (
          <div className="home-products-grid">
            {produits.length === 0 ? (
              <div className="card full-width">
                <p className="text-muted">Aucun produit disponible pour le moment.</p>
              </div>
            ) : (
              produits.map((produit) => {
                const stock = Number(produit.quantite_stock ?? produit.stock ?? 0);
                const price = Number(produit.prix_vente_ht || produit.prix || 0);
                return (
                  <div className="card product-card" key={produit.id || produit._id}>
                    <div className="product-card__header">
                      <h3>{produit.nom || produit.name || 'Produit'}</h3>
                      <span className="badge success">En stock</span>
                    </div>
                    {produit.tenant_nom && (
                      <p style={{ fontSize: '12px', color: 'var(--erp-muted)', marginBottom: '8px' }}>
                        Vendu par <strong>{produit.tenant_nom}</strong>
                      </p>
                    )}
                    <p className="product-card__price">{price.toFixed(2)} Ar</p>
                    <p className="text-muted" style={{ fontSize: '12px', marginBottom: '12px' }}>
                      Stock: {stock}
                    </p>
                    {produit.description_courte && (
                      <p style={{ fontSize: '13px', marginBottom: '16px', color: 'var(--erp-muted)' }}>
                        {produit.description_courte}
                      </p>
                    )}
                    {canBuy ? (
                      <div className="product-card__actions" style={{ display: 'flex', gap: '8px' }}>
                        <Link
                          to={`/produits/${produit.id || produit._id}`}
                          className="btn-secondary"
                          style={{ flex: 1, justifyContent: 'center' }}
                        >
                          Détails
                        </Link>
                        <button
                          type="button"
                          className="btn-primary"
                          style={{ flex: 1, justifyContent: 'center' }}
                          onClick={() => {
                            addItem(produit, 1);
                            toast.success(`${produit.nom || produit.name} ajouté au panier`);
                          }}
                          disabled={stock <= 0}
                        >
                          + Panier
                        </button>
                      </div>
                    ) : (
                      <Link
                        to={`/produits/${produit.id || produit._id}`}
                        className="btn-primary"
                        style={{ width: '100%', justifyContent: 'center' }}
                      >
                        Voir le produit
                      </Link>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Catalogue;
