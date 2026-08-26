import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { publicCatalogueService } from '../../services/publicApi';
import '../../styles/landing.css';

const STEPS = ['Reçue', 'Préparation', 'Expédiée', 'Livrée'];

const OrderTracking = () => {
  const [ref, setRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
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
    } finally {
      setLoading(false);
    }
  };

  const getActiveStep = () => {
    if (!tracking) return -1;
    const status = (tracking.statut || tracking.status || '').toLowerCase();
    if (status.includes('attente') || status.includes('pending')) return 0;
    if (status.includes('confirm') || status.includes('prepa')) return 1;
    if (status.includes('expedi') || status.includes('expedie')) return 2;
    if (status.includes('livr')) return 3;
    if (status.includes('annul')) return -1;
    return 0;
  };

  const getStatusBadgeClass = (status) => {
    const s = (status || '').toLowerCase();
    if (s.includes('attente') || s.includes('pending')) return 'landing-badge warning';
    if (s.includes('confirm') || s.includes('prepa')) return 'landing-badge info';
    if (s.includes('expedi') || s.includes('expedie')) return 'landing-badge info';
    if (s.includes('livr')) return 'landing-badge success';
    if (s.includes('annul')) return 'landing-badge danger';
    return 'landing-badge info';
  };

  const activeStep = getActiveStep();

  return (
    <section className="landing-section" id="suivi" aria-labelledby="suivi-titre">
      <div className="landing-container">
        <div className="landing-section-header">
          <h2 className="landing-section-title" id="suivi-titre">Mes commandes</h2>
          <p className="landing-section-subtitle">
            Suivez votre commande en temps réel grâce à sa référence.
          </p>
        </div>

        <div className="landing-tracking-card">
          <form className="landing-tracking-form" onSubmit={handleSearch}>
            <label htmlFor="tracking-ref" className="landing-sr-only">
              Référence de commande
            </label>
            <input
              id="tracking-ref"
              className="landing-tracking-input"
              type="text"
              placeholder="Suivre une commande par référence..."
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              aria-label="Référence de commande"
              disabled={loading}
            />
            <button
              type="submit"
              className="landing-tracking-btn"
              disabled={loading || !ref.trim()}
              aria-busy={loading}
            >
              {loading ? 'Recherche...' : 'Rechercher'}
            </button>
          </form>

          {loading && (
            <div className="landing-tracking-loading" role="status">
              <div className="landing-spinner" />
              <span>Recherche en cours...</span>
            </div>
          )}

          {!tracking && !error && !loading && (
            <div className="landing-tracking-empty" role="status">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
              <p>Entrez une référence pour voir l&apos;état de votre commande.</p>
            </div>
          )}

          {error && (
            <div className="landing-tracking-error" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
              <button type="button" onClick={() => setError('')}>OK</button>
            </div>
          )}

          {tracking && !loading && (
            <div className="landing-tracking-result">
              <div className="landing-order-card">
                <div className="landing-order-card__header">
                  <div>
                    <div className="landing-order-card__ref">
                      Référence: {tracking.reference || tracking.ref || ref}
                    </div>
                    <div className="landing-order-card__date">
                      {tracking.created_at
                        ? `Commandée le ${new Date(tracking.created_at).toLocaleDateString('mg-MG')}`
                        : ''}
                    </div>
                  </div>
                  <span className={`landing-badge ${getStatusBadgeClass(tracking.statut || tracking.status)}`}>
                    {tracking.statut || tracking.status || 'INCONNU'}
                  </span>
                </div>

                <hr className="landing-divider" />

                {tracking.items && tracking.items.length > 0 && (
                  <div className="landing-order-items">
                    <div className="landing-order-items__title">Articles commandés</div>
                    <div className="landing-order-items__list">
                      {tracking.items.map((item, idx) => (
                        <div className="landing-order-item" key={idx}>
                          <div className="landing-order-item__name">
                            {item.produit_nom || item.nom || `Produit #${item.produit_id}`}
                          </div>
                          <div className="landing-order-item__meta">
                            <span>x{item.quantite || 1}</span>
                            <span>{Number(item.prix_unitaire || item.prix || 0).toFixed(2)} Ar</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="landing-order-card__footer">
                  <div className="landing-order-total">
                    Total: {Number(tracking.montant_total || tracking.total || 0).toFixed(2)} Ar
                  </div>
                </div>
              </div>

              <div className="landing-timeline" role="list" aria-label="Étapes de la commande">
                {STEPS.map((label, idx) => (
                  <div
                    className={`landing-timeline-step ${idx <= activeStep ? 'active' : ''}`}
                    key={label}
                    role="listitem"
                  >
                    <div className="landing-timeline-dot" />
                    <span className="landing-timeline-label">{label}</span>
                    {idx < STEPS.length - 1 && <span className="landing-timeline-line" />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default OrderTracking;
