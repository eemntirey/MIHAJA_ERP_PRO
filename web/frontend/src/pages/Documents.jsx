import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import api, { modeleDocumentService, documentService } from '../services/api';
import { authStorage } from '../../../../shared/storage/authStorage';
import './Documents.css';

export default function Documents() {
    const [tab, setTab] = useState('documents');
    const [modeles, setModeles] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [previewDoc, setPreviewDoc] = useState(null);

    const [modeleForm, setModeleForm] = useState({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' });
    const [docForm, setDocForm] = useState({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '', donnees: '{}' });

    const [editingId, setEditingId] = useState(null);

    useEffect(() => {
        try {
            const raw = sessionStorage.getItem('documents_prefill');
            if (!raw) return;
            const data = JSON.parse(raw);
            sessionStorage.removeItem('documents_prefill');
            setTab('documents');
            setDocForm(prev => ({
                ...prev,
                type_document: data.type_document || prev.type_document,
                reference: data.reference || prev.reference,
                entite_type: data.entite_type || prev.entite_type,
                entite_id: data.entite_id || prev.entite_id,
                donnees: typeof data.donnees === 'string' ? data.donnees : JSON.stringify(data.donnees, null, 2),
            }));
            toast.info('Données pré-remplies depuis la facture');
        } catch (_) { /* ignore */ }
    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [m, d] = await Promise.allSettled([modeleDocumentService.getAll(), documentService.getAll()]);
            const failed = [m, d].filter(r => r.status === 'rejected');
            if (failed.length > 0) {
              const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
              toast.warning(`Chargement partiel: ${msgs.join(', ')}`);
            }
            setModeles((m.status === 'fulfilled' ? m.value?.data?.modeles || m.value?.data || [] : []));
            setDocuments((d.status === 'fulfilled' ? d.value?.data?.documents || d.value?.data || [] : []));
        } catch (err) { toast.error('Erreur chargement'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    if (loading && modeles.length === 0 && documents.length === 0) {
        return (
            <div className="page-container">
                <div className="loading-screen">
                    <div className="spinner-large"></div>
                    <p>Chargement des documents...</p>
                </div>
            </div>
        );
    }

    const handleSubmitModele = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const data = { ...modeleForm, is_active: true };
            if (editingId) { await modeleDocumentService.update(editingId, data); toast.success('Modèle modifié'); }
            else { await modeleDocumentService.create(data); toast.success('Modèle créé'); }
            setModeleForm({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' });
            setEditingId(null); fetchAll();
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
        finally { setSubmitting(false); }
    };

    const handleSubmitDocument = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            let donnees = {};
            try { donnees = JSON.parse(docForm.donnees); } catch { toast.error('JSON invalide dans donnees'); setSubmitting(false); return; }
            const data = { ...docForm, modele_id: Number(docForm.modele_id), entite_id: Number(docForm.entite_id) || null, donnees };
            const response = await documentService.generer(data);
            toast.success('Document généré avec succès');
            setDocForm({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '', donnees: '{}' });
            if (response.data) {
                setDocuments(prev => [response.data, ...prev]);
            } else {
                fetchAll();
            }
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur lors de la génération'); }
        finally { setSubmitting(false); }
    };

    const handleDelete = async (type, id) => {
        if (!window.confirm('Supprimer ce document ?')) return;
        const svc = type === 'modele' ? modeleDocumentService : documentService;
        try {
            await svc.delete(id);
            toast.success('Supprimé');
            fetchAll();
        } catch (e) {
            toast.error(e.response?.data?.message || 'Erreur de suppression');
        }
    };

    const handleEditModele = (m) => {
        setEditingId(m.id);
        setModeleForm({ nom: m.nom, type_document: m.type_document, contenu_modele: m.contenu_modele, est_defaut: m.est_defaut, logo_url: m.logo_url || '', mention_legales: m.mention_legales || '', conditions_generales: m.conditions_generales || '' });
        setTab('modeles');
    };

    const getPdfUrl = (doc) => {
        if (doc.pdf_url) {
            if (doc.pdf_url.startsWith('http')) return doc.pdf_url;
            const baseUrl = api.defaults.baseURL.replace(/\/api\/v1\/?$/, '');
            return `${baseUrl}${doc.pdf_url}`;
        }
        if (doc.contenu_pdf_path) {
            const baseUrl = api.defaults.baseURL.replace(/\/api\/v1\/?$/, '');
            return `${baseUrl}/api/v1/documents/${doc.id}/pdf`;
        }
        return '#';
    };

    const openPreview = (doc) => {
        setPreviewDoc(doc);
    };

    const closePreview = () => {
        setPreviewDoc(null);
    };

    const handleDownload = async (doc) => {
        const url = getPdfUrl(doc);
        try {
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${authStorage.getAccessToken()}`
                }
            });
            if (!response.ok) throw new Error('Erreur téléchargement');
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = doc.contenu_pdf_path ? doc.contenu_pdf_path.split(/[\\/]/).pop() : `${doc.reference}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            toast.success('Téléchargement lancé');
        } catch (err) {
            toast.error('Erreur lors du téléchargement');
        }
    };

    const handlePrint = (doc) => {
        const url = getPdfUrl(doc);
        const win = window.open(url, '_blank');
        if (win) {
            win.addEventListener('load', () => {
                win.print();
            }, { once: true });
        } else {
            toast.error('Impossible d\'ouvrir la fenêtre d\'impression');
        }
    };

    const typeLabels = {
        facture: 'Facture',
        devis: 'Devis',
        contrat: 'Contrat',
        bon_livraison: 'Bon de livraison',
        avoir: 'Avoir',
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
                        <label className="filter-checkbox">
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
                        <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : (editingId ? 'Modifier' : 'Créer')}</button>
                        {editingId && <button type="button" className="btn-secondary" onClick={() => { setEditingId(null); setModeleForm({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' }); }} disabled={submitting}>Annuler</button>}
                    </form>
                    <div className="table-container" style={{marginTop: 24}}>
                        <table className="data-table"><thead><tr><th>Nom</th><th>Type</th><th>Défaut</th><th>Actions</th></tr></thead>
                        <tbody>{modeles.map(m => <tr key={m.id}><td>{m.nom}</td><td>{typeLabels[m.type_document] || m.type_document}</td><td>{m.est_defaut ? 'Oui' : 'Non'}</td><td><button className="btn-small btn-edit" onClick={() => handleEditModele(m)} title="Modifier">&#9998;</button> <button className="btn-small btn-delete" onClick={() => handleDelete('modele', m.id)} title="Supprimer">&#10005;</button></td></tr>)}</tbody></table>
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
                                {modeles.map(m => <option key={m.id} value={m.id}>{m.nom} ({typeLabels[m.type_document] || m.type_document})</option>)}
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
                            <textarea placeholder='Données JSON (ex: {"client_nom":"Boutique Soa","total_ttc":"326400","items":[{"produit_nom":"Riz blanc (sac 50 kg)","quantite":2,"prix_unitaire":136000,"taux_tva":20,"total_ht":272000}]})' value={docForm.donnees} onChange={e => setDocForm({...docForm, donnees: e.target.value})} rows={3} required />
                        </div>
                        <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? <span className="btn-spinner" /> : 'Générer le PDF'}</button>
                    </form>

                    <div className="documents-toolbar">
                        <h4>Documents générés</h4>
                        <span className="documents-count">{documents.length} document(s)</span>
                    </div>
                    <div className="table-container">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Référence</th>
                                    <th>Type</th>
                                    <th>Modèle</th>
                                    <th>Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {documents.length === 0 ? (
                                    <tr><td colSpan="5" className="documents-empty">Aucun document généré</td></tr>
                                ) : documents.map(d => (
                                    <tr key={d.id}>
                                        <td><span className="doc-ref">{d.reference}</span></td>
                                        <td><span className="statut-badge statut-info">{typeLabels[d.type_document] || d.type_document}</span></td>
                                        <td>{d.modele_nom || '-'}</td>
                                        <td>{d.date_generation?.slice(0, 10)}</td>
                                        <td>
                                            <div className="doc-actions">
                                                {d.contenu_pdf_path ? (
                                                    <>
                                                        <button className="btn-small btn-view" onClick={() => openPreview(d)} title="Prévisualiser">&#128065;</button>
                                                        <button className="btn-small btn-primary" onClick={() => handleDownload(d)} title="Télécharger">&#11015;</button>
                                                        <button className="btn-small btn-secondary" onClick={() => handlePrint(d)} title="Imprimer">&#9993;</button>
                                                    </>
                                                ) : <span className="text-muted">-</span>}
                                                <button className="btn-small btn-delete" onClick={() => handleDelete('document', d.id)} title="Supprimer">&#10005;</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {previewDoc && (
                <div className="modal-overlay" onClick={closePreview}>
                    <div className="modal xlarge" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Prévisualisation - {previewDoc.reference}</h2>
                            <div className="modal-header-actions">
                                <button className="btn-small btn-primary" onClick={() => handleDownload(previewDoc)} title="Télécharger">&#11015; Télécharger</button>
                                <button className="btn-small btn-secondary" onClick={() => handlePrint(previewDoc)} title="Imprimer">&#9993; Imprimer</button>
                                <button className="btn-close" onClick={closePreview}>&times;</button>
                            </div>
                        </div>
                        <div className="modal-form pdf-preview-container">
                            <iframe
                                src={getPdfUrl(previewDoc)}
                                title={`Prévisualisation ${previewDoc.reference}`}
                                className="pdf-iframe"
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}