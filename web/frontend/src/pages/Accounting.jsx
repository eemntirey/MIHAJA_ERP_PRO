import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { compteService, ecritureService, tresorerieService } from '../services/api';
import './Pages.css';

export default function Accounting() {
    const [tab, setTab] = useState('ecritures');
    const [comptes, setComptes] = useState([]);
    const [ecritures, setEcritures] = useState([]);
    const [tresoreries, setTresoreries] = useState([]);
    const [solde, setSolde] = useState(null);
    const [loading, setLoading] = useState(false);
    const [importing, setImporting] = useState(false);
    const [importResult, setImportResult] = useState(null);

    const [compteForm, setCompteForm] = useState({ numero: '', nom: '', type_compte: 'actif', sous_compte_id: '' });
    const [ecritureForm, setEcritureForm] = useState({ date: '', compte_id: '', montant_debit: '', montant_credit: '', libelle: '', reference_externe: '', entite_type: '', entite_id: '', piece_joint: '' });
    const [tresForm, setTresForm] = useState({ date: '', type_operation: 'entree', montant: '', mode_paiement: 'espece', libelle: '', compte_bancaire: '', reference: '' });

    const [editingId, setEditingId] = useState(null);
    const [editingType, setEditingType] = useState(null);
    const [importFile, setImportFile] = useState(null);
    const [importPreview, setImportPreview] = useState([]);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [c, e, t] = await Promise.all([compteService.getAll(), ecritureService.getAll(), tresorerieService.getAll()]);
            setComptes(c.data.comptes || []);
            setEcritures(e.data.ecritures || []);
            setTresoreries(t.data.tresoreries || []);
        } catch (err) { toast.error('Erreur chargement'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    const fetchSolde = async () => {
        try { const res = await tresorerieService.getSolde(); setSolde(res.data.solde); }
        catch (e) { toast.error('Erreur solde'); }
    };

    const handleSubmit = async (e, type) => {
        e.preventDefault();
        try {
            let data;
            if (type === 'compte') data = { ...compteForm, sous_compte_id: compteForm.sous_compte_id ? Number(compteForm.sous_compte_id) : null };
            else if (type === 'ecriture') data = { ...ecritureForm, compte_id: Number(ecritureForm.compte_id), montant_debit: Number(ecritureForm.montant_debit) || 0, montant_credit: Number(ecritureForm.montant_credit) || 0, entite_id: ecritureForm.entite_id ? Number(ecritureForm.entite_id) : null };
            else if (type === 'tresorerie') data = { ...tresForm, montant: Number(tresForm.montant), type_operation: tresForm.type_operation, date: tresForm.date || new Date().toISOString().slice(0, 10) };
            const svc = type === 'compte' ? compteService : type === 'ecriture' ? ecritureService : tresorerieService;
            if (editingType === type && editingId) { await svc.update(editingId, data); toast.success('Modifié'); }
            else { await svc.create(data); toast.success('Créé'); }
            resetForm(type); fetchAll();
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
    };

    const handleDelete = async (type, id) => {
        if (!window.confirm('Supprimer ?')) return;
        const svc = type === 'compte' ? compteService : type === 'ecriture' ? ecritureService : tresorerieService;
        try {
            await svc.delete(id);
            toast.success('Supprimé');
            fetchAll();
        } catch (e) {
            toast.error(e.response?.data?.message || 'Erreur suppression');
        }
    };

    const handleEdit = (item, type) => {
        setEditingId(item.id); setEditingType(type);
        if (type === 'compte') setCompteForm({ numero: item.numero || '', nom: item.nom || '', type_compte: item.type_compte || 'actif', sous_compte_id: item.sous_compte_id || '' });
        else if (type === 'ecriture') setEcritureForm({ date: item.date ? item.date.slice(0, 10) : '', compte_id: item.compte_id || '', montant_debit: item.montant_debit || '', montant_credit: item.montant_credit || '', libelle: item.libelle || '', reference_externe: item.reference_externe || '', entite_type: item.entite_type || '', entite_id: item.entite_id || '', piece_joint: item.piece_joint || '' });
        else if (type === 'tresorerie') setTresForm({ date: item.date ? item.date.slice(0, 10) : '', type_operation: item.type_operation || 'entree', montant: item.montant || '', mode_paiement: item.mode_paiement || 'espece', libelle: item.libelle || '', compte_bancaire: item.compte_bancaire || '', reference: item.reference || '' });
        setTab(type === 'compte' ? 'comptes' : type === 'ecriture' ? 'ecritures' : 'tresorerie');
    };

    const resetForm = (type) => {
        setEditingId(null); setEditingType(null);
        if (type === 'compte') setCompteForm({ numero: '', nom: '', type_compte: 'actif', sous_compte_id: '' });
        else if (type === 'ecriture') setEcritureForm({ date: '', compte_id: '', montant_debit: '', montant_credit: '', libelle: '', reference_externe: '', entite_type: '', entite_id: '', piece_joint: '' });
        else if (type === 'tresorerie') setTresForm({ date: '', type_operation: 'entree', montant: '', mode_paiement: 'espece', libelle: '', compte_bancaire: '', reference: '' });
    };

    const handleImportFile = (e) => {
        const file = e.target.files[0];
        setImportFile(file);
        setImportResult(null);
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const text = ev.target.result;
                const lines = text.split('\n').filter(l => l.trim()).slice(0, 6);
                setImportPreview(lines);
            } catch (err) { setImportPreview([]); }
        };
        if (file.name.toLowerCase().endsWith('.csv')) {
            reader.readAsText(file);
        } else {
            setImportPreview(['(fichier Excel - aperçu non disponible)']);
        }
    };

    const handleImport = async (type) => {
        if (!importFile) { toast.error('Sélectionnez un fichier'); return; }
        setImporting(true); setImportResult(null);
        try {
            const svc = type === 'compte' ? compteService : type === 'ecriture' ? ecritureService : tresorerieService;
            const res = await svc.import(importFile);
            setImportResult(res.data);
            toast.success(res.data.message || 'Import terminé');
            fetchAll();
        } catch (e) {
            const msg = e.response?.data?.message || 'Erreur import';
            toast.error(msg);
            setImportResult({ message: msg, errors: [msg] });
        } finally { setImporting(false); }
    };

    const handleValider = async (id) => {
        await ecritureService.valider(id); toast.success('Écriture validée'); fetchAll();
    };
    const handleAnnuler = async (id) => {
        await ecritureService.annuler(id); toast.success('Écriture annulée'); fetchAll();
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <h1>Comptabilité</h1>
                <div className="tabs">
                    {['comptes', 'ecritures', 'tresorerie'].map(t => (
                        <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => { setTab(t); setEditingId(null); setImportFile(null); setImportResult(null); }}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
                    ))}
                </div>
                {tab === 'tresorerie' && <button className="btn-primary" onClick={fetchSolde}>Voir solde</button>}
            </div>

            {solde !== null && <div className="stats-row"><div className="stat-card"><h3>Solde trésorerie</h3><p className="stat-value">{solde.toFixed(2)} MGA</p></div></div>}

            {importResult && (
                <div className="card" style={{marginBottom: 16}}>
                    <h3>Résultat import</h3>
                    <p>{importResult.message}</p>
                    {importResult.errors && importResult.errors.length > 0 && (
                        <ul style={{color: 'red', fontSize: 13}}>
                            {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                        </ul>
                    )}
                </div>
            )}

            {tab === 'comptes' && (
                <div className="card">
                    <h3>{editingType === 'compte' ? 'Modifier' : 'Nouveau'} compte comptable</h3>
                    <form onSubmit={(e) => handleSubmit(e, 'compte')} className="form-grid">
                        <div className="form-group">
                            <label>Numéro (ex: 701) *</label>
                            <input value={compteForm.numero} onChange={e => setCompteForm({...compteForm, numero: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Nom *</label>
                            <input value={compteForm.nom} onChange={e => setCompteForm({...compteForm, nom: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Type de compte</label>
                            <select value={compteForm.type_compte} onChange={e => setCompteForm({...compteForm, type_compte: e.target.value})}>
                                <option value="actif">Actif</option>
                                <option value="passif">Passif</option>
                                <option value="charge">Charge</option>
                                <option value="produit">Produit</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Compte parent</label>
                            <select value={compteForm.sous_compte_id} onChange={e => setCompteForm({...compteForm, sous_compte_id: e.target.value})}>
                                <option value="">Compte parent</option>
                                {comptes.map(c => <option key={c.id} value={c.id}>{c.numero} - {c.nom}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <button type="submit" className="btn-primary">{editingType === 'compte' ? 'Modifier' : 'Créer'}</button>
                        </div>
                        {editingType === 'compte' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('compte')}>Annuler</button></div>}
                    </form>

                    <div className="import-section">
                        <h4>Importer des comptes (CSV / Excel)</h4>
                        <p className="text-muted">Colonnes attendues : numero, nom, type_compte, sous_compte_id (optionnel), solde (optionnel)</p>
                        <div className="form-row">
                            <input type="file" accept=".csv,.xlsx,.xls" onChange={handleImportFile} />
                            <button className="btn-primary" disabled={importing || !importFile} onClick={() => handleImport('compte')}>{importing ? 'Import...' : 'Importer comptes'}</button>
                        </div>
                        {importPreview.length > 0 && (
                            <pre style={{fontSize: 11, background: '#f5f5f5', padding: 8, marginTop: 8}}>{importPreview.join('\n')}</pre>
                        )}
                    </div>

                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Numéro</th><th>Nom</th><th>Type</th><th>Solde</th><th>Actions</th></tr></thead>
                        <tbody>{comptes.map(c => <tr key={c.id}><td>{c.numero}</td><td>{c.nom}</td><td>{c.type_compte}</td><td>{c.solde}</td><td><button className="btn-small btn-edit" onClick={() => handleEdit(c, 'compte')}>Modifier</button> <button className="btn-small btn-delete" onClick={() => handleDelete('compte', c.id)}>Supprimer</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}

            {tab === 'ecritures' && (
                <div className="card">
                    <h3>{editingType === 'ecriture' ? 'Modifier' : 'Nouvelle'} écriture</h3>
                    <form onSubmit={(e) => handleSubmit(e, 'ecriture')} className="form-grid">
                        <div className="form-group">
                            <label>Date *</label>
                            <input type="date" value={ecritureForm.date} onChange={e => setEcritureForm({...ecritureForm, date: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Compte *</label>
                            <select value={ecritureForm.compte_id} onChange={e => setEcritureForm({...ecritureForm, compte_id: e.target.value})} required>
                                <option value="">Compte</option>
                                {comptes.map(c => <option key={c.id} value={c.id}>{c.numero} - {c.nom}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Débit</label>
                            <input type="number" value={ecritureForm.montant_debit} onChange={e => setEcritureForm({...ecritureForm, montant_debit: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Crédit</label>
                            <input type="number" value={ecritureForm.montant_credit} onChange={e => setEcritureForm({...ecritureForm, montant_credit: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Libellé *</label>
                            <input value={ecritureForm.libelle} onChange={e => setEcritureForm({...ecritureForm, libelle: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Référence externe</label>
                            <input value={ecritureForm.reference_externe} onChange={e => setEcritureForm({...ecritureForm, reference_externe: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Entité type</label>
                            <input value={ecritureForm.entite_type} onChange={e => setEcritureForm({...ecritureForm, entite_type: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Entité ID</label>
                            <input type="number" value={ecritureForm.entite_id} onChange={e => setEcritureForm({...ecritureForm, entite_id: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <button type="submit" className="btn-primary">{editingType === 'ecriture' ? 'Modifier' : 'Créer'}</button>
                        </div>
                        {editingType === 'ecriture' && <div className="form-group"><button type="button" className="btn-secondary" onClick={() => resetForm('ecriture')}>Annuler</button></div>}
                    </form>

                    <div className="import-section">
                        <h4>Importer des écritures (CSV / Excel)</h4>
                        <p className="text-muted">Colonnes attendues : date, compte_id, montant_debit, montant_credit, libelle, reference_externe (opt), entite_type (opt), entite_id (opt), statut (opt), piece_joint (opt)</p>
                        <div className="form-row">
                            <input type="file" accept=".csv,.xlsx,.xls" onChange={handleImportFile} />
                            <button className="btn-primary" disabled={importing || !importFile} onClick={() => handleImport('ecriture')}>{importing ? 'Import...' : 'Importer écritures'}</button>
                        </div>
                        {importPreview.length > 0 && (
                            <pre style={{fontSize: 11, background: '#f5f5f5', padding: 8, marginTop: 8}}>{importPreview.join('\n')}</pre>
                        )}
                    </div>

                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Date</th><th>Compte</th><th>Débit</th><th>Crédit</th><th>Libellé</th><th>Statut</th><th>Actions</th></tr></thead>
                        <tbody>{ecritures.map(ec => <tr key={ec.id}><td>{ec.date}</td><td>{ec.compte_numero} - {ec.compte_nom}</td><td>{ec.montant_debit}</td><td>{ec.montant_credit}</td><td>{ec.libelle}</td><td><span className={`badge ${ec.statut}`}>{ec.statut}</span></td><td><button className="btn-small btn-primary" onClick={() => handleValider(ec.id)}>Valider</button> <button className="btn-small btn-secondary" onClick={() => handleAnnuler(ec.id)}>Annuler</button> <button className="btn-small btn-delete" onClick={() => handleDelete('ecriture', ec.id)}>Supprimer</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}

            {tab === 'tresorerie' && (
                <div className="card">
                    <h3>Nouvelle entrée trésorerie</h3>
                    <form onSubmit={(e) => handleSubmit(e, 'tresorerie')} className="form-grid">
                        <div className="form-group">
                            <label>Date *</label>
                            <input type="date" value={tresForm.date} onChange={e => setTresForm({...tresForm, date: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Type d'opération</label>
                            <select value={tresForm.type_operation} onChange={e => setTresForm({...tresForm, type_operation: e.target.value})}>
                                <option value="entree">Entrée</option>
                                <option value="sortie">Sortie</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Montant *</label>
                            <input type="number" value={tresForm.montant} onChange={e => setTresForm({...tresForm, montant: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Mode de paiement</label>
                            <select value={tresForm.mode_paiement} onChange={e => setTresForm({...tresForm, mode_paiement: e.target.value})}>
                                <option value="espece">Espèce</option>
                                <option value="virement">Virement</option>
                                <option value="cheque">Chèque</option>
                                <option value="mobile_money">Mobile Money</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Libellé *</label>
                            <input value={tresForm.libelle} onChange={e => setTresForm({...tresForm, libelle: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Compte bancaire</label>
                            <input value={tresForm.compte_bancaire} onChange={e => setTresForm({...tresForm, compte_bancaire: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Référence</label>
                            <input value={tresForm.reference} onChange={e => setTresForm({...tresForm, reference: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <button type="submit" className="btn-primary">Créer</button>
                        </div>
                    </form>

                    <div className="import-section">
                        <h4>Importer de la trésorerie (CSV / Excel)</h4>
                        <p className="text-muted">Colonnes attendues : date, type_operation, montant, libelle, mode_paiement (opt), compte_bancaire (opt), reference (opt), is_reconcilie (opt)</p>
                        <div className="form-row">
                            <input type="file" accept=".csv,.xlsx,.xls" onChange={handleImportFile} />
                            <button className="btn-primary" disabled={importing || !importFile} onClick={() => handleImport('tresorerie')}>{importing ? 'Import...' : 'Importer trésorerie'}</button>
                        </div>
                        {importPreview.length > 0 && (
                            <pre style={{fontSize: 11, background: '#f5f5f5', padding: 8, marginTop: 8}}>{importPreview.join('\n')}</pre>
                        )}
                    </div>

                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Date</th><th>Type</th><th>Montant</th><th>Mode</th><th>Libellé</th><th>Actions</th></tr></thead>
                        <tbody>{tresoreries.map(t => <tr key={t.id}><td>{t.date}</td><td>{t.type_operation}</td><td>{t.montant}</td><td>{t.mode_paiement}</td><td>{t.libelle}</td><td><button className="btn-small btn-edit" onClick={() => handleEdit(t, 'tresorerie')}>Modifier</button> <button className="btn-small btn-delete" onClick={() => handleDelete('tresorerie', t.id)}>Supprimer</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}
        </div>
    );
}
