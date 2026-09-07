import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { superAdminUserService } from '../services/api';
import ConfirmModal from '../components/common/ConfirmModal';

const ROLE_LABELS = {
  super_admin: 'Super Admin',
  admin: 'Admin',
  manager: 'Manager',
  sales: 'Commercial',
  stock: 'Stock',
  accountant: 'Comptable',
  user: 'Utilisateur',
  rh: 'RH',
};

const Users = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('admins');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [confirmAction, setConfirmAction] = useState(null);

  const perPage = 20;

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, per_page: perPage, role: roleFilter };
      if (search) params.search = search;
      const response = await superAdminUserService.getAll(params);
      const data = response.data || response;
      setUsers(data.users || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Échec du chargement des utilisateurs';
      console.error('Error fetching users:', err);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    const handleUserUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.id) {
        setUsers(prev => {
          const exists = prev.some(u => u.id === updated.id);
          if (exists) {
            return prev.map(u => u.id === updated.id ? { ...u, ...updated } : u);
          }
          if (!search && !roleFilter || roleFilter === 'all') {
            return [updated, ...prev];
          }
          return prev;
        });
      } else {
        fetchUsers();
      }
    };
    window.addEventListener('realtime:user:updated', handleUserUpdated);
    return () => window.removeEventListener('realtime:user:updated', handleUserUpdated);
  }, [fetchUsers, search, roleFilter]);

  const handleDelete = async (id, username, role) => {
    const isAdmin = role === 'admin';
    setConfirmAction({
      title: isAdmin ? 'Supprimer l\'admin et le tenant' : 'Supprimer l\'utilisateur',
      message: isAdmin
        ? `Êtes-vous sûr de vouloir supprimer l'admin "${username}" ? Cela supprimera aussi le tenant et toutes ses données.`
        : `Êtes-vous sûr de vouloir supprimer l'utilisateur "${username}" ?`,
      warning: isAdmin
        ? 'Cette action est IRRÉVERSIBLE. Le tenant et toutes ses données seront supprimés.'
        : 'Cette action est IRRÉVERSIBLE.',
      confirmText: 'Supprimer',
      confirmClass: 'btn-danger',
      onConfirm: async () => {
        try {
          await superAdminUserService.delete(id);
          toast.success(isAdmin ? 'Admin et tenant supprimés' : 'Utilisateur supprimé');
          fetchUsers();
        } catch (err) {
          toast.error(err.response?.data?.message || 'Échec de la suppression');
        }
        setConfirmAction(null);
      },
    });
  };

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleRoleChange = (e) => {
    setRoleFilter(e.target.value);
    setPage(1);
  };

  const getRoleBadge = (role) => {
    const r = (role || '').toLowerCase();
    if (r === 'super_admin') return 'badge-danger';
    if (r === 'admin') return 'badge-warning';
    if (r === 'manager') return 'badge-info';
    return 'badge-success';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Utilisateurs</h1>
          <p>Gestion de tous les utilisateurs de la plateforme ({total} total)</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div className="search-box" style={{ flex: 1, minWidth: '240px' }}>
            <input
              type="text"
              placeholder="Rechercher par nom, email, username..."
              value={search}
              onChange={handleSearchChange}
            />
            <span className="search-icon"><i className="ti ti-search" aria-hidden="true" /></span>
          </div>
          <select value={roleFilter} onChange={handleRoleChange} style={{ width: '200px' }}>
            <option value="admins">Tous les admins</option>
            <option value="tenant_admins">Admins tenant</option>
            <option value="super_admins">Super Admins</option>
            <option value="employees">Employés</option>
            <option value="all">Tous</option>
          </select>
          <button onClick={fetchUsers} className="btn-secondary" disabled={loading}>
            Rafraîchir
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des utilisateurs...</p>
        </div>
      ) : (
        <>
          <div className="card full-width">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Rôle</th>
                    <th>Tenant</th>
                    <th>Statut</th>
                    <th>Créé le</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="text-center text-muted">
                        Aucun utilisateur trouvé
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => (
                      <tr key={user.id}>
                        <td style={{ fontWeight: 600 }}>{user.username}</td>
                        <td>{user.email}</td>
                        <td>
                          <span className={`badge ${getRoleBadge(user.role)}`}>
                            {ROLE_LABELS[user.role] || user.role}
                          </span>
                        </td>
                        <td>{user.tenant_nom || '-'}</td>
                        <td>
                          <span className={`badge ${user.statut === 'actif' ? 'badge-success' : 'badge-danger'}`}>
                            {user.statut || 'INCONNU'}
                          </span>
                        </td>
                        <td>{user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : '-'}</td>
                        <td>
                          {user.role !== 'super_admin' && (
                            <button
                              onClick={() => handleDelete(user.id, user.username, user.role)}
                              className="btn-small btn-danger"
                              title="Supprimer"
                            >
                              <i className="ti ti-trash" aria-hidden="true" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="pagination">
                <button
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  Précédent
                </button>
                <span className="pagination-info">
                  Page {page} sur {totalPages} ({total} utilisateurs)
                </span>
                <button
                  className="pagination-btn"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Suivant
                </button>
              </div>
            )}
          </div>
        </>
      )}

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          warning={confirmAction.warning}
          confirmText={confirmAction.confirmText}
          confirmClass={confirmAction.confirmClass}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  );
};

export default Users;
