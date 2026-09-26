import { useMemo, useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { commandeAchatService, receptionService, productService, fournisseurService } from '../services/api';
import { markOnboardingAction } from '../components/GuidedOnboarding';
import './Pages.css';

const EMPTY_LINE = () => ({
    produit_id: '',
    quantite: 1,
    prix_unitaire_ht: 0,
    taux_tva: 10,
});

const EMPTY_CMD = {
    fournisseur_id: '',
    date_commande: new Date().toISOString().slice(0, 10),
    date_livraison_prevue: '',
    conditions_paiement: '30 jours',
    remarque: '',
};

const EMPTY_REC = {
    commande_achat_id: '',
    produit_id: '',
    reference: '',
    quantite_recue: '',
    remarque: '',
};

const toNumber = (value) => {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
};

export default function Purchases() {
    const [tab, setTab] = useState('commandes');
    const [commandes, setCommandes] = useState([]);
    const [receptions, setReceptions] = useState([]);
    const [products, setProducts] = useState([]);
    const [fournisseurs, setFournisseurs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [cmdForm, setCmdForm] = useState(EMPTY_CMD);
    const [cmdLines, setCmdLines] = useState([EMPTY_LINE()]);
    const [recForm, setRecForm] = useState(EMPTY_REC);
    const [editingId, setEditingId] = useState(null);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [c, r, p, f] = await Promise.allSettled([
                commandeAchatService.getAll(),
                receptionService.getAll(),
                productService.getAll(),
                fournisseurService.getAll(),
            ]);

            const failures = [c, r, p, f].filter((result) => result.status === 'rejected');
            if (failures.length) {
                toast.error(
                    failures
                        .map((result) => result.reason?.response?.data?.message || result.reason?.message || 'Erreur')
                        .join(', ')
                );
            }

            setCommandes(c.status === 'fulfilled' ? (c.value?.data?.commandes || c.value?.data || []) : []);
            setReceptions(r.status === 'fulfilled' ? (r.value?.data?.receptions || r.value?.data || []) : []);
            setProducts(p.status === 'fulfilled' ? (p.value?.data?.produits || p.value?.data || []) : []);
            setFournisseurs(f.status === 'fulfilled' ? (f.value?.data?.fournisseurs || f.value?.data || []) : []);
        } catch (err) {
            toast.error(err.response?.data?.message || 'Erreur chargement');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, []);

    const selectedCommande = useMemo(
        () => commandes.find((commande) => commande.id === Number(recForm.commande_achat_id)),
        [commandes, recForm.commande_achat_id]
    );

    const receptionLines = useMemo(
        () => (selectedCommande?.lignes || []).filter((line) => line.produit_id),
        [selectedCommande]
    );

    const selectedReceptionLine = useMemo(
        () => receptionLines.find((line) => line.produit_id === Number(recForm.produit_id)),
        [receptionLines, recForm.produit_id]
    );

    const commandTotals = useMemo(() => {
        return cmdLines.reduce(
            (totals, line) => {
                const qty = toNumber(line.quantite);
                const price = toNumber(line.prix_unitaire_ht);
                const tva = toNumber(line.taux_tva);
                const ht = qty * price;
                totals.ht += ht;
                totals.ttc += ht * (1 + tva / 100);
                return totals;
            },
            { ht: 0, ttc: 0 }
        );
    }, [cmdLines]);

    const resetCommandForm = () => {
        setCmdForm(EMPTY_CMD);
        setCmdLines([EMPTY_LINE()]);
        setEditingId(null);
    };

    const handleCommandChange = (field, value) => {
        setCmdForm((prev) => ({ ...prev, [field]: value }));
    };

    const updateLine = (index, field, value) => {
        setCmdLines((prev) => prev.map((line, i) => {
            if (i !== index) return line;
            const next = { ...line, [field]: value };
            if (field === 'produit_id') {
                const product = products.find((item) => item.id === Number(value));
                if (product) {
                    next.prix_unitaire_ht = product.prix_achat_ht || 0;
                    next.taux_tva = product.taux_tva ?? 10;
                }
            }
            return next;
        }));
    };

    const addLine = () => setCmdLines((prev) => [...prev, EMPTY_LINE()]);

    const removeLine = (index) => {
        setCmdLines((prev) => prev.length === 1 ? prev : prev.filter((_, i) => i !== index));
    };

    const handleSubmitCmd = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const lignes = cmdLines
                .filter((line) => line.produit_id && toNumber(line.quantite) > 0)
                .map((line) => ({
                    produit_id: Number(line.produit_id),
                    quantite: toNumber(line.quantite),
                    prix_unitaire_ht: toNumber(line.prix_unitaire_ht),
                    taux_tva: toNumber(line.taux_tva),
                }));

            if (!cmdForm.fournisseur_id) {
                toast.error('Sélectionnez un fournisseur.');
                setSubmitting(false);
                return;
            }
            if (!lignes.length) {
                toast.error('Ajoutez au moins un produit à la commande.');
                setSubmitting(false);
                return;
            }

            const data = {
                ...cmdForm,
                fournisseur_id: Number(cmdForm.fournisseur_id),
                lignes,
            };

            if (editingId) {
                await commandeAchatService.update(editingId, data);
                toast.success('Commande modifiée');
            } else {
                await commandeAchatService.create(data);
                toast.success('Commande créée');
                markOnboardingAction('purchases');
            }
            resetCommandForm();
            await fetchAll();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Erreur lors de la sauvegarde de la commande');
        } finally {
            setSubmitting(false);
        }
    };

    const handleSubmitRec = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            if (!recForm.commande_achat_id) {
                toast.error('Sélectionnez la commande reçue.');
                setSubmitting(false);
                return;
            }
            if (receptionLines.length > 1 && !recForm.produit_id) {
                toast.error('Sélectionnez le produit reçu.');
                setSubmitting(false);
                return;
            }

            const quantity = toNumber(recForm.quantite_recue);
            if (quantity <= 0) {
                toast.error('La quantité reçue doit être supérieure à 0.');
                setSubmitting(false);
                return;
            }

            const data = {
                commande_achat_id: Number(recForm.commande_achat_id),
                produit_id: recForm.produit_id ? Number(recForm.produit_id) : null,
                reference: recForm.reference.trim() || undefined,
                quantite_recue: quantity,
                remarque: recForm.remarque,
            };

            await receptionService.create(data);
            toast.success('Réception enregistrée et stock mis à jour');
            markOnboardingAction('purchases');
            setRecForm(EMPTY_REC);
            await fetchAll();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Erreur lors de la réception');
        } finally {
            setSubmitting(false);
        }
    };

    const handleCommandeSelection = (value) => {
        const commandeId = value ? Number(value) : '';
        const commande = commandes.find((item) => item.id === commandeId);
        const lines = commande?.lignes || [];
        setRecForm((prev) => ({
            ...prev,
            commande_achat_id: value,
            produit_id: lines.length === 1 ? String(lines[0].produit_id) : '',
            quantite_recue: '',
        }));
    };

    const handleEditCmd = (commande) => {
        const lines = commande.lignes?.length
            ? commande.lignes.map((line) => ({
                produit_id: line.produit_id || '',
                quantite: line.quantite || 1,
                prix_unitaire_ht: line.prix_unitaire_ht || 0,
                taux_tva: line.taux_tva ?? 10,
            }))
            : [EMPTY_LINE()];

        setCmdForm({
            fournisseur_id: commande.fournisseur_id || '',
            date_commande: commande.date_commande ? commande.date_commande.slice(0, 10) : '',
            date_livraison_prevue: commande.date_livraison_prevue ? commande.date_livraison_prevue.slice(0, 10) : '',
            conditions_paiement: commande.conditions_paiement || '30 jours',
            remarque: commande.remarque || '',
        });
        setCmdLines(lines);
        setEditingId(commande.id);
        setTab('commandes');
    };

    const handleDelete = async (type, id) => {
        if (!window.confirm(type === 'commande' ? 'Supprimer cette commande d’achat ?' : 'Annuler cette réception ?')) return;
        const svc = type === 'commande' ? commandeAchatService : receptionService;
        try {
            await svc.delete(id);
            toast.success(type === 'commande' ? 'Commande supprimée' : 'Réception annulée');
            await fetchAll();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Erreur de suppression');
        }
    };

    if (loading && !commandes.length && !receptions.length) {
        return (
            <div className="page-container">
                <div className="loading-screen">
                    <div className="spinner-large" />
                    <p>Chargement des achats...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>Achats</h1>
                    <p>Commandez ce dont vous avez besoin, puis enregistrez ce qui est réellement reçu.</p>
                </div>
                <div className="tabs">
                    {['commandes', 'receptions'].map((value) => (
                        <button
                            key={value}
                            className={`tab-btn ${tab === value ? 'active' : ''}`}
                            onClick={() => { setTab(value); if (value === 'commandes') resetCommandForm(); }}
                        >
                            {value === 'commandes' ? 'Commandes' : 'Réceptions'}
                        </button>
                    ))}
                </div>
            </div>

            {tab === 'commandes' && (
                <>
                    <div className="card">
                        <h3>{editingId ? 'Modifier la commande d’achat' : 'Nouvelle commande d’achat'}</h3>
                        <p className="text-muted">Les totaux sont calculés automatiquement à partir des produits et quantités.</p>

                        <form onSubmit={handleSubmitCmd} className="form-grid">
                            <div className="form-group">
                                <label>Fournisseur *</label>
                                <select
                                    value={cmdForm.fournisseur_id}
                                    onChange={(e) => handleCommandChange('fournisseur_id', e.target.value)}
                                    required
                                >
                                    <option value="">Sélectionner un fournisseur</option>
                                    {fournisseurs.map((fournisseur) => (
                                        <option key={fournisseur.id} value={fournisseur.id}>
                                            {fournisseur.nom_complet || fournisseur.raison_sociale || fournisseur.nom || `Fournisseur #${fournisseur.id}`}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Date de commande</label>
                                <input type="date" value={cmdForm.date_commande} onChange={(e) => handleCommandChange('date_commande', e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label>Livraison prévue</label>
                                <input type="date" value={cmdForm.date_livraison_prevue} onChange={(e) => handleCommandChange('date_livraison_prevue', e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label>Conditions de paiement</label>
                                <input value={cmdForm.conditions_paiement} onChange={(e) => handleCommandChange('conditions_paiement', e.target.value)} placeholder="Ex. 30 jours" />
                            </div>

                            <div className="form-group full-width">
                                <label>Produits commandés</label>
                                <div className="table-container">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Produit</th>
                                                <th>Quantité</th>
                                                <th>Prix d’achat HT</th>
                                                <th>TVA</th>
                                                <th>Total HT</th>
                                                <th />
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {cmdLines.map((line, index) => {
                                                const qty = toNumber(line.quantite);
                                                const price = toNumber(line.prix_unitaire_ht);
                                                const total = qty * price;
                                                return (
                                                    <tr key={index}>
                                                        <td>
                                                            <select value={line.produit_id} onChange={(e) => updateLine(index, 'produit_id', e.target.value)} required>
                                                                <option value="">Produit</option>
                                                                {products.map((product) => (
                                                                    <option key={product.id} value={product.id}>
                                                                        {product.nom}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </td>
                                                        <td>
                                                            <input type="number" min="0.01" step="0.01" value={line.quantite} onChange={(e) => updateLine(index, 'quantite', e.target.value)} required />
                                                        </td>
                                                        <td>
                                                            <input type="number" min="0" step="0.01" value={line.prix_unitaire_ht} onChange={(e) => updateLine(index, 'prix_unitaire_ht', e.target.value)} required />
                                                        </td>
                                                        <td>
                                                            <input type="number" min="0" step="0.01" value={line.taux_tva} onChange={(e) => updateLine(index, 'taux_tva', e.target.value)} />
                                                        </td>
                                                        <td>{total.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} Ar</td>
                                                        <td>
                                                            <button type="button" className="btn-small btn-delete" title="Retirer" onClick={() => removeLine(index)} disabled={cmdLines.length === 1}>
                                                                <i className="ti ti-trash" aria-hidden="true" />
                                                            </button>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                                <button type="button" className="btn-secondary" onClick={addLine}>
                                    <i className="ti ti-plus" aria-hidden="true" /> Ajouter un produit
                                </button>
                            </div>

                            <div className="form-group full-width">
                                <div className="stats-row">
                                    <div className="stat-card">
                                        <div className="stat-label">Total HT</div>
                                        <div className="stat-value">{commandTotals.ht.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} Ar</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="stat-label">Total TTC</div>
                                        <div className="stat-value">{commandTotals.ttc.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} Ar</div>
                                    </div>
                                </div>
                            </div>

                            <div className="form-group full-width">
                                <label>Remarque</label>
                                <textarea value={cmdForm.remarque} onChange={(e) => handleCommandChange('remarque', e.target.value)} rows="2" />
                            </div>

                            <div className="form-group">
                                <button type="submit" className="btn-primary" disabled={submitting}>
                                    {submitting ? <span className="btn-spinner" /> : (editingId ? 'Enregistrer les modifications' : 'Créer la commande')}
                                </button>
                                {editingId && (
                                    <button type="button" className="btn-secondary" onClick={resetCommandForm} disabled={submitting}>
                                        Annuler
                                    </button>
                                )}
                            </div>
                        </form>
                    </div>

                    <div className="card">
                        <h3>Commandes enregistrées</h3>
                        <div className="table-container">
                            <table className="data-table">
                                <thead><tr><th>Référence</th><th>Fournisseur</th><th>Total HT</th><th>État</th><th>Actions</th></tr></thead>
                                <tbody>
                                    {!commandes.length ? (
                                        <tr><td colSpan="5" className="empty-row">Aucune commande</td></tr>
                                    ) : commandes.map((commande) => (
                                        <tr key={commande.id}>
                                            <td>{commande.reference}</td>
                                            <td>{commande.fournisseur_nom || '-'}</td>
                                            <td>{Number(commande.total_ht || 0).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} Ar</td>
                                            <td>{commande.statut || '-'}</td>
                                            <td>
                                                <button className="btn-small btn-edit" title="Modifier" onClick={() => handleEditCmd(commande)}>
                                                    <i className="ti ti-edit" aria-hidden="true" />
                                                </button>
                                                <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete('commande', commande.id)}>
                                                    <i className="ti ti-trash" aria-hidden="true" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}

            {tab === 'receptions' && (
                <>
                    <div className="card">
                        <h3>Réceptionner une commande</h3>
                        <p className="text-muted">Choisissez la commande, puis indiquez uniquement ce qui est réellement arrivé.</p>
                        <form onSubmit={handleSubmitRec} className="form-grid">
                            <div className="form-group">
                                <label>Commande *</label>
                                <select value={recForm.commande_achat_id} onChange={(e) => handleCommandeSelection(e.target.value)} required>
                                    <option value="">Sélectionner une commande</option>
                                    {commandes
                                        .filter((commande) => commande.statut !== 'recue' && commande.statut !== 'annulee')
                                        .map((commande) => (
                                            <option key={commande.id} value={commande.id}>
                                                {commande.reference} — {commande.fournisseur_nom || 'Fournisseur'}
                                            </option>
                                        ))}
                                </select>
                            </div>

                            {receptionLines.length > 1 && (
                                <div className="form-group">
                                    <label>Produit *</label>
                                    <select value={recForm.produit_id} onChange={(e) => setRecForm((prev) => ({ ...prev, produit_id: e.target.value, quantite_recue: '' }))} required>
                                        <option value="">Sélectionner le produit</option>
                                        {receptionLines.map((line) => (
                                            <option key={line.produit_id} value={line.produit_id}>
                                                {line.produit_nom || `Produit #${line.produit_id}`} — {line.quantite} commandé(s)
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {selectedReceptionLine && (
                                <div className="form-group">
                                    <label>Quantité commandée</label>
                                    <input value={selectedReceptionLine.quantite} readOnly />
                                </div>
                            )}

                            <div className="form-group">
                                <label>Quantité reçue *</label>
                                <input type="number" min="0.01" step="0.01" value={recForm.quantite_recue} onChange={(e) => setRecForm((prev) => ({ ...prev, quantite_recue: e.target.value }))} required />
                                {selectedReceptionLine && (
                                    <small className="text-muted">
                                        Le système calcule automatiquement ce qu’il reste à recevoir.
                                    </small>
                                )}
                            </div>

                            <div className="form-group">
                                <label>Référence fournisseur</label>
                                <input value={recForm.reference} onChange={(e) => setRecForm((prev) => ({ ...prev, reference: e.target.value }))} placeholder="Optionnel" />
                            </div>

                            <div className="form-group full-width">
                                <label>Remarque</label>
                                <textarea value={recForm.remarque} onChange={(e) => setRecForm((prev) => ({ ...prev, remarque: e.target.value }))} rows="2" />
                            </div>

                            <div className="form-group">
                                <button type="submit" className="btn-primary" disabled={submitting || !selectedCommande}>
                                    {submitting ? <span className="btn-spinner" /> : 'Enregistrer la réception'}
                                </button>
                            </div>
                        </form>
                    </div>

                    <div className="card">
                        <h3>Réceptions enregistrées</h3>
                        <div className="table-container">
                            <table className="data-table">
                                <thead><tr><th>Référence</th><th>Commande</th><th>Produit</th><th>Qté reçue</th><th>Qté commandée</th><th>Actions</th></tr></thead>
                                <tbody>
                                    {!receptions.length ? (
                                        <tr><td colSpan="6" className="empty-row">Aucune réception</td></tr>
                                    ) : receptions.map((reception) => (
                                        <tr key={reception.id}>
                                            <td>{reception.reference}</td>
                                            <td>{reception.commande_achat_id || '-'}</td>
                                            <td>{reception.produit?.nom || reception.produit_nom || (reception.produit_id ? `Produit #${reception.produit_id}` : '-')}</td>
                                            <td>{reception.quantite_recue}</td>
                                            <td>{reception.quantite_commandee}</td>
                                            <td>
                                                <button className="btn-small btn-delete" title="Annuler la réception" onClick={() => handleDelete('reception', reception.id)}>
                                                    <i className="ti ti-trash" aria-hidden="true" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
