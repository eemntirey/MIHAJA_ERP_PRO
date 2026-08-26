// src/pages/Invoices.jsx
import React, { useState, useEffect } from 'react';
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
  const [currentInvoice, setCurrentInvoice] = useState(null);
  const [currentSale, setCurrentSale] = useState(null);
  const [selectedSaleId, setSelectedSaleId] = useState('');
  const [paiements, setPaiements] = useState([]);
  
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
      setFormData(prev => ({
        ...prev,
        vente_id: saleId,
        client_id: sale.client_id || sale.client?.id || '',
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
      await factureService.create(formData);
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
                  <td colSpan="8" className="text-center">
                    Aucune facture trouvée
                  </td>
                </tr>
              ) : (
                filteredInvoices.map(invoice => (
                  <tr key={invoice.id}>
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
                ))
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
    </div>
  );
};

export default Invoices;
