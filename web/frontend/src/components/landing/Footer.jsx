// src/components/landing/Footer.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import '../../styles/landing.css';

const Footer = () => {
  const { user, hasRole } = useAuth();
  const isSuperAdmin = hasRole('SUPER_ADMIN');

  const contactEmail = (user?.email || 'contact@erppro.mg').trim();
  const contactPhone = (user?.telephone || user?.phone || '+261 34 12 345 67').trim();
  const contactLocation = (user?.adresse || user?.location || 'Antananarivo, Madagascar').trim();

  return (
    <footer className="landing-footer" id="contact" aria-labelledby="footer-titre">
      <div className="landing-container">
        <div className="landing-footer-grid">
          <div>
            <Link to="/" className="landing-footer-brand" aria-label="ERP Pro accueil">
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
              <li><Link to="/">Accueil</Link></li>
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
                {contactEmail}
              </li>
              <li>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                </svg>
                {contactPhone}
              </li>
              <li>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                {contactLocation}
              </li>
            </ul>
          </div>
        </div>

        <div className="landing-footer-bottom">
          <span>&copy; {new Date().getFullYear()} ERP Pro. Tous droits réservés.</span>
          {isSuperAdmin && <span>Contact super admin : {contactEmail}</span>}
        </div>
      </div>
    </footer>
  );
};

export default Footer;
