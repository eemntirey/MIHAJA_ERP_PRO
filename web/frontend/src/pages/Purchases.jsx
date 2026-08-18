import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { commandeAchatService, receptionService } from '../services/api';
import './Pages.css';

export default function Purchases() {
    const [tab, setTab] = useState('commandes');
    const [commandes, setCommandes] = useState([]);
    const [receptions, setReceptions] = useState([]);
    const [loading, setLoading] = useState(false);

    const [cmdForm, setCmdForm] = useState({ fournisseur_id: '', total_ht: '', total_ttc: '', statut: 'brouillon', date_commande: '', date_livraison_prevue: '', conditions_paiement: '30 jours', lignes: '' });
    const [recForm, setRecForm] = useState({ commande_achat_id: '', reference: '', quantite_recue: '', quantite_commandee: '', remarque: '' });

    const [editingId, setEditingId] = useState(null);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [c, r] = await Promise.all([commandeAchatService.getAll(), receptionService.getAll()]);
            setCommandes(c.data.commandes || []);
            setReceptions(r.data.receptions || []);
        } catch (err) { toast.error('Erreur chargement'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    const handleSubmitCmd = async (e) => {
        e.preventDefault();
        try {
            let lignes = [];
            try { lignes = JSON.parse(cmdForm.lignes); } catch { toast.error('JSON invalide pour les lignes'); return; }
            const data = { ...cmdForm, fournisseur_id: Number(cmdForm.fournisseur_id), total_ht: Number(cmdForm.total_ht) || 0, total_ttc: Number(cmdForm.total_ttc) || 0, lignes };
            if (editingId) { await commandeAchatService.update(editingId, data); toast.success('Commande modifiée'); }
            else { await commandeAchatService.create(data); toast.success('Commande créée'); }
            setCmdForm({ fournisseur_id: '', total_ht: '', total_ttc: '', statut: 'brouillon', date_commande: '', date_livraison_prevue: '', conditions_paiement: '30 jours', lignes: '' });
            setEditingId(null); fetchAll();
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
    };

    const handleSubmitRec = async (e) => {
        e.preventDefault();
        try {
            const data = { ...recForm, commande_achat_id: Number(recForm.commande_achat_id), quantite_recue: Number(recForm.quantite_recue), quantite_commandee: Number(recForm.quantite_commandee) };
            await receptionService.create(data);
            toast.success('Réception créée');
            setRecForm({ commande_achat_id: '', reference: '', quantite_recue: '', quantite_commandee: '', remarque: '' });
            fetchAll();
        } catch (e) { toast.error(e.response?.data?.message || 'Erreur'); }
    };

    const handleEditCmd = (c) => {
        setCmdForm({
            fournisseur_id: c.fournisseur_id || '',
            total_ht: c.total_ht || '',
            total_ttc: c.total_ttc || '',
            statut: c.statut || 'brouillon',
            date_commande: c.date_commande ? c.date_commande.slice(0, 10) : '',
            date_livraison_prevue: c.date_livraison_prevue ? c.date_livraison_prevue.slice(0, 10) : '',
            conditions_paiement: c.conditions_paiement || '30 jours',
            lignes: c.lignes ? (Array.isArray(c.lignes) ? JSON.stringify(c.lignes) : c.lignes) : '',
        });
        setEditingId(c.id);
    };

    const handleDelete = async (type, id) => {
        if (!window.confirm('Supprimer ?')) return;
        const svc = type === 'commande' ? commandeAchatService : receptionService;
        try {
            await svc.delete(id);
            toast.success('Supprimé');
            fetchAll();
        } catch (e) {
            toast.error(e.response?.data?.message || 'Erreur de suppression');
        }
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <h1>Achats</h1>
                <div className="tabs">
                    {['commandes', 'receptions'].map(t => (
                        <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => { setTab(t); setEditingId(null); }}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
                    ))}
                </div>
            </div>

            {tab === 'commandes' && (
                <div className="card">
                    <h3>{editingId ? 'Modifier la commande d\'achat' : 'Nouvelle commande d\'achat'}</h3>
                    <form onSubmit={handleSubmitCmd} className="form-grid">
                        <div className="form-group">
                            <label>Fournisseur ID *</label>
                            <input type="number" value={cmdForm.fournisseur_id} onChange={e => setCmdForm({...cmdForm, fournisseur_id: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Total HT</label>
                            <input type="number" value={cmdForm.total_ht} onChange={e => setCmdForm({...cmdForm, total_ht: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Total TTC</label>
                            <input type="number" value={cmdForm.total_ttc} onChange={e => setCmdForm({...cmdForm, total_ttc: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Statut</label>
                            <select value={cmdForm.statut} onChange={e => setCmdForm({...cmdForm, statut: e.target.value})}>
                                <option value="brouillon">Brouillon</option>
                                <option value="envoyee">Envoyée</option>
                                <option value="confirmee">Confirmée</option>
                                <option value="recue">Reçue</option>
                                <option value="partiellement_recue">Partiellement reçue</option>
                                <option value="annulee">Annulée</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Date de commande</label>
                            <input type="date" value={cmdForm.date_commande} onChange={e => setCmdForm({...cmdForm, date_commande: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Date de livraison prévue</label>
                            <input type="date" value={cmdForm.date_livraison_prevue} onChange={e => setCmdForm({...cmdForm, date_livraison_prevue: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <label>Conditions de paiement</label>
                            <input value={cmdForm.conditions_paiement} onChange={e => setCmdForm({...cmdForm, conditions_paiement: e.target.value})} />
                        </div>
                        <div className="form-group full-width">
                            <label>Lignes JSON</label>
                            <textarea value={cmdForm.lignes} onChange={e => setCmdForm({...cmdForm, lignes: e.target.value})} rows={2} />
                        </div>
                        <div className="form-group">
                            <button type="submit" className="btn-primary">{editingId ? 'Modifier' : 'Créer'}</button>
                            {editingId && <button type="button" className="btn-secondary" onClick={() => { setEditingId(null); setCmdForm({ fournisseur_id: '', total_ht: '', total_ttc: '', statut: 'brouillon', date_commande: '', date_livraison_prevue: '', conditions_paiement: '30 jours', lignes: '' }); }}>Annuler</button>}
                        </div>
                    </form>
                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Référence</th><th>Fournisseur</th><th>Total HT</th><th>Statut</th><th>Actions</th></tr></thead>
                        <tbody>{commandes.length === 0 ? <tr><td colSpan="5" className="empty-row">Aucune commande</td></tr> : commandes.map(c => <tr key={c.id}><td>{c.reference}</td><td>{c.fournisseur_nom}</td><td>{c.total_ht}</td><td><span className={`badge ${c.statut}`}>{c.statut}</span></td><td><button className="btn-small btn-edit" onClick={() => handleEditCmd(c)}>Modifier</button> <button className="btn-small btn-danger" onClick={() => handleDelete('commande', c.id)}>Supprimer</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}

            {tab === 'receptions' && (
                <div className="card">
                    <h3>Nouvelle réception</h3>
                    <form onSubmit={handleSubmitRec} className="form-grid">
                        <div className="form-group">
                            <label>Commande *</label>
                            <select value={recForm.commande_achat_id} onChange={e => setRecForm({...recForm, commande_achat_id: e.target.value})} required>
                                <option value="">Commande</option>
                                {commandes.map(c => <option key={c.id} value={c.id}>{c.reference}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Référence *</label>
                            <input value={recForm.reference} onChange={e => setRecForm({...recForm, reference: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Quantité reçue *</label>
                            <input type="number" value={recForm.quantite_recue} onChange={e => setRecForm({...recForm, quantite_recue: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Quantité commandée *</label>
                            <input type="number" value={recForm.quantite_commandee} onChange={e => setRecForm({...recForm, quantite_commandee: e.target.value})} required />
                        </div>
                        <div className="form-group">
                            <label>Remarque</label>
                            <textarea value={recForm.remarque} onChange={e => setRecForm({...recForm, remarque: e.target.value})} />
                        </div>
                        <div className="form-group">
                            <button type="submit" className="btn-primary">Créer</button>
                        </div>
                    </form>
                    <div className="table-container">
                        <table className="data-table"><thead><tr><th>Référence</th><th>Commande</th><th>Qté reçue</th><th>Qté cmd</th><th>Actions</th></tr></thead>
                        <tbody>{receptions.length === 0 ? <tr><td colSpan="5" className="empty-row">Aucune réception</td></tr> : receptions.map(r => <tr key={r.id}><td>{r.reference}</td><td>{r.commande_achat_id}</td><td>{r.quantite_recue}</td><td>{r.quantite_commandee}</td><td><button className="btn-small btn-danger" onClick={() => handleDelete('reception', r.id)}>Supprimer</button></td></tr>)}</tbody></table>
                    </div>
                </div>
            )}
        </div>
    );
}
