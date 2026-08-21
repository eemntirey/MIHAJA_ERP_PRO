import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import './Pages.css';

const Checkout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cart: ctxCart, clearCart } = useCart();
  const cart = ctxCart.length ? ctxCart : (location.state?.cart || []);

  const [loading, setLoading] = useState(cart.length === 0);
  const [submitting, setSubmitting] = useState(false);
  const [orderRef, setOrderRef] = useState(null);
  const [products, setProducts] = useState([]);

  const [formData, setFormData] = useState({
    nom: user?.nom || '',
    prenom: user?.prenom || '',
    email: user?.email || '',
    telephone: '',
    adresse: '',
    ville: '',
    code_postal: '',
    pays: 'Madagascar',
  });

  useEffect(() => {
    const fetchProducts = async () => {
      if (cart.length === 0) {
        setLoading(false);
        return;
      }
      try {
        const promises = cart.map(item => publicCatalogueService.getProduit(item.id || item.produit_id));
        const responses = await Promise.all(promises);
        setProducts(responses.map(r => r.data?.produit || r.data));
      } catch (err) {
        toast.error('Erreur chargement produits');
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, [cart]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const items = cart.map(item => ({
        produit_id: item.id || item.produit_id,
        quantite: item.quantite || 1,
      }));
      const payload = {
        client: {
          nom: formData.nom,
          prenom: formData.prenom,
          email: formData.email,
          telephone: formData.telephone,
          adresse: formData.adresse,
          ville: formData.ville,
          code_postal: formData.code_postal,
          pays: formData.pays,
        },
        items,
      };
      const response = await publicCatalogueService.createCommande(payload);
      const resData = response.data;
      const ref = resData?.commande?.reference || resData?.reference || resData?.ref || resData?.numero_commande || resData?.commande;
      setOrderRef(ref);
      clearCart();
      toast.success('Commande créée avec succès');
    } catch (err) {
      console.error('Error creating order:', err);
      const msg = err.response?.data?.message || 'Échec de la création de la commande';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const qrData = orderRef ? `${window.location.origin}/order-tracking/${orderRef}` : '';
  const qrUrl = qrData ? `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(qrData)}` : '';

  const orderTotal = products.reduce((sum, product) => {
    const productId = product.id || product.produit_id;
    const cartItem = cart.find(item => item.id === productId || item.produit_id === productId);
    const qty = cartItem?.quantite || 1;
    const price = Number(product.prix_vente_ht || product.prix || 0);
    return sum + price * qty;
  }, 0);

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement...</p>
        </div>
      </div>
    );
  }

  if (cart.length === 0 && !orderRef) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>Panier vide</p>
          <Link to="/" className="btn-primary">Retour à l'accueil</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="public-card" style={{ marginBottom: '18px' }}>
        <div className="public-card__header">
          <div>
            <div className="public-card__title">Commander</div>
            <div className="public-card__subtitle">Finalisez votre commande</div>
          </div>
        </div>
      </div>

      {!orderRef ? (
        <div className="checkout-layout">
          <div className="public-card">
            <div className="public-card__header">
              <div className="public-card__title">Produits sélectionnés</div>
            </div>
            <hr className="public-divider" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {products.map((product, idx) => {
                const cartItem = cart[idx];
                const qty = cartItem?.quantite || 1;
                const price = Number(product.prix_vente_ht || product.prix || 0);
                return (
                  <div key={product.id || idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <p style={{ fontWeight: 700, fontSize: '15px' }}>{product.nom}</p>
                      <p className="public-card__subtitle">Quantité: {qty}</p>
                    </div>
                    <p style={{ fontFamily: 'var(--erp-heading-font)', fontWeight: 800, fontSize: '18px' }}>
                      {(price * qty).toFixed(2)} Ar
                    </p>
                  </div>
                );
              })}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', borderTop: '1px solid var(--erp-border)', paddingTop: '12px' }}>
                <p style={{ fontWeight: 700, fontSize: '15px' }}>Total</p>
                <p style={{ fontFamily: 'var(--erp-heading-font)', fontWeight: 800, fontSize: '20px', color: 'var(--erp-primary)' }}>
                  {orderTotal.toFixed(2)} Ar
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="public-card" style={{ marginTop: '24px' }}>
            <div className="public-card__header">
              <div className="public-card__title">Vos coordonnées</div>
            </div>
            <hr className="public-divider" />
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="nom">Nom</label>
                <input id="nom" name="nom" value={formData.nom} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="prenom">Prénom</label>
                <input id="prenom" name="prenom" value={formData.prenom} onChange={handleChange} required />
              </div>
              <div className="form-group full-width">
                <label htmlFor="email">Email</label>
                <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="telephone">Téléphone</label>
                <input id="telephone" name="telephone" value={formData.telephone} onChange={handleChange} required />
              </div>
              <div className="form-group full-width">
                <label htmlFor="adresse">Adresse de livraison</label>
                <input id="adresse" name="adresse" value={formData.adresse} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="ville">Ville</label>
                <input id="ville" name="ville" value={formData.ville} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="code_postal">Code postal</label>
                <input id="code_postal" name="code_postal" value={formData.code_postal} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="pays">Pays</label>
                <select id="pays" name="pays" value={formData.pays} onChange={handleChange}>
                  <option value="Madagascar">Madagascar</option>
                  <option value="Comores">Comores</option>
                  <option value="Maurice">Maurice</option>
                  <option value="Seychelles">Seychelles</option>
                  <option value="Tanzanie">Tanzanie</option>
                  <option value="Kenya">Kenya</option>
                </select>
              </div>
            </div>
            <button type="submit" className="btn-primary" style={{ marginTop: '18px', width: '100%' }} disabled={submitting}>
              {submitting ? 'Traitement...' : 'Confirmer la commande'}
            </button>
          </form>
        </div>
      ) : (
        <div className="public-card" style={{ textAlign: 'center', padding: '32px' }}>
          <h2 style={{ color: 'var(--erp-success)' }}>Commande confirmée !</h2>
          <p>Référence: <strong>{orderRef}</strong></p>
          {qrUrl && <img src={qrUrl} alt="QR Code" style={{ margin: '16px auto' }} />}
          <p style={{ marginTop: '12px' }}>Utilisez ce QR code pour suivre votre commande.</p>
          <Link to={`/order-tracking/${orderRef}`} className="btn-primary" style={{ marginTop: '12px' }}>Suivre ma commande</Link>
        </div>
      )}
    </div>
  );
};

export default Checkout;
