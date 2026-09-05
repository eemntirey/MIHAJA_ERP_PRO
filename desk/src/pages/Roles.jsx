// src/pages/Roles.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { roleService, permissionService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const PRESET_LABELS = {
  super_admin: 'Super Admin',
  admin: 'Admin',
  manager: 'Manager',
  sales: 'Commercial',
  stock: 'Stock',
  accountant: 'Comptable',
  rh: 'RH',
  user: 'Utilisateur',
};

const Roles = () => {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentRole, setCurrentRole] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    is_default: false,
    is_system: false,
    permission_ids: [],
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [permSearch, setPermSearch] = useState('');

  const fetchRoles = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await roleService.getAll({ search: searchTerm });
      setRoles(response.data?.roles || response.data || []);
    } catch (err) {
      console.error('Error fetching roles:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des rôles';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await permissionService.getAll({});
      setPermissions(response.data?.permissions || response.data || []);
    } catch (err) {
      console.error('Error fetching permissions:', err);
    }
  };

  const fetchPresets = async () => {
    try {
      const response = await roleService.getPresets();
      setPresets(response.data?.presets || []);
    } catch (err) {
      console.error('Error fetching presets:', err);
    }
  };

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
    fetchPresets();
  }, []);

  useEffect(() => {
    fetchRoles();
  }, [searchTerm]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handlePresetChange = (e) => {
    const presetName = e.target.value;
    setSelectedPreset(presetName);
    if (!presetName) {
      setFormData(prev => ({ ...prev, permission_ids: [] }));
      return;
    }
    const preset = presets.find(p => p.name === presetName);
    if (preset) {
      setFormData(prev => ({
        ...prev,
        permission_ids: preset.permission_ids || [],
        name: currentRole ? prev.name : presetName,
        display_name: currentRole ? prev.display_name : (PRESET_LABELS[presetName] || presetName),
        is_system: !currentRole ? true : prev.is_system,
      }));
    }
  };

  const togglePermission = (permId) => {
    setFormData(prev => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permId)
        ? prev.permission_ids.filter(id => id !== permId)
        : [...prev.permission_ids, permId],
    }));
  };

  const groupedPermissions = permissions.reduce((acc, perm) => {
    const module = perm.module || 'general';
    if (!acc[module]) acc[module] = [];
    acc[module].push(perm);
    return acc;
  }, {});

  const filteredGroupedPermissions = useMemo(() => {
    const q = permSearch.trim().toLowerCase();
    if (!q) return groupedPermissions;
    const result = {};
    Object.entries(groupedPermissions).forEach(([module, perms]) => {
      const matched = perms.filter(
        p => p.code.toLowerCase().includes(q) || module.toLowerCase().includes(q)
      );
      if (matched.length) result[module] = matched;
    });
    return result;
  }, [groupedPermissions, permSearch]);

  const formatDescription = (text) =>
    (text || '')
      .replace(/([a-zà-ÿ])([A-Z])/g, '$1 $2')
      .replace(/([.!?])([A-ZÀ-Ú])/g, '$1 $2')
      .replace(/\s+/g, ' ')
      .trim();

  const openModal = (role = null) => {
    setCurrentRole(role);
    setSelectedPreset('');
    setPermSearch('');
    if (role) {
      setFormData({
        name: role.name || '',
        display_name: role.display_name || role.name || '',
        description: formatDescription(role.description),
        is_default: role.is_default || false,
        is_system: role.is_system || false,
        permission_ids: (role.permissions || []).map(p => p.id),
      });
    } else {
      setFormData({
        name: '',
        display_name: '',
        description: '',
        is_default: false,
        is_system: false,
        permission_ids: [],
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentRole(null);
    setSelectedPreset('');
    setPermSearch('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentRole) {
        await roleService.update(currentRole.id, formData);
        toast.success('Rôle mis à jour');
      } else {
        await roleService.create(formData);
        toast.success('Rôle créé');
      }
      closeModal();
      fetchRoles();
    } catch (err) {
      const msg = err.response?.data?.message || "Erreur lors de l'enregistrement";
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce rôle ?')) return;
    try {
      await roleService.delete(id);
      toast.success('Rôle supprimé');
      fetchRoles();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la suppression';
      toast.error(msg);
    }
  };

  if (loading && roles.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des rôles...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchRoles} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Gestion des Rôles</h1>
          <p>Configurez les rôles et leurs permissions</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => openModal()}>
            <i className="ti ti-plus" /> Nouveau rôle
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Liste des rôles ({roles.length})</h3>
          <input
            type="text"
            placeholder="Rechercher un rôle..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="card-body">
          <table className="data-table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Description</th>
                  <th>Défaut</th>
                  <th>Système</th>
                  <th>Permissions</th>
                  <th>Actions</th>
                </tr>
              </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.display_name || r.name}</strong></td>
                  <td>{r.description || '-'}</td>
                  <td>
                    <span className={`badge ${r.is_default ? 'info' : 'light'}`}>
                      {r.is_default ? 'Oui' : 'Non'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${r.is_system ? 'danger' : 'success'}`}>
                      {r.is_system ? 'Système' : 'Custom'}
                    </span>
                  </td>
                  <td>{r.permissions?.length || 0} permissions</td>
                  <td>
                    <button className="btn-small btn-secondary" title="Modifier" onClick={() => openModal(r)}>
                      <i className="ti ti-edit" />
                    </button>
                    {!r.is_system && (
                      <button className="btn-small btn-danger" title="Supprimer" onClick={() => handleDelete(r.id)}>
                        <i className="ti ti-trash" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {roles.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted">Aucun rôle trouvé</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal large role-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>{currentRole ? 'Modifier le rôle' : 'Nouveau rôle'}</h2>
                <button className="modal-close" onClick={closeModal} aria-label="Fermer"><i className="ti ti-x" /></button>
              </div>
            <form onSubmit={handleSubmit} className="role-modal-form">
              <div className="modal-body">
                <section className="info-section">
                  <h3 className="section-title">Informations du rôle</h3>

                  {!currentRole && (
                    <div className="form-group full-width">
                      <label>Preset de rôle</label>
                      <select value={selectedPreset} onChange={handlePresetChange} className="form-select">
                        <option value="">-- Sélectionner un preset --</option>
                        {presets.map(p => (
                          <option key={p.name} value={p.name}>{p.display_name || p.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="form-grid">
                    <div className="form-group">
                      <label>Nom du code</label>
                      <input type="text" name="name" value={formData.name} onChange={handleChange} required disabled={!!currentRole} placeholder="manager" />
                    </div>
                    <div className="form-group">
                      <label>Nom affiché</label>
                      <input type="text" name="display_name" value={formData.display_name} onChange={handleChange} required placeholder="Manager" />
                    </div>
                  </div>

                  <div className="form-group full-width">
                    <label>Description</label>
                    <textarea name="description" value={formData.description} onChange={handleChange} rows={3} placeholder="Description courte du rôle..." />
                  </div>

                  <div className="role-flags">
                    <label className="role-flag">
                      <input type="checkbox" name="is_default" checked={formData.is_default} onChange={handleChange} />
                      <span className="role-flag-text">
                        <span className="role-flag-title">Rôle par défaut</span>
                        <span className="role-flag-desc">Ce rôle sera utilisé par défaut pour les nouveaux utilisateurs.</span>
                      </span>
                    </label>
                    <label className="role-flag">
                      <input type="checkbox" name="is_system" checked={formData.is_system} onChange={handleChange} />
                      <span className="role-flag-text">
                        <span className="role-flag-title">Rôle système</span>
                        <span className="role-flag-desc">Ce rôle est protégé par le système.</span>
                      </span>
                    </label>
                  </div>
                </section>

                <section className="perm-section">
                  <div className="perm-section-head">
                    <h3 className="section-title">Permissions</h3>
                    <div className="perm-search">
                      <i className="ti ti-search" />
                      <input
                        type="text"
                        placeholder="Rechercher une permission..."
                        value={permSearch}
                        onChange={(e) => setPermSearch(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="permissions-grid">
                    {Object.entries(filteredGroupedPermissions).map(([module, perms]) => (
                      <div key={module} className="permission-group">
                        <h4>{module}</h4>
                        {perms.map(perm => (
                          <label key={perm.id} className="checkbox-label">
                            <input
                              type="checkbox"
                              checked={formData.permission_ids.includes(perm.id)}
                              onChange={() => togglePermission(perm.id)}
                            />
                            <span>{perm.code}</span>
                          </label>
                        ))}
                      </div>
                    ))}
                    {Object.keys(filteredGroupedPermissions).length === 0 && (
                      <p className="perm-empty">Aucune permission trouvée.</p>
                    )}
                  </div>
                </section>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal}>Annuler</button>
                <button type="submit" className="btn-primary">Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Roles;
