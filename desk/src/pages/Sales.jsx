import React, { useState, useEffect, useMemo } from 'react';
import { toast } from 'react-toastify';
import { saleService, productService, clientService, devisService, bonLivraisonService, avoirService } from '../services/api';
import './Pages.css';

const formatCurrency = (amount) => {
  const value = Number(amount) || 0;
  return value.toFixed(2) + ' Ar';
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('mg-MG');
};

const getStatutBadge = (statut) => {
  const map = {
    en_attente: { label: 'En attente', class: 'warning' },
    payee: { label: 'Payée', class: 'success' },
    partielle: { label: 'Partielle', class: 'info' },
    annulee: { label: 'Annulée', class: 'danger' },
    accepte: { label: 'Accepté', class: 'success' },
    refuse: { label: 'Refusé', class: 'danger' },
    converti: { label: 'Converti', class: 'info' },
    expire: { label: 'Expiré', class: 'warning' },
    prepare: { label: 'Préparé', class: 'warning' },
    expedie: { label: 'Expédié', class: 'info' },
    livre: { label: 'Livré', class: 'success' },
    rembourse: { label: 'Remboursé', class: 'danger' },
    annule: { label: 'Annulé', class: 'danger' },
  };
  return map[statut] || { label: statut || 'N/A', class: '' };
};

const getModePaiementLabel = (mode) => {
  const map = {
    espece: 'Espèce',
    virement: 'Virement',
    cheque: 'Chèque',
    orange_money: 'Orange Money',
    airtel_money: 'Airtel Money',
  };
  return map[mode] || mode || 'N/A';
};

