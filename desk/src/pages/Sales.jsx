import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { toast } from 'react-toastify';
import { saleService, productService, clientService, devisService, bonLivraisonService, avoirService } from '../services/api';
import { PAYMENT_METHODS, PAYMENT_METHOD_LABELS } from '../constants/erpConstants';
import DataTable from '../components/desktop/DataTable';
import FilterPanel from '../components/desktop/FilterPanel';
import FormGrid, { FormField, FormDraftBanner, FormDraftStatus } from '../components/desktop/FormGrid';
import useFormDraft from '../hooks/useFormDraft';
import { applyFilters, applySearch } from '../utils/filterUtils';
import { exportRowsToCsv, timestampedFilename } from '../utils/exportUtils';
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
  return PAYMENT_METHOD_LABELS[mode] || mode || 'N/A';
};

const computeLineTotal = (item) => {
  const quantite = Number(item?.quantite) || 0;
  const prix = Number(item?.prix_unitaire) || 0;
  const tva = Number(item?.taux_tva) || 0;
  return quantite * prix * (1 + tva / 100);
};

const computeItemsTotal = (items = []) => items.reduce((sum, item) => sum + computeLineTotal(item), 0);

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
  const [filters, setFilters] = useState([]);
  const [appliedFilters, setAppliedFilters] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [viewSale, setViewSale] = useState(null);
  const [viewBl, setViewBl] = useState(null);
  const [viewAvoir, setViewAvoir] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingSale, setEditingSale] = useState(null);
  const [editFormData, setEditFormData] = useState({ client_id: '', items: [], date: '', statut: 'en_attente', mode_paiement: 'especes', remarque: '' });
  const [saleActionLoading, setSaleActionLoading] = useState(false);

  const [formData, setFormData] = useState({ client_id: '', items: [], date: new Date().toISOString().split('T')[0], statut: 'en_attente', mode_paiement: 'especes', remarque: '' });
  const [devisForm, setDevisForm] = useState({ client_id: '', total_ht: '', total_ttc: '', date_validite: '', statut: 'en_attente', conditions_paiement: '30 jours', remarque: '' });
  const [blForm, setBlForm] = useState({ vente_id: '', client_id: '', livreur_id: '', vehicule_id: '', adresse_livraison: '', date_livraison_prevue: '', statut: 'prepare', remarque: '' });
  const [avoirForm, setAvoirForm] = useState({ vente_id: '', facture_id: '', client_id: '', montant_ht: '', montant_ttc: '', motif: '', statut: 'en_attente' });

  // Brouillons locaux (auto-save toutes les 5 s) des deux formulaires de vente
  const createDraft = useFormDraft(showModal ? 'ventes:new' : null, formData, { enabled: showModal });
  const editDraft = useFormDraft(
    showEditModal && editingSale ? `ventes:${editingSale.id}` : null,
    editFormData,
    { enabled: showEditModal }
  );

  const fetchData = useCallback(async () => {
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
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

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

  // Lignes du formulaire d'édition (état distinct de la création)
  const handleEditAddItem = () => {
    setEditFormData(prev => ({ ...prev, items: [...prev.items, { produit_id: '', quantite: 1, prix_unitaire: 0, taux_tva: 20 }] }));
  };

  const handleEditRemoveItem = (index) => {
    setEditFormData(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== index) }));
  };

  const handleEditItemChange = (index, field, value) => {
    setEditFormData(prev => {
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
      createDraft.clear();
      setFormData({ client_id: '', items: [], date: new Date().toISOString().split('T')[0], statut: 'en_attente', mode_paiement: 'especes', remarque: '' });
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
      mode_paiement: sale.mode_paiement || 'especes',
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
      editDraft.clear();
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

  const badgeCell = (value) => {
    const badge = getStatutBadge(value);
    return <span className={`badge ${badge.class}`}>{badge.label}</span>;
  };

  /* ------------------------------------------------------ colonnes DataTable */

  const salesColumns = useMemo(() => [
    { key: 'reference', label: 'Référence', width: 150, render: (v) => v || 'N/A' },
    { key: 'client_nom', label: 'Client', width: 200, render: (v) => v || 'N/A' },
    { key: 'date', label: 'Date', type: 'date', width: 120, render: (v) => formatDate(v) },
    { key: 'total_ht', label: 'Total HT', type: 'number', align: 'right', width: 130, render: (v) => formatCurrency(v) },
    { key: 'total_ttc', label: 'Total TTC', type: 'number', align: 'right', width: 130, render: (v) => formatCurrency(v) },
    { key: 'statut', label: 'Statut', width: 120, align: 'center', render: badgeCell },
    { key: 'mode_paiement', label: 'Mode', width: 130, render: (v) => getModePaiementLabel(v) },
    {
      key: 'actions',
      label: 'Actions',
      width: 130,
      sortable: false,
      resizable: false,
      exportable: false,
      align: 'center',
      render: (_v, row) => (
        <span className="dt-actions">
          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewSale(row)} disabled={saleActionLoading}>
            <i className="ti ti-eye" />
          </button>
          <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEditSale(row)} disabled={saleActionLoading}>
            <i className="ti ti-edit" />
          </button>
          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDeleteSale(row.id)} disabled={saleActionLoading}>
            <i className="ti ti-trash" />
          </button>
        </span>
      ),
    },

  ], [saleActionLoading]);

  const devisColumns = useMemo(() => [
    { key: 'reference', label: 'Référence', width: 150, render: (v) => v || 'N/A' },
    { key: 'client_nom', label: 'Client', width: 190, render: (v) => v || 'N/A' },
    { key: 'date', label: 'Date', type: 'date', width: 115, accessor: (row) => row.date || row.created_at, render: (v) => formatDate(v) },
    { key: 'total_ht', label: 'Total HT', type: 'number', align: 'right', width: 125, render: (v) => formatCurrency(v) },
    { key: 'total_ttc', label: 'Total TTC', type: 'number', align: 'right', width: 125, render: (v) => formatCurrency(v) },
    { key: 'date_validite', label: 'Validité', type: 'date', width: 115, render: (v) => formatDate(v) },
    { key: 'statut', label: 'Statut', width: 120, align: 'center', render: badgeCell },
    {
      key: 'actions',
      label: 'Actions',
      width: 100,
      sortable: false,
      resizable: false,
      exportable: false,
      align: 'center',
      render: (_v, row) => (
        <span className="dt-actions">
          <button className="btn-small btn-edit" title="Convertir en vente" onClick={() => handleConvertDevis(row.id)} disabled={saleActionLoading}>
            <i className="ti ti-refresh" />
          </button>
        </span>
      ),
    },

  ], [saleActionLoading]);

  const blColumns = useMemo(() => [
    { key: 'reference', label: 'Référence', width: 150, render: (v) => v || 'N/A' },
    { key: 'client_nom', label: 'Client', width: 190, render: (v) => v || 'N/A' },
    { key: 'vente_reference', label: 'Vente', width: 140, accessor: (row) => row.vente_reference || row.vente_id, render: (v) => v || 'N/A' },
    { key: 'adresse_livraison', label: 'Adresse', width: 220, render: (v) => v || 'N/A' },
    { key: 'date_livraison_prevue', label: 'Date livraison', type: 'date', width: 130, render: (v) => formatDate(v) },
    { key: 'statut', label: 'Statut', width: 120, align: 'center', render: badgeCell },
    {
      key: 'actions',
      label: 'Actions',
      width: 90,
      sortable: false,
      resizable: false,
      exportable: false,
      align: 'center',
      render: (_v, row) => (
        <span className="dt-actions">
          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewBl(row)}>
            <i className="ti ti-eye" />
          </button>
        </span>
      ),
    },

  ], []);

  const avoirColumns = useMemo(() => [
    { key: 'reference', label: 'Référence', width: 150, render: (v) => v || 'N/A' },
    { key: 'client_nom', label: 'Client', width: 190, render: (v) => v || 'N/A' },
    { key: 'montant_ht', label: 'Montant HT', type: 'number', align: 'right', width: 130, render: (v) => formatCurrency(v) },
    { key: 'montant_ttc', label: 'Montant TTC', type: 'number', align: 'right', width: 130, render: (v) => formatCurrency(v) },
    { key: 'motif', label: 'Motif', width: 240, render: (v) => v || 'N/A' },
    { key: 'statut', label: 'Statut', width: 120, align: 'center', render: badgeCell },
    {
      key: 'actions',
      label: 'Actions',
      width: 90,
      sortable: false,
      resizable: false,
      exportable: false,
      align: 'center',
      render: (_v, row) => (
        <span className="dt-actions">
          <button className="btn-small btn-view" title="Voir" onClick={() => handleViewAvoir(row)}>
            <i className="ti ti-eye" />
          </button>
        </span>
      ),
    },

  ], []);

  /* --------------------------------------------------------------- filtres */

  const clientOptions = useMemo(
    () => [...new Set([...sales, ...devisList, ...bls, ...avoirs].map((r) => r.client_nom).filter(Boolean))],
    [sales, devisList, bls, avoirs]
  );

  const salesFilterFields = useMemo(() => [
    { key: 'reference', label: 'Référence', type: 'text' },
    { key: 'client_nom', label: 'Client', type: 'select', options: clientOptions },
    { key: 'date', label: 'Date', type: 'date' },
    { key: 'total_ht', label: 'Total HT', type: 'number' },
    { key: 'total_ttc', label: 'Total TTC', type: 'number' },
    {
      key: 'statut',
      label: 'Statut',
      type: 'select',
      options: [
        { value: 'en_attente', label: 'En attente' },
        { value: 'payee', label: 'Payée' },
        { value: 'partielle', label: 'Partielle' },
        { value: 'annulee', label: 'Annulée' },
      ],
    },
    {
      key: 'mode_paiement',
      label: 'Mode de paiement',
      type: 'select',
      options: PAYMENT_METHODS.map(m => ({ value: m.value, label: m.label })),
    },
  ], [clientOptions]);

  const devisFilterFields = useMemo(() => [
    { key: 'reference', label: 'Référence', type: 'text' },
    { key: 'client_nom', label: 'Client', type: 'select', options: clientOptions },
    { key: 'total_ttc', label: 'Total TTC', type: 'number' },
    { key: 'date_validite', label: 'Validité', type: 'date' },
    {
      key: 'statut',
      label: 'Statut',
      type: 'select',
      options: [
        { value: 'en_attente', label: 'En attente' },
        { value: 'accepte', label: 'Accepté' },
        { value: 'refuse', label: 'Refusé' },
        { value: 'converti', label: 'Converti' },
        { value: 'expire', label: 'Expiré' },
      ],
    },
  ], [clientOptions]);

  const blFilterFields = useMemo(() => [
    { key: 'reference', label: 'Référence', type: 'text' },
    { key: 'client_nom', label: 'Client', type: 'select', options: clientOptions },
    { key: 'adresse_livraison', label: 'Adresse', type: 'text' },
    { key: 'date_livraison_prevue', label: 'Date livraison', type: 'date' },
    {
      key: 'statut',
      label: 'Statut',
      type: 'select',
      options: [
        { value: 'prepare', label: 'Préparé' },
        { value: 'expedie', label: 'Expédié' },
        { value: 'livre', label: 'Livré' },
      ],
    },
  ], [clientOptions]);

  const avoirFilterFields = useMemo(() => [
    { key: 'reference', label: 'Référence', type: 'text' },
    { key: 'client_nom', label: 'Client', type: 'select', options: clientOptions },
    { key: 'montant_ttc', label: 'Montant TTC', type: 'number' },
    { key: 'motif', label: 'Motif', type: 'text' },
    {
      key: 'statut',
      label: 'Statut',
      type: 'select',
      options: [
        { value: 'en_attente', label: 'En attente' },
        { value: 'accepte', label: 'Accepté' },
        { value: 'rembourse', label: 'Remboursé' },
        { value: 'annule', label: 'Annulé' },
      ],
    },
  ], [clientOptions]);

  const tabConfig = useMemo(() => ({
    ventes: { module: 'ventes', fields: salesFilterFields, searchFields: ['reference', 'client_nom', 'statut', 'mode_paiement'] },
    devis: { module: 'ventes-devis', fields: devisFilterFields, searchFields: ['reference', 'client_nom', 'statut'] },
    'bons-livraison': { module: 'ventes-bl', fields: blFilterFields, searchFields: ['reference', 'client_nom', 'statut'] },
    avoirs: { module: 'ventes-avoirs', fields: avoirFilterFields, searchFields: ['reference', 'client_nom', 'motif', 'statut'] },
  }), [salesFilterFields, devisFilterFields, blFilterFields, avoirFilterFields]);

  const activeTabConfig = tabConfig[tab] || tabConfig.ventes;

  const filterRows = useCallback((rows, fields, searchFields) => {
    const searched = applySearch(rows, searchTerm, searchFields.map((key) => ({ key })));
    return applyFilters(searched, appliedFilters, fields);
  }, [appliedFilters, searchTerm]);

  const filteredSales = useMemo(
    () => filterRows(sales, salesFilterFields, tabConfig.ventes.searchFields),
    [filterRows, sales, salesFilterFields, tabConfig]
  );
  const filteredDevis = useMemo(
    () => filterRows(devisList, devisFilterFields, tabConfig.devis.searchFields),
    [filterRows, devisList, devisFilterFields, tabConfig]
  );
  const filteredBls = useMemo(
    () => filterRows(bls, blFilterFields, tabConfig['bons-livraison'].searchFields),
    [filterRows, bls, blFilterFields, tabConfig]
  );
  const filteredAvoirs = useMemo(
    () => filterRows(avoirs, avoirFilterFields, tabConfig.avoirs.searchFields),
    [filterRows, avoirs, avoirFilterFields, tabConfig]
  );

  /* ------------------------------------------------------- actions groupées */

  const makeExportAction = useCallback((prefix, columns, label) => ({
    key: 'export',
    label: 'Exporter CSV',
    icon: 'ti-download',
    onClick: (ids, rows) => {
      const ok = exportRowsToCsv(timestampedFilename(prefix), columns, rows);
      if (ok) toast.success(`${rows.length} ${label} exporté(s)`);
      else toast.error("Échec de l'export CSV");
    },
  }), []);

  const salesBulkActions = useMemo(() => [
    makeExportAction('ventes', salesColumns, 'vente(s)'),
    {
      key: 'delete',
      label: 'Supprimer',
      icon: 'ti-trash',
      variant: 'danger',
      confirm: (count) => `Supprimer définitivement ${count} vente(s) ?`,
      onClick: async (ids) => {
        const results = await Promise.allSettled(ids.map((id) => saleService.delete(id)));
        const failed = results.filter((r) => r.status === 'rejected').length;
        const done = results.length - failed;
        if (done > 0) toast.success(`${done} vente(s) supprimée(s)`);
        if (failed > 0) toast.error(`${failed} suppression(s) en échec`);
        fetchData();
      },
    },
  ], [fetchData, makeExportAction, salesColumns]);

  const devisBulkActions = useMemo(() => [
    makeExportAction('devis', devisColumns, 'devis'),
    {
      key: 'convert',
      label: 'Convertir en ventes',
      icon: 'ti-refresh',
      confirm: (count) => `Convertir ${count} devis en vente(s) ?`,
      onClick: async (ids) => {
        const results = await Promise.allSettled(ids.map((id) => devisService.convertir(id)));
        const failed = results.filter((r) => r.status === 'rejected').length;
        const done = results.length - failed;
        if (done > 0) toast.success(`${done} devis converti(s)`);
        if (failed > 0) toast.error(`${failed} conversion(s) en échec`);
        fetchData();
      },
    },
  ], [devisColumns, fetchData, makeExportAction]);

  const blBulkActions = useMemo(
    () => [makeExportAction('bons-livraison', blColumns, 'bon(s) de livraison')],
    [blColumns, makeExportAction]
  );

  const avoirBulkActions = useMemo(
    () => [makeExportAction('avoirs', avoirColumns, 'avoir(s)')],
    [avoirColumns, makeExportAction]
  );

  const handleTabChange = (nextTab) => {
    setTab(nextTab);
    setSelectedIds([]);
    setFilters([]);
    setAppliedFilters([]);
    setSearchTerm('');
  };

  const renderFilterPanel = () => (
    <FilterPanel
      key={tab}
      module={activeTabConfig.module}
      fields={activeTabConfig.fields}
      filters={filters}
      onFiltersChange={setFilters}
      onApply={setAppliedFilters}
      onReset={() => setAppliedFilters([])}
    />
  );

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

  const sortedSales = filteredSales;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Ventes</h1>
        <div className="tabs">
          {['ventes', 'devis', 'bons-livraison', 'avoirs'].map(t => (
            <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => handleTabChange(t)}>{t === 'bons-livraison' ? 'Bons de livraison' : t === 'avoirs' ? 'Avoirs' : t === 'devis' ? 'Devis' : 'Ventes'}</button>
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
          {renderFilterPanel()}
          <DataTable
            module="ventes"
            columns={salesColumns}
            data={sortedSales}
            rowKey="id"
            loading={loading}
            emptyMessage="Aucune vente trouvée"
            defaultSort={[{ key: 'date', direction: 'desc' }]}
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={salesBulkActions}
            rowHeight={46}
            maxHeight={560}
          />
          {showModal && (
            <div className="modal-overlay">
              <div className="modal large" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>Nouvelle vente</h2>
                  <button onClick={() => setShowModal(false)} className="btn-close">×</button>
                </div>
                <form onSubmit={handleCreateSale} className="modal-form">
                  <FormDraftBanner draft={createDraft} onRestore={(data) => setFormData(prev => ({ ...prev, ...data }))} />
                  <FormGrid columns={2}>
                    <FormField label="Client" required htmlFor="vente-client">
                      <select id="vente-client" value={formData.client_id} onChange={e => setFormData({...formData, client_id: e.target.value})} required>
                        <option value="">Client</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
                      </select>
                    </FormField>
                    <FormField label="Date" htmlFor="vente-date">
                      <input id="vente-date" type="date" value={formData.date} onChange={e => setFormData({...formData, date: e.target.value})} />
                    </FormField>
                    <FormField label="Statut" htmlFor="vente-statut">
                      <select id="vente-statut" value={formData.statut} onChange={e => setFormData({...formData, statut: e.target.value})}>
                        <option value="en_attente">En attente</option>
                        <option value="payee">Payée</option>
                        <option value="annulee">Annulée</option>
                      </select>
                    </FormField>
                    <FormField label="Mode de paiement" htmlFor="vente-mode">
                      <select id="vente-mode" value={formData.mode_paiement} onChange={e => setFormData({...formData, mode_paiement: e.target.value})}>
                        {PAYMENT_METHODS.map(m => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Remarque" span="full" htmlFor="vente-remarque">
                      <textarea id="vente-remarque" value={formData.remarque} onChange={e => setFormData({...formData, remarque: e.target.value})} rows="2" />
                    </FormField>
                  </FormGrid>

                  <div className="form-grid-section">
                    <div className="form-grid-section-head">
                      <h4 className="form-grid-section-title">Lignes de vente</h4>
                      <div className="form-grid-section-actions">
                        <span className="form-field-hint">Total TTC : {formatCurrency(computeItemsTotal(formData.items))}</span>
                        <button type="button" className="btn-secondary" onClick={handleAddItem}>+ Ajouter ligne</button>
                      </div>
                    </div>
                    {formData.items.length === 0 ? (
                      <p className="form-field-hint">Aucune ligne — ajoutez au moins un produit.</p>
                    ) : (
                      formData.items.map((item, idx) => (
                        <div key={idx} className="form-line-block">
                          <FormGrid columns={3} dense>
                            <FormField label={`Produit ${idx + 1}`} required>
                              <select value={item.produit_id} onChange={e => handleItemChange(idx, 'produit_id', e.target.value)} required>
                                <option value="">Produit</option>
                                {products.map(p => <option key={p.id} value={p.id}>{p.nom}</option>)}
                              </select>
                            </FormField>
                            <FormField label="Quantité" required>
                              <input type="number" min="1" value={item.quantite} onChange={e => handleItemChange(idx, 'quantite', e.target.value)} required />
                            </FormField>
                            <FormField label="Prix HT" required>
                              <input type="number" min="0" step="0.01" value={item.prix_unitaire} onChange={e => handleItemChange(idx, 'prix_unitaire', e.target.value)} required />
                            </FormField>
                            <FormField label="TVA %">
                              <input type="number" min="0" value={item.taux_tva} onChange={e => handleItemChange(idx, 'taux_tva', e.target.value)} />
                            </FormField>
                            <FormField label="Total ligne" hint="TTC">
                              <input type="text" value={formatCurrency(computeLineTotal(item))} readOnly tabIndex={-1} />
                            </FormField>
                            <FormField label="Action">
                              <button type="button" className="btn-small btn-danger" onClick={() => handleRemoveItem(idx)}>Supprimer</button>
                            </FormField>
                          </FormGrid>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="modal-footer">
                    <FormDraftStatus draft={createDraft} />
                    <div className="modal-footer-actions">
                      <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Fermer</button>
                      <button type="submit" className="btn-primary">Créer</button>
                    </div>
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
                  <FormDraftBanner draft={editDraft} onRestore={(data) => setEditFormData(prev => ({ ...prev, ...data }))} />
                  <FormGrid columns={2}>
                    <FormField label="Client" required htmlFor="vente-edit-client">
                      <select id="vente-edit-client" value={editFormData.client_id} onChange={e => setEditFormData({...editFormData, client_id: e.target.value})} required>
                        <option value="">Client</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.nom_complet || c.nom}</option>)}
                      </select>
                    </FormField>
                    <FormField label="Date" htmlFor="vente-edit-date">
                      <input id="vente-edit-date" type="date" value={editFormData.date} onChange={e => setEditFormData({...editFormData, date: e.target.value})} />
                    </FormField>
                    <FormField label="Statut" htmlFor="vente-edit-statut">
                      <select id="vente-edit-statut" value={editFormData.statut} onChange={e => setEditFormData({...editFormData, statut: e.target.value})}>
                        <option value="en_attente">En attente</option>
                        <option value="payee">Payée</option>
                        <option value="partielle">Partielle</option>
                        <option value="annulee">Annulée</option>
                      </select>
                    </FormField>
                    <FormField label="Mode de paiement" htmlFor="vente-edit-mode">
                      <select id="vente-edit-mode" value={editFormData.mode_paiement} onChange={e => setEditFormData({...editFormData, mode_paiement: e.target.value})}>
                        {PAYMENT_METHODS.map(m => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Remarque" span="full" htmlFor="vente-edit-remarque">
                      <textarea id="vente-edit-remarque" value={editFormData.remarque} onChange={e => setEditFormData({...editFormData, remarque: e.target.value})} rows="2" />
                    </FormField>
                  </FormGrid>

                  <div className="form-grid-section">
                    <div className="form-grid-section-head">
                      <h4 className="form-grid-section-title">Lignes de vente</h4>
                      <div className="form-grid-section-actions">
                        <span className="form-field-hint">Total TTC : {formatCurrency(computeItemsTotal(editFormData.items))}</span>
                        <button type="button" className="btn-secondary" onClick={handleEditAddItem}>+ Ajouter ligne</button>
                      </div>
                    </div>
                    {editFormData.items.length === 0 ? (
                      <p className="form-field-hint">Aucune ligne — ajoutez au moins un produit.</p>
                    ) : (
                      editFormData.items.map((item, idx) => (
                        <div key={idx} className="form-line-block">
                          <FormGrid columns={3} dense>
                            <FormField label={`Produit ${idx + 1}`} required>
                              <select value={item.produit_id} onChange={e => handleEditItemChange(idx, 'produit_id', e.target.value)} required>
                                <option value="">Produit</option>
                                {products.map(p => <option key={p.id} value={p.id}>{p.nom}</option>)}
                              </select>
                            </FormField>
                            <FormField label="Quantité" required>
                              <input type="number" min="1" value={item.quantite} onChange={e => handleEditItemChange(idx, 'quantite', e.target.value)} required />
                            </FormField>
                            <FormField label="Prix HT" required>
                              <input type="number" min="0" step="0.01" value={item.prix_unitaire} onChange={e => handleEditItemChange(idx, 'prix_unitaire', e.target.value)} required />
                            </FormField>
                            <FormField label="TVA %">
                              <input type="number" min="0" value={item.taux_tva} onChange={e => handleEditItemChange(idx, 'taux_tva', e.target.value)} />
                            </FormField>
                            <FormField label="Total ligne" hint="TTC">
                              <input type="text" value={formatCurrency(computeLineTotal(item))} readOnly tabIndex={-1} />
                            </FormField>
                            <FormField label="Action">
                              <button type="button" className="btn-small btn-danger" onClick={() => handleEditRemoveItem(idx)}>Supprimer</button>
                            </FormField>
                          </FormGrid>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="modal-footer">
                    <FormDraftStatus draft={editDraft} />
                    <div className="modal-footer-actions">
                      <button type="button" className="btn-secondary" onClick={() => setShowEditModal(false)}>Fermer</button>
                      <button type="submit" className="btn-primary" disabled={saleActionLoading}>Enregistrer</button>
                    </div>
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
          {renderFilterPanel()}
          <DataTable
            module="ventes-devis"
            columns={devisColumns}
            data={filteredDevis}
            rowKey="id"
            loading={loading}
            emptyMessage="Aucun devis trouvé"
            defaultSort={[{ key: 'date', direction: 'desc' }]}
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={devisBulkActions}
            rowHeight={46}
            maxHeight={520}
          />
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
          {renderFilterPanel()}
          <DataTable
            module="ventes-bl"
            columns={blColumns}
            data={filteredBls}
            rowKey="id"
            loading={loading}
            emptyMessage="Aucun bon de livraison trouvé"
            defaultSort={[{ key: 'date_livraison_prevue', direction: 'desc' }]}
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={blBulkActions}
            rowHeight={46}
            maxHeight={520}
          />
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
          {renderFilterPanel()}
          <DataTable
            module="ventes-avoirs"
            columns={avoirColumns}
            data={filteredAvoirs}
            rowKey="id"
            loading={loading}
            emptyMessage="Aucun avoir trouvé"
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            bulkActions={avoirBulkActions}
            rowHeight={46}
            maxHeight={520}
          />
        </div>
      )}
    </div>
  );
};

export default Sales;
