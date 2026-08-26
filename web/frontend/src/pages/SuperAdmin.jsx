// src/pages/SuperAdmin.jsx
import React, { useEffect, useState, useMemo } from 'react';
import { toast } from 'react-toastify';
import { tenantService, subscriptionService } from '../services/api';
import { VILLES_MADAGASCAR } from '../constants/erpConstants';
import './SuperAdmin.css';
import './Pages.css';

const SuperAdmin = () => {
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
      const response = await subscriptionService.getAll();
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

  useEffect(() => {
    fetchTenants();
  }, []);

  useEffect(() => {
    if (activeTab === 'subscriptions') {
      fetchSubscriptions();
    } else if (activeTab === 'historique') {
      if (selectedTenantId) {
        fetchHistorique(selectedTenantId);
      } else {
        setHistorique([]);
      }
    }
  }, [activeTab, selectedTenantId]);

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
        await tenantService.update(editingTenant.id, formData);
        toast.success('Tenant mis à jour');
      } else {
        await tenantService.create(formData);
        toast.success('Tenant créé');
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
