// src/components/landing/Header.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import '../../styles/landing.css';

const Header = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const userMenuRef = useRef(null);

  const greeting = isAuthenticated && user
    ? `Bienvenue, ${user.prenom || user.tenant?.nom || 'Utilisateur'}`
    : '';

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setUserMenuOpen(false);
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  const handleLogout = () => {
    logout();
    setUserMenuOpen(false);
    navigate('/');
  };

  return (
    <header className="landing-header">
      <div className="landing-container">
        <div className="landing-header-inner">
          <Link to="/" className="landing-logo" aria-label="ERP Pro accueil">
            <span className="landing-logo-mark">EP</span>
            <span className="landing-logo-text">ERP Pro</span>
          </Link>

          <nav className="landing-nav" aria-label="Navigation principale">
            <Link to="/" className="landing-nav-link">Accueil</Link>
            <Link to="/catalogue" className="landing-nav-link">Catalogue</Link>
            <Link to="/suivi" className="landing-nav-link">Suivi</Link>
            <Link to="/contact" className="landing-nav-link">Contact</Link>
          </nav>

          {isAuthenticated && greeting && (
            <div className="landing-user-menu" ref={userMenuRef}>
              <button
                type="button"
                className="landing-user-menu-trigger"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                aria-haspopup="true"
                aria-expanded={userMenuOpen}
                aria-label="Menu utilisateur"
              >
                <span className="landing-user-menu-avatar">
                  {(user?.prenom?.[0] || user?.tenant?.nom?.[0] || 'U').toUpperCase()}
                </span>
                <span className="landing-user-menu-greeting">
                  {greeting}
                </span>
                <span className="landing-user-menu-chevron" aria-hidden="true">
                  ▾
                </span>
              </button>

              {userMenuOpen && (
                <div className="landing-user-menu-dropdown" role="menu">
                  <div className="landing-user-menu-header">
                    <div className="landing-user-menu-avatar-large">
                      {(user?.prenom?.[0] || user?.tenant?.nom?.[0] || 'U').toUpperCase()}
                    </div>
                    <div className="landing-user-menu-meta">
                      <strong>{user?.prenom} {user?.nom}</strong>
                      <span>{user?.email}</span>
                    </div>
                  </div>
                  <div className="landing-user-menu-actions">
                    <Link
                      to="/"
                      className="landing-user-menu-item"
                      role="menuitem"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Mon Profil
                    </Link>
                    <Link
                      to="/suivi"
                      className="landing-user-menu-item"
                      role="menuitem"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Mes Commandes
                    </Link>
                    <button
                      type="button"
                      className="landing-user-menu-item landing-user-menu-item--logout"
                      role="menuitem"
                      onClick={handleLogout}
                    >
                      Déconnexion
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {!isAuthenticated && (
            <Link to="/login" className="landing-nav-link">Connexion</Link>
          )}

          <button
            className="landing-burger"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
            aria-expanded={menuOpen}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {menuOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="landing-container">
          <nav className="landing-nav" style={{ display: 'flex', padding: '12px 0 16px', flexDirection: 'column', gap: '4px' }} aria-label="Menu mobile">
            <Link to="/" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Accueil</Link>
            <Link to="/catalogue" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Catalogue</Link>
            <Link to="/suivi" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Suivi</Link>
            <Link to="/contact" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Contact</Link>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
