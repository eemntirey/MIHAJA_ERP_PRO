// src/pages/Payments.jsx
import React, { useState, useEffect } from 'react';
import { paiementService, factureService, clientService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Payments = () => {
  const [payments, setPayments] = useState([]);
  const [factures, setFactures] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    facture_id: '',
    client_id: '',
    montant: 0,
    mode_paiement: 'especes',
    operateur_mobile: '',
    numero_telephone: '',
    date_paiement: new Date().toISOString().split('T')[0],
    notes: '',
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [paymentsResponse, facturesResponse, clientsResponse] = await Promise.allSettled([
        paiementService.getAll({}),
        factureService.getAll({}),
        clientService.getAll({}),
      ]);

      setPayments((paymentsResponse.status === 'fulfilled' ? paymentsResponse.value?.data?.paiements || paymentsResponse.value?.data || [] : []));
      setFactures((facturesResponse.status === 'fulfilled' ? facturesResponse.value?.data?.factures || facturesResponse.value?.data || [] : []));
      setClients((clientsResponse.status === 'fulfilled' ? clientsResponse.value?.data?.clients || clientsResponse.value?.data || [] : []));

      const failed = [paymentsResponse, facturesResponse, clientsResponse].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
        toast.warning(`Chargement partiel: ${msgs.join(', ')}`);
      }
    } catch (err) {
      console.error('Error fetching payments data:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des paiements';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'montant' ? parseFloat(value) || 0 : value,
    }));
  };

  const handleFactureChange = (e) => {
    const factureId = parseInt(e.target.value, 10) || '';
    const facture = factures.find(f => f.id === factureId);
    setFormData(prev => ({
      ...prev,
      facture_id: factureId,
      client_id: facture?.client_id || '',
      montant: facture ? (facture.total_ttc || 0) - (facture.paiements?.reduce((sum, p) => sum + (p.montant || 0), 0) || 0) : 0,
    }));
  };

  const openModal = () => {
    setFormData({
      facture_id: '',
      client_id: '',
      montant: 0,
      mode_paiement: 'especes',
      operateur_mobile: '',
      numero_telephone: '',
      date_paiement: new Date().toISOString().split('T')[0],
      notes: '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.facture_id) {
      toast.error('Veuillez sélectionner une facture');
      return;
    }
    if (!formData.client_id) {
      toast.error('Le client associé à la facture est requis');
      return;
    }
    if (formData.montant <= 0) {
      toast.error('Le montant doit être supérieur à 0');
      return;
    }
    try {
      await paiementService.create(formData);
      toast.success('Paiement enregistré avec succès');
      fetchData();
      closeModal();
    } catch (err) {
      console.error('Error creating payment:', err);
      const msg = err.response?.data?.message || 'Échec de l’enregistrement du paiement';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Voulez-vous vraiment supprimer ce paiement ?')) return;
    try {
      await paiementService.delete(id);
      toast.success('Paiement supprimé');
      fetchData();
    } catch (err) {
      console.error('Error deleting payment:', err);
      const msg = err.response?.data?.message || 'Échec de la suppression du paiement';
      toast.error(msg);
    }
  };

  const totalAmount = payments.reduce((sum, payment) => sum + (payment.montant || 0), 0);
  const averageAmount = payments.length ? totalAmount / payments.length : 0;

  const getModeLabel = (mode) => {
    const labels = {
      especes: 'Espèces',
      virement: 'Virement',
      carte: 'Carte bancaire',
      cheque: 'Chèque',
      mobile_money: 'Mobile money',
      orange_money: 'Orange Money',
      airtel_money: 'Airtel Money',
    };
    return labels[mode] || mode;
  };

  const getStatutLabel = (statut) => {
    const labels = {
      en_attente: 'En attente',
      confirme: 'Confirmé',
      echec: 'Échec',
      rembourse: 'Remboursé',
    };
    return labels[statut] || statut || 'Non défini';
  };

  const getStatutClass = (statut) => {
    const map = {
      en_attente: 'statut-warning',
      confirme: 'statut-success',
      echec: 'statut-error',
      rembourse: 'statut-info',
    };
    return map[statut] || '';
  };

  if (loading && payments.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des paiements...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchData} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Paiements</h1>
          <p>Suivi des règlements et encaissements</p>
        </div>
        <div className="header-actions">
          <button onClick={openModal} className="btn-primary">
            + Ajouter un paiement
          </button>
          <button onClick={fetchData} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-value">{payments.length}</div>
          <div className="stat-label">Total paiements</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totalAmount.toFixed(2)} Ar</div>
          <div className="stat-label">Montant total</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{averageAmount.toFixed(2)} Ar</div>
          <div className="stat-label">Montant moyen</div>
        </div>
      </div>

      <div className="card full-width">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                 <th>Facture</th>
                 <th>Client</th>
                 <th>Montant</th>
                 <th>Mode de paiement</th>
                 <th>Statut</th>
                 <th>Date</th>
                 <th>Remarque</th>
                 <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {payments.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center">
                    Aucun paiement enregistré
                  </td>
                </tr>
              ) : (
                payments.map(payment => {
                  const facture = factures.find(f => f.id === payment.facture_id);
                  const client = clients.find(c => c.id === payment.client_id);
                  return (
                    <tr key={payment.id}>
                      <td>#{payment.id}</td>
                      <td>{facture ? `#${facture.id}` : payment.facture_id}</td>
                      <td>{client ? client.nom || client.raison_sociale || 'N/A' : payment.client_id}</td>
                      <td>{(payment.montant || 0).toFixed(2)} Ar</td>
                      <td>{getModeLabel(payment.mode_paiement)}</td>
                      <td><span className={`statut-badge ${getStatutClass(payment.statut)}`}>{getStatutLabel(payment.statut)}</span></td>
                      <td>{payment.date_paiement ? new Date(payment.date_paiement).toLocaleDateString('mg-MG') : (payment.created_at ? new Date(payment.created_at).toLocaleDateString('mg-MG') : 'N/A')}</td>
                      <td>{payment.notes || payment.remarque || '-'}</td>
                      <td>
                        <button onClick={() => handleDelete(payment.id)} className="btn-small btn-delete" title="Supprimer">
                          <i className="ti ti-trash" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
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
              <h2>Ajouter un paiement</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Facture *</label>
                  <select name="facture_id" value={formData.facture_id} onChange={handleFactureChange} required>
                    <option value="">Sélectionnez une facture</option>
                    {factures.map(facture => (
                      <option key={facture.id} value={facture.id}>
                        #{facture.id} - {facture.total_ttc?.toFixed(2) || '0.00'} Ar
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Client associé</label>
                  <select name="client_id" value={formData.client_id} onChange={handleChange} required>
                    <option value="">Sélectionnez un client</option>
                    {clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.nom || client.raison_sociale || `Client #${client.id}`}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Montant (Ar) *</label>
                  <input
                    type="number"
                    name="montant"
                    value={formData.montant}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Mode de paiement *</label>
                  <select name="mode_paiement" value={formData.mode_paiement} onChange={handleChange} required>
                    <option value="especes">Espèces</option>
                    <option value="virement">Virement</option>
                    <option value="carte">Carte bancaire</option>
                    <option value="cheque">Chèque</option>
                    <option value="orange_money">Orange Money</option>
                    <option value="airtel_money">Airtel Money</option>
                    <option value="mobile_money">Autre Mobile Money</option>
                  </select>
                </div>

                {(formData.mode_paiement === 'orange_money' || formData.mode_paiement === 'airtel_money' || formData.mode_paiement === 'mobile_money') && (
                  <>
                    <div className="form-group">
                      <label>Opérateur</label>
                      <input name="operateur_mobile" value={formData.operateur_mobile || ''} onChange={handleChange} placeholder="Orange / Airtel" />
                    </div>
                    <div className="form-group">
                      <label>N° Téléphone</label>
                      <input name="numero_telephone" value={formData.numero_telephone || ''} onChange={handleChange} placeholder="+261 34 00 000 00" />
                    </div>
                  </>
                )}

                <div className="form-group">
                  <label>Date *</label>
                  <input
                    type="date"
                    name="date_paiement"
                    value={formData.date_paiement}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label>Remarque</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder="Ajouter une note..."
                    rows="3"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary">
                  Enregistrer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Payments;
