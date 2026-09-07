// src/pages/SuperAdmin.jsx
import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { toast } from 'react-toastify';
import { tenantService, subscriptionService, superAdminPaymentService } from '../services/api';
import { VILLES_MADAGASCAR } from '../constants/erpConstants';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import './SuperAdmin.css';
import './Pages.css';

const PAYMENT_STATUS_LABEL = {
  succes: 'SUCCESS',
  confirme: 'CONFIRME',
  en_attente: 'EN_ATTENTE',
  traitement: 'PROCESSING',
  echec: 'FAILED',
  annule: 'CANCELLED',
  expire: 'EXPIRE',
};

const PAYMENT_METHOD_LABEL = {
  MVOLA: 'MVola',
  ORANGE_MONEY: 'Orange Money',
  AIRTEL_MONEY: 'Airtel Money',
  BRED: 'Visa / BRED',
  ESPECES: 'Espèces',
  VIREMENT: 'Virement',
  CHEQUE: 'Chèque',
};

const PROVIDER_LABEL = {
  papi: 'Papi (en ligne)',
  manuel: 'Manuel (hors ligne)',
  especes: 'Manuel (hors ligne)',
  visa: 'Visa',
};

function formatCurrency(amount, devise = 'MGA') {
  const value = Number(amount || 0).toLocaleString('mg-MG', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  return `${value} ${devise || 'Ar'}`;
}

function getPaymentStatusBadge(statut) {
  const normalized = (statut || '').toLowerCase();
  if (normalized === 'succes' || normalized === 'confirme') return 'badge-success';
  if (normalized === 'en_attente' || normalized === 'traitement') return 'badge-warning';
  if (normalized === 'echec' || normalized === 'annule' || normalized === 'expire') {
    return 'badge-danger';
  }
  return 'badge-info';
}

const SuperAdmin = () => {
  const { hasRole } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('tenants');
  const [tenants, setTenants] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [historique, setHistorique] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subLoading, setSubLoading] = useState(false);
  const [histLoading, setHistLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingTenant, setEditingTenant] = useState(null);
  const [selectedTenantId, setSelectedTenantId] = useState('');
  const [subFilter, setSubFilter] = useState('');

  // ====== PAIEMENTS & REVENUS ======
  const [payments, setPayments] = useState([]);
  const [paymentsPagination, setPaymentsPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    pages: 1,
  });
  const [paymentsStats, setPaymentsStats] = useState(null);
  const [paymentsLoading, setPaymentsLoading] = useState(false);
  const [paymentsFilters, setPaymentsFilters] = useState({
    search: '',
    tenant_id: '',
    status: '',
    provider: '',
    payment_method: '',
    plan: '',
    date_from: '',
    date_to: '',
    page: 1,
    per_page: 20,
  });
  const [paymentDetail, setPaymentDetail] = useState(null);
  const [paymentDetailLoading, setPaymentDetailLoading] = useState(false);
  const [showPaymentDetail, setShowPaymentDetail] = useState(false);

  useEffect(() => {
    if (!hasRole('SUPER_ADMIN')) {
      navigate('/dashboard', { replace: true });
    }
  }, [hasRole, navigate]);

  const [formData, setFormData] = useState({
    nom: '',
    email: '',
    telephone: '',
    adresse: '',
    ville: '',
    code_postal: '',
    pays: 'Madagascar',
    statut: 'actif',
  });

  const fetchTenants = async () => {
    try {
      setLoading(true);
      const response = await tenantService.getAll();
      setTenants(response.data?.tenants || response.data || []);
    } catch (err) {
      console.error('Error fetching tenants:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des tenants';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = async () => {
    try {
      setSubLoading(true);
      const response = await subscriptionService.getAllForSuperAdmin();
      setSubscriptions(response.data?.abonnements || response.data?.subscriptions || response.data || []);
    } catch (err) {
      console.error('Error fetching subscriptions:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des abonnements';
      toast.error(msg);
    } finally {
      setSubLoading(false);
    }
  };

  const fetchHistorique = async (tenantId) => {
    if (!tenantId) {
      setHistorique([]);
      return;
    }
    try {
      setHistLoading(true);
      const response = await subscriptionService.getHistoriqueByTenant(tenantId);
      setHistorique(response.data?.abonnements || response.data || []);
    } catch (err) {
      console.error('Error fetching historique:', err);
      toast.error('Échec du chargement de l\'historique');
    } finally {
      setHistLoading(false);
    }
  };

  const fetchPayments = useCallback(async (filters) => {
    try {
      setPaymentsLoading(true);
      const params = {};
      Object.entries(filters).forEach(([key, val]) => {
        if (val !== '' && val !== null && val !== undefined) {
          params[key] = val;
        }
      });
      const response = await superAdminPaymentService.getAll(params);
      const body = response.data || {};
      setPayments(body.items || []);
      setPaymentsPagination(body.pagination || {
        page: 1, per_page: 20, total: 0, pages: 1,
      });
    } catch (err) {
      console.error('Error fetching payments:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des paiements';
      toast.error(msg);
      setPayments([]);
    } finally {
      setPaymentsLoading(false);
    }
  }, []);

  const fetchPaymentsStats = useCallback(async (filters) => {
    try {
      const params = {};
      Object.entries(filters).forEach(([key, val]) => {
        if (val !== '' && val !== null && val !== undefined &&
            ['tenant_id', 'plan'].includes(key)) {
          params[key] = val;
        }
      });
      const response = await superAdminPaymentService.getStats(params);
      setPaymentsStats(response.data || null);
    } catch (err) {
      console.error('Error fetching payment stats:', err);
      setPaymentsStats(null);
    }
  }, []);

  const fetchPaymentDetail = async (id) => {
    try {
      setPaymentDetailLoading(true);
      const response = await superAdminPaymentService.getById(id);
      setPaymentDetail(response.data || null);
      setShowPaymentDetail(true);
    } catch (err) {
      console.error('Error fetching payment detail:', err);
      toast.error(err.response?.data?.message || 'Échec du chargement du détail');
    } finally {
      setPaymentDetailLoading(false);
    }
  };

  const handlePaymentsSearch = () => {
    fetchPayments(paymentsFilters);
    fetchPaymentsStats(paymentsFilters);
  };

  const handlePaymentsPageChange = (page) => {
    const next = { ...paymentsFilters, page };
    setPaymentsFilters(next);
    fetchPayments(next);
  };

  const handlePaymentsReset = () => {
    const cleared = {
      search: '', tenant_id: '', status: '', provider: '',
      payment_method: '', plan: '', date_from: '', date_to: '',
      page: 1, per_page: 20,
    };
    setPaymentsFilters(cleared);
    fetchPayments(cleared);
    fetchPaymentsStats(cleared);
  };

  useEffect(() => {
    fetchTenants();
  }, []);

  useEffect(() => {
    const handleTenantUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id) {
        setTenants(prev => prev.map(t => t.id === updated.id ? updated : t));
      } else {
        fetchTenants();
      }
    };
    window.addEventListener('realtime:tenant:updated', handleTenantUpdated);
    return () => window.removeEventListener('realtime:tenant:updated', handleTenantUpdated);
  }, [fetchTenants]);

  useEffect(() => {
    if (activeTab === 'subscriptions') {
      fetchSubscriptions();
    } else if (activeTab === 'historique') {
      if (selectedTenantId) {
        fetchHistorique(selectedTenantId);
      } else {
        setHistorique([]);
      }
    } else if (activeTab === 'payments') {
      fetchPayments(paymentsFilters);
      fetchPaymentsStats(paymentsFilters);
    }
    // NB : le rechargement des paiements est déclenché explicitement par
    // handlePaymentsSearch / handlePaymentsPageChange / handlePaymentsReset
    // afin d'éviter une requête API à chaque frappe dans les filtres.
  }, [activeTab, selectedTenantId, fetchPayments, fetchPaymentsStats]);

  const openModal = (tenant = null) => {
    setEditingTenant(tenant);
    setFormData(tenant ? {
      nom: tenant.nom || '',
      email: tenant.email_contact || '',
      telephone: tenant.telephone || '',
      adresse: tenant.adresse || '',
      ville: tenant.ville || '',
      code_postal: tenant.code_postal || '',
      pays: tenant.pays || 'Madagascar',
      statut: tenant.statut || 'actif',
    } : {
      nom: '',
      email: '',
      telephone: '',
      adresse: '',
      ville: '',
      code_postal: '',
      pays: 'Madagascar',
      statut: 'actif',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingTenant(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTenant) {
        const response = await tenantService.update(editingTenant.id, formData);
        toast.success('Tenant mis à jour');
        if (response.data && response.data.id) {
          setTenants(prev => prev.map(t => t.id === editingTenant.id ? response.data : t));
        }
      } else {
        const response = await tenantService.create(formData);
        toast.success('Tenant créé');
        if (response.data && response.data.id) {
          setTenants(prev => [...prev, response.data]);
        }
      }
      closeModal();
      fetchTenants();
    } catch (err) {
      console.error('Error saving tenant:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde';
      toast.error(msg);
    }
  };

  const handleSuspend = async (id) => {
    if (!window.confirm('Suspendre ce tenant ?')) return;
    try {
      await tenantService.suspend(id);
      toast.success('Tenant suspendu');
      setTenants(prev => prev.map(t => t.id === id ? { ...t, statut: 'inactif' } : t));
      fetchTenants();
    } catch (err) {
      console.error('Error suspending tenant:', err);
      const msg = err.response?.data?.message || 'Échec de la suspension';
      toast.error(msg);
    }
  };

  const getStatusBadge = (statut) => {
    const normalized = (statut || '').toUpperCase();
    if (normalized === 'ACTIF' || normalized === 'ACTIVE') return 'badge-success';
    if (normalized === 'SUSPENDU' || normalized === 'SUSPENDED' || normalized === 'INACTIF') return 'badge-danger';
    return 'badge-warning';
  };

  const getSubStatusBadge = (statut) => {
    const normalized = (statut || '').toUpperCase();
    if (normalized === 'ACTIF' || normalized === 'ACTIVE') return 'badge-success';
    if (normalized === 'EN_ATTENTE' || normalized === 'PENDING') return 'badge-warning';
    if (normalized === 'EXPIRE' || normalized === 'EXPIRED') return 'badge-danger';
    return 'badge-info';
  };

  const filteredSubscriptions = useMemo(() => {
    if (!subFilter) return subscriptions;
    return subscriptions.filter(sub => 
      (sub.statut || '').toLowerCase().includes(subFilter.toLowerCase())
    );
  }, [subscriptions, subFilter]);

  const getTenantName = (tenantId) => {
    const tenant = tenants.find(t => t.id === tenantId);
    return tenant?.nom || `Tenant #${tenantId}`;
  };

  return (
    <div className="page-container superadmin-page">
      <div className="page-header">
        <div>
          <h1>Administration</h1>
          <p>Gestion de la plateforme</p>
        </div>
      </div>

      <div className="superadmin-tabs">
        <button 
          className={`superadmin-tab ${activeTab === 'tenants' ? 'superadmin-tab--active' : ''}`}
          onClick={() => setActiveTab('tenants')}
        >
          Tenants
        </button>
        <button 
          className={`superadmin-tab ${activeTab === 'subscriptions' ? 'superadmin-tab--active' : ''}`}
          onClick={() => setActiveTab('subscriptions')}
        >
          Abonnements
        </button>
        <button
          className={`superadmin-tab ${activeTab === 'historique' ? 'superadmin-tab--active' : ''}`}
          onClick={() => setActiveTab('historique')}
        >
          Historique par entreprise
        </button>
        <button
          className={`superadmin-tab ${activeTab === 'payments' ? 'superadmin-tab--active' : ''}`}
          onClick={() => setActiveTab('payments')}
        >
          💰 Paiements & Revenus
        </button>
      </div>

      {activeTab === 'tenants' && (
        <>
          <div className="header-actions" style={{ marginBottom: '18px' }}>
            <button onClick={() => openModal()} className="btn-primary">
              + Nouveau tenant
            </button>
            <button onClick={fetchTenants} className="btn-secondary" disabled={loading}>
              Rafraîchir
            </button>
          </div>

          {loading && tenants.length === 0 ? (
            <div className="loading-screen">
              <div className="spinner-large"></div>
              <p>Chargement des tenants...</p>
            </div>
          ) : (
            <div className="card full-width">
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nom</th>
                      <th>Email</th>
                      <th>Téléphone</th>
                      <th>Ville</th>
                      <th>Pays</th>
                      <th>Statut</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tenants.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="text-center">
                          Aucun tenant trouvé
                        </td>
                      </tr>
                    ) : (
                      tenants.map((tenant) => (
                        <tr key={tenant.id}>
                          <td>{tenant.nom}</td>
                          <td>{tenant.email_contact || '-'}</td>
                          <td>{tenant.telephone || '-'}</td>
                          <td>{tenant.ville || '-'}</td>
                          <td>{tenant.pays || '-'}</td>
                          <td>
                            <span className={`badge ${getStatusBadge(tenant.statut)}`}>
                              {tenant.statut || 'ACTIF'}
                            </span>
                          </td>
                          <td>
                            <button onClick={() => openModal(tenant)} className="btn-small btn-edit" title="Modifier">
                              <i className="ti ti-edit" aria-hidden="true" />
                            </button>
                            <button onClick={() => handleSuspend(tenant.id)} className="btn-small btn-delete" title="Suspendre">
                              <i className="ti ti-ban" aria-hidden="true" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'subscriptions' && (
        <>
          <div className="header-actions" style={{ marginBottom: '18px', alignItems: 'center' }}>
            <div className="filter-controls" style={{ flex: 1, maxWidth: '300px' }}>
              <div className="search-box">
                <input
                  type="text"
                  placeholder="Filtrer par statut..."
                  value={subFilter}
                  onChange={(e) => setSubFilter(e.target.value)}
                />
                <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
              </div>
            </div>
            <button onClick={fetchSubscriptions} className="btn-secondary" disabled={subLoading}>
              Rafraîchir
            </button>
          </div>

          {subLoading ? (
            <div className="loading-screen">
              <div className="spinner-large"></div>
              <p>Chargement des abonnements...</p>
            </div>
          ) : (
            <div className="card full-width">
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Entreprise</th>
                      <th>Plan</th>
                      <th>Date début</th>
                      <th>Date fin</th>
                      <th>Statut</th>
                      <th>Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSubscriptions.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="text-center">
                          Aucun abonnement trouvé
                        </td>
                      </tr>
                    ) : (
                      filteredSubscriptions.map((sub) => (
                        <tr key={sub.id}>
                          <td>{getTenantName(sub.tenant_id)}</td>
                          <td>{sub.plan || '-'}</td>
                          <td>{sub.date_debut ? new Date(sub.date_debut).toLocaleDateString('mg-MG') : '-'}</td>
                          <td>{sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('mg-MG') : '-'}</td>
                          <td>
                            <span className={`badge ${getSubStatusBadge(sub.statut)}`}>
                              {sub.statut || 'INCONNU'}
                            </span>
                          </td>
                          <td>{sub.montant ? `${Number(sub.montant).toFixed(2)} Ar` : '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'historique' && (
        <>
          <div className="header-actions" style={{ marginBottom: '18px', alignItems: 'center' }}>
            <div className="form-group" style={{ flex: 1, maxWidth: '400px' }}>
              <label htmlFor="tenant-select" style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
                Sélectionner une entreprise
              </label>
              <select
                id="tenant-select"
                value={selectedTenantId}
                onChange={(e) => setSelectedTenantId(e.target.value)}
                className="form-select"
                style={{ width: '100%' }}
              >
                <option value="">-- Choisir un tenant --</option>
                {tenants.map(t => (
                  <option key={t.id} value={t.id}>{t.nom} ({t.email_contact || '-'})</option>
                ))}
              </select>
            </div>
          </div>

          {histLoading ? (
            <div className="loading-screen">
              <div className="spinner-large"></div>
              <p>Chargement de l'historique...</p>
            </div>
          ) : !selectedTenantId ? (
            <div className="card full-width">
              <p className="text-center text-muted">Sélectionnez une entreprise pour afficher son historique d'abonnements.</p>
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
                    {historique.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="text-center">
                          Aucun historique disponible
                        </td>
                      </tr>
                    ) : (
                      historique.map((item) => (
                        <tr key={item.id}>
                          <td>{item.plan || '-'}</td>
                          <td>{item.date_debut ? new Date(item.date_debut).toLocaleDateString('mg-MG') : '-'}</td>
                          <td>{item.date_fin ? new Date(item.date_fin).toLocaleDateString('mg-MG') : '-'}</td>
                          <td>{item.montant ? `${Number(item.montant).toFixed(2)} Ar` : '-'}</td>
                          <td>
                            <span className={`badge ${getSubStatusBadge(item.statut)}`}>
                              {item.statut || 'INCONNU'}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'payments' && (
        <>
          <div className="card-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '20px',
          }}>
            <div className="card">
              <div className="card-body">
                <div className="stat-label">Revenus confirmés</div>
                <div className="stat-value">
                  {paymentsStats
                    ? formatCurrency(paymentsStats.total_success, paymentsStats.currency)
                    : 'N/A'}
                </div>
                <div className="stat-note">
                  {paymentsStats
                    ? `${paymentsStats.success_count || 0} paiement(s) SUCCESS`
                    : 'Chargement...'}
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-body">
                <div className="stat-label">Paiements en attente</div>
                <div className="stat-value">
                  {paymentsStats
                    ? formatCurrency(paymentsStats.total_pending, paymentsStats.currency)
                    : 'N/A'}
                </div>
                <div className="stat-note">
                  {paymentsStats
                    ? `${paymentsStats.pending_count || 0} paiement(s)`
                    : 'Chargement...'}
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-body">
                <div className="stat-label">Paiements réussis</div>
                <div className="stat-value">
                  {paymentsStats ? paymentsStats.success_count : 'N/A'}
                </div>
                <div className="stat-note">Statut SUCCESS / CONFIRME</div>
              </div>
            </div>
            <div className="card">
              <div className="card-body">
                <div className="stat-label">Paiements échoués</div>
                <div className="stat-value">
                  {paymentsStats ? paymentsStats.failed_count : 'N/A'}
                </div>
                <div className="stat-note">
                  {paymentsStats
                    ? formatCurrency(paymentsStats.total_failed, paymentsStats.currency)
                    : 'Chargement...'}
                </div>
              </div>
            </div>
          </div>

          {paymentsStats?.settlement && !paymentsStats.settlement.available && (
            <div className="card" style={{
              marginBottom: '16px',
              padding: '12px 16px',
              backgroundColor: '#fff8e1',
              borderLeft: '4px solid #ff9800',
              fontSize: '13px',
            }}>
              <strong>⚠️ Versements Papi :</strong> {paymentsStats.settlement.message}
              {paymentsStats?.papi_fees && !paymentsStats.papi_fees.available && (
                <div style={{ marginTop: '6px' }}>
                  <strong>💸 Frais Papi :</strong> {paymentsStats.papi_fees.message}
                </div>
              )}
              <div style={{ marginTop: '6px', color: '#5d4037' }}>
                ℹ️ total_success représente la somme des paiements MIHAJA confirmés
                (SUCCESS/CONFIRME). Cela n'implique PAS un versement effectif sur le
                compte bancaire MIHAJA.
              </div>
            </div>
          )}

          {paymentsStats?.by_method_confirmed?.length > 0 && (
            <div className="card" style={{ marginBottom: '16px' }}>
              <div className="card-header" style={{ padding: '12px 16px' }}>
                <h3 style={{ margin: 0, fontSize: '15px' }}>Revenus par méthode de paiement</h3>
              </div>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Méthode</th>
                      <th>Nombre</th>
                      <th>Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentsStats.by_method_confirmed.map((row) => (
                      <tr key={row.payment_method}>
                        <td>{PAYMENT_METHOD_LABEL[row.payment_method] || row.payment_method}</td>
                        <td>{row.count}</td>
                        <td>{formatCurrency(row.montant, paymentsStats.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {paymentsStats?.by_plan_confirmed?.length > 0 && (
            <div className="card" style={{ marginBottom: '16px' }}>
              <div className="card-header" style={{ padding: '12px 16px' }}>
                <h3 style={{ margin: 0, fontSize: '15px' }}>Revenus par plan</h3>
              </div>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Plan</th>
                      <th>Nombre</th>
                      <th>Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentsStats.by_plan_confirmed.map((row) => (
                      <tr key={row.plan}>
                        <td>{row.plan}</td>
                        <td>{row.count}</td>
                        <td>{formatCurrency(row.montant, paymentsStats.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="card full-width">
            <div className="card-header" style={{
              padding: '12px 16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <h3 style={{ margin: 0, fontSize: '15px' }}>Transactions</h3>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <input
                  type="search"
                  placeholder="Recherche..."
                  value={paymentsFilters.search}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, search: e.target.value, page: 1,
                  }))}
                  className="form-input"
                  style={{ minWidth: '180px' }}
                />
                <select
                  value={paymentsFilters.status}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, status: e.target.value, page: 1,
                  }))}
                  className="form-select"
                >
                  <option value="">Tous statuts</option>
                  <option value="SUCCESS">SUCCESS</option>
                  <option value="CONFIRME">CONFIRME</option>
                  <option value="EN_ATTENTE">EN_ATTENTE</option>
                  <option value="PROCESSING">PROCESSING</option>
                  <option value="FAILED">FAILED</option>
                  <option value="CANCELLED">CANCELLED</option>
                  <option value="EXPIRED">EXPIRE</option>
                </select>
                <select
                  value={paymentsFilters.provider}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, provider: e.target.value, page: 1,
                  }))}
                  className="form-select"
                >
                  <option value="">Tous providers</option>
                  <option value="papi">Papi (en ligne)</option>
                  <option value="manuel">Manuel (hors ligne)</option>
                </select>
                <select
                  value={paymentsFilters.payment_method}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, payment_method: e.target.value, page: 1,
                  }))}
                  className="form-select"
                >
                  <option value="">Toutes méthodes</option>
                  <option value="MVOLA">MVola</option>
                  <option value="ORANGE_MONEY">Orange Money</option>
                  <option value="AIRTEL_MONEY">Airtel Money</option>
                  <option value="ESPECES">Espèces</option>
                  <option value="VIREMENT">Virement</option>
                  <option value="CHEQUE">Chèque</option>
                </select>
                <select
                  value={paymentsFilters.plan}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, plan: e.target.value, page: 1,
                  }))}
                  className="form-select"
                >
                  <option value="">Tous plans</option>
                  <option value="gratuit">Gratuit</option>
                  <option value="starter">Starter</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <select
                  value={paymentsFilters.tenant_id}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, tenant_id: e.target.value, page: 1,
                  }))}
                  className="form-select"
                >
                  <option value="">Tous tenants</option>
                  {tenants.map((t) => (
                    <option key={t.id} value={t.id}>{t.nom}</option>
                  ))}
                </select>
                <input
                  type="date"
                  value={paymentsFilters.date_from}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, date_from: e.target.value, page: 1,
                  }))}
                  className="form-input"
                  title="Date début"
                />
                <input
                  type="date"
                  value={paymentsFilters.date_to}
                  onChange={(e) => setPaymentsFilters((f) => ({
                    ...f, date_to: e.target.value, page: 1,
                  }))}
                  className="form-input"
                  title="Date fin"
                />
                <button
                  onClick={handlePaymentsSearch}
                  className="btn-primary"
                  type="button"
                >
                  Rechercher
                </button>
                <button
                  onClick={handlePaymentsReset}
                  className="btn-secondary"
                  type="button"
                >
                  Réinitialiser
                </button>
              </div>
            </div>

            {paymentsLoading ? (
              <div className="loading-screen">
                <div className="spinner-large"></div>
                <p>Chargement des paiements...</p>
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Tenant</th>
                      <th>Abonnement</th>
                      <th>Plan</th>
                      <th>Méthode</th>
                      <th>Provider</th>
                      <th>Montant</th>
                      <th>Statut</th>
                      <th>Référence</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.length === 0 ? (
                      <tr>
                        <td colSpan="10" className="text-center">
                          Aucune transaction trouvée
                        </td>
                      </tr>
                    ) : (
                      payments.map((p) => (
                        <tr key={p.id}>
                          <td>{p.created_at ? new Date(p.created_at).toLocaleDateString('mg-MG') : '-'}</td>
                          <td>{p.tenant_name || `Tenant #${p.tenant_id}`}</td>
                          <td>{p.subscription_id ? `#${p.subscription_id}` : '-'}</td>
                          <td>{p.plan || '-'}</td>
                          <td>{PAYMENT_METHOD_LABEL[p.payment_method] || p.payment_method || '-'}</td>
                          <td>{PROVIDER_LABEL[p.provider] || p.provider || '-'}</td>
                          <td>{formatCurrency(p.montant, p.devise)}</td>
                          <td>
                            <span className={`badge ${getPaymentStatusBadge(p.statut)}`}>
                              {PAYMENT_STATUS_LABEL[p.statut] || p.statut_label || p.statut || '-'}
                            </span>
                          </td>
                          <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                            {p.external_reference || p.reference || '-'}
                          </td>
                          <td>
                            <button
                              onClick={() => fetchPaymentDetail(p.id)}
                              className="btn-small btn-edit"
                              title="Voir"
                              disabled={paymentDetailLoading}
                            >
                              <i className="ti ti-eye" aria-hidden="true" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {paymentsPagination.pages > 1 && (
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px 16px',
                borderTop: '1px solid #e0e0e0',
              }}>
                <div style={{ fontSize: '13px', color: '#666' }}>
                  Page {paymentsPagination.page} / {paymentsPagination.pages}
                  {' '}({paymentsPagination.total} résultats)
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handlePaymentsPageChange(Math.max(1, paymentsPagination.page - 1))}
                    disabled={paymentsPagination.page <= 1}
                    className="btn-secondary"
                    type="button"
                  >
                    ← Précédent
                  </button>
                  <button
                    onClick={() => handlePaymentsPageChange(Math.min(paymentsPagination.pages, paymentsPagination.page + 1))}
                    disabled={paymentsPagination.page >= paymentsPagination.pages}
                    className="btn-secondary"
                    type="button"
                  >
                    Suivant →
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {showPaymentDetail && paymentDetail && (
        <div className="modal-overlay" onClick={() => setShowPaymentDetail(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Détail transaction #{paymentDetail.id}</h2>
              <button type="button" className="btn-close" onClick={() => setShowPaymentDetail(false)}>×</button>
            </div>
            <div className="modal-body" style={{ padding: '16px' }}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Tenant</label>
                  <div>{paymentDetail.tenant_name || '-'} ({paymentDetail.tenant_id})</div>
                </div>
                <div className="form-group">
                  <label>Abonnement</label>
                  <div>{paymentDetail.subscription_id ? `#${paymentDetail.subscription_id}` : '-'}</div>
                </div>
                <div className="form-group">
                  <label>Montant</label>
                  <div>{formatCurrency(paymentDetail.montant, paymentDetail.devise)}</div>
                </div>
                <div className="form-group">
                  <label>Devise</label>
                  <div>{paymentDetail.devise}</div>
                </div>
                <div className="form-group">
                  <label>Provider</label>
                  <div>{PROVIDER_LABEL[paymentDetail.provider] || paymentDetail.provider || '-'}</div>
                </div>
                <div className="form-group">
                  <label>Méthode</label>
                  <div>{PAYMENT_METHOD_LABEL[paymentDetail.payment_method] || paymentDetail.payment_method || '-'}</div>
                </div>
                <div className="form-group">
                  <label>Statut</label>
                  <div>
                    <span className={`badge ${getPaymentStatusBadge(paymentDetail.statut)}`}>
                      {PAYMENT_STATUS_LABEL[paymentDetail.statut] || paymentDetail.statut_label || paymentDetail.statut}
                    </span>
                  </div>
                </div>
                <div className="form-group">
                  <label>Référence externe</label>
                  <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {paymentDetail.external_reference || '-'}
                  </div>
                </div>
                <div className="form-group">
                  <label>Date de création</label>
                  <div>{paymentDetail.created_at ? new Date(paymentDetail.created_at).toLocaleString('mg-MG') : '-'}</div>
                </div>
                <div className="form-group">
                  <label>Date de paiement</label>
                  <div>{paymentDetail.date_paiement ? new Date(paymentDetail.date_paiement).toLocaleString('mg-MG') : '-'}</div>
                </div>
                {paymentDetail.completed_at && (
                  <div className="form-group">
                    <label>Date de confirmation</label>
                    <div>{new Date(paymentDetail.completed_at).toLocaleString('mg-MG')}</div>
                  </div>
                )}
              </div>

              <hr style={{ margin: '16px 0' }} />

              <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>Section Versements Papi</h3>
              {paymentDetail.settlement ? (
                paymentDetail.settlement.available ? (
                  <div>{/* Non disponible actuellement */}</div>
                ) : (
                  <div className="card" style={{
                    padding: '12px',
                    backgroundColor: '#fff8e1',
                    borderLeft: '4px solid #ff9800',
                  }}>
                    <div style={{ fontSize: '13px' }}>
                      ℹ️ {paymentDetail.settlement.message}
                    </div>
                    <div style={{ fontSize: '13px', marginTop: '6px' }}>
                      💸 {paymentDetail.papi_fees?.available
                        ? `Frais Papi réels : ${formatCurrency(paymentDetail.papi_fees.fee, paymentDetail.devise)}`
                        : `Frais Papi : ${paymentDetail.papi_fees?.message || 'Non disponible'}`}
                    </div>
                    <div style={{ fontSize: '13px', marginTop: '6px' }}>
                      💰 Net à recevoir : {paymentDetail.net_amount?.available
                        ? formatCurrency(paymentDetail.net_amount.montant, paymentDetail.net_amount.devise)
                        : (paymentDetail.net_amount?.message || 'Non disponible')}
                    </div>
                  </div>
                )
              ) : null}

              {paymentDetail.payment_events?.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>Évènements webhook</h3>
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Event ID</th>
                          <th>Type</th>
                          <th>Traité</th>
                          <th>Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paymentDetail.payment_events.map((ev) => (
                          <tr key={ev.id || ev.event_id}>
                            <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>{ev.event_id}</td>
                            <td>{ev.event_type}</td>
                            <td>{ev.processed ? '✅' : '⏳'}</td>
                            <td>{ev.processed_at ? new Date(ev.processed_at).toLocaleString('mg-MG') : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={() => setShowPaymentDetail(false)}>
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingTenant ? 'Modifier le tenant' : 'Nouveau tenant'}</h2>
              <button type="button" className="btn-close" onClick={closeModal}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group full-width">
                  <label htmlFor="nom">Nom</label>
                  <input id="nom" name="nom" value={formData.nom} onChange={handleChange} required />
                </div>
                <div className="form-group full-width">
                  <label htmlFor="email">Email</label>
                  <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required />
                </div>
                <div className="form-group">
                  <label htmlFor="telephone">Téléphone</label>
                  <input id="telephone" name="telephone" value={formData.telephone} onChange={handleChange} />
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
                    <option value="Mozambique">Mozambique</option>
                  </select>
                </div>
                <div className="form-group full-width">
                  <label htmlFor="adresse">Adresse</label>
                  <input id="adresse" name="adresse" value={formData.adresse} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label htmlFor="ville">Ville</label>
                  <select id="ville" name="ville" value={formData.ville} onChange={handleChange}>
                    <option value="">Sélectionnez une ville</option>
                    {VILLES_MADAGASCAR.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="code_postal">Code postal</label>
                  <input id="code_postal" name="code_postal" value={formData.code_postal} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label htmlFor="statut">Statut</label>
                  <select id="statut" name="statut" value={formData.statut} onChange={handleChange}>
                    <option value="actif">Actif</option>
                    <option value="inactif">Inactif</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal}>Annuler</button>
                <button type="submit" className="btn-primary">Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdmin;
