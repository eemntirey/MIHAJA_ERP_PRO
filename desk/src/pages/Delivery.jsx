import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { livreurService, vehiculeService, itineraireService, livraisonService } from '../services/api';
import './Pages.css';
import './Delivery.css';

const TABS = [
  { id: 'livraisons', label: 'Livraisons', icon: 'ti-truck-delivery' },
  { id: 'livreurs', label: 'Livreurs', icon: 'ti-steering-wheel' },
  { id: 'vehicules', label: 'Véhicules', icon: 'ti-car' },
  { id: 'itineraires', label: 'Itinéraires', icon: 'ti-route' },
  { id: 'suivis', label: 'Suivis', icon: 'ti-map-pin' },
];

const STATUS_TONES = {
  en_attente: 'warning', chargee: 'info', en_route: 'info', livree: 'success', retournee: 'neutral', echec: 'danger',
  actif: 'success', inactif: 'neutral', en_conges: 'warning',
  disponible: 'success', en_mission: 'info', en_maintenance: 'warning',
  planifie: 'warning', en_cours: 'info', termine: 'success', annule: 'danger',
};

const STATUS_LABELS = {
  en_attente: 'En attente', chargee: 'Chargée', en_route: 'En route', livree: 'Livrée', retournee: 'Retournée', echec: 'Échec',
  actif: 'Actif', inactif: 'Inactif', en_conges: 'En congés',
  disponible: 'Disponible', en_mission: 'En mission', en_maintenance: 'En maintenance',
  planifie: 'Planifié', en_cours: 'En cours', termine: 'Terminé', annule: 'Annulé',
};

const StatusBadge = ({ status }) => (
  <span className={`badge ${STATUS_TONES[status] || 'neutral'}`}>
    {STATUS_LABELS[status] || status}
  </span>
);

