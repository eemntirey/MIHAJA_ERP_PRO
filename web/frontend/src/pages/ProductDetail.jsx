// src/pages/ProductDetail.jsx
import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/api';
import Seo from '../components/Seo';
import { useCart } from '../contexts/CartContext';
import './Pages.css';
import PublicHeader from '../components/PublicHeader';

const ProductDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addItem } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);

  // Tout visiteur (connecté ou non) peut acheter via la vitrine publique
  const canBuy = true;

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
        navigate('/');
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
        <PublicHeader />
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
        <PublicHeader />
        <div className="alert error">
          <p>Produit introuvable</p>
          <Link to="/" className="btn-primary">Retour au catalogue</Link>
        </div>
      </div>
    );
  }

  const price = Number(product.prix_vente_ht || product.prix || 0);
  const formatMGA = (value) => Number(value || 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  const stock = Number(product.quantite_stock ?? product.stock ?? 0);
  const maxQty = Math.min(stock, 99);
  const productDescription =
    product.description_longue ||
    product.description_courte ||
    `Découvrez ${product.nom} sur MIHAJA ERP PRO.`;
  const productImage = product.image_url || product.image || product.photo || undefined;
  const productStructuredData = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.nom,
    description: productDescription,
    sku: product.reference || undefined,
    image: productImage,
    brand: product.marque
      ? { '@type': 'Brand', name: product.marque }
      : undefined,
    offers: {
      '@type': 'Offer',
      url: `https://erp.sekoliko.com/produits/${id}`,
      priceCurrency: 'MGA',
      price: price,
      availability: stock > 0
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
  };

  return (
    <>
      <Seo
        title={`${product.nom} | MIHAJA ERP PRO`}
        description={productDescription.slice(0, 160)}
        canonical={`https://erp.sekoliko.com/produits/${id}`}
        type="product"
        image={productImage}
        structuredData={productStructuredData}
      />
      <div className="page-container public-product-page">
        <PublicHeader />
        <div className="page-header public-product-header">
        <div>
          <h1>{product.nom}</h1>
          {product.tenant_nom && (
            <p className="public-product-seller">
              Vendu par <strong>{product.tenant_nom}</strong>
            </p>
          )}
        </div>
        {canBuy && (
          <div className="header-actions">
            <Link to="/catalogue" className="btn-secondary">Catalogue</Link>
            <Link to="/cart" className="btn-primary">Mon panier</Link>
          </div>
        )}
      </div>

      <div className="card product-detail-grid public-product-detail">
        <div>
          <div className="public-product-visual">
            {product.image_url || product.image || product.photo ? (
              <img src={product.image_url || product.image || product.photo} alt={product.nom} />
            ) : (
              <div className="public-product-placeholder">
                <i className="ti ti-package" aria-hidden="true" />
                <span>Visuel produit indisponible</span>
              </div>
            )}
          </div>
        </div>

        <div className="public-product-info">
          <div>
            <div className="public-product-category">
              {product.categorie || 'Général'}
            </div>
            <div className="public-product-price">
              {formatMGA(price)} Ar
            </div>
            <p className="public-product-stock">
              <i className={stock > 0 ? 'ti ti-circle-check' : 'ti ti-alert-circle'} aria-hidden="true" />
              Stock disponible : {stock} unité{stock > 1 ? 's' : ''}
            </p>
          </div>

          {product.description_longue && (
            <p className="public-product-description">{product.description_longue}</p>
          )}

          {product.description_courte && !product.description_longue && (
            <p className="public-product-description">{product.description_courte}</p>
          )}

          {product.marque && (
            <p className="public-product-meta"><strong>Marque :</strong> {product.marque}</p>
          )}
          {product.reference && (
            <p className="public-product-meta"><strong>Référence :</strong> {product.reference}</p>
          )}

          {canBuy ? (
            <div className="public-product-buy">
              <label className="public-product-quantity">
                <span>Quantité</span>
                <input
                  type="number"
                  min="1"
                  max={maxQty || 1}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, Math.min(Math.max(maxQty, 1), parseInt(e.target.value, 10) || 1)))}
                  aria-label="Quantité"
                />
              </label>
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
              <Link to="/" className="btn-secondary">
                ← Retour au catalogue
              </Link>
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
};

export default ProductDetail;
