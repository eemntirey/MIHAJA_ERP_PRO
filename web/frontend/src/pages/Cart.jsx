// src/pages/Cart.jsx
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useCart } from '../contexts/CartContext';
import './Pages.css';

const Cart = () => {
  const navigate = useNavigate();
  const { cart, removeItem, updateQuantity, clearCart, totalItems, totalPrice } = useCart();

  const handleCheckout = () => {
    if (cart.length === 0) return;
    navigate('/checkout', { state: { cart } });
    toast.info('Finalisez votre commande');
  };

  if (cart.length === 0) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1>Votre panier</h1>
            <p>Votre panier est actuellement vide.</p>
          </div>
          <Link to="/" className="btn-primary">Retour au catalogue</Link>
        </div>
        <div className="card full-width" style={{ marginTop: '24px', textAlign: 'center', padding: '48px' }}>
          <p style={{ color: 'var(--erp-muted)', marginBottom: '16px' }}>
            Aucun article dans le panier. Découvrez nos produits publics.
          </p>
          <Link to="/" className="btn-primary">Découvrir le catalogue</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Votre panier</h1>
          <p>{totalItems} article{totalItems > 1 ? 's' : ''} sélectionné{totalItems > 1 ? 's' : ''}</p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn-secondary" onClick={clearCart}>
            Vider le panier
          </button>
          <Link to="/" className="btn-primary">Continuer les courses</Link>
        </div>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Produit</th>
              <th>Vendu par</th>
              <th className="text-center">Qté</th>
              <th className="text-center">Prix</th>
              <th className="text-center">Total</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cart.map((item, idx) => {
              const key = item.id || item.reference || item._id || `cart-item-${idx}`;
              const price = Number(item.prix_vente_ht || item.prix || 0);
              const qty = item.quantite;
              return (
                <tr key={key}>
                  <td>
                    <strong>{item.nom}</strong>
                    <div style={{ fontSize: '11px', color: 'var(--erp-muted)' }}>
                      Réf. {item.reference}
                    </div>
                  </td>
                  <td>{item.tenant_nom || '-'}</td>
                  <td className="text-center">
                    <input
                      type="number"
                      min="1"
                      max={Number(item.quantite_stock ?? item.stock ?? 0)}
                      value={qty}
                      onChange={(e) => updateQuantity(item, Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="qty-input"
                      style={{ width: '60px', textAlign: 'center' }}
                      aria-label={`Quantité de ${item.nom}`}
                    />
                  </td>
                  <td className="text-center">{price.toFixed(2)} Ar</td>
                  <td className="text-center">{(price * qty).toFixed(2)} Ar</td>
                  <td className="text-center">
                    <button
                      type="button"
                      className="btn-small btn-delete"
                      onClick={() => removeItem(item)}
                      aria-label={`Retirer ${item.nom}`}
                    >
                      <i className="ti ti-x" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div className="stat-label">Total du panier</div>
          <div className="stat-value">{totalPrice.toFixed(2)} Ar</div>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <Link to="/" className="btn-secondary">Continuer les courses</Link>
          <button type="button" className="btn-primary" onClick={handleCheckout}>
            Passer commande
          </button>
        </div>
      </div>
    </div>
  );
};

export default Cart;
