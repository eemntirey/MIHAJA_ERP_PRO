// src/components/landing/Catalog.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { publicCatalogueService } from '../../services/api';
import '../../styles/landing.css';

const SKELETON_COUNT = 8;

const fmtStock = (qty) => {
  const n = Number(qty || 0);
  if (n <= 0) return 'Rupture';
  if (n < 10) return `Stock faible (${n})`;
  return `Stock: ${n}`;
};

const getImage = (produit) => {
  return produit.image_url || produit.image || produit.photo || null;
};

const Catalog = () => {
  const [produits, setProduits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchCatalogue = async () => {
    setLoading(true);
    setError('');
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

  useEffect(() => {
    fetchCatalogue();
  }, []);

  return (
    <section className="landing-section" id="catalogue" aria-labelledby="catalogue-titre">
      <div className="landing-container">
        <div className="landing-section-header">
          <h2 className="landing-section-title" id="catalogue-titre">Catalogue public</h2>
          <p className="landing-section-subtitle">
            Découvrez nos produits sélectionnés pour les établissements hôteliers.
          </p>
        </div>

        {loading && (
          <div className="landing-catalog-grid" role="status" aria-busy="true" aria-label="Chargement du catalogue">
            {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
              <div className="landing-catalog-skeleton" key={i}>
                <div className="landing-skeleton-visual" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
                  <div className="landing-skeleton-line short" />
                  <div className="landing-skeleton-line medium" />
                  <div className="landing-skeleton-line short" />
                </div>
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="landing-catalog-error" role="alert">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>{error}</p>
            <button type="button" onClick={fetchCatalogue}>Réessayer</button>
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="landing-catalog-grid">
              {produits.map((produit) => {
                const stock = Number(produit.quantite_stock ?? produit.stock ?? 0);
                const inStock = stock > 0;
                const category = produit.categorie_nom || produit.categorie || 'Général';
                const seller = produit.tenant_nom || produit.vendeur || 'Vendeur';
                const price = Number(produit.prix_vente_ht || produit.prix || 0);
                const image = getImage(produit);

                return (
                  <article className="landing-product-card" key={produit.id || produit._id}>
                    <div className="landing-product-visual">
                      {image ? (
                        <img src={image} alt={produit.nom || produit.name || 'Produit'} loading="lazy" />
                      ) : (
                        <span>IMG</span>
                      )}
                    </div>

                    <div className="landing-product-body">
                      <div className="landing-product-header">
                        <span className="landing-product-badge">{category}</span>
                        {inStock && <span className="landing-product-stock">{fmtStock(stock)}</span>}
                      </div>

                      <h3 className="landing-product-name">{produit.nom || produit.name || 'Produit'}</h3>

                      <div className="landing-product-meta">
                        <div className="landing-product-price">{price.toFixed(2)} Ar</div>
                        <div className="landing-product-seller" title={seller}>{seller}</div>
                      </div>

                      <div className="landing-product-actions">
                        <Link to={`/produits/${produit.id || produit._id}`} className="landing-btn landing-btn-fut" style={{ width: '100%' }}>
                          Voir
                        </Link>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            <div className="landing-catalog-cta">
              <Link to="/produits" className="landing-btn landing-btn-primary">
                Voir tout le catalogue
              </Link>
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default Catalog;
