import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import DarkModeToggle from '../layout/DarkModeToggle';
import './LandingLayout.css';

const LandingLayout = ({ darkMode, onToggleDarkMode }) => {
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
    navigate('/login');
  };

  return (
    <div className="landing-root" data-theme={darkMode ? 'dark' : undefined}>
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
              <Link to="/documentation" className="landing-nav-link">Documentation</Link>
            </nav>

            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <DarkModeToggle enabled={darkMode} onChange={onToggleDarkMode} />
            </div>

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
                        to="/catalogue"
                        className="landing-user-menu-item"
                        role="menuitem"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        Mon Profil
                      </Link>
                      <Link
                        to="/mes-commandes"
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
              <Link to="/catalogue" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Catalogue</Link>
              <Link to="/suivi" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Suivi</Link>
              <Link to="/contact" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Contact</Link>
              <Link to="/documentation" className="landing-nav-link" onClick={() => setMenuOpen(false)}>Documentation</Link>
            </nav>
          </div>
        )}
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="landing-footer" aria-labelledby="footer-titre">
        <div className="landing-container">
          <div className="landing-footer-grid">
            <div>
              <Link to="/catalogue" className="landing-footer-brand" aria-label="ERP Pro accueil">
                <span className="landing-footer-brand-mark">EP</span>
                <span className="landing-footer-brand-text">ERP Pro</span>
              </Link>
              <p className="landing-footer-desc">
                Plateforme de fournitures pour hôtels. Commandes, catalogue et suivi simplifiés pour les professionnels.
              </p>
            </div>

            <div>
              <h4>Navigation</h4>
              <ul className="landing-footer-links">
                <li><Link to="/catalogue">Catalogue</Link></li>
                <li><Link to="/suivi">Suivi</Link></li>
                <li><Link to="/contact">Contact</Link></li>
                <li><Link to="/documentation">Documentation</Link></li>
              </ul>
            </div>

            <div>
              <h4>Légal</h4>
              <ul className="landing-footer-links">
                <li><a href="#mentions">Mentions légales</a></li>
                <li><a href="#cgv">CGV</a></li>
                <li><a href="#confidentialite">Confidentialité</a></li>
              </ul>
            </div>

            <div>
              <h4>Contact</h4>
              <ul className="landing-footer-contact">
                <li>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  {user?.email || 'contact@erppro.mg'}
                </li>
                <li>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                  </svg>
                  {user?.telephone || user?.phone || '+261 34 12 345 67'}
                </li>
                <li>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                  {user?.adresse || user?.location || 'Antananarivo, Madagascar'}
                </li>
              </ul>
            </div>
          </div>

          <div className="landing-footer-bottom">
            <span>&copy; {new Date().getFullYear()} ERP Pro. Tous droits réservés.</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingLayout;
