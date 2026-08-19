// src/pages/Suivi.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { publicCatalogueService } from '../services/publicApi';
import { Icon } from '../components/common/Icon';
import './Pages.css';

const Suivi = () => {
  const [ref, setRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ref.trim()) return;
    setLoading(true);
    setError('');
    setTracking(null);
    try {
      const response = await publicCatalogueService.getCommandeTracking(ref.trim());
      setTracking(response.data);
    } catch (err) {
      const msg = err.response?.data?.message || 'Commande introuvable. Vérifiez la référence.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    const s = (status || '').toLowerCase();
    if (s.includes('attente') || s.includes('pending')) return 'warning';
    if (s.includes('confirm') || s.includes('prepa')) return 'info';
    if (s.includes('expedi') || s.includes('expedie')) return 'info';
    if (s.includes('livr')) return 'success';
    if (s.includes('annul')) return 'danger';
    return 'info';
  };

  return (
    <div className="home-page">
      <div className="home-content page-container">
        <div className="page-header">
          <div>
            <h1>Suivi de commande</h1>
            <p>Consultez l'état de votre commande grâce à sa référence.</p>
          </div>
          <Link to="/" className="btn-secondary">Retour à l'accueil</Link>
        </div>

        <div className="public-card">
          <div className="public-card__header">
            <div className="public-card__title">Entrez votre référence</div>
          </div>
          <hr className="public-divider" />
          <form onSubmit={handleSubmit} className="orders-track">
            <div className="orders-track__field">
              <Icon name="search" className="orders-track__icon" />
              <input
                type="text"
                placeholder="Ex : CMD-2024-0001"
                value={ref}
                onChange={(e) => setRef(e.target.value)}
                aria-label="Référence de commande"
              />
            </div>
            <button type="submit" className="btn-primary orders-track__btn" disabled={loading || !ref.trim()}>
              {loading ? 'Recherche...' : 'Rechercher'}
            </button>
          </form>

          {error && (
            <div className="alert error" style={{ marginTop: '16px' }}>
              <p>{error}</p>
            </div>
          )}

          {tracking && !loading && (
            <div style={{ marginTop: '20px' }}>
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
                    <span className={`badge ${getStatusBadgeClass(tracking.statut || tracking.status)}`}>
                      {tracking.statut || tracking.status || 'INCONNU'}
                    </span>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-content">
                    <p className="stat-label">Montant</p>
                    <p className="stat-value" style={{ fontSize: '16px' }}>
                      {Number(tracking.total_ttc || tracking.total_ht || tracking.montant_total || 0).toFixed(2)} Ar
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
          )}
        </div>
      </div>
    </div>
  );
};

export default Suivi;