const Sales = () => {
  const [tab, setTab] = useState('ventes');
  const [sales, setSales] = useState([]);
  const [devisList, setDevisList] = useState([]);
  const [bls, setBls] = useState([]);
  const [avoirs, setAvoirs] = useState([]);
  const [products, setProducts] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [viewSale, setViewSale] = useState(null);
  const [viewBl, setViewBl] = useState(null);
  const [viewAvoir, setViewAvoir] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingSale, setEditingSale] = useState(null);
  const [editFormData, setEditFormData] = useState({ client_id: '', items: [], date: '', statut: 'en_attente', mode_paiement: 'espece', remarque: '' });
  const [saleActionLoading, setSaleActionLoading] = useState(false);

  const [formData, setFormData] = useState({ client_id: '', items: [], date: new Date().toISOString().split('T')[0], statut: 'en_attente', mode_paiement: 'espece', remarque: '' });
  const [devisForm, setDevisForm] = useState({ client_id: '', total_ht: '', total_ttc: '', date_validite: '', statut: 'en_attente', conditions_paiement: '30 jours', remarque: '' });
  const [blForm, setBlForm] = useState({ vente_id: '', client_id: '', livreur_id: '', vehicule_id: '', adresse_livraison: '', date_livraison_prevue: '', statut: 'prepare', remarque: '' });
  const [avoirForm, setAvoirForm] = useState({ vente_id: '', facture_id: '', client_id: '', montant_ht: '', montant_ttc: '', motif: '', statut: 'en_attente' });

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sRes, dRes, bRes, aRes, pRes, cRes] = await Promise.allSettled([
        saleService.getAll(),
        devisService.getAll(),
        bonLivraisonService.getAll(),
        avoirService.getAll(),
        productService.getAll({}),
        clientService.getAll({}),
      ]);
      setSales((sRes.status === 'fulfilled' ? sRes.value?.data?.ventes : undefined) || []);
      setDevisList((dRes.status === 'fulfilled' ? dRes.value?.data?.devis : undefined) || []);
      setBls((bRes.status === 'fulfilled' ? bRes.value?.data?.bons_livraison : undefined) || []);
      setAvoirs((aRes.status === 'fulfilled' ? aRes.value?.data?.avoirs : undefined) || []);
      setProducts((pRes.status === 'fulfilled' ? pRes.value?.data?.produits : undefined) || []);
      setClients((cRes.status === 'fulfilled' ? cRes.value?.data?.clients : undefined) || []);
      const failed = [sRes, dRes, bRes, aRes, pRes, cRes].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
        toast.warning(`Chargement partiel: ${msgs.join(', ')}`);
      }
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur chargement';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleAddItem = () => {
    setFormData(prev => ({ ...prev, items: [...prev.items, { produit_id: '', quantite: 1, prix_unitaire: 0, taux_tva: 20 }] }));
  };

  const handleRemoveItem = (index) => {
    setFormData(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== index) }));
  };

  const handleItemChange = (index, field, value) => {
    setFormData(prev => {
      const items = [...prev.items];
      items[index] = { ...items[index], [field]: value };
      return { ...prev, items };
    });
  };

  const handleCreateSale = async (e) => {
    e.preventDefault();
    try {
      const data = {
        ...formData,
        client_id: Number(formData.client_id),
        lignes: formData.items.map(it => ({ produit_id: Number(it.produit_id), quantite: it.quantite ? Number(it.quantite) : 0, prix_unitaire: Number(it.prix_unitaire), taux_tva: Number(it.taux_tva) })),
      };
      await saleService.create(data);
      toast.success('Vente créée');
      setFormData({ client_id: '', items: [], date: new Date().toISOString().split('T')[0], statut: 'en_attente', mode_paiement: 'espece', remarque: '' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.message || 'Erreur'); }
  };

  const handleCreateDevis = async (e) => {
    e.preventDefault();
    try {
      const data = { ...devisForm, client_id: Number(devisForm.client_id), total_ht: Number(devisForm.total_ht), total_ttc: Number(devisForm.total_ttc) };
      await devisService.create(data);
      toast.success('Devis créé');
      setDevisForm({ client_id: '', total_ht: '', total_ttc: '', date_validite: '', statut: 'en_attente', conditions_paiement: '30 jours', remarque: '' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.message || 'Erreur'); }
  };

  const handleCreateBl = async (e) => {
    e.preventDefault();
    try {
      const data = { ...blForm, vente_id: blForm.vente_id ? Number(blForm.vente_id) : null, client_id: Number(blForm.client_id), livreur_id: blForm.livreur_id ? Number(blForm.livreur_id) : null, vehicule_id: blForm.vehicule_id ? Number(blForm.vehicule_id) : null };
      await bonLivraisonService.create(data);
      toast.success('Bon de livraison créé');
      setBlForm({ vente_id: '', client_id: '', livreur_id: '', vehicule_id: '', adresse_livraison: '', date_livraison_prevue: '', statut: 'prepare', remarque: '' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.message || 'Erreur'); }
  };

  const handleCreateAvoir = async (e) => {
    e.preventDefault();
    try {
      const data = { ...avoirForm, vente_id: avoirForm.vente_id ? Number(avoirForm.vente_id) : null, facture_id: avoirForm.facture_id ? Number(avoirForm.facture_id) : null, client_id: Number(avoirForm.client_id), montant_ht: Number(avoirForm.montant_ht), montant_ttc: Number(avoirForm.montant_ttc) };
      await avoirService.create(data);
      toast.success('Avoir créé');
      setAvoirForm({ vente_id: '', facture_id: '', client_id: '', montant_ht: '', montant_ttc: '', motif: '', statut: 'en_attente' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.message || 'Erreur'); }
  };

  const handleConvertDevis = async (id) => {
    try {
      setSaleActionLoading(true);
      await devisService.convertir(id);
      toast.success('Devis converti en vente');
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la conversion';
      toast.error(msg);
    } finally { setSaleActionLoading(false); }
  };

  const handleDeleteSale = async (id) => {
    if (!window.confirm('Voulez-vous supprimer cette vente ?')) return;
    try {
      setSaleActionLoading(true);
      await saleService.delete(id);
      toast.success('Vente supprimée');
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la suppression';
      toast.error(msg);
    } finally { setSaleActionLoading(false); }
  };

  const handleViewSale = async (sale) => {
    try {
      setSaleActionLoading(true);
      const res = await saleService.getById(sale.id);
      setViewSale(res.data);
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors du chargement des détails';
      toast.error(msg);
    } finally {
      setSaleActionLoading(false);
    }
  };

  const handleViewBl = (bl) => {
    setViewBl(bl);
  };

  const handleViewAvoir = (avoir) => {
    setViewAvoir(avoir);
  };

  const handleEditSale = (sale) => {
    setEditingSale(sale);
    setEditFormData({
      client_id: sale.client_id || '',
      items: sale.lignes?.map(l => ({ produit_id: l.produit_id ?? '', quantite: l.quantite || 1, prix_unitaire: l.prix_unitaire || 0, taux_tva: l.taux_tva || 20 })) || [],
      date: sale.date ? sale.date.split('T')[0] : new Date().toISOString().split('T')[0],
      statut: sale.statut || 'en_attente',
      mode_paiement: sale.mode_paiement || 'espece',
      remarque: sale.remarque || ''
    });
    setShowEditModal(true);
  };

  const handleUpdateSale = async (e) => {
    e.preventDefault();
    if (!editingSale) return;
    try {
      setSaleActionLoading(true);
      const data = {
        ...editFormData,
        client_id: Number(editFormData.client_id),
        lignes: editFormData.items.map(it => ({ produit_id: Number(it.produit_id), quantite: Number(it.quantite), prix_unitaire: Number(it.prix_unitaire), taux_tva: Number(it.taux_tva) })),
      };
      await saleService.update(editingSale.id, data);
      toast.success('Vente modifiée');
      setShowEditModal(false);
      setEditingSale(null);
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la modification';
      toast.error(msg);
    } finally {
      setSaleActionLoading(false);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const getSortedFilteredData = (data, searchFields) => {
    let result = [...data];
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(item =>
        searchFields.some(field => {
          const val = item[field];
          return val && String(val).toLowerCase().includes(term);
        })
      );
    }
    if (sortConfig.key) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        if (typeof aVal === 'string') {
          return sortConfig.direction === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        }
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      });
    }
    return result;
  };

  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return '';
    return sortConfig.direction === 'asc' ? ' ▲' : ' ▼';
  };

  if (loading && !sales.length && !products.length && !clients.length && !devisList.length && !bls.length && !avoirs.length) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des ventes...</p>
        </div>
      </div>
    );
  }

  if (error && !sales.length && !products.length && !clients.length && !devisList.length && !bls.length && !avoirs.length) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchData} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  const sortedSales = getSortedFilteredData(sales, ['reference', 'client_nom', 'statut', 'mode_paiement']);
  const sortedDevis = getSortedFilteredData(devisList, ['reference', 'client_nom', 'statut']);
  const sortedBls = getSortedFilteredData(bls, ['reference', 'client_nom', 'statut']);
  const sortedAvoirs = getSortedFilteredData(avoirs, ['reference', 'client_nom', 'motif', 'statut']);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Ventes</h1>
        <div className="tabs">
          {['ventes', 'devis', 'bons-livraison', 'avoirs'].map(t => (
            <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t === 'bons-livraison' ? 'Bons de livraison' : t === 'avoirs' ? 'Avoirs' : t === 'devis' ? 'Devis' : 'Ventes'}</button>
          ))}
        </div>
      </div>

      {tab === 'ventes' && (
        <div className="card">
          <div className="card-actions">
            <button className="btn-primary" onClick={() => setShowModal(true)}>Nouvelle vente</button>
          </div>
          <div className="filter-controls">
            <div className="search-box">
              <input
                type="text"
                placeholder="Rechercher une vente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('reference')} className="sortable">Référence{getSortIndicator('reference')}</th>
                  <th onClick={() => handleSort('client_nom')} className="sortable">Client{getSortIndicator('client_nom')}</th>
                  <th onClick={() => handleSort('date')} className="sortable">Date{getSortIndicator('date')}</th>
                  <th onClick={() => handleSort('total_ttc')} className="sortable">Total TTC{getSortIndicator('total_ttc')}</th>
                  <th onClick={() => handleSort('statut')} className="sortable">Statut{getSortIndicator('statut')}</th>
                  <th onClick={() => handleSort('mode_paiement')} className="sortable">Mode{getSortIndicator('mode_paiement')}</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedSales.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center">Aucune vente trouvée</td>
                  </tr>
                ) : (
                  sortedSales.map(s => {
                    const badge = getStatutBadge(s.statut);
                    return (
                      <tr key={s.id}>
                        <td>{s.reference || 'N/A'}</td>
                        <td>{s.client_nom || 'N/A'}</td>
                        <td>{formatDate(s.date)}</td>
                        <td>{formatCurrency(s.total_ttc)}</td>
                        <td><span className={`badge ${badge.class}`}>{badge.label}</span></td>
                        <td>{getModePaiementLabel(s.mode_paiement)}</td>
                        <td>
                          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewSale(s)} disabled={saleActionLoading}>
                            {saleActionLoading ? <span className="btn-spinner" /> : <i className="ti ti-eye" />}
                          </button>
                          <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEditSale(s)} disabled={saleActionLoading}>
                            {saleActionLoading ? <span className="btn-spinner" /> : <i className="ti ti-edit" />}
                          </button>
                          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDeleteSale(s.id)} disabled={saleActionLoading}>
                            {saleActionLoading ? <span className="btn-spinner" /> : <i className="ti ti-trash" />}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
          {showModal && (
            <div className="modal-overlay">
              <div className="modal large" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Nouvelle vente</h2>
                  <button onClick={() => setShowModal(false)} className="btn-close">×</button>
                </div>
                <form onSubmit={handleCreateSale} className="modal-form">
                  <div className="form-grid">
                    <div className="form-group">
                      <label>Client *</label>
                      <select value={formData.client_id} onChange={e => setFormData({...formData, client_id: e.target.value})} required>
                        <option value="">Client</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Date</label>
                      <input type="date" value={formData.date} onChange={e => setFormData({...formData, date: e.target.value})} />
                    </div>
                    <div className="form-group">
                      <label>Statut</label>
                      <select value={formData.statut} onChange={e => setFormData({...formData, statut: e.target.value})}>
                        <option value="en_attente">En attente</option>
                        <option value="payee">Payée</option>
                        <option value="annulee">Annulée</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Mode de paiement</label>
                      <select value={formData.mode_paiement} onChange={e => setFormData({...formData, mode_paiement: e.target.value})}>
                        <option value="espece">Espèce</option>
                        <option value="virement">Virement</option>
                        <option value="cheque">Chèque</option>
                        <option value="orange_money">Orange Money</option>
                        <option value="airtel_money">Airtel Money</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-section">
                    <h3>Lignes de vente</h3>
                    <div className="form-grid">
                      {formData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Produit</label>
                          <select value={item.produit_id} onChange={e => handleItemChange(idx, 'produit_id', e.target.value)} required>
                            <option value="">Produit</option>
                            {products.map(p => <option key={p.id} value={p.id}>{p.nom}</option>)}
                          </select>
                        </div>
                      ))}
                      {formData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Quantité</label>
                          <input type="number" value={item.quantite} onChange={e => handleItemChange(idx, 'quantite', e.target.value)} required />
                        </div>
                      ))}
                      {formData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Prix HT</label>
                          <input type="number" value={item.prix_unitaire} onChange={e => handleItemChange(idx, 'prix_unitaire', e.target.value)} required />
                        </div>
                      ))}
                      {formData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>TVA %</label>
                          <input type="number" value={item.taux_tva} onChange={e => handleItemChange(idx, 'taux_tva', e.target.value)} />
                        </div>
                      ))}
                      {formData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Action</label>
                          <button type="button" className="btn-small btn-danger" onClick={() => handleRemoveItem(idx)}>Supprimer</button>
                        </div>
                      ))}
                    </div>
                    <button type="button" className="btn-secondary" onClick={handleAddItem}>+ Ajouter ligne</button>
                  </div>
                  <div className="form-group full-width">
                    <label>Remarque</label>
                    <textarea value={formData.remarque} onChange={e => setFormData({...formData, remarque: e.target.value})} />
                  </div>
                  <div className="modal-footer">
                    <button type="submit" className="btn-primary">Créer</button>
                    <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Fermer</button>
                  </div>
                </form>
              </div>
            </div>
          )}
          {viewSale && (
            <div className="modal-overlay" onClick={() => setViewSale(null)}>
              <div className="modal large" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Détails de la vente #{viewSale.id}</h2>
                  <button onClick={() => setViewSale(null)} className="btn-close">×</button>
                </div>
                <div className="modal-form">
                  <div className="form-grid">
                    <div className="form-group"><label>Référence</label><div>{viewSale.reference || 'N/A'}</div></div>
                    <div className="form-group"><label>Client</label><div>{viewSale.client_nom || 'N/A'}</div></div>
                    <div className="form-group"><label>Date</label><div>{formatDate(viewSale.date)}</div></div>
                    <div className="form-group"><label>Total HT</label><div>{formatCurrency(viewSale.total_ht)}</div></div>
                    <div className="form-group"><label>Total TTC</label><div>{formatCurrency(viewSale.total_ttc)}</div></div>
                    <div className="form-group"><label>Statut</label><div><span className={`badge ${getStatutBadge(viewSale.statut).class}`}>{getStatutBadge(viewSale.statut).label}</span></div></div>
                    <div className="form-group"><label>Mode de paiement</label><div>{getModePaiementLabel(viewSale.mode_paiement)}</div></div>
                  </div>
                  {viewSale.lignes && viewSale.lignes.length > 0 && (
                    <div className="form-section">
                      <h3>Lignes de vente</h3>
                      <table className="data-table">
                        <thead><tr><th>Produit</th><th>Quantité</th><th>Prix HT</th><th>TVA %</th><th>Total</th></tr></thead>
                        <tbody>
                          {viewSale.lignes.map((l, i) => (
                            <tr key={i}>
                              <td>{l.produit_nom || ('Produit #' + l.produit_id)}</td>
                              <td>{l.quantite}</td>
                              <td>{formatCurrency(l.prix_unitaire)}</td>
                              <td>{l.taux_tva}%</td>
                              <td>{formatCurrency((l.quantite * l.prix_unitaire) * (1 + (l.taux_tva || 0) / 100))}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {viewSale.remarque && (
                    <div className="form-group full-width"><label>Remarque</label><div>{viewSale.remarque}</div></div>
                  )}
                </div>
              </div>
            </div>
          )}
          {showEditModal && (
            <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
              <div className="modal large" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Modifier la vente #{editingSale?.id}</h2>
                  <button onClick={() => setShowEditModal(false)} className="btn-close">×</button>
                </div>
                <form onSubmit={handleUpdateSale} className="modal-form">
                  <div className="form-grid">
                    <div className="form-group">
                      <label>Client *</label>
                      <select value={editFormData.client_id} onChange={e => setEditFormData({...editFormData, client_id: e.target.value})} required>
                        <option value="">Client</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Date</label>
                      <input type="date" value={editFormData.date} onChange={e => setEditFormData({...editFormData, date: e.target.value})} />
                    </div>
                    <div className="form-group">
                      <label>Statut</label>
                      <select value={editFormData.statut} onChange={e => setEditFormData({...editFormData, statut: e.target.value})}>
                        <option value="en_attente">En attente</option>
                        <option value="payee">Payée</option>
                        <option value="partielle">Partielle</option>
                        <option value="annulee">Annulée</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Mode de paiement</label>
                      <select value={editFormData.mode_paiement} onChange={e => setEditFormData({...editFormData, mode_paiement: e.target.value})}>
                        <option value="espece">Espèce</option>
                        <option value="virement">Virement</option>
                        <option value="cheque">Chèque</option>
                        <option value="orange_money">Orange Money</option>
                        <option value="airtel_money">Airtel Money</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-section">
                    <h3>Lignes de vente</h3>
                    <div className="form-grid">
                      {editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Produit</label>
                          <select value={item.produit_id} onChange={e => handleItemChange(idx, 'produit_id', e.target.value)} required>
                            <option value="">Produit</option>
                            {products.map(p => <option key={p.id} value={p.id}>{p.nom}</option>)}
                          </select>
                        </div>
                      ))}
                      {editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Quantité</label>
                          <input type="number" value={item.quantite} onChange={e => handleItemChange(idx, 'quantite', e.target.value)} required />
                        </div>
                      ))}
                      {editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Prix HT</label>
                          <input type="number" value={item.prix_unitaire} onChange={e => handleItemChange(idx, 'prix_unitaire', e.target.value)} required />
                        </div>
                      ))}
                      {editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>TVA %</label>
                          <input type="number" value={item.taux_tva} onChange={e => handleItemChange(idx, 'taux_tva', e.target.value)} />
                        </div>
                      ))}
                      {editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-group">
                          <label>Action</label>
                          <button type="button" className="btn-small btn-danger" onClick={() => handleRemoveItem(idx)}>Supprimer</button>
                        </div>
                      ))}
                    </div>
                    <button type="button" className="btn-secondary" onClick={handleAddItem}>+ Ajouter ligne</button>
                  </div>
                  <div className="form-group full-width">
                    <label>Remarque</label>
                    <textarea value={editFormData.remarque} onChange={e => setEditFormData({...editFormData, remarque: e.target.value})} />
                  </div>
                  <div className="modal-footer">
                    <button type="submit" className="btn-primary">Enregistrer</button>
                    <button type="button" className="btn-secondary" onClick={() => setShowEditModal(false)}>Fermer</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'devis' && (
        <div className="card">
          <h3>Nouveau devis</h3>
          <form onSubmit={handleCreateDevis} className="form-grid">
            <div className="form-group">
              <label>Client *</label>
              <select value={devisForm.client_id} onChange={e => setDevisForm({...devisForm, client_id: e.target.value})} required>
                <option value="">Client</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Total HT *</label>
              <input type="number" value={devisForm.total_ht} onChange={e => setDevisForm({...devisForm, total_ht: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Total TTC *</label>
              <input type="number" value={devisForm.total_ttc} onChange={e => setDevisForm({...devisForm, total_ttc: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Date de validité</label>
              <input type="date" value={devisForm.date_validite} onChange={e => setDevisForm({...devisForm, date_validite: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={devisForm.statut} onChange={e => setDevisForm({...devisForm, statut: e.target.value})}>
                <option value="en_attente">En attente</option>
                <option value="accepte">Accepté</option>
                <option value="refuse">Refusé</option>
                <option value="converti">Converti</option>
                <option value="expire">Expiré</option>
              </select>
            </div>
            <div className="form-group">
              <label>Conditions de paiement</label>
              <input value={devisForm.conditions_paiement} onChange={e => setDevisForm({...devisForm, conditions_paiement: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Remarque</label>
              <textarea value={devisForm.remarque} onChange={e => setDevisForm({...devisForm, remarque: e.target.value})} />
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary">Créer</button>
            </div>
          </form>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('reference')} className="sortable">Référence{getSortIndicator('reference')}</th>
                  <th onClick={() => handleSort('client_nom')} className="sortable">Client{getSortIndicator('client_nom')}</th>
                  <th>Date</th>
                  <th>Total HT</th>
                  <th>Total TTC</th>
                  <th>Validité</th>
                  <th onClick={() => handleSort('statut')} className="sortable">Statut{getSortIndicator('statut')}</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedDevis.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="text-center">Aucun devis trouvé</td>
                  </tr>
                ) : (
                  sortedDevis.map(d => {
                    const badge = getStatutBadge(d.statut);
                    return (
                      <tr key={d.id}>
                        <td>{d.reference || 'N/A'}</td>
                        <td>{d.client_nom || 'N/A'}</td>
                        <td>{formatDate(d.date || d.created_at)}</td>
                        <td>{formatCurrency(d.total_ht)}</td>
                        <td>{formatCurrency(d.total_ttc)}</td>
                        <td>{formatDate(d.date_validite)}</td>
                        <td><span className={`badge ${badge.class}`}>{badge.label}</span></td>
                        <td>
                          <button className="btn-small btn-edit" title="Convertir" onClick={() => handleConvertDevis(d.id)}>
                            <i className="ti ti-refresh" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
          {viewBl && (
            <div className="modal-overlay" onClick={() => setViewBl(null)}>
              <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Détails du bon de livraison</h2>
                  <button onClick={() => setViewBl(null)} className="btn-close">×</button>
                </div>
                <div className="modal-form">
                  <div className="form-grid">
                    <div className="form-group"><label>Référence</label><div>{viewBl.reference || 'N/A'}</div></div>
                    <div className="form-group"><label>Client</label><div>{viewBl.client_nom || 'N/A'}</div></div>
                    <div className="form-group"><label>Vente Réf</label><div>{viewBl.vente_reference || viewBl.vente_id || 'N/A'}</div></div>
                    <div className="form-group"><label>Adresse de livraison</label><div>{viewBl.adresse_livraison || 'N/A'}</div></div>
                    <div className="form-group"><label>Date de livraison</label><div>{formatDate(viewBl.date_livraison_prevue)}</div></div>
                    <div className="form-group"><label>Statut</label><div><span className={`badge ${getStatutBadge(viewBl.statut).class}`}>{getStatutBadge(viewBl.statut).label}</span></div></div>
                  </div>
                  {viewBl.remarque && (
                    <div className="form-group full-width"><label>Remarque</label><div>{viewBl.remarque}</div></div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'bons-livraison' && (
        <div className="card">
          <h3>Nouveau bon de livraison</h3>
          <form onSubmit={handleCreateBl} className="form-grid">
            <div className="form-group">
              <label>Vente *</label>
              <select value={blForm.vente_id} onChange={e => setBlForm({...blForm, vente_id: e.target.value})} required>
                <option value="">Sélectionner une vente</option>
                {sales.map(s => <option key={s.id} value={s.id}>{s.reference}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Client *</label>
              <select value={blForm.client_id} onChange={e => setBlForm({...blForm, client_id: e.target.value})} required>
                <option value="">Client</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Adresse de livraison</label>
              <input value={blForm.adresse_livraison} onChange={e => setBlForm({...blForm, adresse_livraison: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Date de livraison prévue</label>
              <input type="date" value={blForm.date_livraison_prevue} onChange={e => setBlForm({...blForm, date_livraison_prevue: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={blForm.statut} onChange={e => setBlForm({...blForm, statut: e.target.value})}>
                <option value="prepare">Préparé</option>
                <option value="expedie">Expédié</option>
                <option value="livre">Livré</option>
              </select>
            </div>
            <div className="form-group">
              <label>Remarque</label>
              <textarea value={blForm.remarque} onChange={e => setBlForm({...blForm, remarque: e.target.value})} />
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary">Créer</button>
            </div>
          </form>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('reference')} className="sortable">Référence{getSortIndicator('reference')}</th>
                  <th onClick={() => handleSort('client_nom')} className="sortable">Client{getSortIndicator('client_nom')}</th>
                  <th>Vente</th>
                  <th>Adresse</th>
                  <th>Date livraison</th>
                  <th onClick={() => handleSort('statut')} className="sortable">Statut{getSortIndicator('statut')}</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedBls.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center">Aucun bon de livraison trouvé</td>
                  </tr>
                ) : (
                  sortedBls.map(b => {
                    const badge = getStatutBadge(b.statut);
                    return (
                      <tr key={b.id}>
                        <td>{b.reference || 'N/A'}</td>
                        <td>{b.client_nom || 'N/A'}</td>
                        <td>{b.vente_reference || b.vente_id || 'N/A'}</td>
                        <td>{b.adresse_livraison || 'N/A'}</td>
                        <td>{formatDate(b.date_livraison_prevue)}</td>
                        <td><span className={`badge ${badge.class}`}>{badge.label}</span></td>
                        <td>
                          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewBl(b)}>
                            <i className="ti ti-eye" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
          {viewAvoir && (
            <div className="modal-overlay" onClick={() => setViewAvoir(null)}>
              <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Détails de l'avoir</h2>
                  <button onClick={() => setViewAvoir(null)} className="btn-close">×</button>
                </div>
                <div className="modal-form">
                  <div className="form-grid">
                    <div className="form-group"><label>Référence</label><div>{viewAvoir.reference || 'N/A'}</div></div>
                    <div className="form-group"><label>Client</label><div>{viewAvoir.client_nom || 'N/A'}</div></div>
                    <div className="form-group"><label>Montant HT</label><div>{formatCurrency(viewAvoir.montant_ht)}</div></div>
                    <div className="form-group"><label>Montant TTC</label><div>{formatCurrency(viewAvoir.montant_ttc)}</div></div>
                    <div className="form-group"><label>Statut</label><div><span className={`badge ${getStatutBadge(viewAvoir.statut).class}`}>{getStatutBadge(viewAvoir.statut).label}</span></div></div>
                  </div>
                  {viewAvoir.motif && (
                    <div className="form-group full-width"><label>Motif</label><div>{viewAvoir.motif}</div></div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'avoirs' && (
        <div className="card">
          <h3>Nouvel avoir</h3>
          <form onSubmit={handleCreateAvoir} className="form-grid">
            <div className="form-group">
              <label>Vente</label>
              <select value={avoirForm.vente_id} onChange={e => setAvoirForm({...avoirForm, vente_id: e.target.value})}>
                <option value="">Vente</option>
                {sales.map(s => <option key={s.id} value={s.id}>{s.reference}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Client *</label>
              <select value={avoirForm.client_id} onChange={e => setAvoirForm({...avoirForm, client_id: e.target.value})} required>
                <option value="">Client</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Montant HT *</label>
              <input type="number" value={avoirForm.montant_ht} onChange={e => setAvoirForm({...avoirForm, montant_ht: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Montant TTC *</label>
              <input type="number" value={avoirForm.montant_ttc} onChange={e => setAvoirForm({...avoirForm, montant_ttc: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Motif</label>
              <textarea value={avoirForm.motif} onChange={e => setAvoirForm({...avoirForm, motif: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={avoirForm.statut} onChange={e => setAvoirForm({...avoirForm, statut: e.target.value})}>
                <option value="en_attente">En attente</option>
                <option value="accepte">Accepté</option>
                <option value="rembourse">Remboursé</option>
                <option value="annule">Annulé</option>
              </select>
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary">Créer</button>
            </div>
          </form>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('reference')} className="sortable">Référence{getSortIndicator('reference')}</th>
                  <th onClick={() => handleSort('client_nom')} className="sortable">Client{getSortIndicator('client_nom')}</th>
                  <th>Montant HT</th>
                  <th>Montant TTC</th>
                  <th>Motif</th>
                  <th onClick={() => handleSort('statut')} className="sortable">Statut{getSortIndicator('statut')}</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedAvoirs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center">Aucun avoir trouvé</td>
                  </tr>
                ) : (
                  sortedAvoirs.map(a => {
                    const badge = getStatutBadge(a.statut);
                    return (
                      <tr key={a.id}>
                        <td>{a.reference || 'N/A'}</td>
                        <td>{a.client_nom || 'N/A'}</td>
                        <td>{formatCurrency(a.montant_ht)}</td>
                        <td>{formatCurrency(a.montant_ttc)}</td>
                        <td>{a.motif || 'N/A'}</td>
                        <td><span className={`badge ${badge.class}`}>{badge.label}</span></td>
                        <td>
                          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewAvoir(a)}>
                            <i className="ti ti-eye" />
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
      )}
    </div>
  );
};

export default Sales;
