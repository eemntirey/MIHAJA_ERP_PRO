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
      if (currentUser) {
        await userService.update(currentUser.id, data);
        toast.success('Utilisateur mis à jour');
      } else {
        await userService.create(data);
        toast.success('Utilisateur créé');
      }
      closeModal();
      fetchUsers();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de l\'enregistrement';
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    try {
      await userService.delete(id);
      toast.success('Utilisateur supprimé');
      fetchUsers();
    } catch (err) {
      const msg = err.response?.data?.message || 'Erreur lors de la suppression';
      toast.error(msg);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Utilisateurs</h1>
        <button className="btn-primary" onClick={() => openModal()}>
          Nouvel utilisateur
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
                  <td>{u.role}</td>
                  <td>
                    <span className={`statut-badge ${u.statut === 'actif' ? 'statut-success' : 'statut-danger'}`}>
                      {u.statut}
                    </span>
                  </td>
                  <td>
                    <button className="btn-small" onClick={() => openModal(u)}>Modifier</button>
                    <button className="btn-small btn-danger" onClick={() => handleDelete(u.id)}>Supprimer</button>
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
              <h2>{currentUser ? 'Modifier' : 'Nouvel'} utilisateur</h2>
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
                      <option value="user">User</option>
                      <option value="super_admin">Super Admin</option>
                      <option value="admin">Admin</option>
                    </select>
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
