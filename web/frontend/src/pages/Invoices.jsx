// src/pages/Invoices.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { factureService, saleService, clientService, paiementService } from '../services/api';
import { toast } from 'react-toastify';
import { PAYMENT_METHODS } from '../constants/erpConstants';
import './Pages.css';

const Invoices = () => {
  const [invoices, setInvoices] = useState([]);
  const [sales, setSales] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showJsonModal, setShowJsonModal] = useState(false);
  const [jsonPayload, setJsonPayload] = useState('');
  const [jsonLoading, setJsonLoading] = useState(false);
  const [currentInvoice, setCurrentInvoice] = useState(null);
  const [currentSale, setCurrentSale] = useState(null);
  const [selectedSaleId, setSelectedSaleId] = useState('');
  const [paiements, setPaiements] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [lignesByInvoiceId, setLignesByInvoiceId] = useState({});
  const [lignesLoadingId, setLignesLoadingId] = useState(null);
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    vente_id: '',
    client_id: '',
    total_ttc: 0,
    date_echeance: '',
    statut: 'en_attente',
  });

  const [paymentData, setPaymentData] = useState({
    facture_id: '',
    montant: 0,
    mode_paiement: 'especes',
    date: new Date().toISOString().split('T')[0],
    remarque: '',
  });

  const [statusFilter, setStatusFilter] = useState('');

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter) params.statut = statusFilter;
      const response = await factureService.getAll(params);
      setInvoices(response.data?.factures || response.data || []);
    } catch (err) {
      console.error('Error fetching invoices:', err);
      const msg = err.response?.data?.message || "Échec du chargement des factures";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchSales = async () => {
    try {
      const response = await saleService.getAll({});
      setSales(response.data?.ventes || response.data || []);
    } catch (err) {
      console.error('Error fetching sales:', err);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await clientService.getAll({});
      setClients(response.data?.clients || response.data || []);
    } catch (err) {
      console.error('Error fetching clients:', err);
    }
  };

  useEffect(() => {
    fetchInvoices();
    fetchSales();
    fetchClients();
  }, []);

  const handleChange = (e, setState) => {
    const { name, value } = e.target;
    if (setState) {
      setState(prev => ({ ...prev, [name]: value }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSaleChange = (e) => {
    const saleId = parseInt(e.target.value, 10);
    setSelectedSaleId(saleId);
    const sale = sales.find(s => s.id === saleId);
    if (sale) {
      const clientId = sale.client_id || sale.client?.id || '';
      if (!clientId) {
        toast.error('Cette vente n\'est pas associée à un client');
      }
      setFormData(prev => ({
        ...prev,
        vente_id: saleId,
        client_id: clientId,
        total_ttc: sale.total_ttc || 0,
      }));
    }
  };

  const openModal = () => {
    setFormData({
      vente_id: '',
      client_id: '',
      total_ttc: 0,
      date_echeance: '',
      statut: 'en_attente',
    });
    setSelectedSaleId('');
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedSaleId('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const reference = `FAC-${Date.now()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
      await factureService.create({ ...formData, reference });
      toast.success('Facture créée avec succès');
      fetchInvoices();
      closeModal();
    } catch (err) {
      console.error('Error creating invoice:', err);
      const msg = err.response?.data?.message || 'Échec de la création de la facture';
      toast.error(msg);
    }
  };

  const viewInvoiceDetails = async (invoice) => {
    try {
      const response = await factureService.getById(invoice.id);
      setCurrentInvoice(response.data || invoice);
      setShowDetailModal(true);
    } catch (err) {
      setCurrentInvoice(invoice);
      setShowDetailModal(true);
    }
  };

  const closeDetailModal = () => {
    setShowDetailModal(false);
    setCurrentInvoice(null);
  };

  const openPaymentModal = (invoice) => {
    setCurrentInvoice(invoice);
    const total = invoice.total_ttc || 0;
    const paid = invoice.paiements?.reduce((sum, p) => sum + (p.montant || 0), 0) || 0;
    setPaymentData({
      facture_id: invoice.id,
      montant: total - paid,
      mode_paiement: 'especes',
      date: new Date().toISOString().split('T')[0],
      remarque: '',
    });
    setShowPaymentModal(true);
  };

  const closePaymentModal = () => {
    setShowPaymentModal(false);
    setCurrentInvoice(null);
  };

  const buildDonneesJson = (invoice, sale, client) => {
    const items = (sale?.lignes || []).map(l => ({
      produit_nom: l.produit_nom || l.designation || (`Produit #${l.produit_id}`),
      quantite: Number(l.quantite) || 0,
      prix_unitaire: Number(l.prix_unitaire_ht ?? l.prix_unitaire ?? 0),
      taux_tva: Number(l.taux_tva ?? 0),
      total_ht: Number(l.total_ht ?? ((Number(l.quantite) || 0) * (Number(l.prix_unitaire_ht) || 0))) || 0,
    }));

    const total_ht = Number(sale?.total_ht ?? invoice.total_ht ?? 0);
    const taux_tva = items.length ? Number(items[0].taux_tva) || 0 : 0;
    const total_ttc = Number(sale?.total_ttc ?? invoice.total_ttc ?? (total_ht * (1 + taux_tva / 100)));

    const payload = {
      client_nom: client?.nom_complet || invoice.client_nom || '',
      client_adresse: client?.adresse_facturation || '',
      client_ville: client?.ville_facturation || '',
      client_email: client?.email || '',
      client_telephone: client?.telephone || client?.mobile || '',
      total_ht,
      taux_tva,
      total_ttc,
      remise: 0,
      items,
    };
    return payload;
  };

  const openJsonModalForInvoice = async (invoice) => {
    setJsonLoading(true);
    setShowJsonModal(true);
    setJsonPayload('');
    try {
      const invRes = await factureService.getById(invoice.id);
      const inv = invRes.data || invoice;
      const venteId = inv.vente_id || invoice.vente_id;
      let sale = null;
      let client = null;
      try {
        if (venteId) {
          const saleRes = await saleService.getById(venteId);
          sale = saleRes.data || null;
        }
      } catch (_) { /* tolerate */ }
      try {
        const clientId = inv.client_id || sale?.client_id || invoice.client_id;
        if (clientId) {
          const clientRes = await clientService.getById(clientId);
          client = clientRes.data || null;
        }
      } catch (_) { /* tolerate */ }
      const payload = buildDonneesJson(inv, sale, client);
      setJsonPayload(JSON.stringify(payload, null, 2));
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la génération du JSON';
      toast.error(msg);
      setShowJsonModal(false);
    } finally {
      setJsonLoading(false);
    }
  };

  const closeJsonModal = () => {
    setShowJsonModal(false);
    setJsonPayload('');
  };

  const copyJsonToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(jsonPayload);
      toast.success('JSON copié dans le presse-papier');
    } catch (_) {
      const ta = document.getElementById('invoice-json-textarea');
      if (ta) {
        ta.select();
        document.execCommand('copy');
        toast.success('JSON copié');
      } else {
        toast.error('Impossible de copier');
      }
    }
  };

  const openDocumentsWithJson = () => {
    try {
      sessionStorage.setItem('documents_prefill', JSON.stringify({
        entite_type: 'facture',
        entite_id: currentInvoice?.id || null,
        reference: currentInvoice?.reference || '',
        type_document: 'facture',
        donnees: jsonPayload,
      }));
    } catch (_) { /* ignore quota errors */ }
    navigate('/documents');
  };

  const toggleExpandInvoice = async (invoice) => {
    if (expandedId === invoice.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(invoice.id);
    if (lignesByInvoiceId[invoice.id]) return;
    const venteId = invoice.vente_id;
    if (!venteId) {
      setLignesByInvoiceId(prev => ({ ...prev, [invoice.id]: [] }));
      return;
    }
    try {
      setLignesLoadingId(invoice.id);
      const res = await saleService.getById(venteId);
      const lignes = res.data?.lignes || res.data?.lignes_vente || [];
      setLignesByInvoiceId(prev => ({ ...prev, [invoice.id]: lignes }));
    } catch (err) {
      toast.error('Impossible de charger les lignes de la vente');
      setLignesByInvoiceId(prev => ({ ...prev, [invoice.id]: [] }));
    } finally {
      setLignesLoadingId(null);
    }
  };

  const handlePaymentSubmit = async (e) => {
    e.preventDefault();
    try {
      await paiementService.create(paymentData);
      toast.success('Paiement enregistré avec succès');
      fetchInvoices();
      closePaymentModal();
    } catch (err) {
      console.error('Error recording payment:', err);
      const msg = err.response?.data?.message || 'Échec de l\'enregistrement du paiement';
      toast.error(msg);
    }
  };

  const getStatusBadge = (statut) => {
    const statuses = {
      en_attente: { label: 'En attente', class: 'warning' },
      payee: { label: 'Payée', class: 'success' },
      partielle: { label: 'Partielle', class: 'info' },
      annulee: { label: 'Annulée', class: 'danger' },
    };
    return statuses[statut] || statuses.en_attente;
  };

  const formatCurrency = (amount) => {
    const value = Number(amount) || 0;
    return value.toFixed(2) + ' Ar';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('mg-MG');
  };

  const filteredInvoices = statusFilter
    ? invoices.filter(inv => inv.statut === statusFilter)
    : invoices;

  if (loading && invoices.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des factures...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchInvoices} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Factures</h1>
          <p>Suivi et création des factures</p>
        </div>
        <div className="header-actions">
          <button onClick={openModal} className="btn-primary">
            + Nouvelle facture
          </button>
          <button onClick={fetchInvoices} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-value">{invoices.length}</div>
          <div className="stat-label">Total factures</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {invoices.filter(i => i.statut === 'payee').length}
          </div>
          <div className="stat-label">Payées</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {invoices.filter(i => i.statut === 'en_attente').length}
          </div>
          <div className="stat-label">En attente</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {formatCurrency(invoices.reduce((sum, i) => {
              const paid = (i.paiements || []).reduce((s, p) => s + (p.montant || 0), 0);
              return sum + ((i.total_ttc || 0) - paid);
            }, 0))}
          </div>
          <div className="stat-label">Impayé</div>
        </div>
      </div>

      <div className="card filter-card">
        <div className="filter-controls">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-select"
          >
            <option value="">Tous les statuts</option>
            <option value="en_attente">En attente</option>
            <option value="payee">Payée</option>
            <option value="partielle">Partielle</option>
            <option value="annulee">Annulée</option>
          </select>
        </div>
      </div>

      <div className="card full-width">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th></th>
                <th>N° Facture</th>
                <th>Date</th>
                <th>Client</th>
                <th>Montant total</th>
                <th>Montant payé</th>
                <th>Reste</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center">
                    Aucune facture trouvée
                  </td>
                </tr>
              ) : (
                filteredInvoices.map(invoice => {
                  const isExpanded = expandedId === invoice.id;
                  const lignes = lignesByInvoiceId[invoice.id];
                  const isLoadingLignes = lignesLoadingId === invoice.id;
                  return (
                    <React.Fragment key={invoice.id}>
                      <tr className={isExpanded ? 'row-expanded' : ''}>
                        <td style={{ width: 32, textAlign: 'center' }}>
                          <button
                            onClick={() => toggleExpandInvoice(invoice)}
                            className="btn-expand"
                            title={isExpanded ? 'Masquer les produits' : 'Voir les produits'}
                            aria-expanded={isExpanded}
                          >
                            <i className={`ti ${isExpanded ? 'ti-chevron-down' : 'ti-chevron-right'}`} aria-hidden="true" />
                          </button>
                        </td>
                        <td>#{invoice.id}</td>
                        <td>{formatDate(invoice.created_at)}</td>
                        <td>{invoice.client_nom || invoice.client_id || 'N/A'}</td>
                        <td>{formatCurrency(invoice.total_ttc)}</td>
                        <td>{formatCurrency((invoice.paiements || []).reduce((sum, p) => sum + (p.montant || 0), 0))}</td>
                        <td>{formatCurrency((invoice.total_ttc || 0) - (invoice.paiements || []).reduce((sum, p) => sum + (p.montant || 0), 0))}</td>
                        <td>
                          <span className={`badge ${getStatusBadge(invoice.statut).class}`}>
                            {getStatusBadge(invoice.statut).label}
                          </span>
                        </td>
                        <td>
                            <button
                              onClick={() => viewInvoiceDetails(invoice)}
                              className="btn-small btn-view"
                              title="Voir les détails"
                            >
                              <i className="ti ti-eye" aria-hidden="true" />
                            </button>
                            <button
                              onClick={() => openJsonModalForInvoice(invoice)}
                              className="btn-small btn-json"
                              title="Créer JSON pour Documents"
                            >
                              <i className="ti ti-file-code" aria-hidden="true" />
                            </button>
                          {invoice.statut !== 'payee' && (
                            <button
                              onClick={() => openPaymentModal(invoice)}
                              className="btn-small btn-edit"
                              title="Enregistrer un paiement"
                            >
                              <i className="ti ti-cash" aria-hidden="true" />
                            </button>
                          )}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="invoice-lignes-row">
                          <td colSpan="9" style={{ background: '#fafafa', padding: '12px 24px' }}>
                            {isLoadingLignes ? (
                              <span className="text-muted">Chargement des produits...</span>
                            ) : !lignes || lignes.length === 0 ? (
                              <span className="text-muted">Aucun produit associé à cette facture.</span>
                            ) : (
                              <table className="data-table" style={{ margin: 0 }}>
                                <thead>
                                  <tr>
                                    <th style={{ width: '40%' }}>Produit</th>
                                    <th style={{ width: '15%' }}>Quantité</th>
                                    <th style={{ width: '20%' }}>Prix unitaire HT</th>
                                    <th style={{ width: '10%' }}>TVA %</th>
                                    <th style={{ width: '15%' }}>Total HT</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {lignes.map((l, i) => {
                                    const qty = Number(l.quantite) || 0;
                                    const pu = Number(l.prix_unitaire_ht ?? l.prix_unitaire ?? 0);
                                    const tva = Number(l.taux_tva ?? 0);
                                    const totalHt = Number(l.total_ht ?? (qty * pu));
                                    return (
                                      <tr key={i}>
                                        <td>{l.produit_nom || l.designation || `Produit #${l.produit_id}`}</td>
                                        <td>{qty}</td>
                                        <td>{formatCurrency(pu)}</td>
                                        <td>{tva}%</td>
                                        <td>{formatCurrency(totalHt)}</td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Nouvelle facture</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Vente associée *</label>
                  <select 
                    name="vente_id" 
                    value={formData.vente_id}
                    onChange={handleSaleChange}
                    required
                  >
                    <option value="">Sélectionnez une vente</option>
                    {sales.map(sale => (
                      <option key={sale.id} value={sale.id}>
                        Vente #{sale.id} - {sale.client_nom || sale.client?.nom || 'Client'} - {formatCurrency(sale.total_ttc)}
                      </option>
                    ))}
                  </select>
                </div>
                  <div className="form-group">
                    <label>Montant total (Ar)</label>
                    <input 
                      type="number" 
                      name="total_ttc" 
                      value={formData.total_ttc}
                      onChange={handleChange}
                      step="0.01"
                      min="0"
                      readOnly
                    />
                  </div>
                <div className="form-group">
                  <label>Date d'échéance</label>
                  <input 
                    type="date" 
                    name="date_echeance" 
                    value={formData.date_echeance}
                    onChange={handleChange}
                  />
                </div>
                <div className="form-group">
                  <label>Statut</label>
                  <select 
                    name="statut" 
                    value={formData.statut}
                    onChange={handleChange}
                  >
                    <option value="en_attente">En attente</option>
                    <option value="payee">Payée</option>
                    <option value="partielle">Partielle</option>
                    <option value="annulee">Annulée</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={!formData.vente_id}>
                  Créer la facture
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDetailModal && currentInvoice && (
        <div className="modal-overlay" onClick={closeDetailModal}>
          <div className="modal large" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Facture #{currentInvoice.id}</h2>
              <button onClick={closeDetailModal} className="btn-close">×</button>
            </div>
            <div className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Client</label>
                  <div>{currentInvoice.client_nom || currentInvoice.client_id || 'N/A'}</div>
                </div>
                <div className="form-group">
                  <label>Date</label>
                  <div>{formatDate(currentInvoice.created_at)}</div>
                </div>
                  <div className="form-group">
                    <label>Montant total</label>
                    <div><strong>{formatCurrency(currentInvoice.total_ttc)}</strong></div>
                  </div>
                  <div className="form-group">
                    <label>Montant payé</label>
                    <div>{formatCurrency((currentInvoice.paiements || []).reduce((sum, p) => sum + (p.montant || 0), 0))}</div>
                  </div>
                  <div className="form-group">
                    <label>Reste à payer</label>
                    <div>{formatCurrency((currentInvoice.total_ttc || 0) - (currentInvoice.paiements || []).reduce((sum, p) => sum + (p.montant || 0), 0))}</div>
                  </div>
                <div className="form-group">
                  <label>Statut</label>
                  <span className={`badge ${getStatusBadge(currentInvoice.statut).class}`}>
                    {getStatusBadge(currentInvoice.statut).label}
                  </span>
                </div>
              </div>
              <div className="modal-footer">
                <button onClick={closeDetailModal} className="btn-secondary">Fermer</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showPaymentModal && currentInvoice && (
        <div className="modal-overlay" onClick={closePaymentModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Enregistrer un paiement</h2>
              <button onClick={closePaymentModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handlePaymentSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Facture #{currentInvoice.id}</label>
                  <div>Reste à payer: {formatCurrency((currentInvoice.total_ttc || 0) - (currentInvoice.paiements || []).reduce((sum, p) => sum + (p.montant || 0), 0))}</div>
                </div>
                <div className="form-group">
                  <label>Montant payé (Ar) *</label>
                  <input 
                    type="number" 
                    name="montant" 
                    value={paymentData.montant}
                    onChange={(e) => handleChange(e, setPaymentData)}
                    step="0.01"
                    min="0"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Mode de paiement *</label>
                  <select 
                    name="mode_paiement" 
                    value={paymentData.mode_paiement}
                    onChange={(e) => handleChange(e, setPaymentData)}
                    required
                  >
                    {PAYMENT_METHODS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Date</label>
                  <input 
                    type="date" 
                    name="date" 
                    value={paymentData.date}
                    onChange={(e) => handleChange(e, setPaymentData)}
                  />
                </div>
                <div className="form-group full-width">
                  <label>Remarque</label>
                  <textarea 
                    name="remarque" 
                    value={paymentData.remarque}
                    onChange={(e) => handleChange(e, setPaymentData)}
                    placeholder="Remarques..."
                    rows="2"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closePaymentModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary">
                  Enregistrer le paiement
                </button>
              </div>
          </form>
        </div>
      </div>
      )}

      {showJsonModal && (
        <div className="modal-overlay" onClick={closeJsonModal}>
          <div className="modal large" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>JSON pour Documents {currentInvoice ? `(Facture #${currentInvoice.id})` : ''}</h2>
              <button onClick={closeJsonModal} className="btn-close">×</button>
            </div>
            <div className="modal-form">
              <p className="text-muted" style={{ marginBottom: 8 }}>
                Copiez ce JSON dans le champ <code>donnees</code> de la page Documents, ou ouvrez Documents directement (le champ sera pré-rempli).
              </p>
              <textarea
                id="invoice-json-textarea"
                value={jsonPayload}
                readOnly
                rows={16}
                style={{
                  width: '100%',
                  fontFamily: 'monospace',
                  fontSize: 12,
                  padding: 8,
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  background: '#f7f7f5',
                }}
              />
              <div className="modal-footer">
                <button type="button" onClick={closeJsonModal} className="btn-secondary">Fermer</button>
                <button type="button" onClick={copyJsonToClipboard} className="btn-primary" disabled={!jsonPayload || jsonLoading}>
                  Copier
                </button>
                <button type="button" onClick={openDocumentsWithJson} className="btn-primary" disabled={!jsonPayload || jsonLoading}>
                  Ouvrir Documents
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Invoices;
