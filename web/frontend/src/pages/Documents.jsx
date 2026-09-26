import { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { modeleDocumentService, documentService, saleService, factureService } from '../services/api';
import './Documents.css';

export default function Documents() {
    const [tab, setTab] = useState('documents');
    const [modeles, setModeles] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [sales, setSales] = useState([]);
    const [factures, setFactures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [previewDoc, setPreviewDoc] = useState(null);
    const [previewPdfUrl, setPreviewPdfUrl] = useState(null);

    const [modeleForm, setModeleForm] = useState({ nom: '', type_document: 'facture', contenu_modele: '', est_defaut: false, logo_url: '', mention_legales: '', conditions_generales: '' });
    const [docForm, setDocForm] = useState({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '' });

    const [editingId, setEditingId] = useState(null);
    const contenuRef = useRef(null);
    const [stretchActive, setStretchActive] = useState(false);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [m, d, s, f] = await Promise.allSettled([modeleDocumentService.getAll(), documentService.getAll(), saleService.getAll(), factureService.getAll()]);
            const failed = [m, d, s, f].filter(r => r.status === 'rejected');
            if (failed.length > 0) {
              const msgs = failed.map(r => r.reason?.response?.data?.message || r.reason?.message || 'Erreur');
            }
            setModeles((m.status === 'fulfilled' ? m.value?.data?.modeles || m.value?.data || [] : []));
            setDocuments((d.status === 'fulfilled' ? d.value?.data?.documents || d.value?.data || [] : []));
            setSales((s.status === 'fulfilled' ? s.value?.data?.ventes || s.value?.data || [] : []));
            setFactures((f.status === 'fulfilled' ? f.value?.data?.factures || f.value?.data || [] : []));
        } catch (err) { toast.error('Erreur chargement'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    useEffect(() => {
        if (!contenuRef.current || !stretchActive) return;
        const ta = contenuRef.current;
        ta.style.fieldSizing = 'content';
        ta.style.height = 'auto';
        const handleInput = () => {
            ta.style.height = 'auto';
            ta.style.height = ta.scrollHeight + 'px';
        };
        ta.addEventListener('input', handleInput);
        handleInput();
        return () => ta.removeEventListener('input', handleInput);
    }, [stretchActive]);

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
            const data = {
                modele_id: docForm.modele_id ? Number(docForm.modele_id) : null,
                type_document: docForm.type_document,
                reference: docForm.reference.trim() || null,
                entite_type: docForm.entite_type,
                entite_id: Number(docForm.entite_id),
                donnees: {},
            };
            const response = await documentService.generer(data);
            toast.success('Document généré avec succès');
            setDocForm({ modele_id: '', type_document: 'facture', reference: '', entite_type: 'vente', entite_id: '' });
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

    const openPreview = async (doc) => {
        setPreviewDoc(doc);
        if (previewPdfUrl) {
            window.URL.revokeObjectURL(previewPdfUrl);
            setPreviewPdfUrl(null);
        }
        try {
            const response = await documentService.getPdf(doc.id);
            const url = window.URL.createObjectURL(response.data);
            setPreviewPdfUrl(url);
        } catch (e) {
            toast.error(e.response?.data?.message || 'Erreur lors de la prévisualisation');
        }
    };

    const closePreview = () => {
        if (previewPdfUrl) {
            window.URL.revokeObjectURL(previewPdfUrl);
            setPreviewPdfUrl(null);
        }
        setPreviewDoc(null);
    };

    const handleDownload = async (doc) => {
        try {
            const response = await documentService.getPdf(doc.id);
            const downloadUrl = window.URL.createObjectURL(response.data);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = doc.contenu_pdf_path ? doc.contenu_pdf_path.split(/[\\/]/).pop() : `${doc.reference}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            toast.success('Téléchargement lancé');
        } catch (err) {
            toast.error(err.response?.data?.message || 'Erreur lors du téléchargement');
        }
    };

    const handlePrint = async (doc) => {
        try {
            const response = await documentService.getPdf(doc.id);
            const url = window.URL.createObjectURL(response.data);
            const win = window.open(url, '_blank');
            if (!win) {
                window.URL.revokeObjectURL(url);
                toast.error("Impossible d'ouvrir la fenêtre d'impression");
                return;
            }
            win.addEventListener('load', () => {
                win.print();
                window.setTimeout(() => window.URL.revokeObjectURL(url), 30000);
            }, { once: true });
        } catch (err) {
            toast.error(err.response?.data?.message || "Erreur lors de l'impression");
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
                <a href="/documentation" className="manual-link" title="Manuel d'utilisation du module Documents, de A à Z">Manuel d'utilisation — Module Documents (de A à Z)</a>
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
                            <textarea ref={contenuRef} placeholder="Contenu HTML avec {{placeholders}}" value={modeleForm.contenu_modele} onChange={e => setModeleForm({...modeleForm, contenu_modele: e.target.value})} rows={4} required />
                            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                                <button type="button" className="btn-secondary btn-sm" onClick={() => setStretchActive(v => !v)}>{stretchActive ? 'Auto-stretch actif' : 'Auto-stretch'}</button>
                            </div>
                        </div>
                        <div className="form-group">
                            <input type="file" accept="image/*" onChange={e => {
                                const file = e.target.files?.[0];
                                if (!file) return;
                                const reader = new FileReader();
                                reader.onload = (ev) => setModeleForm({...modeleForm, logo_url: ev.target.result});
                                reader.readAsDataURL(file);
                            }} />
                            {modeleForm.logo_url && <img src={modeleForm.logo_url} alt="Logo" style={{maxHeight: 40, marginTop: 6, display: 'block'}} />}
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
                        <div className="form-group full-width">
                            <label>Document à partir de</label>
                            <select
                                value={docForm.entite_type}
                                onChange={(event) => {
                                    const type = event.target.value;
                                    const items = type === 'vente' ? sales : factures;
                                    const first = items[0];
                                    setDocForm((prev) => ({
                                        ...prev,
                                        entite_type: type,
                                        entite_id: first?.id ? String(first.id) : '',
                                        reference: first?.reference || '',
                                    }));
                                }}
                            >
                                <option value="vente">Vente</option>
                                <option value="facture">Facture</option>
                            </select>
                            <small className="text-muted">Les données métier sont reprises automatiquement. Vous n’avez pas à saisir de JSON ni d’ID.</small>
                        </div>
                        <div className="form-group full-width">
                            <label>{docForm.entite_type === 'vente' ? 'Vente' : 'Facture'} *</label>
                            <select
                                value={docForm.entite_id}
                                onChange={(event) => {
                                    const id = Number(event.target.value);
                                    const items = docForm.entite_type === 'vente' ? sales : factures;
                                    const item = items.find((entry) => entry.id === id);
                                    setDocForm((prev) => ({
                                        ...prev,
                                        entite_id: event.target.value,
                                        reference: item?.reference || '',
                                    }));
                                }}
                                required
                            >
                                <option value="">Sélectionner</option>
                                {(docForm.entite_type === 'vente' ? sales : factures).map((item) => (
                                    <option key={item.id} value={item.id}>
                                        {(item.reference || '#' + item.id) + ' — ' + (item.client_nom || item.client?.nom || 'Client')}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Type de document</label>
                            <select value={docForm.type_document} onChange={event => setDocForm({...docForm, type_document: event.target.value})}>
                                <option value="facture">Facture</option>
                                <option value="devis">Devis</option>
                                <option value="bon_livraison">Bon de livraison</option>
                                <option value="avoir">Avoir</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Référence</label>
                            <input id="reference" name="reference" placeholder="Reprise automatiquement" value={docForm.reference} onChange={event => setDocForm({...docForm, reference: event.target.value})} />
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