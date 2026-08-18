// src/pages/Users.jsx
import React, { useState, useEffect } from 'react';
import { userService, roleService } from '../services/api';
import { toast } from 'react-toastify';
import './Pages.css';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
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

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, []);

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
        custom_role_id: user.custom_role?.id || '',
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
      if (currentUser) {
        const updateData = { ...formData };
        if (!updateData.password) delete updateData.password;
        if (!updateData.custom_role_id) delete updateData.custom_role_id;
        await userService.update(currentUser.id, updateData);
        toast.success('Utilisateur mis à jour avec succès');
      } else {
        await userService.create(formData);
        toast.success('Utilisateur créé avec succès');
      }
      fetchUsers();
      closeModal();
    } catch (err) {
      console.error('Error saving user:', err);
      const msg = err.response?.data?.message || 'Échec de la sauvegarde de l\'utilisateur';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir desactiver cet utilisateur ?')) {
      try {
        await userService.delete(id);
        toast.success('Utilisateur désactivé avec succès');
        fetchUsers();
      } catch (err) {
        console.error('Error deleting user:', err);
        const msg = err.response?.data?.message || 'Échec de la suppression de l\'utilisateur';
        toast.error(msg);
      }
    }
  };

  const getRoleBadge = (role) => {
    const colors = {
      super_admin: 'badge--danger',
      admin: 'badge--warning',
      manager: 'badge--info',
      sales: 'badge--success',
      stock: 'badge--primary',
      accountant: 'badge--secondary',
      user: 'badge--default',
    };
    return colors[role] || 'badge--default';
  };

  const getStatutBadge = (statut) => {
    const colors = {
      actif: 'badge--success',
      inactif: 'badge--secondary',
      bloque: 'badge--danger',
      en_attente: 'badge--warning',
    };
    return colors[statut] || 'badge--default';
  };

  if (loading && users.length === 0) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des utilisateurs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <p>{error}</p>
          <button onClick={fetchUsers} className="btn-primary">Réessayer</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Gestion des Utilisateurs</h1>
          <p>Gerez les comptes utilisateurs et leurs roles</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => openModal()}>
            <i className="ti ti-plus" /> Nouvel Utilisateur
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Liste des utilisateurs ({users.length})</h3>
          <div className="header-filters">
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="search-input"
            >
              <option value="">Tous les roles</option>
              {roles.map(role => (
                <option key={role.id} value={role.name}>{role.display_name || role.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="card-body">
          <table className="data-table">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Email</th>
                <th>Role</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>
                    <div className="user-cell">
                      <div className="user-avatar">
                        {user.prenom?.[0] || user.username?.[0] || 'U'}
                      </div>
                      <div>
                        <strong>{user.prenom} {user.nom}</strong>
                        <div className="text-muted text-sm">@{user.username}</div>
                      </div>
                    </div>
                  </td>
                  <td>{user.email}</td>
                  <td>
                    <span className={`badge ${getRoleBadge(user.role)}`}>
                      {user.role}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${getStatutBadge(user.statut)}`}>
                      {user.statut}
                    </span>
                  </td>
                  <td>
                    <button className="btn-sm btn-secondary" onClick={() => openModal(user)}>
                      <i className="ti ti-edit" />
                    </button>
                    {user.role !== 'super_admin' && (
                      <button className="btn-sm btn-danger" onClick={() => handleDelete(user.id)}>
                        <i className="ti ti-trash" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="5" className="text-center text-muted">Aucun utilisateur trouve</td>
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
              <h2>{currentUser ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}</h2>
              <button className="modal-close" onClick={closeModal}><i className="ti ti-x" /></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label>Username</label>
                    <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      required
                      disabled={!!currentUser}
                    />
                  </div>
                  <div className="form-group">
                    <label>Email</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      disabled={!!currentUser}
                    />
                  </div>
                </div>
                {!currentUser && (
                  <div className="form-group">
                    <label>Mot de passe</label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required
                    />
                  </div>
                )}
                <div className="form-row">
                  <div className="form-group">
                    <label>Nom</label>
                    <input
                      type="text"
                      name="nom"
                      value={formData.nom}
                      onChange={handleChange}
                    />
                  </div>
                  <div className="form-group">
                    <label>Prenom</label>
                    <input
                      type="text"
                      name="prenom"
                      value={formData.prenom}
                      onChange={handleChange}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Telephone</label>
                    <input
                      type="text"
                      name="telephone"
                      value={formData.telephone}
                      onChange={handleChange}
                    />
                  </div>
                  <div className="form-group">
                    <label>Mobile</label>
                    <input
                      type="text"
                      name="mobile"
                      value={formData.mobile}
                      onChange={handleChange}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Role</label>
                    <select name="role" value={formData.role} onChange={handleChange}>
                      {roles.map(role => (
                        <option key={role.id} value={role.name}>{role.display_name || role.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Statut</label>
                    <select name="statut" value={formData.statut} onChange={handleChange}>
                      <option value="actif">Actif</option>
                      <option value="inactif">Inactif</option>
                      <option value="bloque">Bloque</option>
                      <option value="en_attente">En attente</option>
                    </select>
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

export default Users;
