// src/pages/Profile.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { authService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import ConfirmModal from '../components/common/ConfirmModal';
import './Pages.css';

const Profile = () => {
    const { user, setUser, tenant, logout } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showChangeAccountModal, setShowChangeAccountModal] = useState(false);
    const [changingAccount, setChangingAccount] = useState(false);
    const [formData, setFormData] = useState({
        nom: '',
        prenom: '',
        email: '',
        telephone: '',
        mobile: '',
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                setLoading(true);
                const response = await authService.getCurrentUser();
                const data = response.data?.user || response.data || {};
                setFormData({
                    nom: data.nom || '',
                    prenom: data.prenom || '',
                    email: data.email || '',
                    telephone: data.telephone || '',
                    mobile: data.mobile || '',
                });
            } catch (err) {
                console.error('Error fetching profile:', err);
                if (err.response?.status !== 403) {
                    const msg = err.response?.data?.message || 'Échec du chargement du profil';
                    toast.error(msg);
                }
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            setSaving(true);
            const response = await authService.updateMe(formData);
            const updated = response.data?.user || response.data || {};
            const mergedUser = { ...(user || {}), ...updated };
            setUser(mergedUser);
            toast.success('Profil mis à jour');
        } catch (err) {
            console.error('Error updating profile:', err);
            if (err.response?.status !== 403) {
                const msg = err.response?.data?.message || 'Échec de la mise à jour';
                toast.error(msg);
            }
        } finally {
            setSaving(false);
        }
    };

    const openChangeAccountModal = () => {
        setShowChangeAccountModal(true);
    };

    const closeChangeAccountModal = () => {
        if (changingAccount) return;
        setShowChangeAccountModal(false);
    };

    const confirmChangeAccount = async () => {
        try {
            setChangingAccount(true);
            await logout();
        } catch {
            // logout best-effort
        } finally {
            setShowChangeAccountModal(false);
            setChangingAccount(false);
            navigate('/login', { replace: true });
        }
    };

    if (loading) {
        return (
            <div className="page-container">
                <div className="loading-screen">
                    <div className="spinner-large"></div>
                    <p>Chargement du profil...</p>
                </div>
            </div>
        );
    }

    const role = (user?.role || '').toLowerCase();
    const tenantInfo = tenant || user?.tenant || null;

    return (
        <>
        <div className="page-container">
            <div className="page-header">
                <div>
                    <h1>Mon profil</h1>
                    <p>Consulter et modifier mes informations</p>
                </div>
            </div>

            <div className="card full-width" style={{ maxWidth: '900px', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '16px', marginBottom: '12px' }}>Informations du compte</h2>
                <div className="form-grid">
                    <div className="form-group">
                        <label>Rôle</label>
                        <input value={role || '-'} disabled readOnly />
                    </div>
                    <div className="form-group">
                        <label>Identifiant</label>
                        <input value={user?.username || user?.email || '-'} disabled readOnly />
                    </div>
                    {tenantInfo && (
                        <>
                            <div className="form-group full-width">
                                <label>Entreprise</label>
                                <input value={tenantInfo.nom || '-'} disabled readOnly />
                            </div>
                            <div className="form-group">
                                <label>Email entreprise</label>
                                <input value={tenantInfo.email_contact || '-'} disabled readOnly />
                            </div>
                            <div className="form-group">
                                <label>Téléphone entreprise</label>
                                <input value={tenantInfo.telephone || '-'} disabled readOnly />
                            </div>
                            <div className="form-group">
                                <label>Pays</label>
                                <input value={tenantInfo.pays || '-'} disabled readOnly />
                            </div>
                            <div className="form-group">
                                <label>Ville</label>
                                <input value={tenantInfo.ville || '-'} disabled readOnly />
                            </div>
                        </>
                    )}
                </div>
            </div>

            <form onSubmit={handleSubmit} className="card" style={{ maxWidth: '900px' }}>
                <h2 style={{ fontSize: '16px', marginBottom: '12px' }}>Informations personnelles</h2>
                <div className="form-grid">
                    <div className="form-group">
                        <label htmlFor="nom">Nom</label>
                        <input id="nom" name="nom" value={formData.nom} onChange={handleChange} />
                    </div>
                    <div className="form-group">
                        <label htmlFor="prenom">Prénom</label>
                        <input id="prenom" name="prenom" value={formData.prenom} onChange={handleChange} />
                    </div>
                    <div className="form-group full-width">
                        <label htmlFor="email">Email</label>
                        <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} />
                    </div>
                    <div className="form-group">
                        <label htmlFor="telephone">Téléphone</label>
                        <input id="telephone" name="telephone" value={formData.telephone} onChange={handleChange} />
                    </div>
                    <div className="form-group">
                        <label htmlFor="mobile">Mobile</label>
                        <input id="mobile" name="mobile" value={formData.mobile} onChange={handleChange} />
                    </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginTop: '24px', flexWrap: 'wrap' }}>
                    <button type="button" className="btn-secondary" onClick={openChangeAccountModal}>
                        <i className="ti ti-switch-horizontal" aria-hidden="true" /> Changer de compte
                    </button>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <Link to="/dashboard" className="btn-secondary">Annuler</Link>
                        <button type="submit" className="btn-primary" disabled={saving}>
                            {saving ? 'Enregistrement...' : 'Enregistrer'}
                        </button>
                    </div>
                </div>
            </form>
        </div>

        {showChangeAccountModal && (
            <ConfirmModal
                title="Changer de compte ?"
                message="Vous allez etre deconnecte de votre session actuelle. Vous pourrez vous reconnecter avec un autre compte immediatement."
                warning="Toute modification non enregistree sur votre profil sera perdue."
                confirmText={changingAccount ? 'Deconnexion...' : 'Oui, changer de compte'}
                cancelText="Annuler"
                confirmClass="btn-danger"
                onCancel={closeChangeAccountModal}
                onConfirm={confirmChangeAccount}
            />
        )}
        </>
    );
};

export default Profile;