// src/pages/HR.jsx
import { useState, useEffect, useMemo } from 'react';
import { toast } from 'react-toastify';
import { employeService, presenceService, salaireService, primeService } from '../services/api';
import './Pages.css';
import './HR.css';

const EMPLOYE_STATUTS = {
  actif: { label: 'Actif', class: 'success' },
  inactif: { label: 'Inactif', class: 'danger' },
  en_conges: { label: 'En congés', class: 'warning' },
  depart: { label: 'Départ', class: 'info' },
};

const PRESENCE_STATUTS = {
  present: { label: 'Présent', class: 'success' },
  absent: { label: 'Absent', class: 'danger' },
  en_retard: { label: 'En retard', class: 'warning' },
  conge: { label: 'Congé', class: 'info' },
  maladie: { label: 'Maladie', class: 'warning' },
};

const PAIEMENT_STATUTS = {
  paye: { label: 'Payé', class: 'success' },
  en_attente: { label: 'En attente', class: 'warning' },
  partiel: { label: 'Partiel', class: 'info' },
  impaye: { label: 'Impayé', class: 'danger' },
};

const MODES_PAIEMENT = {
  virement: 'Virement',
  especes: 'Espèces',
  cheque: 'Chèque',
};

const TYPES_PRIME = {
  performance: 'Performance',
  anciennete: 'Ancienneté',
  objectif: 'Objectif',
  exceptionnel: 'Exceptionnel',
};

const TABS = [
  { key: 'employes', label: 'Employés', icon: 'ti-users' },
  { key: 'presences', label: 'Présences', icon: 'ti-clock' },
  { key: 'salaires', label: 'Salaires', icon: 'ti-cash' },
  { key: 'primes', label: 'Primes', icon: 'ti-trophy' },
];

const fmtMoney = (v) => `${(Number(v) || 0).toLocaleString('mg-MG')} Ar`;
const fmtTime = (v) => (v ? String(v).slice(11, 16) : '—');
const fmtDate = (v) => (v ? String(v).slice(0, 10) : '—');
const empName = (e) => e?.nom_complet || `${e?.prenom ? e.prenom + ' ' : ''}${e?.nom || ''}`.trim() || `#${e?.id}`;
const initials = (e) => {
  const n = (e?.prenom?.[0] || '') + (e?.nom?.[0] || '');
  return n.toUpperCase() || '?';
};

const emptyForms = {
  employe: { matricule: '', nom: '', prenom: '', date_naissance: '', lieu_naissance: '', sexe: 'M', adresse: '', telephone: '', email: '', poste: '', departement: '', date_embauche: '', date_fin_contrat: '', type_contrat: 'cdi', salaire_base: '', banque_nom: '', banque_iban: '', banque_bic: '', statut: 'actif' },
  presence: { employe_id: '', date: '', heure_arrivee: '', heure_depart: '', heure_pause_debut: '', heure_pause_fin: '', statut: 'present', remarque: '' },
  salaire: { employe_id: '', mois: '', annee: '', salaire_base: '', primes: '', indemnites: '', deductions: '', avances: '', mode_paiement: 'virement', reference_paiement: '', notes: '', statut_paiement: 'en_attente' },
  prime: { employe_id: '', type_prime: 'performance', montant: '', date_octroi: '', motif: '' },
};

const services = {
  employe: employeService,
  presence: presenceService,
  salaire: salaireService,
  prime: primeService,
};

