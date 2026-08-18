// src/pages/Roles.jsx
import React, { useState, useEffect } from 'react';
import { roleService, permissionService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const ROLES_API_BASE = '/api/v1';

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
      const msg = err.response?.data?.message || 'Échec du chargement des roles';
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
        display_name: role.display_name || role.name || '',
        description: role.description || '',
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
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentRole) {
        await roleService.update(currentRole.id, formData);
        toast.success('Role mis à jour avec succès');
      } else {
        await roleService.create(formData);
        toast.success('Role créé avec succès');
      }
      fetchRoles();
      closeModal();
    } catch (err) {
      console.error('Error saving role:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde du role';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce role ? Cette action est irréversible.')) {
      try {
        await roleService.delete(id);
        toast.success('Role supprimé avec succès');
        fetchRoles();
      } catch (err) {
        console.error('Error deleting role:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression du role';
        toast.error(msg);
      }
    }
  };

  const groupedPermissions = permissions.reduce((acc, perm) => {
    const module = perm.module || 'general';
    if (!acc[module]) acc[module] = [];
    acc[module].push(perm);
    return acc;
  }, {});

  if (loading && roles.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des roles...</p>
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
          <h1>Gestion des Roles</h1>
          <p>Configurez les roles et leurs permissions</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => openModal()}>
            <i className="ti ti-plus" /> Nouveau Role
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Liste des roles ({roles.length})</h3>
          <input
            type="text"
            placeholder="Rechercher un role..."
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
                <th>Systeme</th>
                <th>Permissions</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {roles.map(role => (
                <tr key={role.id}>
                  <td><strong>{role.display_name || role.name}</strong></td>
                  <td>{role.description || '-'}</td>
                  <td>
                    <span className={`badge ${role.is_system ? 'badge--danger' : 'badge--success'}`}>
                      {role.is_system ? 'Systeme' : 'Custom'}
                    </span>
                  </td>
                  <td>{role.permissions?.length || 0} permissions</td>
                  <td>
                    <button className="btn-sm btn-secondary" onClick={() => openModal(role)}>
                      <i className="ti ti-edit" />
                    </button>
                    {!role.is_system && (
                      <button className="btn-sm btn-danger" onClick={() => handleDelete(role.id)}>
                        <i className="ti ti-trash" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {roles.length === 0 && (
                <tr>
                  <td colSpan="5" className="text-center text-muted">Aucun role trouve</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{currentRole ? 'Modifier le role' : 'Nouveau role'}</h2>
              <button className="modal-close" onClick={closeModal}><i className="ti ti-x" /></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Nom technique</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    disabled={!!currentRole}
                  />
                </div>
                <div className="form-group">
                  <label>Nom affiche</label>
                  <input
                    type="text"
                    name="display_name"
                    value={formData.display_name}
                    onChange={handleChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows="3"
                  />
                </div>
                <div className="form-group">
                  <label>Permissions</label>
                  <div className="permissions-grid">
                    {Object.entries(groupedPermissions).map(([module, perms]) => (
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
