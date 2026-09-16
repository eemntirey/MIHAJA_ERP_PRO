// src/pages/Permissions.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { permissionService, roleService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-toastify';
import './Pages.css';

const Permissions = () => {
  const { user } = useAuth();
  const userRole = (user?.role || '').toLowerCase();
  const isTenantAdmin = userRole === 'admin';
  const [permissions, setPermissions] = useState([]);
  const [roles, setRoles] = useState([]);
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
  const [roleFilter, setRoleFilter] = useState('');

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

  const fetchRoles = async () => {
    try {
      const response = await roleService.getAll({});
      setRoles(response.data?.roles || response.data || []);
    } catch (err) {
      console.error('Error fetching roles:', err);
    }
  };

  useEffect(() => {
    fetchPermissions();
    fetchRoles();
  }, []);

  useEffect(() => {
    fetchPermissions();
  }, [searchTerm, moduleFilter]);

  // Filtre par défaut : affiche les permissions de l'utilisateur connecté (admin = ses perms)
  // Si tenant/admin, montre directement son rôle au lieu de 'admin_empl' vide si roles pas encore chargés
  useEffect(() => {
    if (!roles.length || roleFilter) return;
    if (userRole && roles.some(r => r.name === userRole)) {
      setRoleFilter(userRole);
    } else if (isTenantAdmin) {
      setRoleFilter('admin');
    }
  }, [roles, roleFilter, userRole, isTenantAdmin]);

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

  // Map permission code -> roles qui la possèdent
  const permissionRolesMap = useMemo(() => {
    const map = {};
    roles.forEach(r => {
      (r.permissions || []).forEach(p => {
        if (!map[p.code]) map[p.code] = [];
        map[p.code].push(r.name);
      });
    });
    return map;
  }, [roles]);

  const adminRole = useMemo(() => roles.find(r => r.name === 'admin'), [roles]);
  const adminPermissionsCount = adminRole?.permissions?.length || 0;

  const filteredPermissions = useMemo(() => {
    if (!roleFilter) return permissions;
    if (roleFilter === 'admin_empl') {
      const adminCodes = new Set((roles.find(r => r.name === 'admin')?.permissions || []).map(p => p.code));
      const tenantCodes = new Set();
      roles.filter(r => r.name !== 'super_admin' && r.name !== 'admin').forEach(r => {
        (r.permissions || []).forEach(p => tenantCodes.add(p.code));
      });
      const combined = new Set([...adminCodes, ...tenantCodes]);
      // Fallback : si roles pas encore chargés ou custom rôle vide, afficher au moins les perms admin ou tout
      if (combined.size === 0) return permissions;
      return permissions.filter(p => combined.has(p.code));
    }
    const role = roles.find(r => r.name === roleFilter);
    if (!role) return permissions;
    const codes = new Set((role.permissions || []).map(p => p.code));
    if (codes.size === 0) return permissions;
    return permissions.filter(p => codes.has(p.code));
  }, [permissions, roleFilter, roles]);

  const displayedPermissions = filteredPermissions;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Permissions</h1>
          <p className="text-muted">
            {isTenantAdmin
              ? `Filtre Admin + Employés — ${displayedPermissions.length} permissions affichées`
              : `${permissions.length} permissions système — filtre Admin + Employés (${displayedPermissions.length})`}
          </p>
        </div>
        <button className="btn-primary" onClick={() => openModal()}>
          + Nouvelle permission
        </button>
      </div>

      {/* Résumé pour admin / tenant inscrit / employés */}
      {adminRole && (
        <div className="card" style={{ padding: '12px 16px', marginBottom: '16px', background: 'var(--color-surface)' }}>
          <strong>Admin + Employés (Tenant)</strong> — affichage combiné des permissions admin et des rôles du tenant inscrit &nbsp;
          <span className="text-muted" style={{ fontSize: '13px' }}>
            (admin = {adminPermissionsCount} permissions ; employés = {roles.filter(r => r.name !== 'super_admin' && r.name !== 'admin').reduce((sum, r) => sum + (r.permissions?.length || 0), 0)} permissions)
          </span>
          {roleFilter !== 'admin_empl' && (
            <button className="btn-small btn-secondary" style={{ marginLeft: '12px' }} onClick={() => setRoleFilter('admin_empl')}>
              Voir Admin + Employés
            </button>
          )}
          {roleFilter === 'admin_empl' && (
            <button className="btn-small" style={{ marginLeft: '12px' }} onClick={() => setRoleFilter('')}>Voir tout</button>
          )}
        </div>
      )}

      <div className="filter-controls" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div className="search-box">
          <i className="ti ti-search search-icon" aria-hidden="true" />
          <input
            type="text"
            placeholder="Rechercher une permission…"
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
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="form-select"
          title="Filtrer par rôle (admin / tenant inscrit / employés)"
        >
          <option value="">Tous les rôles</option>
          <option value="admin_empl">Admin + Employés (Tenant)</option>
          {roles.filter(r => r.name !== 'super_admin').map((r) => (
            <option key={r.name} value={r.name}>{r.display_name || r.name} ({r.permissions?.length || 0})</option>
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
                <th>Rôles</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedPermissions.map((p) => {
                const roleNames = permissionRolesMap[p.code] || [];
                const isAdminPerm = roleNames.includes('admin');
                return (
                  <tr key={p.id} style={isAdminPerm && (roleFilter === 'admin_empl' || isTenantAdmin) ? { background: 'rgba(212,175,55,0.06)' } : undefined}>
                    <td><code style={{ fontSize: '13px' }}>{p.code}</code> {isAdminPerm && <span className="badge badge-info" style={{ marginLeft: '6px', fontSize: '10px' }}>Admin</span>}</td>
                    <td>{p.module}</td>
                    <td>{p.action}</td>
                    <td>{p.description}</td>
                    <td>
                      {roleNames.length > 0 ? (
                        <span className="text-muted" style={{ fontSize: '12px' }} title={roleNames.join(', ')}>
                          {roleNames.slice(0, 3).join(', ')}{roleNames.length > 3 ? ` +${roleNames.length - 3}` : ''}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal(p)}>
                        <i className="ti ti-edit" aria-hidden="true" />
                      </button>
                      <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete(p.id)}>
                        <i className="ti ti-trash" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {displayedPermissions.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center text-muted" style={{ padding: '24px' }}>
                    {roleFilter ? `Aucune permission pour le filtre "${roleFilter}"` : 'Aucune permission trouvée'}
                    {roleFilter === 'admin_empl' && adminRole && (
                      <span> — vérifiez que des permissions existent pour le rôle Admin et les employés du tenant</span>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="text-muted" style={{ fontSize: '12px', marginTop: '8px', textAlign: 'right' }}>
            {displayedPermissions.length} / {permissions.length} permissions affichées
            {roleFilter && ` — filtre: ${roleFilter === 'admin_empl' ? 'Admin + Employés (Tenant)' : roleFilter}`}
          </div>
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
