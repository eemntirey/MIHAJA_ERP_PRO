import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import './Pages.css';

const ProductDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const { addItem } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);

  const isUser = (user?.role || '').toLowerCase() === 'user';
  const canBuy = isUser && isAuthenticated;

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true);
        const response = await publicCatalogueService.getProduit(id);
        const data = response.data?.produit || response.data || {};
        setProduct(data);
      } catch (err) {
        console.error('Error fetching product:', err);
        toast.error('Produit introuvable');
        navigate('/catalogue');
      } finally {
        setLoading(false);
      }
    };
    fetchProduct();
  }, [id]);

  const handleAddToCart = () => {
    addItem(product, quantity);
    toast.success(`${product.nom} ajouté au panier (${quantity})`);
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement du produit...</p>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>Produit introuvable</p>
          <Link to="/catalogue" className="btn-primary">Retour au catalogue</Link>
        </div>
      </div>
    );
  }

  const price = Number(product.prix_vente_ht || product.prix || 0);
  const stock = Number(product.quantite_stock ?? product.stock ?? 0);
  const maxQty = Math.min(stock, 99);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>{product.nom}</h1>
          {product.tenant_nom && (
            <p style={{ color: 'var(--erp-muted)', fontSize: '13px', marginTop: '4px' }}>
              Vendu par <strong>{product.tenant_nom}</strong>
            </p>
          )}
        </div>
        {canBuy && (
          <Link to="/cart" className="btn-secondary">
            Mon panier
          </Link>
        )}
      </div>

      <div className="card product-detail-grid">
        <div>
          <div style={{
            width: '100%', height: '0', paddingTop: '60%', background: 'var(--erp-paper)',
            borderRadius: '0', border: '1px solid var(--erp-line)', display: 'grid', placeItems: 'center',
            color: 'var(--erp-muted)', fontSize: '13px',
          }}>
            {product.image || product.photo ? (
              <img src={product.image || product.photo} alt={product.nom} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            ) : (
              'Visuel produit'
            )}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div className="public-card__subtitle" style={{ textTransform: 'uppercase', fontSize: '10px', letterSpacing: '0.1em' }}>
              {product.categorie || 'Général'}
            </div>
            <div className="product-card__price" style={{ fontSize: '26px', marginTop: '6px' }}>
              {price.toFixed(2)} Ar
            </div>
            <p className="text-muted" style={{ fontSize: '12px', marginTop: '8px' }}>
              Stock disponible : {stock} unité{stock > 1 ? 's' : ''}
            </p>
          </div>

          {product.description_longue && (
            <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--erp-muted)' }}>
              {product.description_longue}
            </p>
          )}

          {product.description_courte && !product.description_longue && (
            <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--erp-muted)' }}>
              {product.description_courte}
            </p>
          )}

          {product.marque && (
            <p style={{ fontSize: '13px' }}>
              <strong>Marque :</strong> {product.marque}
            </p>
          )}
          {product.reference && (
            <p style={{ fontSize: '13px' }}>
              <strong>Référence :</strong> {product.reference}
            </p>
          )}

          {canBuy ? (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="number"
                min="1"
                max={maxQty}
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, Math.min(maxQty, parseInt(e.target.value, 10) || 1)))}
                style={{ width: '70px', padding: '8px 10px', border: '1px solid var(--erp-line-strong)', fontFamily: 'var(--erp-body-font)', fontSize: '13px' }}
                aria-label="Quantité"
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleAddToCart}
                disabled={stock <= 0}
              >
                {stock <= 0 ? 'Rupture de stock' : 'Ajouter au panier'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '10px' }}>
              <Link to="/login" className="btn-primary">
                Se connecter pour commander
              </Link>
              <Link to="/catalogue" className="btn-secondary">
                ← Retour au catalogue
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
