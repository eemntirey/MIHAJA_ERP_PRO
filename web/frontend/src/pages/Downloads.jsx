import React from 'react';
import { Link } from 'react-router-dom';
import './Pages.css';

const DESKTOP_DOWNLOAD_URL = 'https://github.com/eemntirey/MIHAJA_ERP_PRO/releases/download/desktop-latest/MIHAJA-ERP-PRO-Setup.exe';

const DOWNLOADS = [
  {
    id: 'desktop',
    icon: 'ti ti-monitor',
    title: 'ERP Pro Desktop',
    platform: 'Windows 10 ou versions ultérieures',
    description: 'Installez la version de bureau pour une utilisation intensive sur votre ordinateur.',
    href: DESKTOP_DOWNLOAD_URL,
    available: true,
  },
  {
    id: 'mobile',
    icon: 'ti ti-device-mobile',
    title: 'ERP Pro Mobile',
    platform: 'Android',
    description: 'L’application mobile Android sera publiée dès que le package de production sera disponible.',
    href: null,
    available: false,
  },
];

const Downloads = () => (
  <div className="downloads-page">
    <header className="public-header">
      <Link to="/" className="brand" aria-label="ERP Pro accueil">
        <span className="brand-icon">EP</span>
        <span className="brand-name">ERP Pro</span>
      </Link>
      <nav className="public-nav" aria-label="Navigation principale">
        <Link to="/" className="public-nav-link">Accueil</Link>
        <Link to="/catalogue" className="public-nav-link">Catalogue</Link>
        <Link to="/contact" className="public-nav-link">Contact</Link>
        <Link to="/login" className="public-nav-link btn-nav-login">Connexion</Link>
      </nav>
    </header>

    <main className="downloads-main">
      <div className="downloads-hero">
        <span className="downloads-hero__tag">Applications officielles</span>
        <h1>Choisissez votre application</h1>
        <p>
          Téléchargez ERP Pro sur ordinateur. Les versions mobiles seront proposées
          ici dès leur publication officielle.
        </p>
      </div>

      <section className="downloads-grid" aria-label="Applications à télécharger">
        {DOWNLOADS.map((download) => (
          <article className={`downloads-card downloads-card--${download.id}`} key={download.id}>
            <div className="downloads-card__heading">
              <span className="downloads-card__icon" aria-hidden="true">
                <i className={download.icon} />
              </span>
              <div>
                <h2>{download.title}</h2>
                <span>{download.platform}</span>
              </div>
            </div>
            <p className="downloads-card__description">{download.description}</p>
            {download.available ? (
              <a className="downloads-card__button" href={download.href} download>
                <i className="ti ti-download" aria-hidden="true" />
                Télécharger {download.title}
              </a>
            ) : (
              <span className="downloads-card__button downloads-card__button--disabled" aria-disabled="true">
                <i className="ti ti-clock" aria-hidden="true" />
                Bientôt disponible
              </span>
            )}
          </article>
        ))}
      </section>
    </main>

    <footer className="downloads-footer">
      ERP Pro — MIHAJA. Applications destinées aux utilisateurs autorisés.
    </footer>
  </div>
);

export default Downloads;
