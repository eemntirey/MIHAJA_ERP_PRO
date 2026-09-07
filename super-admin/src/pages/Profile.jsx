import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useSuperAdminAuth } from '../contexts/SuperAdminAuthContext';
import { superAdminAuthService } from '../services/api';

const VILLES_MADAGASCAR_LIST = [
  'Antananarivo', 'Antsirabe', 'Fianarantsoa', 'Mahajanga', 'Toamasina',
  'Toliara', 'Antsiranana', 'Morondava', 'Ambovombe', 'Farafangana',
  'Manakara', 'Maroantsetra', 'Port-Bergé', 'Sambava', 'Antalaha',
  'Ihosy', 'Ivohibe', 'Mananjary', 'Nosy Be', 'Saint-Marie',
];

const Profile = () => {
  const { user, updateProfile } = useSuperAdminAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    nom: '',
    prenom: '',
    email: '',
    telephone: '',
    adresse: '',
    ville: '',
    code_postal: '',
    pays: 'Madagascar',
  });

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await superAdminAuthService.getMe();
      const data = response.data?.user || response.data;
      setFormData({
        nom: data.nom || '',
        prenom: data.prenom || '',
        email: data.email || '',
        telephone: data.telephone || '',
        adresse: data.adresse || '',
        ville: data.ville || '',
        code_postal: data.code_postal || '',
        pays: data.pays || 'Madagascar',
      });
    } catch {
      toast.error('Échec du chargement du profil');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
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
      const response = await superAdminAuthService.updateMe(formData);
      const updated = response.data?.user || response.data || {};
      updateProfile(updated);
      toast.success('Profil mis à jour');
    } catch {
      toast.error('Échec de la mise à jour');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner-large"></div>
        <p>Chargement du profil...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Mon profil</h1>
          <p>Modifier vos informations personnelles</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ maxWidth: '800px', width: '100%' }}>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="nom">Nom</label>
            <input id="nom" name="nom" value={formData.nom} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="prenom">Prénom</label>
            <input id="prenom" name="prenom" value={formData.prenom} onChange={handleChange} required />
          </div>
          <div className="form-group full-width">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="telephone">Téléphone</label>
            <input id="telephone" name="telephone" value={formData.telephone} onChange={handleChange} />
          </div>
          <div className="form-group full-width">
            <label htmlFor="adresse">Adresse</label>
            <input id="adresse" name="adresse" value={formData.adresse} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label htmlFor="code_postal">Code postal</label>
            <input id="code_postal" name="code_postal" value={formData.code_postal} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label htmlFor="pays">Pays</label>
            <select id="pays" name="pays" value={formData.pays} onChange={handleChange}>
              <option value="Madagascar">Madagascar</option>
              <option value="Comores">Comores</option>
              <option value="Maurice">Maurice</option>
              <option value="Seychelles">Seychelles</option>
              <option value="Tanzanie">Tanzanie</option>
              <option value="Kenya">Kenya</option>
              <option value="Mozambique">Mozambique</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="ville">Ville</label>
            <select id="ville" name="ville" value={formData.ville} onChange={handleChange}>
              <option value="">Sélectionnez une ville</option>
              {VILLES_MADAGASCAR_LIST.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <button type="button" className="btn-secondary" onClick={() => window.history.back()}>Annuler</button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Enregistrement...' : 'Enregistrer'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Profile;
