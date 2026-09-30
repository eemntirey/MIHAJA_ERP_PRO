import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../contexts/CartContext';
import '../pages/Pages.css';

const PublicHeader = ({ compact = false }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { totalItems } = useCart();
  const closeMenu = () => setMobileOpen(false);

  return (
  <header className={`public-header public-page-header${compact ? ' public-header--compact' : ''}`}>
    <Link to="/" className="brand" aria-label="MIHAJA ERP PRO accueil">
      <span className="brand-icon" aria-hidden="true">M</span>
      <span className="brand-name"><strong>MIHAJA</strong><small>ERP PRO</small></span>
    </Link>
    <button
      type="button"
      className="public-nav-toggle"
      aria-label={mobileOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
      aria-expanded={mobileOpen}
      aria-controls="mihaja-public-nav"
      onClick={() => setMobileOpen((open) => !open)}
    >
      <i className={mobileOpen ? 'ti ti-x' : 'ti ti-menu-2'} aria-hidden="true" />
    </button>
    <nav id="mihaja-public-nav" className={`public-nav${mobileOpen ? ' is-open' : ''}`} aria-label="Navigation principale">
      <Link to="/" className="public-nav-link" onClick={closeMenu}>Accueil</Link>
      <Link to="/catalogue" className="public-nav-link" onClick={closeMenu}>Catalogue</Link>
      <Link to="/telechargements" className="public-nav-link" onClick={closeMenu}>Téléchargements</Link>
      <Link to="/contact" className="public-nav-link" onClick={closeMenu}>Contact</Link>
      <Link to="/login" className="public-nav-link btn-nav-login">Connexion</Link>
      </nav>
  </header>
  );
};

export default PublicHeader;
