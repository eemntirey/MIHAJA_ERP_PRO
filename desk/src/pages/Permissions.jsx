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
        toast.success('Permission mise à jour avec succès');
      } else {
        await permissionService.create(formData);
        toast.success('Permission créée avec succès');
      }
      fetchPermissions();
      closeModal();
    } catch (err) {
      console.error('Error saving permission:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde de la permission';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette permission ?')) {
      try {
        await permissionService.delete(id);
        toast.success('Permission supprimée avec succès');
        fetchPermissions();
      } catch (err) {
        console.error('Error deleting permission:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression de la permission';
        toast.error(msg);
      }
    }
  };

  const grouped = permissions.reduce((acc, perm) => {
    const module = perm.module || 'general';
    if (!acc[module]) acc[module] = [];
    acc[module].push(perm);
    return acc;
  }, {});

  if (loading && permissions.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des permissions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchPermissions} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Gestion des Permissions</h1>
          <p>Configurez les permissions disponibles dans le systeme</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => openModal()}>
            <i className="ti ti-plus" /> Nouvelle Permission
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Liste des permissions ({permissions.length})</h3>
          <div className="header-filters">
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <input
              type="text"
              placeholder="Filtrer par module..."
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              className="search-input"
            />
          </div>
        </div>
        <div className="card-body">
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
              {permissions.map(perm => (
                <tr key={perm.id}>
                  <td><code>{perm.code}</code></td>
                  <td>{perm.module || '-'}</td>
                  <td>{perm.action || '-'}</td>
                  <td>{perm.description || '-'}</td>
                  <td>
                    <button className="btn-sm btn-secondary" onClick={() => openModal(perm)}>
                      <i className="ti ti-edit" />
                    </button>
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(perm.id)}>
                      <i className="ti ti-trash" />
                    </button>
                  </td>
                </tr>
              ))}
              {permissions.length === 0 && (
                <tr>
                  <td colSpan="5" className="text-center text-muted">Aucune permission trouvee</td>
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
              <h2>{currentPermission ? 'Modifier la permission' : 'Nouvelle permission'}</h2>
              <button className="modal-close" onClick={closeModal}><i className="ti ti-x" /></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Code</label>
                  <input
                    type="text"
                    name="code"
                    value={formData.code}
                    onChange={handleChange}
                    required
                    placeholder="ex: product.view"
                    disabled={!!currentPermission}
                  />
                </div>
                <div className="form-group">
                  <label>Module</label>
                  <input
                    type="text"
                    name="module"
                    value={formData.module}
                    onChange={handleChange}
                    placeholder="ex: product"
                  />
                </div>
                <div className="form-group">
                  <label>Action</label>
                  <input
                    type="text"
                    name="action"
                    value={formData.action}
                    onChange={handleChange}
                    placeholder="ex: view, create, update, delete"
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
