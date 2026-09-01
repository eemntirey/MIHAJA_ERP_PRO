import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  superAdminTenantService,
  superAdminSubscriptionService,
  superAdminPlanService,
} from '../services/api';
import ConfirmModal from '../components/common/ConfirmModal';

const formatPlanPrice = (prix) => {
  if (prix === 0) return 'Gratuit';
  return `${Number(prix).toLocaleString('fr-FR')} Ar`;
};

const formatPlanDuration = (duree_jours) => {
  if (duree_jours === -1) return 'Illimité';
  return `${duree_jours} jours`;
};

const TenantDetail = () => {
  const { id } = useParams();
  const [tenant, setTenant] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subLoading, setSubLoading] = useState(false);
  const [showExtendModal, setShowExtendModal] = useState(false);
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [extendDays, setExtendDays] = useState(30);
  const [selectedPlan, setSelectedPlan] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);
  const [plans, setPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const navigate = useNavigate();

  const fetchTenant = async () => {
    try {
      setLoading(true);
      const response = await superAdminTenantService.getById(id);
      setTenant(response.data || response);
    } catch (err) {
      toast.error('Tenant non trouvé');
      navigate('/tenants');
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = async () => {
    try {
      setSubLoading(true);
      const response = await superAdminSubscriptionService.getHistoriqueByTenant(id);
      setSubscriptions(response.data?.abonnements || response.data || []);
    } catch {
      toast.error('Échec du chargement des abonnements');
    } finally {
      setSubLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const response = await superAdminPlanService.getAll();
      const list = response?.data?.plans || response?.plans || [];
      setPlans(list);
    } catch (err) {
      console.error('Error fetching plans:', err);
    } finally {
      setPlansLoading(false);
    }
  };

  useEffect(() => {
    fetchTenant();
    fetchSubscriptions();
    fetchPlans();
  }, [id]);

  useEffect(() => {
    const handleTenantUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id === parseInt(id)) {
        setTenant(updated);
      }
    };
    window.addEventListener('realtime:tenant:updated', handleTenantUpdated);
    return () => window.removeEventListener('realtime:tenant:updated', handleTenantUpdated);
  }, [id]);

  useEffect(() => {
    const onFocus = () => {
      fetchTenant();
      fetchSubscriptions();
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [id]);

  const handleSuspend = () => {
    setConfirmAction({
      title: 'Suspendre le tenant',
      message: `Êtes-vous sûr de vouloir suspendre ${tenant.nom} ? Les utilisateurs ne pourront plus accéder à la plateforme.`,
      warning: 'Cette action peut être annulée à tout moment.',
      confirmText: 'Suspendre',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        try {
          await superAdminTenantService.suspend(tenant.id);
          toast.success('Tenant suspendu');
          setTenant(prev => prev ? { ...prev, statut: 'inactif' } : prev);
          fetchTenant();
        } catch {
          toast.error('Échec de la suspension');
        }
        setConfirmAction(null);
      },
    });
  };

  const handleActivate = async () => {
    try {
      await superAdminTenantService.activate(tenant.id);
      toast.success('Tenant activé');
      setTenant(prev => prev ? { ...prev, statut: 'actif' } : prev);
      fetchTenant();
    } catch {
      toast.error("Échec de l'activation");
    }
  };

  const handleReactivate = async () => {
    try {
      await superAdminTenantService.reactivate(tenant.id);
      toast.success('Tenant réactivé');
      setTenant(prev => prev ? { ...prev, statut: 'actif' } : prev);
      fetchTenant();
    } catch {
      toast.error("Échec de la réactivation");
    }
  };

  const handleDelete = () => {
    setConfirmAction({
      title: 'Supprimer le tenant',
      message: `Êtes-vous sûr de vouloir supprimer définitivement ${tenant.nom} ? Toutes les données (utilisateurs, employés, produits, ventes, factures, etc.) seront supprimées de la base de données.`,
      warning: 'Cette action est irréversible.',
      confirmText: 'Supprimer',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        try {
          await superAdminTenantService.delete(tenant.id);
          toast.success('Tenant supprimé');
          navigate('/tenants');
        } catch {
          toast.error('Échec de la suppression');
        }
        setConfirmAction(null);
      },
    });
  };

  const handleExtend = async (e) => {
    e.preventDefault();
    try {
      await superAdminTenantService.extendSubscription(tenant.id, extendDays);
      toast.success('Abonnement prolongé');
      setShowExtendModal(false);
      fetchTenant();
      fetchSubscriptions();
    } catch {
      toast.error("Échec de la prolongation");
    }
  };

  const handleChangePlan = async (e) => {
    e.preventDefault();
    if (!selectedPlan) {
      toast.error('Sélectionnez un plan');
      return;
    }
    try {
      await superAdminTenantService.changeSubscription(tenant.id, selectedPlan, 30);
      toast.success('Abonnement modifié');
      setShowChangeModal(false);
      fetchTenant();
      fetchSubscriptions();
    } catch {
      toast.error("Échec du changement d'abonnement");
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner-large"></div>
        <p>Chargement...</p>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="page-container">
        <p className="text-center text-muted">Tenant non trouvé</p>
      </div>
    );
  }

  const getStatusBadge = (statut) => {
    const s = (statut || '').toLowerCase();
    if (s === 'actif') return 'badge-success';
    if (s === 'inactif' || s === 'bloque') return 'badge-danger';
    if (s === 'en_essai') return 'badge-warning';
    return 'badge-info';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>{tenant.nom}</h1>
          <p>{tenant.slug}</p>
        </div>
        <div className="page-header-actions">
          {(tenant.statut === 'inactif' || tenant.statut === 'bloque') ? (
            <button onClick={handleReactivate} className="btn-success">Réactiver</button>
          ) : (
            <button onClick={handleSuspend} className="btn-danger">Suspendre</button>
          )}
          <button onClick={() => setShowChangeModal(true)} className="btn-primary">Modifier abonnement</button>
          <button onClick={() => setShowExtendModal(true)} className="btn-secondary">Prolonger</button>
          <button onClick={handleDelete} className="btn-danger" style={{ backgroundColor: '#dc2626' }}>Supprimer</button>
        </div>
      </div>

      <div className="detail-section">
        <h3>Informations générales</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Raison sociale</span>
            <span className="detail-value">{tenant.nom}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Slug</span>
            <span className="detail-value">{tenant.slug}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Email</span>
            <span className="detail-value">{tenant.email_contact || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Téléphone</span>
            <span className="detail-value">{tenant.telephone || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Adresse</span>
            <span className="detail-value">{tenant.adresse || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Ville</span>
            <span className="detail-value">{tenant.ville || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Pays</span>
            <span className="detail-value">{tenant.pays || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Statut</span>
            <span className={`badge ${getStatusBadge(tenant.statut)}`}>{tenant.statut || 'INCONNU'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Plan</span>
            <span className="detail-value">{tenant.plan}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Date création</span>
            <span className="detail-value">{tenant.created_at ? new Date(tenant.created_at).toLocaleDateString('fr-FR') : '-'}</span>
          </div>
        </div>
      </div>

      <div className="detail-section">
        <h3>Utilisation</h3>
        <div className="usage-grid">
          <div className="usage-item">
            <div className="usage-value">{tenant.utilisateurs_count || 0}</div>
            <div className="usage-label">Utilisateurs</div>
          </div>
          <div className="usage-item">
            <div className="usage-value">{tenant.produits_count || 0}</div>
            <div className="usage-label">Produits</div>
          </div>
          <div className="usage-item">
            <div className="usage-value">{tenant.clients_count || 0}</div>
            <div className="usage-label">Clients</div>
          </div>
          <div className="usage-item">
            <div className="usage-value">{tenant.fournisseurs_count || 0}</div>
            <div className="usage-label">Fournisseurs</div>
          </div>
          <div className="usage-item">
            <div className="usage-value">{tenant.ventes_count || 0}</div>
            <div className="usage-label">Ventes</div>
          </div>
          <div className="usage-item">
            <div className="usage-value">{tenant.factures_count || 0}</div>
            <div className="usage-label">Factures</div>
          </div>
        </div>
      </div>

      <div className="detail-section">
        <h3>Abonnement</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Plan actuel</span>
            <span className="detail-value">{tenant.plan}</span>
          </div>
          {tenant.abonnement_actuel && (
            <>
              <div className="detail-item">
                <span className="detail-label">Date début</span>
                <span className="detail-value">{tenant.abonnement_actuel.date_debut ? new Date(tenant.abonnement_actuel.date_debut).toLocaleDateString('fr-FR') : '-'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Expiration</span>
                <span className="detail-value">{tenant.abonnement_actuel.date_fin ? new Date(tenant.abonnement_actuel.date_fin).toLocaleDateString('fr-FR') : '-'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Montant</span>
                <span className="detail-value">{tenant.abonnement_actuel.montant} {tenant.abonnement_actuel.devise}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Statut paiement</span>
                <span className={`badge ${getStatusBadge(tenant.abonnement_actuel.statut)}`}>{tenant.abonnement_actuel.statut}</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="detail-section">
        <h3>Activité</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Dernière activité</span>
            <span className="detail-value">{tenant.last_activity ? new Date(tenant.last_activity).toLocaleString('fr-FR') : '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Connexions (7 jours)</span>
            <span className="detail-value">{tenant.connexions_recentes || 0}</span>
          </div>
        </div>
      </div>

      {tenant.administrateurs && tenant.administrateurs.length > 0 && (
        <div className="detail-section">
          <h3>Administrateurs</h3>
          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nom d'utilisateur</th>
                    <th>Email</th>
                    <th>Rôle</th>
                    <th>Dernière connexion</th>
                  </tr>
                </thead>
                <tbody>
                  {tenant.administrateurs.map((admin) => (
                    <tr key={admin.id}>
                      <td>{admin.username}</td>
                      <td>{admin.email}</td>
                      <td><span className="badge badge-info">{admin.role}</span></td>
                      <td>{admin.last_login ? new Date(admin.last_login).toLocaleString('fr-FR') : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="detail-section">
        <h3>Historique des abonnements</h3>
        {subLoading ? (
          <div className="loading-screen">
            <div className="spinner-large"></div>
            <p>Chargement...</p>
          </div>
        ) : (
          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Plan</th>
                    <th>Date début</th>
                    <th>Date fin</th>
                    <th>Montant</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="text-center text-muted">Aucun abonnement</td>
                    </tr>
                  ) : subscriptions.map((sub) => (
                    <tr key={sub.id}>
                      <td>{sub.plan || '-'}</td>
                      <td>{sub.date_debut ? new Date(sub.date_debut).toLocaleDateString('fr-FR') : '-'}</td>
                      <td>{sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('fr-FR') : '-'}</td>
                      <td>{sub.montant ? `${Number(sub.montant).toFixed(2)} Ar` : '-'}</td>
                      <td>
                        <span className={`badge ${sub.statut === 'actif' ? 'badge-success' : sub.statut === 'expire' ? 'badge-danger' : 'badge-warning'}`}>
                          {sub.statut || 'INCONNU'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {showExtendModal && (
        <div className="modal-overlay" onClick={() => setShowExtendModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Prolonger l'abonnement</h2>
              <button type="button" className="btn-close" onClick={() => setShowExtendModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleExtend} className="modal-form">
              <div className="form-group full-width">
                <label htmlFor="days">Durée (jours)</label>
                <input
                  id="days"
                  type="number"
                  value={extendDays}
                  onChange={(e) => setExtendDays(parseInt(e.target.value) || 30)}
                  min="1"
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowExtendModal(false)}>Annuler</button>
                <button type="submit" className="btn-primary">Prolonger</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showChangeModal && (
        <div className="modal-overlay" onClick={() => setShowChangeModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Modifier l'abonnement</h2>
              <button type="button" className="btn-close" onClick={() => setShowChangeModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleChangePlan} className="modal-form">
              <div className="form-group full-width">
                <label>Sélectionnez un plan</label>
                <div className="subscription-plans">
                  {plans.map((plan) => (
                    <div
                      key={plan.code}
                      className={`plan-option ${selectedPlan === plan.code ? 'plan-option--selected' : ''}`}
                      onClick={() => setSelectedPlan(plan.code)}
                    >
                      <div className="plan-option-name">{plan.label}</div>
                      <div className="plan-option-price">{plan.prix === 0 ? 'Gratuit' : `${Number(plan.prix).toLocaleString('fr-FR')} Ar/mois`}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowChangeModal(false)}>Annuler</button>
                <button type="submit" className="btn-primary">Confirmer</button>
              </div>
            </form>
          </div>
        </div>
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

export default TenantDetail;
