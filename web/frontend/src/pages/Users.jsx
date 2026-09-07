// src/pages/Users.jsx
import React, { useState, useEffect } from 'react';
import { userService, roleService, subscriptionService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-toastify';
import './Pages.css';

const ROLE_LABELS = {
  manager: 'Manager',
  sales: 'Commercial',
  stock: 'Stock',
  accountant: 'Comptable',
  user: 'Utilisateur',
  rh: 'RH',
};

const EMPLOYEE_ROLES = ['user', 'sales', 'stock', 'accountant', 'rh', 'manager'];
const isEmployeeRole = (role) => EMPLOYEE_ROLES.includes(role);

const Users = () => {
  const { user, hasPermission, hasRole } = useAuth();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [tenantSummary, setTenantSummary] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    nom: '',
    prenom: '',
    telephone: '',
    mobile: '',
    role: 'user',
    statut: 'actif',
    custom_role_id: '',
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const canCreateUser = Boolean(
    hasRole && (hasRole('super_admin') || hasRole('admin') || hasRole('manager'))
  ) || (hasPermission && hasPermission('user.create'));

  const isEmployeeLimitReached = () => {
    if (!tenantSummary || !isEmployeeRole(formData.role)) return false;
    if (tenantSummary.max_employees === -1) return false;
    return (tenantSummary.employees_count ?? 0) >= (tenantSummary.max_employees ?? 0);
  };

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (roleFilter) params.role = roleFilter;
      const response = await userService.getAll(params);
      setUsers(response.data?.users || response.data || []);
    } catch (err) {
      console.error('Error fetching users:', err);
      const msg = err.response?.data?.message || 'Échec du chargement des utilisateurs';
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

  const fetchTenantSummary = async () => {
    try {
      const response = await subscriptionService.getMonAbonnement();
      setTenantSummary(response.data?.tenant || null);
    } catch (err) {
      console.error('Error fetching tenant summary:', err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchRoles();
    fetchTenantSummary();
  }, []);

  useEffect(() => {
    const handleUserUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id) {
        setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
      } else {
        fetchUsers();
      }
    };
    window.addEventListener('realtime:user:updated', handleUserUpdated);
    return () => window.removeEventListener('realtime:user:updated', handleUserUpdated);
  }, [fetchUsers]);

  useEffect(() => {
    fetchUsers();
  }, [searchTerm, roleFilter]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const openModal = (user = null) => {
    setCurrentUser(user);
    if (user) {
      setFormData({
        username: user.username || '',
        email: user.email || '',
        password: '',
        nom: user.nom || '',
        prenom: user.prenom || '',
        telephone: user.telephone || '',
        mobile: user.mobile || '',
        role: user.role || 'user',
        statut: user.statut || 'actif',
        custom_role_id: user.custom_role_id || '',
      });
    } else {
      setFormData({
        username: '',
        email: '',
        password: '',
        nom: '',
        prenom: '',
        telephone: '',
        mobile: '',
        role: 'user',
        statut: 'actif',
        custom_role_id: '',
      });
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setCurrentUser(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = { ...formData };
      if (!data.password) delete data.password;
      if (EMPLOYEE_ROLES.includes(data.role) && tenantSummary) {
        const remaining = (tenantSummary.max_employees === -1 ? Infinity : (tenantSummary.max_employees ?? 0)) - (tenantSummary.employees_count ?? 0);
        if (remaining <= 0) {
          toast.error('Limite d\'employés atteinte pour votre abonnement actuel.');
          return;
        }
      }
      if (currentUser) {
        const response = await userService.update(currentUser.id, data);
        toast.success('Employé mis à jour');
        if (response.data && response.data.id) {
          setUsers(prev => prev.map(u => u.id === currentUser.id ? response.data : u));
        }
      } else {
        const response = await userService.create(data);
        toast.success('Employé créé');
        if (response.data && response.data.id) {
          setUsers(prev => [...prev, response.data]);
        }
      }
      closeModal();
      fetchUsers();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de l\'enregistrement';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cet employé ?')) return;
    try {
      await userService.delete(id);
      toast.success('Employé supprimé');
      fetchUsers();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la suppression';
      toast.error(msg);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Employés</h1>
        {canCreateUser && (
          <button className="btn-primary" onClick={() => openModal()}>
            Nouvel employé
          </button>
        )}
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
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="form-select"
        >
          <option value="">Tous les rôles</option>
          {roles.map((r) => (
            <option key={r.id} value={r.name}>
              {r.display_name || r.name}
            </option>
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
                <th>Nom</th>
                <th>Prénom</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.nom}</td>
                  <td>{u.prenom}</td>
                  <td>{u.email}</td>
                  <td>{u.custom_role?.display_name || ROLE_LABELS[u.role] || u.role}</td>
                  <td>
                    <span className={`statut-badge ${u.statut === 'actif' ? 'statut-success' : 'statut-danger'}`}>
                      {u.statut}
                    </span>
                  </td>
                  <td>
                    <button className="btn-small btn-edit" title="Modifier" onClick={() => openModal(u)}>
                      <i className="ti ti-edit" aria-hidden="true" />
                    </button>
                    <button className="btn-small btn-delete" title="Supprimer" onClick={() => handleDelete(u.id)}>
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
              <h2>{currentUser ? 'Modifier' : 'Nouvel'} employé</h2>
              <button onClick={closeModal} className="btn-close">×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label>Nom</label>
                    <input type="text" name="nom" value={formData.nom} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Prénom</label>
                    <input type="text" name="prenom" value={formData.prenom} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Username</label>
                    <input type="text" name="username" value={formData.username} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Email</label>
                    <input type="email" name="email" value={formData.email} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label>Mot de passe {currentUser ? '(laisser vide pour ne pas changer)' : ''}</label>
                    <input type="password" name="password" value={formData.password} onChange={handleChange} required={!currentUser} />
                  </div>
                  <div className="form-group">
                    <label>Téléphone</label>
                    <input type="text" name="telephone" value={formData.telephone} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Mobile</label>
                    <input type="text" name="mobile" value={formData.mobile} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Rôle</label>
                    <select name="role" value={formData.role} onChange={handleChange}>
                      <option value="user">Utilisateur</option>
                      <option value="manager">Manager</option>
                      <option value="sales">Commercial</option>
                      <option value="stock">Stock</option>
                      <option value="accountant">Comptable</option>
                      <option value="rh">RH</option>
                    </select>
                    {EMPLOYEE_ROLES.includes(formData.role) && tenantSummary && (
                      <div style={{ marginTop: '6px', fontSize: '12px', color: '#6b7280' }}>
                        Employés restants : {(tenantSummary.max_employees === -1 ? 'Illimité' : ((tenantSummary.max_employees ?? 0) - (tenantSummary.employees_count ?? 0)))}
                      </div>
                    )}
                  </div>
                  <div className="form-group">
                    <label>Statut</label>
                    <select name="statut" value={formData.statut} onChange={handleChange}>
                      <option value="actif">Actif</option>
                      <option value="inactif">Inactif</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal}>Annuler</button>
                <button type="submit" className="btn-primary" disabled={isEmployeeLimitReached()}>Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Users;
