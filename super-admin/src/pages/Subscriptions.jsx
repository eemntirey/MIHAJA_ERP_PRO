import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { superAdminSubscriptionService } from '../services/api';

const Subscriptions = () => {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const perPage = 15;

  const fetchSubscriptions = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, per_page: perPage };
      if (statusFilter) params.statut = statusFilter;
      if (planFilter) params.plan = planFilter;
      const response = await superAdminSubscriptionService.getAll(params);
      const data = response.data || response;
      setSubscriptions(data.abonnements || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch {
      toast.error('Échec du chargement des abonnements');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, planFilter]);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  useEffect(() => {
    const handleSubscriptionUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id) {
        setSubscriptions(prev => {
          const exists = prev.some(s => s.id === updated.id);
          if (exists) {
            return prev.map(s => s.id === updated.id ? { ...s, ...updated } : s);
          }
          return [updated, ...prev];
        });
      } else {
        fetchSubscriptions();
      }
    };
    window.addEventListener('realtime:subscription:updated', handleSubscriptionUpdated);
    return () => window.removeEventListener('realtime:subscription:updated', handleSubscriptionUpdated);
  }, [fetchSubscriptions]);

  const getStatusBadge = (statut) => {
    const s = (statut || '').toLowerCase();
    if (s === 'actif') return 'badge-success';
    if (s === 'en_attente') return 'badge-warning';
    if (s === 'expire') return 'badge-danger';
    if (s === 'annule') return 'badge-info';
    return 'badge-info';
  };

  const handleStatusChange = (e) => {
    setStatusFilter(e.target.value);
    setPage(1);
  };

  const handlePlanChange = (e) => {
    setPlanFilter(e.target.value);
    setPage(1);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Abonnements</h1>
          <p>Tous les abonnements de la plateforme ({total} total)</p>
        </div>
        <button onClick={fetchSubscriptions} className="btn-secondary" disabled={loading}>
          Rafraîchir
        </button>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="filter-selects">
          <select value={statusFilter} onChange={handleStatusChange}>
            <option value="">Tous statuts</option>
            <option value="actif">Actif</option>
            <option value="en_attente">En attente</option>
            <option value="expire">Expiré</option>
            <option value="annule">Annulé</option>
          </select>
          <select value={planFilter} onChange={handlePlanChange}>
            <option value="">Tous plans</option>
            <option value="gratuit">Gratuit</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des abonnements...</p>
        </div>
      ) : (
        <>
          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tenant</th>
                    <th>Plan</th>
                    <th>Date début</th>
                    <th>Date fin</th>
                    <th>Statut</th>
                    <th>Montant</th>
                    <th>Méthode</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="text-center text-muted">
                        Aucun abonnement trouvé
                      </td>
                    </tr>
                  ) : (
                    subscriptions.map((sub) => (
                      <tr key={sub.id}>
                        <td>
                          {sub.tenant ? (
                            <div>
                              <div style={{ fontWeight: 600 }}>{sub.tenant.nom}</div>
                              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{sub.tenant.slug}</div>
                            </div>
                          ) : (
                            `Tenant #${sub.tenant_id}`
                          )}
                        </td>
                        <td>{sub.plan || '-'}</td>
                        <td>{sub.date_debut ? new Date(sub.date_debut).toLocaleDateString('fr-FR') : '-'}</td>
                        <td>{sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('fr-FR') : '-'}</td>
                        <td>
                          <span className={`badge ${getStatusBadge(sub.statut)}`}>
                            {sub.statut || 'INCONNU'}
                          </span>
                        </td>
                        <td>{sub.montant ? `${Number(sub.montant).toFixed(2)} Ar` : '-'}</td>
                        <td>{sub.methode_paiement || '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="pagination">
                <button
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  Précédent
                </button>
                <span className="pagination-info">
                  Page {page} sur {totalPages} ({total} abonnements)
                </span>
                <button
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Suivant
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Subscriptions;
