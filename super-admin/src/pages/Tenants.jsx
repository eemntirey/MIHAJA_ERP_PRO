import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { superAdminTenantService } from '../services/api';
import ConfirmModal from '../components/common/ConfirmModal';

const Tenants = () => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [confirmAction, setConfirmAction] = useState(null);
  const navigate = useNavigate();

  const perPage = 15;

  const fetchTenants = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, per_page: perPage };
      if (search) params.search = search;
      if (statusFilter) params.statut = statusFilter;
      if (planFilter) params.plan = planFilter;
      const response = await superAdminTenantService.getAll(params);
      const data = response.data || response;
      setTenants(data.tenants || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error('Échec du chargement des tenants');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, planFilter]);

  const visibleTenants = useMemo(
    () => tenants.filter(t => t.is_active !== false),
    [tenants]
  );

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  useEffect(() => {
    const handleTenantUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id) {
        if (updated.is_active === false) {
          setTenants(prev => prev.filter(t => t.id !== updated.id));
          fetchTenants();
        } else {
          setTenants(prev => prev.map(t => t.id === updated.id ? updated : t));
        }
      } else {
        fetchTenants();
      }
    };
    window.addEventListener('realtime:tenant:updated', handleTenantUpdated);
    return () => window.removeEventListener('realtime:tenant:updated', handleTenantUpdated);
  }, [fetchTenants]);

  const handleDeletePermanent = async (id, nom) => {
    setConfirmAction({
      title: 'Supprimer définitivement le tenant',
      message: `Êtes-vous sûr de vouloir supprimer le tenant "${nom}" ?`,
      warning: 'Cette action est IRRÉVERSIBLE. Toutes les données du tenant (utilisateurs, employés, produits, clients, ventes, factures, etc.) seront supprimées définitivement.',
      confirmText: 'Supprimer définitivement',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        try {
          await superAdminTenantService.delete(id);
          toast.success('Tenant et toutes ses données supprimés');
          setTenants(prev => prev.filter(t => t.id !== id));
          fetchTenants();
        } catch (err) {
          toast.error(err.response?.data?.message || 'Échec de la suppression');
        }
        setConfirmAction(null);
      },
    });
  };

  const handleActivate = async (id) => {
    try {
      await superAdminTenantService.activate(id);
      toast.success('Tenant activé');
      setTenants(prev => prev.map(t => t.id === id ? { ...t, statut: 'actif' } : t));
      fetchTenants();
    } catch (err) {
      toast.error(err.response?.data?.message || "Échec de l'activation");
    }
  };

  const handleReactivate = async (id) => {
    try {
      await superAdminTenantService.reactivate(id);
      toast.success('Tenant réactivé');
      fetchTenants();
    } catch (err) {
      toast.error(err.response?.data?.message || "Échec de la réactivation");
    }
  };

  const handleSuspend = async (id) => {
    try {
      await superAdminTenantService.suspend(id);
      toast.success('Tenant suspendu');
      setTenants(prev => prev.map(t => t.id === id ? { ...t, statut: 'bloque' } : t));
      fetchTenants();
    } catch (err) {
      toast.error(err.response?.data?.message || "Échec de la suspension");
    }
  };

  const getStatusBadge = (statut) => {
    const s = (statut || '').toLowerCase();
    if (s === 'actif') return 'badge-success';
    if (s === 'inactif' || s === 'bloque') return 'badge-danger';
    if (s === 'en_essai') return 'badge-warning';
    return 'badge-info';
  };

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
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
          <h1>Tenants</h1>
          <p>Gestion de l'ensemble des tenants de la plateforme ({total} total)</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div className="search-box" style={{ flex: 1, minWidth: '240px' }}>
            <input
              type="text"
              placeholder="Rechercher par nom, slug, email..."
              value={search}
              onChange={handleSearchChange}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          <select value={statusFilter} onChange={handleStatusChange} style={{ width: '180px' }}>
            <option value="">Tous statuts</option>
            <option value="actif">Actif</option>
            <option value="inactif">Inactif</option>
            <option value="en_essai">En essai</option>
            <option value="bloque">Bloqué</option>
          </select>
          <select value={planFilter} onChange={handlePlanChange} style={{ width: '180px' }}>
            <option value="">Tous plans</option>
            <option value="gratuit">Gratuit</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
          <button onClick={fetchTenants} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des tenants...</p>
        </div>
      ) : (
        <>
          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nom</th>
                    <th>Slug</th>
                    <th>Email</th>
                    <th>Plan</th>
                    <th>Statut</th>
                    <th>Utilisateurs</th>
                    <th>Créé le</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleTenants.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="text-center text-muted">
                        Aucun tenant trouvé
                      </td>
                    </tr>
                  ) : (
                    visibleTenants.map((tenant) => (
                      <tr key={tenant.id}>
                        <td>
                          <a
                            href="#"
                            onClick={(e) => { e.preventDefault(); navigate(`/tenants/${tenant.id}`); }}
                            style={{ fontWeight: 600 }}
                          >
                            {tenant.nom}
                          </a>
                        </td>
                        <td>{tenant.slug}</td>
                        <td>{tenant.email_contact || '-'}</td>
                        <td>{tenant.plan}</td>
                        <td>
                          <span className={`badge ${getStatusBadge(tenant.statut)}`}>
                            {tenant.statut || 'INCONNU'}
                          </span>
                        </td>
                        <td>{tenant.utilisateurs_count ?? '-'}</td>
                        <td>{tenant.created_at ? new Date(tenant.created_at).toLocaleDateString('fr-FR') : '-'}</td>
                        <td>
                          <button
                            onClick={() => navigate(`/tenants/${tenant.id}`)}
                            className="btn-small btn-secondary"
                            title="Voir détails"
                            style={{ marginRight: '6px' }}
                          >
                            <i className="ti ti-eye" aria-hidden="true" />
                          </button>
                          {(tenant.statut === 'inactif' || tenant.statut === 'bloque') ? (
                            <button
                              onClick={() => handleReactivate(tenant.id)}
                              className="btn-small btn-success"
                              title="Réactiver"
                              style={{ marginRight: '6px' }}
                            >
                              <i className="ti ti-refresh" aria-hidden="true" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleSuspend(tenant.id)}
                              className="btn-small btn-danger"
                              title="Suspendre"
                              style={{ marginRight: '6px' }}
                            >
                              <i className="ti ti-ban" aria-hidden="true" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDeletePermanent(tenant.id, tenant.nom)}
                            className="btn-small btn-danger"
                            title="Supprimer"
                          >
                            <i className="ti ti-trash" aria-hidden="true" />
                          </button>
                        </td>
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
                  Page {page} sur {totalPages} ({total} tenants)
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

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          warning={confirmAction.warning}
          confirmText={confirmAction.confirmText}
          confirmClass={confirmAction.confirmClass}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  );
};

export default Tenants;
