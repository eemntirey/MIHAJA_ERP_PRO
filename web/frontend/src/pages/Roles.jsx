// src/pages/Roles.jsx
import React, { useState, useEffect } from 'react';
import { roleService, permissionService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Roles = () => {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentRole, setCurrentRole] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    is_default: false,
    is_system: false,
    permission_ids: [],
  });
  const [searchTerm, setSearchTerm] = useState('');

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

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
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

  const togglePermission = (permId) => {
    setFormData(prev => ({
      ...prev,
      permission_ids: prev.permission_ids.includes(permId)
        ? prev.permission_ids.filter(id => id !== permId)
        : [...prev.permission_ids, permId],
    }));
  };

  const openModal = (role = null) => {
    setCurrentRole(role);
    if (role) {
      setFormData({
        name: role.name || '',
        display_name: role.display_name || '',
        description: role.description || '',
        is_default: !!role.is_default,
        is_system: !!role.is_system,
        permission_ids: role.permissions?.map(p => p.id) || [],
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
      const msg = err.response?.data?.message || 'Erreur lors de l\'enregistrement';
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

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Rôles</h1>
        <button className="btn-primary" onClick={() => openModal()}>
          Nouveau rôle
        </button>
      </div>

      <div className="filter-controls">
        <div className="search-box">
          <i className="ti ti-search search-icon" aria-hidden="true" />
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      {loading ? (
        <div className="loading">Chargement...</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Affichage</th>
                <th>Description</th>
                <th>Système</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.display_name}</td>
                  <td>{r.description}</td>
                  <td>{r.is_system ? 'Oui' : 'Non'}</td>
                  <td>
                    <button className="btn-small" onClick={() => openModal(r)}>Modifier</button>
                    {!r.is_system && (
                      <button className="btn-small btn-danger" onClick={() => handleDelete(r.id)}>Supprimer</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{currentRole ? 'Modifier' : 'Nouveau'} rôle</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label>Nom (code)</label>
                    <input type="text" name="name" value={formData.name} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Nom affiché</label>
                    <input type="text" name="display_name" value={formData.display_name} onChange={handleChange} required />
                  </div>
                  <div className="form-group full-width">
                    <label>Description</label>
                    <textarea name="description" value={formData.description} onChange={handleChange} rows={3} />
                  </div>
                  <div className="form-group">
                    <label>
                      <input type="checkbox" name="is_default" checked={formData.is_default} onChange={handleChange} />
                      Défaut
                    </label>
                  </div>
                  <div className="form-group">
                    <label>
                      <input type="checkbox" name="is_system" checked={formData.is_system} onChange={handleChange} />
                      Système
                    </label>
                  </div>
                </div>
                <div className="form-section">
                  <h3>Permissions</h3>
                  <div className="permissions-grid">
                    {permissions.map((p) => (
                      <label key={p.id} className="permission-item">
                        <input
                          type="checkbox"
                          checked={formData.permission_ids.includes(p.id)}
                          onChange={() => togglePermission(p.id)}
                        />
                        <span>{p.code} - {p.description}</span>
                      </label>
                    ))}
                  </div>
                </div>
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
