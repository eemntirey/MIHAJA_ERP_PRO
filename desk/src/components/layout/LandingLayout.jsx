// src/components/layout/LandingLayout.jsx
// Layout public adapté au Desktop : en-tête de navigation, panier, liens publics.
// Utilisé pour les pages accessibles sans authentification (catalogue, suivi, contact...)
// ainsi que pour les pages "espace public" nécessitant une simple connexion (/cart, /checkout...).

import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useCart } from '../../contexts/CartContext';
import { Icon } from '../common/Icon';
import './LandingLayout.css';

const LandingLayout = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const { totalItems } = useCart();
  const navigate = useNavigate();

  const isUser = (user?.role || '').toLowerCase() === 'user';

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // silencieux
    }
    navigate('/');
  };

  return (
    <div className="home-page landing-layout">
      <header className="public-header landing-header">
        <Link to="/" className="brand">
          <span className="brand-icon">EP</span>
          <span className="brand-name">ERP Pro</span>
        </Link>

        <nav className="public-nav landing-nav">
          <Link to="/catalogue" className="public-nav-link">Catalogue</Link>
          <Link to="/suivi" className="public-nav-link">Suivi</Link>
          <Link to="/contact" className="public-nav-link">Contact</Link>
          <Link to="/documentation" className="public-nav-link">Documentation</Link>

          <Link to="/cart" className="public-nav-link btn-cart-link" aria-label="Mon panier">
            Panier
            {totalItems > 0 && <span className="cart-badge">{totalItems}</span>}
          </Link>

          {isAuthenticated && isUser && (
            <Link to="/mes-commandes" className="public-nav-link">Mes commandes</Link>
          )}

          {isAuthenticated ? (
            <button type="button" className="public-nav-link landing-logout" onClick={handleLogout}>
              Déconnexion
            </button>
          ) : (
            <Link to="/login" className="public-nav-link btn-nav-login">Connexion</Link>
          )}
        </nav>
      </header>

      <main className="landing-main">
        <Outlet />
      </main>

      <footer className="landing-footer-bar">
        <span>ERP Pro &middot; Plateforme de gestion intégrée</span>
        <span>&copy; {new Date().getFullYear()} ERP Pro. Tous droits réservés.</span>
      </footer>
    </div>
  );
};

export default LandingLayout;