export default function Delivery() {
  const [tab, setTab] = useState('livraisons');
  const [livreurs, setLivreurs] = useState([]);
  const [vehicules, setVehicules] = useState([]);
  const [itineraires, setItineraires] = useState([]);
  const [livraisons, setLivraisons] = useState([]);
  const [suivis, setSuivis] = useState({});
  const [loading, setLoading] = useState(true);

  const [livreurForm, setLivreurForm] = useState({ nom: '', prenom: '', telephone: '', email: '', numero_permis: '', statut: 'actif' });
  const [vehiculeForm, setVehiculeForm] = useState({ marque: '', modele: '', plaque_immatriculation: '', type: 'camion', capacite_charge: '', capacite_volume: '', statut: 'disponible' });
  const [itineraireForm, setItineraireForm] = useState({ nom: '', description: '', date_depart: '', date_retour: '', points_intermediaires: '', livreur_id: '', vehicule_id: '', statut: 'planifie' });
  const [livraisonForm, setLivraisonForm] = useState({ vente_id: '', commande_client_id: '', itineraire_id: '', livreur_id: '', vehicule_id: '', adresse_livraison: '', ville_livraison: '', telephone_livraison: '', nom_destinataire: '', date_livraison_prevue: '', statut: 'en_attente', notes: '' });
  const [suiviForm, setSuiviForm] = useState({ statut: '', commentaire: '', localisation_lat: '', localisation_lng: '' });

  const [editingId, setEditingId] = useState(null);
  const [editingType, setEditingType] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [lRes, vRes, iRes, liRes] = await Promise.allSettled([
        livreurService.getAll(),
        vehiculeService.getAll(),
        itineraireService.getAll(),
        livraisonService.getAll(),
      ]);
      setLivreurs((lRes.status === 'fulfilled' ? lRes.value?.data?.livreurs || lRes.value?.data || [] : []));
      setVehicules((vRes.status === 'fulfilled' ? vRes.value?.data?.vehicules || vRes.value?.data || [] : []));
      setItineraires((iRes.status === 'fulfilled' ? iRes.value?.data?.itineraires || iRes.value?.data || [] : []));
      setLivraisons((liRes.status === 'fulfilled' ? liRes.value?.data?.livraisons || liRes.value?.data || [] : []));

      const failed = [lRes, vRes, iRes, liRes].filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
        toast.warning(`Chargement partiel: ${msgs.join(', ')}`);
      }
    } catch (e) {
      toast.error('Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

    useEffect(() => { fetchAll(); }, []);

    if (loading && livreurs.length === 0 && vehicules.length === 0 && itineraires.length === 0 && livraisons.length === 0) {
        return (
            <div className="page-container">
                <div className="loading-screen">
                    <div className="spinner-large"></div>
                    <p>Chargement des livraisons...</p>
                </div>
            </div>
        );
    }

  const handleSubmit = async (e, type) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      let data;
      if (type === 'livreur') data = { ...livreurForm };
      else if (type === 'vehicule') data = { ...vehiculeForm, capacite_charge: vehiculeForm.capacite_charge ? Number(vehiculeForm.capacite_charge) : null, capacite_volume: vehiculeForm.capacite_volume ? Number(vehiculeForm.capacite_volume) : null };
      else if (type === 'itineraire') data = { ...itineraireForm, livreur_id: itineraireForm.livreur_id ? Number(itineraireForm.livreur_id) : null, vehicule_id: itineraireForm.vehicule_id ? Number(itineraireForm.vehicule_id) : null, points_intermediaires: itineraireForm.points_intermediaires ? JSON.stringify(itineraireForm.points_intermediaires.split('\n')) : null };
      else if (type === 'livraison') data = { ...livraisonForm, livreur_id: livraisonForm.livreur_id ? Number(livraisonForm.livreur_id) : null, vehicule_id: livraisonForm.vehicule_id ? Number(livraisonForm.vehicule_id) : null, itineraire_id: livraisonForm.itineraire_id ? Number(livraisonForm.itineraire_id) : null, vente_id: livraisonForm.vente_id ? Number(livraisonForm.vente_id) : null, commande_client_id: livraisonForm.commande_client_id ? Number(livraisonForm.commande_client_id) : null };
      const svc = type === 'livreur' ? livreurService : type === 'vehicule' ? vehiculeService : type === 'itineraire' ? itineraireService : livraisonService;
      if (editingType === type && editingId) {
        await svc.update(editingId, data);
        toast.success('Modifié avec succès');
      } else {
        await svc.create(data);
        toast.success('Créé avec succès');
      }
      resetForm(type);
      fetchAll();
    } catch (e) {
      toast.error(e.response?.data?.message || 'Erreur');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm('Supprimer ?')) return;
    const svc = type === 'livreur' ? livreurService : type === 'vehicule' ? vehiculeService : type === 'itineraire' ? itineraireService : livraisonService;
    try {
      await svc.delete(id);
      toast.success('Supprimé');
      fetchAll();
    } catch (e) {
      toast.error('Erreur de suppression');
    }
  };

  const handleEdit = (item, type) => {
    setEditingId(item.id);
    setEditingType(type);
    if (type === 'livreur') setLivreurForm({ nom: item.nom || '', prenom: item.prenom || '', telephone: item.telephone || '', email: item.email || '', numero_permis: item.numero_permis || '', statut: item.statut || 'actif' });
    else if (type === 'vehicule') setVehiculeForm({ marque: item.marque || '', modele: item.modele || '', plaque_immatriculation: item.plaque_immatriculation || '', type: item.type || 'camion', capacite_charge: item.capacite_charge || '', capacite_volume: item.capacite_volume || '', statut: item.statut || 'disponible' });
    else if (type === 'itineraire') setItineraireForm({ nom: item.nom || '', description: item.description || '', date_depart: item.date_depart ? item.date_depart.slice(0, 16) : '', date_retour: item.date_retour ? item.date_retour.slice(0, 16) : '', points_intermediaires: (() => { try { const arr = JSON.parse(item.points_intermediaires || '[]'); return Array.isArray(arr) ? arr.join('\n') : (item.points_intermediaires || ''); } catch { return item.points_intermediaires || ''; } })(), livreur_id: item.livreur_id || '', vehicule_id: item.vehicule_id || '', statut: item.statut || 'planifie' });
    else if (type === 'livraison') setLivraisonForm({ vente_id: item.vente_id || '', commande_client_id: item.commande_client_id || '', itineraire_id: item.itineraire_id || '', livreur_id: item.livreur_id || '', vehicule_id: item.vehicule_id || '', adresse_livraison: item.adresse_livraison || '', ville_livraison: item.ville_livraison || '', telephone_livraison: item.telephone_livraison || '', nom_destinataire: item.nom_destinataire || '', date_livraison_prevue: item.date_livraison_prevue ? item.date_livraison_prevue.slice(0, 16) : '', statut: item.statut || 'en_attente', notes: item.notes || '' });
    setTab(type);
  };

  const resetForm = (type) => {
    setEditingId(null);
    setEditingType(null);
    if (type === 'livreur') setLivreurForm({ nom: '', prenom: '', telephone: '', email: '', numero_permis: '', statut: 'actif' });
    else if (type === 'vehicule') setVehiculeForm({ marque: '', modele: '', plaque_immatriculation: '', type: 'camion', capacite_charge: '', capacite_volume: '', statut: 'disponible' });
    else if (type === 'itineraire') setItineraireForm({ nom: '', description: '', date_depart: '', date_retour: '', points_intermediaires: '', livreur_id: '', vehicule_id: '', statut: 'planifie' });
    else if (type === 'livraison') setLivraisonForm({ vente_id: '', commande_client_id: '', itineraire_id: '', livreur_id: '', vehicule_id: '', adresse_livraison: '', ville_livraison: '', telephone_livraison: '', nom_destinataire: '', date_livraison_prevue: '', statut: 'en_attente', notes: '' });
  };

  const viewSuivis = async (livraisonId) => {
    if (!suivis[livraisonId]) {
      try {
        const res = await livraisonService.getSuivis(livraisonId);
        setSuivis(prev => ({ ...prev, [livraisonId]: res.data.suivis || [] }));
      } catch (e) { toast.error('Erreur chargement suivis'); }
    }
    setTab('suivis');
  };

  const submitSuivi = async (e, livraisonId) => {
    e.preventDefault();
    setSubmitting(true);
    if (!livraisonId) return;
    try {
      await livraisonService.addSuivi(livraisonId, {
        ...suiviForm,
        localisation_lat: suiviForm.localisation_lat ? Number(suiviForm.localisation_lat) : null,
        localisation_lng: suiviForm.localisation_lng ? Number(suiviForm.localisation_lng) : null,
      });
      toast.success('Suivi ajouté');
      setSuiviForm({ statut: '', commentaire: '', localisation_lat: '', localisation_lng: '' });
      const res = await livraisonService.getSuivis(livraisonId);
      setSuivis(prev => ({ ...prev, [livraisonId]: res.data.suivis || [] }));
      fetchAll();
    } catch (e) { toast.error('Erreur'); }
    finally { setSubmitting(false); }
  };

  const handleAvancer = async (id) => {
    try {
      await livraisonService.avancer(id);
      toast.success('Statut avancé');
      fetchAll();
    } catch (e) { toast.error('Erreur'); }
  };

  const counts = {
    livraisons: livraisons.length,
    livreurs: livreurs.length,
    vehicules: vehicules.length,
    itineraires: itineraires.length,
    suivis: Object.values(suivis).reduce((sum, list) => sum + list.length, 0),
  };

  const livraisonsActives = livraisons.filter(l => l.statut === 'en_attente' || l.statut === 'chargee' || l.statut === 'en_route').length;
  const livreursActifs = livreurs.filter(l => l.statut === 'actif').length;
  const vehiculesDispo = vehicules.filter(v => v.statut === 'disponible').length;
  const itinerairesEnCours = itineraires.filter(i => i.statut === 'en_cours').length;

  return (
    <div className="page-container delivery-page">
      <div className="page-header">
        <h1>Gestion des livraisons</h1>
        <p>Planifiez et suivez vos tournées, livreurs, véhicules et itinéraires.</p>
      </div>

      <div className="delivery-stats">
        <div className="delivery-stat">
          <span className="delivery-stat__icon"><i className="ti ti-truck-delivery" /></span>
          <div className="delivery-stat__body">
            <span className="delivery-stat__value">{livraisonsActives}</span>
            <span className="delivery-stat__label">Livraisons actives</span>
          </div>
        </div>
        <div className="delivery-stat">
          <span className="delivery-stat__icon"><i className="ti ti-steering-wheel" /></span>
          <div className="delivery-stat__body">
            <span className="delivery-stat__value">{livreursActifs}</span>
            <span className="delivery-stat__label">Livreurs actifs</span>
          </div>
        </div>
        <div className="delivery-stat">
          <span className="delivery-stat__icon"><i className="ti ti-car" /></span>
          <div className="delivery-stat__body">
            <span className="delivery-stat__value">{vehiculesDispo}</span>
            <span className="delivery-stat__label">Véhicules dispo.</span>
          </div>
        </div>
        <div className="delivery-stat">
          <span className="delivery-stat__icon"><i className="ti ti-route" /></span>
          <div className="delivery-stat__body">
            <span className="delivery-stat__value">{itinerairesEnCours}</span>
            <span className="delivery-stat__label">Itinéraires en cours</span>
          </div>
        </div>
      </div>

      <div className="delivery-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`delivery-tab ${tab === t.id ? 'is-active' : ''}`}
            onClick={() => { setTab(t.id); setEditingId(null); setEditingType(null); }}
          >
            <i className={`ti ${t.icon}`} />
            <span>{t.label}</span>
            <span className="delivery-tab__count">{counts[t.id] || 0}</span>
          </button>
        ))}
      </div>

      {tab === 'livreurs' && (
        <div className="card">
          <div className="delivery-section-head">
            <h3>{editingType === 'livreur' ? 'Modifier le livreur' : 'Nouveau livreur'}</h3>
          </div>
          <form onSubmit={(e) => handleSubmit(e, 'livreur')} className="form-grid">
            <div className="form-group">
              <label>Prénom *</label>
              <input value={livreurForm.prenom} onChange={e => setLivreurForm({...livreurForm, prenom: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Nom *</label>
              <input value={livreurForm.nom} onChange={e => setLivreurForm({...livreurForm, nom: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Téléphone</label>
              <input value={livreurForm.telephone} onChange={e => setLivreurForm({...livreurForm, telephone: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input value={livreurForm.email} onChange={e => setLivreurForm({...livreurForm, email: e.target.value})} />
            </div>
            <div className="form-group">
              <label>N° permis</label>
              <input value={livreurForm.numero_permis} onChange={e => setLivreurForm({...livreurForm, numero_permis: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={livreurForm.statut} onChange={e => setLivreurForm({...livreurForm, statut: e.target.value})}>
                <option value="actif">Actif</option>
                <option value="inactif">Inactif</option>
                <option value="en_conges">En congés</option>
              </select>
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : (editingType === 'livreur' ? 'Modifier' : 'Créer')}</button>
            </div>
            {editingType === 'livreur' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('livreur')} disabled={submitting}>Annuler</button></div>}
          </form>
          <div className="table-container">
            <table className="data-table delivery-table">
              <thead><tr><th>Nom</th><th>Prénom</th><th>Téléphone</th><th>Email</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
                {livreurs.map(l => (
                  <tr key={l.id}>
                    <td>{l.nom}</td><td>{l.prenom}</td><td>{l.telephone}</td><td>{l.email}</td>
                    <td><StatusBadge status={l.statut} /></td>
                    <td>
                      <span className="delivery-actions">
                        <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEdit(l, 'livreur')}><i className="ti ti-edit" /></button>
                        <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('livreur', l.id)}><i className="ti ti-trash" /></button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {livreurs.length === 0 && <div className="delivery-empty"><i className="ti ti-user-off" /><span>Aucun livreur enregistré.</span></div>}
        </div>
      )}

      {tab === 'vehicules' && (
        <div className="card">
          <div className="delivery-section-head">
            <h3>{editingType === 'vehicule' ? 'Modifier le véhicule' : 'Nouveau véhicule'}</h3>
          </div>
          <form onSubmit={(e) => handleSubmit(e, 'vehicule')} className="form-grid">
            <div className="form-group">
              <label>Marque *</label>
              <input value={vehiculeForm.marque} onChange={e => setVehiculeForm({...vehiculeForm, marque: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Modèle *</label>
              <input value={vehiculeForm.modele} onChange={e => setVehiculeForm({...vehiculeForm, modele: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Plaque *</label>
              <input value={vehiculeForm.plaque_immatriculation} onChange={e => setVehiculeForm({...vehiculeForm, plaque_immatriculation: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select value={vehiculeForm.type} onChange={e => setVehiculeForm({...vehiculeForm, type: e.target.value})}>
                <option value="camion">Camion</option>
                <option value="van">Van</option>
                <option value="voiture">Voiture</option>
                <option value="moto">Moto</option>
              </select>
            </div>
            <div className="form-group">
              <label>Capacité charge (kg)</label>
              <input type="number" value={vehiculeForm.capacite_charge} onChange={e => setVehiculeForm({...vehiculeForm, capacite_charge: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Capacité volume (L)</label>
              <input type="number" value={vehiculeForm.capacite_volume} onChange={e => setVehiculeForm({...vehiculeForm, capacite_volume: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={vehiculeForm.statut} onChange={e => setVehiculeForm({...vehiculeForm, statut: e.target.value})}>
                <option value="disponible">Disponible</option>
                <option value="en_mission">En mission</option>
                <option value="en_maintenance">En maintenance</option>
              </select>
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : (editingType === 'vehicule' ? 'Modifier' : 'Créer')}</button>
            </div>
            {editingType === 'vehicule' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('vehicule')} disabled={submitting}>Annuler</button></div>}
          </form>
          <div className="table-container">
            <table className="data-table delivery-table">
              <thead><tr><th>Marque</th><th>Modèle</th><th>Plaque</th><th>Type</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
                {vehicules.map(v => (
                  <tr key={v.id}>
                    <td>{v.marque}</td><td>{v.modele}</td><td>{v.plaque_immatriculation}</td><td>{v.type}</td>
                    <td><StatusBadge status={v.statut} /></td>
                    <td>
                      <span className="delivery-actions">
                        <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEdit(v, 'vehicule')}><i className="ti ti-edit" /></button>
                        <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('vehicule', v.id)}><i className="ti ti-trash" /></button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {vehicules.length === 0 && <div className="delivery-empty"><i className="ti ti-car-off" /><span>Aucun véhicule enregistré.</span></div>}
        </div>
      )}

      {tab === 'itineraires' && (
        <div className="card">
          <div className="delivery-section-head">
            <h3>{editingType === 'itineraire' ? 'Modifier l’itinéraire' : 'Nouvel itinéraire'}</h3>
          </div>
          <form onSubmit={(e) => handleSubmit(e, 'itineraire')} className="form-grid">
            <div className="form-group">
              <label>Nom *</label>
              <input value={itineraireForm.nom} onChange={e => setItineraireForm({...itineraireForm, nom: e.target.value})} required />
            </div>
            <div className="form-group full-width">
              <label>Description</label>
              <textarea value={itineraireForm.description} onChange={e => setItineraireForm({...itineraireForm, description: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Date de départ *</label>
              <input type="datetime-local" value={itineraireForm.date_depart} onChange={e => setItineraireForm({...itineraireForm, date_depart: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Date de retour *</label>
              <input type="datetime-local" value={itineraireForm.date_retour} onChange={e => setItineraireForm({...itineraireForm, date_retour: e.target.value})} required />
            </div>
            <div className="form-group full-width">
              <label>Points intermédiaires (un par ligne)</label>
              <textarea value={itineraireForm.points_intermediaires} onChange={e => setItineraireForm({...itineraireForm, points_intermediaires: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Livreur *</label>
              <select value={itineraireForm.livreur_id} onChange={e => setItineraireForm({...itineraireForm, livreur_id: e.target.value})} required>
                <option value="">Livreur</option>
                {livreurs.map(l => <option key={l.id} value={l.id}>{l.nom_complet}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Véhicule *</label>
              <select value={itineraireForm.vehicule_id} onChange={e => setItineraireForm({...itineraireForm, vehicule_id: e.target.value})} required>
                <option value="">Véhicule</option>
                {vehicules.map(v => <option key={v.id} value={v.id}>{v.marque} {v.modele} - {v.plaque_immatriculation}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={itineraireForm.statut} onChange={e => setItineraireForm({...itineraireForm, statut: e.target.value})}>
                <option value="planifie">Planifié</option>
                <option value="en_cours">En cours</option>
                <option value="termine">Terminé</option>
                <option value="annule">Annulé</option>
              </select>
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : (editingType === 'itineraire' ? 'Modifier' : 'Créer')}</button>
            </div>
            {editingType === 'itineraire' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('itineraire')} disabled={submitting}>Annuler</button></div>}
          </form>
          <div className="table-container">
            <table className="data-table delivery-table">
              <thead><tr><th>Nom</th><th>Date départ</th><th>Date retour</th><th>Livreur</th><th>Véhicule</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
                {itineraires.map(it => (
                  <tr key={it.id}>
                    <td>{it.nom}</td><td>{it.date_depart?.slice(0, 16)}</td><td>{it.date_retour?.slice(0, 16)}</td><td>{it.livreur_nom}</td><td>{it.vehicule_plaque}</td>
                    <td><StatusBadge status={it.statut} /></td>
                    <td>
                      <span className="delivery-actions">
                        <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEdit(it, 'itineraire')}><i className="ti ti-edit" /></button>
                        <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('itineraire', it.id)}><i className="ti ti-trash" /></button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {itineraires.length === 0 && <div className="delivery-empty"><i className="ti ti-route-off" /><span>Aucun itinéraire planifié.</span></div>}
        </div>
      )}

      {tab === 'livraisons' && (
        <div className="card">
          <div className="delivery-section-head">
            <h3>{editingType === 'livraison' ? 'Modifier la livraison' : 'Nouvelle livraison'}</h3>
          </div>
          <form onSubmit={(e) => handleSubmit(e, 'livraison')} className="form-grid">
            <div className="form-group">
              <label>Vente ID</label>
              <input type="number" value={livraisonForm.vente_id} onChange={e => setLivraisonForm({...livraisonForm, vente_id: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Commande client ID</label>
              <input type="number" value={livraisonForm.commande_client_id} onChange={e => setLivraisonForm({...livraisonForm, commande_client_id: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Itinéraire</label>
              <select value={livraisonForm.itineraire_id} onChange={e => setLivraisonForm({...livraisonForm, itineraire_id: e.target.value})}>
                <option value="">Itinéraire</option>
                {itineraires.map(it => <option key={it.id} value={it.id}>{it.nom}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Livreur</label>
              <select value={livraisonForm.livreur_id} onChange={e => setLivraisonForm({...livraisonForm, livreur_id: e.target.value})}>
                <option value="">Livreur</option>
                {livreurs.map(l => <option key={l.id} value={l.id}>{l.nom_complet}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Véhicule</label>
              <select value={livraisonForm.vehicule_id} onChange={e => setLivraisonForm({...livraisonForm, vehicule_id: e.target.value})}>
                <option value="">Véhicule</option>
                {vehicules.map(v => <option key={v.id} value={v.id}>{v.marque} {v.modele}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Destinataire *</label>
              <input value={livraisonForm.nom_destinataire} onChange={e => setLivraisonForm({...livraisonForm, nom_destinataire: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Adresse</label>
              <input value={livraisonForm.adresse_livraison} onChange={e => setLivraisonForm({...livraisonForm, adresse_livraison: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Ville</label>
              <input value={livraisonForm.ville_livraison} onChange={e => setLivraisonForm({...livraisonForm, ville_livraison: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Téléphone</label>
              <input value={livraisonForm.telephone_livraison} onChange={e => setLivraisonForm({...livraisonForm, telephone_livraison: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Date de livraison prévue</label>
              <input type="datetime-local" value={livraisonForm.date_livraison_prevue} onChange={e => setLivraisonForm({...livraisonForm, date_livraison_prevue: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Statut</label>
              <select value={livraisonForm.statut} onChange={e => setLivraisonForm({...livraisonForm, statut: e.target.value})}>
                <option value="en_attente">En attente</option>
                <option value="chargee">Chargée</option>
                <option value="en_route">En route</option>
                <option value="livree">Livrée</option>
                <option value="retournee">Retournée</option>
                <option value="echec">Échec</option>
              </select>
            </div>
            <div className="form-group full-width">
              <label>Notes</label>
              <textarea value={livraisonForm.notes} onChange={e => setLivraisonForm({...livraisonForm, notes: e.target.value})} />
            </div>
            <div className="form-group">
              <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : (editingType === 'livraison' ? 'Modifier' : 'Créer')}</button>
            </div>
            {editingType === 'livraison' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('livraison')} disabled={submitting}>Annuler</button></div>}
          </form>
          <div className="table-container">
            <table className="data-table delivery-table">
              <thead><tr><th>Destinataire</th><th>Adresse</th><th>Statut</th><th>Date prévue</th><th>Actions</th></tr></thead>
              <tbody>
                {livraisons.map(l => (
                  <tr key={l.id}>
                    <td>{l.nom_destinataire}</td><td>{l.adresse_livraison}</td>
                    <td><StatusBadge status={l.statut} /></td>
                    <td>{l.date_livraison_prevue?.slice(0, 16)}</td>
                    <td>
                      <span className="delivery-actions">
                        <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEdit(l, 'livraison')}><i className="ti ti-edit" /></button>
                        <button className="btn-small btn-view" title="Suivis" onClick={() => viewSuivis(l.id)}><i className="ti ti-map-pin" /></button>
                        {(l.statut === 'en_attente' || l.statut === 'chargee' || l.statut === 'en_route') && (
                          <button className="btn-small btn-primary" title="Avancer statut" onClick={() => handleAvancer(l.id)}><i className="ti ti-arrow-forward" /></button>
                        )}
                        <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('livraison', l.id)}><i className="ti ti-trash" /></button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {livraisons.length === 0 && <div className="delivery-empty"><i className="ti ti-package-export" /><span>Aucune livraison enregistrée.</span></div>}
        </div>
      )}

      {tab === 'suivis' && (
        <div className="card">
          <div className="delivery-section-head">
            <h3>Suivis de livraison</h3>
          </div>
          {Object.keys(suivis).length === 0 && (
            <div className="delivery-empty">
              <i className="ti ti-map-pin-off" />
              <span>Aucun suivi sélectionné. Cliquez sur « Suivis » sur une livraison pour commencer le suivi.</span>
            </div>
          )}
          <div className="delivery-track-list">
            {Object.keys(suivis).map(livraisonId => {
              const livraison = livraisons.find(l => String(l.id) === String(livraisonId));
              const events = suivis[livraisonId] || [];
              return (
                <div className="delivery-track" key={livraisonId}>
                  <div className="delivery-track__head">
                    <div>
                      <p className="delivery-track__title">Livraison #{livraisonId}</p>
                      <p className="delivery-track__sub">{livraison ? livraison.nom_destinataire : '—'}</p>
                    </div>
                    {livraison && <StatusBadge status={livraison.statut} />}
                  </div>
                  <div className="delivery-track__body">
                    {events.length === 0 ? (
                      <p className="text-muted">Aucun événement de suivi pour l'instant.</p>
                    ) : (
                      <div className="delivery-timeline">
                        {events.map(s => (
                          <div className="delivery-event" key={s.id}>
                            <span className={`delivery-event__dot tone-${STATUS_TONES[s.statut] || 'neutral'}`} />
                            <p className="delivery-event__status">{STATUS_LABELS[s.statut] || s.statut}</p>
                            <p className="delivery-event__meta">{s.date_mise_a_jour?.slice(0, 16)}</p>
                            {s.commentaire && <p className="delivery-event__comment">{s.commentaire}</p>}
                            {(s.localisation_lat || s.localisation_lng) && (
                              <p className="delivery-event__loc"><i className="ti ti-map-pin" />{s.localisation_lat}, {s.localisation_lng}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <form className="delivery-track__add" onSubmit={(e) => submitSuivi(e, Number(livraisonId))}>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Statut</label>
                        <select value={suiviForm.statut} onChange={e => setSuiviForm({...suiviForm, statut: e.target.value})} required>
                          <option value="">Statut</option>
                          <option value="en_attente">En attente</option>
                          <option value="chargee">Chargée</option>
                          <option value="en_route">En route</option>
                          <option value="livree">Livrée</option>
                          <option value="retournee">Retournée</option>
                          <option value="echec">Échec</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Latitude</label>
                        <input value={suiviForm.localisation_lat} onChange={e => setSuiviForm({...suiviForm, localisation_lat: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label>Longitude</label>
                        <input value={suiviForm.localisation_lng} onChange={e => setSuiviForm({...suiviForm, localisation_lng: e.target.value})} />
                      </div>
                      <div className="form-group full-width">
                        <label>Commentaire</label>
                        <input value={suiviForm.commentaire} onChange={e => setSuiviForm({...suiviForm, commentaire: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <button type="submit" className="btn-small btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : <><i className="ti ti-plus" /> Ajouter</>}</button>
                      </div>
                    </div>
                  </form>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
