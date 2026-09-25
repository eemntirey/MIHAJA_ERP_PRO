import React from 'react';
import { Link } from 'react-router-dom';

const PublicHeader = ({ compact = false }) => (
  <header className={`public-header${compact ? ' public-header--compact' : ''}`}>
    <Link to="/" className="brand" aria-label="MIHAJA ERP PRO accueil">
      <span className="brand-icon">EP</span>
      <span className="brand-name">ERP Pro</span>
    </Link>
    <nav className="public-nav" aria-label="Navigation principale">
      <Link to="/" className="public-nav-link">Accueil</Link>
      <Link to="/catalogue" className="public-nav-link">Catalogue</Link>
      <Link to="/telechargements" className="public-nav-link">Téléchargements</Link>
      <Link to="/contact" className="public-nav-link">Contact</Link>
      <Link to="/login" className="public-nav-link btn-nav-login">Connexion</Link>
    </nav>
  </header>
);

export default PublicHeader;
