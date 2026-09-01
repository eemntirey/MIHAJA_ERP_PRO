import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { superAdminAuditService } from '../services/api';

const Audit = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState('');

  const perPage = 20;

  const fetchLogs = useCallback(async (p = 1) => {
    try {
      setLoading(true);
      const params = { page: p, per_page: perPage };
      if (actionFilter) params.action_type = actionFilter;
      const response = await superAdminAuditService.getLogs(params);
      const data = response.data || response;
      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setTotalPages(data.pages || 1);
      setPage(p);
    } catch {
      toast.error('Échec du chargement des logs');
    } finally {
      setLoading(false);
    }
  }, [actionFilter]);

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  const getActionLabel = (type) => {
    const labels = {
      creation_utilisateur: 'Création utilisateur',
      changement_role: 'Changement rôle',
      changement_abonnement: 'Changement abonnement',
      creation_tenant: 'Création tenant',
      activation_tenant: 'Activation tenant',
      suspension_tenant: 'Suspension tenant',
      prolongation_abonnement: 'Prolongation abonnement',
      connexion_super_admin: 'Connexion Super Admin',
      deconnexion_super_admin: 'Déconnexion Super Admin',
      modification_tenant: 'Modification tenant',
      creation_employe: 'Création employe',
      modification_employe: 'Modification employe',
      suppression_employe: 'Suppression employe',
      modification_permission: 'Modification permission',
    };
    return labels[type] || type;
  };

  const getActionBadge = (type) => {
    if (type.includes('suspension') || type.includes('suppression')) return 'badge-danger';
    if (type.includes('activation') || type.includes('creation') || type.includes('connexion')) return 'badge-success';
    if (type.includes('changement') || type.includes('modification') || type.includes('prolongation')) return 'badge-warning';
    return 'badge-info';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Audit</h1>
          <p>Journal des actions sensibles ({total} entrées)</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Filtrer par type d'action..."
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            style={{ maxWidth: '320px' }}
          />
        </div>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des logs...</p>
        </div>
      ) : (
        <div className="card full-width">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Acteur</th>
                  <th>Action</th>
                  <th>Cible</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center text-muted">
                      Aucun log trouvé
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id}>
                      <td>{log.created_at ? new Date(log.created_at).toLocaleString('fr-FR') : '-'}</td>
                      <td>
                        {log.utilisateur ? (
                          <div>
                            <div style={{ fontWeight: 600 }}>{log.utilisateur.username}</div>
                            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{log.utilisateur.email}</div>
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>
                        <span className={`badge ${getActionBadge(log.type_action)}`}>
                          {getActionLabel(log.type_action)}
                        </span>
                      </td>
                      <td>
                        {log.tenant ? (
                          <div>
                            <div style={{ fontWeight: 600 }}>{log.tenant.nom}</div>
                            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{log.tenant.slug}</div>
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>
                        <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                          {log.description || '-'}
                        </span>
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
                onClick={() => fetchLogs(page - 1)}
                disabled={page <= 1}
              >
                Précédent
              </button>
              <span className="pagination-info">
                Page {page} sur {totalPages} ({total} logs)
              </span>
              <button
                className="pagination-btn"
                onClick={() => fetchLogs(page + 1)}
                disabled={page >= totalPages}
              >
                Suivant
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Audit;
