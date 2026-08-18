import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import api, { modeleDocumentService, documentService } from '../services/api';

export default function Documents() {
    const [tab, setTab] = useState('documents');
    const [modeles, setModeles] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);

    const [modeleForm, setModeleForm] = useState({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' });
    const [docForm, setDocForm] = useState({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '', donnees: '{}' });

    const [editingId, setEditingId] = useState(null);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [m, d] = await Promise.all([modeleDocumentService.getAll(), documentService.getAll()]);
            setModeles(m.data.modeles || []);
            setDocuments(d.data.documents || []);
        } catch (err) { toast.error('Erreur chargement'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    const handleSubmitModele = async (e) => {
        e.preventDefault();
        try {
            const data = { ...modeleForm, est_actif: true };
            if (editingId) { await modeleDocumentService.update(editingId, data); toast.success('Modèle modifié'); }
            else { await modeleDocumentService.create(data); toast.success('Modèle créé'); }
            setModeleForm({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' });
            setEditingId(null); fetchAll();
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
    };

    const handleSubmitDocument = async (e) => {
        e.preventDefault();
        try {
            let donnees = {};
            try { donnees = JSON.parse(docForm.donnees); } catch { toast.error('JSON invalide dans donnees'); return; }
            const data = { ...docForm, modele_id: Number(docForm.modele_id), entite_id: Number(docForm.entite_id) || null, donnees };
            const response = await documentService.generer(data);
            toast.success('Document généré');
            setDocForm({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '', donnees: '{}' });
            if (response.data) {
                setDocuments(prev => [response.data, ...prev]);
            } else {
                fetchAll();
            }
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
    };

    const handleDelete = async (type, id) => {
        if (!window.confirm('Supprimer ?')) return;
        const svc = type === 'modele' ? modeleDocumentService : documentService;
        await svc.delete(id); toast.success('Supprimé'); fetchAll();
    };

    const handleEditModele = (m) => {
        setEditingId(m.id);
        setModeleForm({ nom: m.nom, type_document: m.type_document, contenu_modele: m.contenu_modele, est_defaut: m.est_defaut, logo_url: m.logo_url || '', mention_legales: m.mention_legales || '', conditions_generales: m.conditions_generales || '' });
        setTab('modeles');
    };

    const getPdfUrl = (doc) => {
        if (doc.pdf_url) {
            if (doc.pdf_url.startsWith('http')) return doc.pdf_url;
            const baseUrl = api.defaults.baseURL.replace('/api/v1', '');
            return `${baseUrl}${doc.pdf_url}`;
        }
        if (doc.contenu_pdf_path) {
            const filename = doc.contenu_pdf_path.split(/[\\/]/).pop();
            const baseUrl = api.defaults.baseURL.replace('/api/v1', '');
            return `${baseUrl}/api/v1/documents/${doc.id}/pdf`;
        }
        return '#';
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <h1>Documents</h1>
                <div className="tabs">
                    {['modeles', 'documents'].map(t => (
                        <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => { setTab(t); setEditingId(null); }}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
                    ))}
                </div>
            </div>

            {tab === 'modeles' && (
                <div className="card">
                    <h3>{editingId ? 'Modifier' : 'Nouveau'} modèle de document</h3>
                    <form onSubmit={handleSubmitModele} className="form-grid">
                        <div className="form-group">
                            <input placeholder="Nom" value={modeleForm.nom} onChange={e => setModeleForm({...modeleForm, nom: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <select value={modeleForm.type_document} onChange={e => setModeleForm({...modeleForm, type_document: e.target.value})}>
                                <option value="facture">Facture</option><option value="devis">Devis</option><option value="contrat">Contrat</option><option value="bon_livraison">Bon de livraison</option><option value="avoir">Avoir</option>
                            </select>
                        </div>
                        <label style={{display:'flex', alignItems:'center', gap: 8}}>
                            <input type="checkbox" checked={modeleForm.est_defaut} onChange={e => setModeleForm({...modeleForm, est_defaut: e.target.checked})} />
                            Défaut
                        </label>
                        <div className="form-group full-width">
                            <textarea placeholder="Contenu HTML avec {{placeholders}}" value={modeleForm.contenu_modele} onChange={e => setModeleForm({...modeleForm, contenu_modele: e.target.value})} rows={4} required />
                        </div>
                        <div className="form-group">
                            <input placeholder="Logo URL" value={modeleForm.logo_url} onChange={e => setModeleForm({...modeleForm, logo_url: e.target.value})} />
                        </div>
                        <div className="form-group full-width">
                            <textarea placeholder="Mentions légales" value={modeleForm.mention_legales} onChange={e => setModeleForm({...modeleForm, mention_legales: e.target.value})} rows={2} />
                        </div>
                        <div className="form-group full-width">
                            <textarea placeholder="Conditions générales" value={modeleForm.conditions_generales} onChange={e => setModeleForm({...modeleForm, conditions_generales: e.target.value})} rows={2} />
                        </div>
                        <button type="submit" className="btn-primary">{editingId ? 'Modifier' : 'Créer'}</button>
                        {editingId && <button type="button" className="btn-secondary" onClick={() => { setEditingId(null); setModeleForm({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' }); }}>Annuler</button>}
                    </form>
                    <div className="table-container" style={{marginTop: 24}}>
                        <table className="data-table"><thead><tr><th>Nom</th><th>Type</th><th>Défaut</th><th>Actions</th></tr></thead>
                        <tbody>{modeles.map(m => <tr key={m.id}><td>{m.nom}</td><td>{m.type_document}</td><td>{m.est_defaut ? 'Oui' : 'Non'}</td><td><button className="btn-small btn-edit" onClick={() => handleEditModele(m)} title="Modifier">&#9998;</button> <button className="btn-small btn-delete" onClick={() => handleDelete('modele', m.id)} title="Supprimer">&#10005;</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}

            {tab === 'documents' && (
                <div className="card">
                    <h3>Générer un document</h3>
                    <form onSubmit={handleSubmitDocument} className="form-grid">
                        <div className="form-group">
                            <select value={docForm.modele_id} onChange={e => setDocForm({...docForm, modele_id: e.target.value})} required>
                                <option value="">Modèle</option>
                                {modeles.map(m => <option key={m.id} value={m.id}>{m.nom} ({m.type_document})</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <input placeholder="Référence" value={docForm.reference} onChange={e => setDocForm({...docForm, reference: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <select value={docForm.type_document} onChange={e => setDocForm({...docForm, type_document: e.target.value})}>
                                <option value="facture">Facture</option><option value="devis">Devis</option><option value="contrat">Contrat</option><option value="bon_livraison">Bon de livraison</option><option value="avoir">Avoir</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <select value={docForm.entite_type} onChange={e => setDocForm({...docForm, entite_type: e.target.value})}>
                                <option value="vente">Vente</option><option value="facture">Facture</option><option value="commande">Commande</option><option value="abonnement">Abonnement</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <input placeholder="Entité ID" type="number" value={docForm.entite_id} onChange={e => setDocForm({...docForm, entite_id: e.target.value})} />
                        </div>
                        <div className="form-group full-width">
                            <textarea placeholder='Données JSON (ex: {"client_nom":"Dupont","total_ttc":"1500"})' value={docForm.donnees} onChange={e => setDocForm({...docForm, donnees: e.target.value})} rows={3} required />
                        </div>
                        <button type="submit" className="btn-primary">Générer</button>
                    </form>
                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Référence</th><th>Type</th><th>Modèle</th><th>PDF</th><th>Date</th><th>Actions</th></tr></thead>
                        <tbody>{documents.map(d => <tr key={d.id}><td>{d.reference}</td><td>{d.type_document}</td><td>{d.modele_nom}</td><td>{d.contenu_pdf_path ? <a href={getPdfUrl(d)} target="_blank" rel="noopener noreferrer" className="badge success">PDF</a> : '-'}</td><td>{d.date_generation?.slice(0, 10)}</td><td><button className="btn-small btn-view" onClick={() => window.open(getPdfUrl(d), '_blank')} title="Voir PDF">&#128065;</button> <button className="btn-small btn-delete" onClick={() => handleDelete('document', d.id)} title="Supprimer">&#10005;</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}
        </div>
    );
}