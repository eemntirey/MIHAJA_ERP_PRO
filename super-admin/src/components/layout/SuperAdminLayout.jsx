import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useSuperAdminAuth } from '../../contexts/SuperAdminAuthContext';
import './SuperAdminLayout.css';

const SuperAdminLayout = () => {
  const { user, logout } = useSuperAdminAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="sa-layout">
      <aside className="sa-sidebar">
        <div className="sa-sidebar-brand">
          <h2>MIHAJA</h2>
          <span className="sa-sidebar-subtitle">Super Admin</span>
        </div>

        <nav className="sa-sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Tableau de bord
          </NavLink>
          <NavLink to="/tenants" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Tenants
          </NavLink>
          <NavLink to="/users" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Utilisateurs
          </NavLink>
          <NavLink to="/subscriptions" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Abonnements
          </NavLink>
          <NavLink to="/plans" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Plans
          </NavLink>
          <NavLink to="/audit" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Audit
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => isActive ? 'sa-nav-link sa-nav-link--active' : 'sa-nav-link'}>
            Profil
          </NavLink>
        </nav>

        <div className="sa-sidebar-footer">
          <button onClick={handleLogout} className="sa-logout-btn">
            Déconnexion
          </button>
        </div>
      </aside>

      <main className="sa-main">
        <header className="sa-topbar">
          <div className="sa-topbar-title">
            <h1>Console Super Admin</h1>
          </div>
          <div className="sa-topbar-user">
            <span className="sa-user-name">{user?.full_name || user?.username}</span>
            <span className="sa-user-role">SUPER_ADMIN</span>
          </div>
        </header>

        <div className="sa-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default SuperAdminLayout;
