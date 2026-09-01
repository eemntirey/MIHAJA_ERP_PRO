// src/pages/Permissions.jsx
import React, { useState, useEffect } from 'react';
import { permissionService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Permissions = () => {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentPermission, setCurrentPermission] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    description: '',
    module: '',
    action: '',
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');

  const fetchPermissions = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (moduleFilter) params.module = moduleFilter;
      const response = await permissionService.getAll(params);
      setPermissions(response.data?.permissions || response.data || []);
    } catch (err) {
      console.error('Error fetching permissions:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des permissions';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPermissions();
  }, []);

  useEffect(() => {
    fetchPermissions();
  }, [searchTerm, moduleFilter]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const openModal = (permission = null) => {
    setCurrentPermission(permission);
    if (permission) {
      setFormData({
        code: permission.code || '',
        description: permission.description || '',
        module: permission.module || '',
        action: permission.action || '',
      });
    } else {
      setFormData({
        code: '',
        description: '',
        module: '',
        action: '',
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentPermission(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (currentPermission) {
        await permissionService.update(currentPermission.id, formData);
        toast.success('Permission mise à jour');
      } else {
        await permissionService.create(formData);
        toast.success('Permission créée');
      }
      closeModal();
      fetchPermissions();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de l\'enregistrement';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette permission ?')) return;
    try {
      await permissionService.delete(id);
      toast.success('Permission supprimée');
      fetchPermissions();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la suppression';
      toast.error(msg);
    }
  };

  const modules = Array.from(new Set(permissions.map(p => p.module).filter(Boolean)));

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Permissions</h1>
        <button className="btn-primary" onClick={() => openModal()}>
          Nouvelle permission
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
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="form-select"
        >
          <option value="">Tous les modules</option>
          {modules.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {error && <div className="alert error">{error}</div>}

      {loading ? (
        <div className="loading">Chargement...</div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Module</th>
                <th>Action</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {permissions.map((p) => (
                <tr key={p.id}>
                  <td>{p.code}</td>
                  <td>{p.module}</td>
                  <td>{p.action}</td>
                  <td>{p.description}</td>
                  <td>
                    <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal(p)}>
                      <i className="ti ti-edit" aria-hidden="true" />
                    </button>
                    <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete(p.id)}>
                      <i className="ti ti-trash" aria-hidden="true" />
                    </button>
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
              <h2>{currentPermission ? 'Modifier' : 'Nouvelle'} permission</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label>Code</label>
                    <input type="text" name="code" value={formData.code} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Module</label>
                    <input type="text" name="module" value={formData.module} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Action</label>
                    <input type="text" name="action" value={formData.action} onChange={handleChange} required />
                  </div>
                  <div className="form-group full-width">
                    <label>Description</label>
                    <textarea name="description" value={formData.description} onChange={handleChange} rows={3} />
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

export default Permissions;
