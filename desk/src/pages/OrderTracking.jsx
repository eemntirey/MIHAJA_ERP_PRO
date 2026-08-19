import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import './Pages.css';

const OrderTracking = () => {
  const { ref } = useParams();
  const [tracking, setTracking] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notifLoading, setNotifLoading] = useState(false);

  useEffect(() => {
    const fetchTracking = async () => {
      try {
        setLoading(true);
        const response = await publicCatalogueService.getCommandeTracking(ref);
        setTracking(response.data);
      } catch (err) {
        console.error('Error fetching tracking:', err);
        const msg = err.response?.data?.message || 'Commande introuvable';
        toast.error(msg);
      } finally {
        setLoading(false);
      }
    };
    fetchTracking();
  }, [ref]);

  const fetchNotifications = async () => {
    try {
      setNotifLoading(true);
      const response = await publicCatalogueService.getNotifications(ref);
      setNotifications(response.data?.notifications || response.data || []);
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setNotifLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const map = {
      'EN_ATTENTE': 'warning',
      'CONFIRMEE': 'info',
      'EXPEDIEE': 'info',
      'LIVREE': 'success',
      'ANNULEE': 'danger',
    };
    return map[status] || 'info';
  };

  const qrData = `${window.location.origin}/order-tracking/${ref}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(qrData)}`;

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement du suivi...</p>
        </div>
      </div>
    );
  }

  if (!tracking) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>Commande introuvable. Vérifiez la référence.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="public-card" style={{ marginBottom: '18px' }}>
        <div className="public-card__header">
          <div>
            <div className="public-card__title">Suivi de commande</div>
            <div className="public-card__subtitle">Référence: {ref}</div>
          </div>
          <div className="header-actions">
            <button onClick={fetchNotifications} className="btn-secondary" disabled={notifLoading}>
              {notifLoading ? 'Actualisation...' : 'Actualiser les notifications'}
            </button>
            <Link to="/catalogue" className="btn-primary">Retour au catalogue</Link>
          </div>
        </div>
      </div>

      <div className="tracking-layout">
        <div className="public-card">
          <div className="public-card__header">
            <div className="public-card__title">Détails de la commande</div>
          </div>
          <hr className="public-divider" />
          <div className="stats-grid mini">
            <div className="stat-card">
              <div className="stat-content">
                <p className="stat-label">Référence</p>
                <p className="stat-value" style={{ fontSize: '16px' }}>{tracking.reference || tracking.ref || ref}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-content">
                <p className="stat-label">Statut</p>
                <span className={`badge ${getStatusBadge(tracking.statut || tracking.status)}`}>
                  {tracking.statut || tracking.status || 'INCONNU'}
                </span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-content">
                <p className="stat-label">Montant total</p>
                <p className="stat-value" style={{ fontSize: '16px' }}>
                  {Number(tracking.total_ttc || tracking.total_ht || 0).toFixed(2)} Ar
                </p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-content">
                <p className="stat-label">Date</p>
                <p className="stat-value" style={{ fontSize: '16px' }}>
                  {tracking.created_at ? new Date(tracking.created_at).toLocaleDateString('mg-MG') : '-'}
                </p>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '20px', display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--erp-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                QR Code
              </p>
              <div style={{ padding: '12px', background: 'var(--erp-white)', borderRadius: '8px', border: '1px solid var(--erp-line)', display: 'inline-block' }}>
                <img src={qrUrl} alt="QR Code de suivi" style={{ display: 'block' }} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--erp-muted)', marginTop: '6px', fontFamily: 'monospace' }}>
                {ref}
              </p>
            </div>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--erp-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Code barre texte
              </p>
              <div style={{ 
                padding: '12px 16px', 
                background: 'var(--erp-onyx)', 
                borderRadius: '6px', 
                fontFamily: 'monospace', 
                fontSize: '18px', 
                letterSpacing: '4px',
                color: 'var(--erp-white)',
                textAlign: 'center',
                userSelect: 'all'
              }}>
                {ref}
              </div>
              <p style={{ fontSize: '11px', color: 'var(--erp-muted)', marginTop: '6px' }}>
                Scannez ou copiez la référence pour suivre votre commande
              </p>
            </div>
          </div>

          {tracking.items && tracking.items.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <h4 style={{ marginBottom: '12px', fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--erp-muted)' }}>
                Articles
              </h4>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Produit</th>
                      <th>Quantité</th>
                      <th>Prix unitaire</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tracking.items.map((item, idx) => (
                      <tr key={idx}>
                        <td>{item.produit_nom || item.nom || `Produit #${item.produit_id}`}</td>
                        <td>{item.quantite || 1}</td>
                        <td>{Number(item.prix_unitaire || item.prix || 0).toFixed(2)} Ar</td>
                        <td>{Number(item.total || ((item.prix_unitaire || item.prix || 0) * (item.quantite || 1))).toFixed(2)} Ar</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="public-card" style={{ marginTop: '24px' }}>
          <div className="public-card__header">
            <div className="public-card__title">Notifications</div>
          </div>
          <hr className="public-divider" />
          {notifications.length === 0 ? (
            <p className="public-empty">Aucune notification disponible.</p>
          ) : (
            <div className="public-list">
              {notifications.map((notif, idx) => (
                <div className="public-list-item" key={idx}>
                  <div>
                    <div className="public-list-item__primary">{notif.message || JSON.stringify(notif)}</div>
                    <div className="public-list-item__secondary">{notif.created_at || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderTracking;
