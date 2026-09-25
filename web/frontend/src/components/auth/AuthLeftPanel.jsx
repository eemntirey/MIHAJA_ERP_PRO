import React from 'react';
import { Link } from 'react-router-dom';

const AuthLeftPanel = ({ brandLink = '/' }) => {
  return (
    <>
      <span className="auth-login__context-divider" aria-hidden="true" />
      <span className="auth-login__context-orbit auth-login__context-orbit--large" aria-hidden="true" />
      <span className="auth-login__context-orbit auth-login__context-orbit--small" aria-hidden="true" />

      <div className="auth-login__context-inner">
        <div className="auth-login__brand-row">
          <Link to={brandLink} className="auth-login__brand" aria-label="MIHAJA ERP PRO accueil">
            <span className="auth-login__brand-mark" aria-hidden="true" >M</span>
            <span className="auth-login__brand-name" >MIHAJA ERP PRO</span>
          </Link>
          <span className="auth-login__brand-meta">Gestion intégrée</span>
        </div>

        <div className="auth-login__context-content">
          <p className="auth-login__eyebrow">
            <span aria-hidden="true" />
            Espace professionnel
          </p>
          <h1 id="auth-login-context-title">
            Gardez le contrôle sur chaque décision.
          </h1>
          <p className="auth-login__context-copy">
            Une vue précise de vos ventes, de vos clients et de votre stock
            pour avancer avec confiance, chaque jour.
          </p>

          <div className="auth-login__feature-grid" role="list" aria-label="Modules ERP">
            <div className="auth-login__feature" role="listitem">
              <i className="ti ti-shopping-cart" aria-hidden="true" />
              <div>
                <strong>Ventes</strong>
                <span>Suivi en temps réel</span>
              </div>
            </div>
            <div className="auth-login__feature" role="listitem">
              <i className="ti ti-box" aria-hidden="true" />
              <div>
                <strong>Stock</strong>
                <span>Alertes maîtrisées</span>
              </div>
            </div>
            <div className="auth-login__feature" role="listitem">
              <i className="ti ti-file-invoice" aria-hidden="true" />
              <div>
                <strong>Factures</strong>
                <span>Gestion simplifiée</span>
              </div>
            </div>
          </div>
        </div>

        <footer className="auth-login__context-footer">
          <span>© 2026 MIHAJA ERP PRO</span>
          <span className="auth-login__watermark" aria-hidden="true">
            MIHAJA · ERP · PILOTAGE · PRÉCISION
          </span>
          <span className="auth-login__status">
            <span aria-hidden="true" />
            Une gestion plus claire
          </span>
        </footer>
      </div>
    </>
  );
};

export default AuthLeftPanel;