export default function HR() {
  const [tab, setTab] = useState('employes');
  const [employes, setEmployes] = useState([]);
  const [presences, setPresences] = useState([]);
  const [salaires, setSalaires] = useState([]);
  const [primes, setPrimes] = useState([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState('');
  const [modalType, setModalType] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [forms, setForms] = useState(emptyForms);

  const empMap = useMemo(() => Object.fromEntries(employes.map((e) => [e.id, e])), [employes]);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [e, p, s, pr] = await Promise.all([
        employeService.getAll(),
        presenceService.getAll(),
        salaireService.getAll(),
        primeService.getAll(),
      ]);
      setEmployes(e.data.employes || []);
      setPresences(p.data.presences || []);
      setSalaires(s.data.salaires || []);
      setPrimes(pr.data.primes || []);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur de chargement des données RH');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const tabCounts = {
    employes: employes.length,
    presences: presences.length,
    salaires: salaires.length,
    primes: primes.length,
  };

  const summary = useMemo(() => {
    const actifs = employes.filter((e) => e.statut === 'actif').length;
    const masseSalariale = salaires.reduce((sum, s) => sum + (Number(s.salaire_net) || 0), 0);
    const totalPrimes = primes.reduce((sum, p) => sum + (Number(p.montant) || 0), 0);
    const presencesMois = presences.filter((p) => p.date && p.date.slice(0, 7) === new Date().toISOString().slice(0, 7)).length;
    return { total: employes.length, actifs, masseSalariale, totalPrimes, presencesMois };
  }, [employes, salaires, primes, presences]);

  const openModal = (type, item = null) => {
    if (item) {
      const filled = { ...emptyForms[type] };
      Object.keys(filled).forEach((k) => {
        const val = item[k];
        if (k === 'employe_id') filled[k] = item.employe_id ?? '';
        else if (val === undefined || val === null) filled[k] = '';
        else if (['date_naissance', 'date_embauche', 'date_fin_contrat', 'date_octroi', 'date'].includes(k)) filled[k] = String(val).slice(0, 10);
        else if (['heure_arrivee', 'heure_depart', 'heure_pause_debut', 'heure_pause_fin'].includes(k)) filled[k] = String(val).slice(0, 16);
        else filled[k] = val;
      });
      setForms((f) => ({ ...f, [type]: filled }));
      setEditingItem(item);
    } else {
      setForms((f) => ({ ...f, [type]: { ...emptyForms[type] } }));
      setEditingItem(null);
    }
    setModalType(type);
  };

  const closeModal = () => {
    setModalType(null);
    setEditingItem(null);
  };

  const handleChange = (type) => (e) => {
    const { name, value } = e.target;
    setForms((f) => ({ ...f, [type]: { ...f[type], [name]: value } }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const type = modalType;
    const svc = services[type];
    const raw = forms[type];
    let data = { ...raw };
    const numFields = {
      employe: ['salaire_base'],
      presence: ['employe_id'],
      salaire: ['employe_id', 'mois', 'annee', 'salaire_base', 'primes', 'indemnites', 'deductions', 'avances'],
      prime: ['employe_id', 'montant'],
    }[type];
    numFields.forEach((k) => { data[k] = Number(data[k]) || 0; });
    const dateFields = ['date_naissance', 'date_embauche', 'date_fin_contrat', 'date_octroi', 'date'];
    dateFields.forEach((k) => { if (data[k] === '') data[k] = null; });

    try {
      if (editingItem) {
        await svc.update(editingItem.id, data);
        toast.success('Élément mis à jour');
      } else {
        await svc.create(data);
        toast.success('Élément créé');
      }
      closeModal();
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur de sauvegarde');
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm('Supprimer cet élément ? Cette action est irréversible.')) return;
    try {
      await services[type].delete(id);
      toast.success('Élément supprimé');
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur de suppression');
    }
  };

  const filtered = {
    employes: employes.filter((e) =>
      !search ||
      empName(e).toLowerCase().includes(search.toLowerCase()) ||
      (e.matricule || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.poste || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.departement || '').toLowerCase().includes(search.toLowerCase())
    ),
    presences: presences.filter((p) =>
      !search ||
      (empMap[p.employe_id] ? empName(empMap[p.employe_id]) : p.employe_nom || '').toLowerCase().includes(search.toLowerCase())
    ),
    salaires: salaires.filter((s) =>
      !search ||
      (empMap[s.employe_id] ? empName(empMap[s.employe_id]) : s.employe_nom || '').toLowerCase().includes(search.toLowerCase())
    ),
    primes: primes.filter((p) =>
      !search ||
      (empMap[p.employe_id] ? empName(empMap[p.employe_id]) : p.employe_nom || '').toLowerCase().includes(search.toLowerCase())
    ),
  };

  const renderBadge = (map, value) => {
    const b = map[value] || { label: value, class: 'info' };
    return <span className={`badge ${b.class}`}>{b.label}</span>;
  };

  const employeOptions = (selected) => (
    <select name="employe_id" value={forms[modalType].employe_id} onChange={handleChange(modalType)} required>
      <option value="">Sélectionner un employé</option>
      {employes.map((e) => (
        <option key={e.id} value={e.id}>{empName(e)}</option>
      ))}
    </select>
  );

  if (loading && employes.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des ressources humaines...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Ressources Humaines</h1>
          <p>Gestion des employés, présences, salaires et primes</p>
        </div>
      </div>

      <div className="stats-grid mini">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--erp-onyx)' }}><i className="ti ti-users" aria-hidden="true" /></div>
          <div className="stat-content">
            <span className="stat-value">{summary.total}</span>
            <span className="stat-label">Employés ({summary.actifs} actifs)</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--erp-gold-dark)' }}><i className="ti ti-clock" aria-hidden="true" /></div>
          <div className="stat-content">
            <span className="stat-value">{summary.presencesMois}</span>
            <span className="stat-label">Présences ce mois</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--erp-success)' }}><i className="ti ti-cash" aria-hidden="true" /></div>
          <div className="stat-content">
            <span className="stat-value">{fmtMoney(summary.masseSalariale)}</span>
            <span className="stat-label">Masse salariale</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--erp-critical)' }}><i className="ti ti-trophy" aria-hidden="true" /></div>
          <div className="stat-content">
            <span className="stat-value">{fmtMoney(summary.totalPrimes)}</span>
            <span className="stat-label">Total primes</span>
          </div>
        </div>
      </div>

      <div className="hr-tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`hr-tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => { setTab(t.key); setSearch(''); }}
          >
            <span className="hr-tab-icon"><i className={`ti ${t.icon}`} aria-hidden="true" /></span>
            <span className="hr-tab-label">{t.label}</span>
            <span className="hr-tab-count">{tabCounts[t.key]}</span>
          </button>
        ))}
      </div>

      <div className="card filter-card">
        <div className="filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder={`Rechercher un${tab === 'employes' ? 'e employé' : `e ${TABS.find((t) => t.key === tab).label.toLowerCase().slice(0, -1)}`}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
        </div>
      </div>

      {/* ============ EMPLOYÉS ============ */}
      {tab === 'employes' && (
        <>
          <div className="hr-section-head">
            <div>
              <h2>Liste des employés</h2>
              <p>Fiches employés, contrats et coordonnées bancaires</p>
            </div>
            <div className="hr-section-actions">
              <button className="btn-primary" onClick={() => openModal('employe')}>+ Nouvel employé</button>
            </div>
          </div>

          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Matricule</th>
                    <th>Nom</th>
                    <th>Poste</th>
                    <th>Département</th>
                    <th>Salaire de base</th>
                    <th>Statut</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.employes.length === 0 ? (
                    <tr><td colSpan="7" className="text-center">Aucun employé trouvé</td></tr>
                  ) : (
                    filtered.employes.map((e) => (
                      <tr key={e.id}>
                        <td>{e.matricule || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div className="hr-avatar" style={{ width: 32, height: 32, fontSize: 12 }}>{initials(e)}</div>
                            <div>
                              <div>{empName(e)}</div>
                              <div className="hr-table-meta">{e.email || e.telephone || ''}</div>
                            </div>
                          </div>
                        </td>
                        <td>{e.poste || '—'}</td>
                        <td>{e.departement || '—'}</td>
                        <td className="hr-money">{fmtMoney(e.salaire_base)}</td>
                        <td>{renderBadge(EMPLOYE_STATUTS, e.statut)}</td>
                        <td>
                          <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal('employe', e)}><i className="ti ti-edit" aria-hidden="true" /></button>
                          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('employe', e.id)}><i className="ti ti-trash" aria-hidden="true" /></button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ============ PRÉSENCES ============ */}
      {tab === 'presences' && (
        <>
          <div className="hr-section-head">
            <div>
              <h2>Suivi des présences</h2>
              <p>Pointage, retards et absences</p>
            </div>
            <div className="hr-section-actions">
              <button className="btn-primary" onClick={() => openModal('presence')}>+ Nouvelle présence</button>
            </div>
          </div>

          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Employé</th>
                    <th>Date</th>
                    <th>Arrivée</th>
                    <th>Départ</th>
                    <th>Statut</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.presences.length === 0 ? (
                    <tr><td colSpan="6" className="text-center">Aucune présence trouvée</td></tr>
                  ) : (
                    filtered.presences.map((p) => (
                      <tr key={p.id}>
                        <td>{empMap[p.employe_id] ? empName(empMap[p.employe_id]) : (p.employe_nom || '—')}</td>
                        <td>{fmtDate(p.date)}</td>
                        <td>{fmtTime(p.heure_arrivee)}</td>
                        <td>{fmtTime(p.heure_depart)}</td>
                        <td>{renderBadge(PRESENCE_STATUTS, p.statut)}</td>
                        <td>
                          <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal('presence', p)}><i className="ti ti-edit" aria-hidden="true" /></button>
                          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('presence', p.id)}><i className="ti ti-trash" aria-hidden="true" /></button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ============ SALAIRES ============ */}
      {tab === 'salaires' && (
        <>
          <div className="hr-section-head">
            <div>
              <h2>Bulletins de salaire</h2>
              <p>Rémunération, primes, déductions et paiements</p>
            </div>
            <div className="hr-section-actions">
              <button className="btn-primary" onClick={() => openModal('salaire')}>+ Nouveau salaire</button>
            </div>
          </div>

          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Employé</th>
                    <th>Période</th>
                    <th>Base</th>
                    <th>Primes</th>
                    <th>Déductions</th>
                    <th>Net</th>
                    <th>Paiement</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.salaires.length === 0 ? (
                    <tr><td colSpan="8" className="text-center">Aucun salaire trouvé</td></tr>
                  ) : (
                    filtered.salaires.map((s) => (
                      <tr key={s.id}>
                        <td>{empMap[s.employe_id] ? empName(empMap[s.employe_id]) : (s.employe_nom || '—')}</td>
                        <td>{s.mois}/{s.annee}</td>
                        <td className="hr-money">{fmtMoney(s.salaire_base)}</td>
                        <td className="hr-money">{fmtMoney(s.primes)}</td>
                        <td className="hr-money">{fmtMoney(s.deductions)}</td>
                        <td className="hr-money">{fmtMoney(s.salaire_net)}</td>
                        <td>{renderBadge(PAIEMENT_STATUTS, s.statut_paiement)}</td>
                        <td>
                          <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal('salaire', s)}><i className="ti ti-edit" aria-hidden="true" /></button>
                          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('salaire', s.id)}><i className="ti ti-trash" aria-hidden="true" /></button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ============ PRIMES ============ */}
      {tab === 'primes' && (
        <>
          <div className="hr-section-head">
            <div>
              <h2>Primes et avantages</h2>
              <p>Attribution de primes par type et motif</p>
            </div>
            <div className="hr-section-actions">
              <button className="btn-primary" onClick={() => openModal('prime')}>+ Nouvelle prime</button>
            </div>
          </div>

          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Employé</th>
                    <th>Type</th>
                    <th>Montant</th>
                    <th>Date d'octroi</th>
                    <th>Motif</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.primes.length === 0 ? (
                    <tr><td colSpan="6" className="text-center">Aucune prime trouvée</td></tr>
                  ) : (
                    filtered.primes.map((p) => (
                      <tr key={p.id}>
                        <td>{empMap[p.employe_id] ? empName(empMap[p.employe_id]) : (p.employe_nom || '—')}</td>
                        <td>{TYPES_PRIME[p.type_prime] || p.type_prime}</td>
                        <td className="hr-money">{fmtMoney(p.montant)}</td>
                        <td>{fmtDate(p.date_octroi)}</td>
                        <td>{p.motif || '—'}</td>
                        <td>
                          <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal('prime', p)}><i className="ti ti-edit" aria-hidden="true" /></button>
                          <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('prime', p.id)}><i className="ti ti-trash" aria-hidden="true" /></button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ============ MODAL ============ */}
      {modalType && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {editingItem ? 'Modifier' : 'Nouveau'}
                {' '}
                {TABS.find((t) => t.key === modalType)?.label.toLowerCase().replace(/s$/, '')}
              </h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              {modalType === 'employe' && (
                <>
                  <div className="hr-form-section">
                    <div className="hr-form-section-header">
                      <span className="hr-form-section-icon"><i className="ti ti-user" aria-hidden="true" /></span>
                      <span className="hr-form-section-title">Informations personnelles</span>
                    </div>
                    <div className="form-grid">
                      <div className="form-group"><label>Matricule <span className="hr-required">*</span></label><input name="matricule" value={forms.employe.matricule} onChange={handleChange('employe')} required placeholder="EMP-001" /></div>
                      <div className="form-group"><label>Nom <span className="hr-required">*</span></label><input name="nom" value={forms.employe.nom} onChange={handleChange('employe')} required placeholder="Nom" /></div>
                      <div className="form-group"><label>Prénom</label><input name="prenom" value={forms.employe.prenom} onChange={handleChange('employe')} placeholder="Prénom" /></div>
                      <div className="form-group"><label>Sexe</label><select name="sexe" value={forms.employe.sexe} onChange={handleChange('employe')}><option value="M">M</option><option value="F">F</option></select></div>
                      <div className="form-group"><label>Date de naissance</label><input type="date" name="date_naissance" value={forms.employe.date_naissance} onChange={handleChange('employe')} /></div>
                      <div className="form-group"><label>Lieu de naissance</label><input name="lieu_naissance" value={forms.employe.lieu_naissance} onChange={handleChange('employe')} placeholder="Ville" /></div>
                      <div className="form-group full-width"><label>Adresse</label><input name="adresse" value={forms.employe.adresse} onChange={handleChange('employe')} placeholder="Adresse" /></div>
                      <div className="form-group"><label>Email</label><input type="email" name="email" value={forms.employe.email} onChange={handleChange('employe')} placeholder="email@exemple.com" /></div>
                      <div className="form-group"><label>Téléphone</label><input name="telephone" value={forms.employe.telephone} onChange={handleChange('employe')} placeholder="0600000000" /></div>
                    </div>
                  </div>

                  <div className="hr-form-section">
                    <div className="hr-form-section-header">
                      <span className="hr-form-section-icon"><i className="ti ti-file-text" aria-hidden="true" /></span>
                      <span className="hr-form-section-title">Contrat</span>
                    </div>
                    <div className="form-grid">
                      <div className="form-group"><label>Poste</label><input name="poste" value={forms.employe.poste} onChange={handleChange('employe')} placeholder="Poste" /></div>
                      <div className="form-group"><label>Département</label><input name="departement" value={forms.employe.departement} onChange={handleChange('employe')} placeholder="Département" /></div>
                      <div className="form-group"><label>Type de contrat</label><select name="type_contrat" value={forms.employe.type_contrat} onChange={handleChange('employe')}><option value="cdi">CDI</option><option value="cdd">CDD</option><option value="stage">Stage</option><option value="freelance">Freelance</option></select></div>
                      <div className="form-group"><label>Statut</label><select name="statut" value={forms.employe.statut} onChange={handleChange('employe')}><option value="actif">Actif</option><option value="inactif">Inactif</option><option value="en_conges">En congés</option><option value="depart">Départ</option></select></div>
                      <div className="form-group"><label>Date d'embauche</label><input type="date" name="date_embauche" value={forms.employe.date_embauche} onChange={handleChange('employe')} /></div>
                      <div className="form-group"><label>Fin de contrat</label><input type="date" name="date_fin_contrat" value={forms.employe.date_fin_contrat} onChange={handleChange('employe')} /></div>
                    </div>
                  </div>

                  <div className="hr-form-section">
                    <div className="hr-form-section-header">
                      <span className="hr-form-section-icon"><i className="ti ti-cash" aria-hidden="true" /></span>
                      <span className="hr-form-section-title">Rémunération & banque</span>
                    </div>
                    <div className="form-grid">
                      <div className="form-group"><label>Salaire de base</label><input type="number" name="salaire_base" value={forms.employe.salaire_base} onChange={handleChange('employe')} placeholder="0" /></div>
                      <div className="form-group"><label>Banque</label><input name="banque_nom" value={forms.employe.banque_nom} onChange={handleChange('employe')} placeholder="Nom banque" /></div>
                      <div className="form-group"><label>IBAN</label><input name="banque_iban" value={forms.employe.banque_iban} onChange={handleChange('employe')} placeholder="IBAN" /></div>
                      <div className="form-group"><label>BIC</label><input name="banque_bic" value={forms.employe.banque_bic} onChange={handleChange('employe')} placeholder="BIC" /></div>
                    </div>
                  </div>
                </>
              )}

              {modalType === 'presence' && (
                <div className="hr-form-section">
                  <div className="hr-form-section-header">
                    <span className="hr-form-section-icon"><i className="ti ti-clock" aria-hidden="true" /></span>
                    <span className="hr-form-section-title">Nouvelle présence</span>
                  </div>
                  <div className="form-grid">
                    <div className="form-group"><label>Employé <span className="hr-required">*</span></label>{employeOptions()}</div>
                    <div className="form-group"><label>Date <span className="hr-required">*</span></label><input type="date" name="date" value={forms.presence.date} onChange={handleChange('presence')} required /></div>
                    <div className="form-group"><label>Heure d'arrivée</label><input type="time" name="heure_arrivee" value={forms.presence.heure_arrivee} onChange={handleChange('presence')} /></div>
                    <div className="form-group"><label>Heure de départ</label><input type="time" name="heure_depart" value={forms.presence.heure_depart} onChange={handleChange('presence')} /></div>
                    <div className="form-group"><label>Début pause</label><input type="time" name="heure_pause_debut" value={forms.presence.heure_pause_debut} onChange={handleChange('presence')} /></div>
                    <div className="form-group"><label>Fin pause</label><input type="time" name="heure_pause_fin" value={forms.presence.heure_pause_fin} onChange={handleChange('presence')} /></div>
                    <div className="form-group"><label>Statut</label><select name="statut" value={forms.presence.statut} onChange={handleChange('presence')}><option value="present">Présent</option><option value="absent">Absent</option><option value="en_retard">En retard</option><option value="conge">Congé</option><option value="maladie">Maladie</option></select></div>
                    <div className="form-group full-width"><label>Remarque</label><input name="remarque" value={forms.presence.remarque} onChange={handleChange('presence')} placeholder="Remarque" /></div>
                  </div>
                </div>
              )}

              {modalType === 'salaire' && (
                <div className="hr-form-section">
                  <div className="hr-form-section-header">
                      <span className="hr-form-section-icon"><i className="ti ti-cash" aria-hidden="true" /></span>
                    <span className="hr-form-section-title">Nouveau bulletin de salaire</span>
                  </div>
                  <div className="form-grid">
                    <div className="form-group"><label>Employé <span className="hr-required">*</span></label>{employeOptions()}</div>
                    <div className="form-group"><label>Mois <span className="hr-required">*</span></label><input type="number" min="1" max="12" name="mois" value={forms.salaire.mois} onChange={handleChange('salaire')} required placeholder="1-12" /></div>
                    <div className="form-group"><label>Année <span className="hr-required">*</span></label><input type="number" name="annee" value={forms.salaire.annee} onChange={handleChange('salaire')} required placeholder="2026" /></div>
                    <div className="form-group"><label>Salaire de base</label><input type="number" name="salaire_base" value={forms.salaire.salaire_base} onChange={handleChange('salaire')} placeholder="0" /></div>
                    <div className="form-group"><label>Primes</label><input type="number" name="primes" value={forms.salaire.primes} onChange={handleChange('salaire')} placeholder="0" /></div>
                    <div className="form-group"><label>Indemnités</label><input type="number" name="indemnites" value={forms.salaire.indemnites} onChange={handleChange('salaire')} placeholder="0" /></div>
                    <div className="form-group"><label>Déductions</label><input type="number" name="deductions" value={forms.salaire.deductions} onChange={handleChange('salaire')} placeholder="0" /></div>
                    <div className="form-group"><label>Avances</label><input type="number" name="avances" value={forms.salaire.avances} onChange={handleChange('salaire')} placeholder="0" /></div>
                    <div className="form-group"><label>Mode de paiement</label><select name="mode_paiement" value={forms.salaire.mode_paiement} onChange={handleChange('salaire')}><option value="virement">Virement</option><option value="especes">Espèces</option><option value="cheque">Chèque</option></select></div>
                    <div className="form-group"><label>Statut paiement</label><select name="statut_paiement" value={forms.salaire.statut_paiement} onChange={handleChange('salaire')}><option value="en_attente">En attente</option><option value="paye">Payé</option><option value="partiel">Partiel</option><option value="impaye">Impayé</option></select></div>
                    <div className="form-group"><label>Référence paiement</label><input name="reference_paiement" value={forms.salaire.reference_paiement} onChange={handleChange('salaire')} placeholder="Référence" /></div>
                    <div className="form-group full-width"><label>Notes</label><textarea name="notes" value={forms.salaire.notes} onChange={handleChange('salaire')} placeholder="Notes" /></div>
                  </div>
                </div>
              )}

              {modalType === 'prime' && (
                <div className="hr-form-section">
                  <div className="hr-form-section-header">
                      <span className="hr-form-section-icon"><i className="ti ti-trophy" aria-hidden="true" /></span>
                    <span className="hr-form-section-title">Nouvelle prime</span>
                  </div>
                  <div className="form-grid">
                    <div className="form-group"><label>Employé <span className="hr-required">*</span></label>{employeOptions()}</div>
                    <div className="form-group"><label>Type de prime</label><select name="type_prime" value={forms.prime.type_prime} onChange={handleChange('prime')}><option value="performance">Performance</option><option value="anciennete">Ancienneté</option><option value="objectif">Objectif</option><option value="exceptionnel">Exceptionnel</option></select></div>
                    <div className="form-group"><label>Montant <span className="hr-required">*</span></label><input type="number" name="montant" value={forms.prime.montant} onChange={handleChange('prime')} required placeholder="0" /></div>
                    <div className="form-group"><label>Date d'octroi <span className="hr-required">*</span></label><input type="date" name="date_octroi" value={forms.prime.date_octroi} onChange={handleChange('prime')} required /></div>
                    <div className="form-group full-width"><label>Motif</label><input name="motif" value={forms.prime.motif} onChange={handleChange('prime')} placeholder="Motif de la prime" /></div>
                  </div>
                </div>
              )}

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal}>Annuler</button>
                <button type="submit" className="btn-primary">{editingItem ? 'Mettre à jour' : 'Créer'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
