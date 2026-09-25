import React from 'react';
import { Link } from 'react-router-dom';
import Seo from '../components/Seo';
import '../styles/landing.css';
import PublicHeader from '../components/PublicHeader';

const SITE_URL = 'https://erp.sekoliko.com';

const Privacy = () => (
  <>
    <Seo
      title="Politique de confidentialité | MIHAJA ERP PRO"
      description="Politique de confidentialité et principes de protection des données de MIHAJA ERP PRO."
      canonical={`${SITE_URL}/privacy`}
    />
    <div className="landing-root"><PublicHeader />\n\n      <main className="landing-container landing-legal-page">
        <div className="landing-section-header">
          <span className="vit-section-tag">Informations légales</span>
          <h1 className="landing-section-title">Politique de confidentialité</h1>
          <p className="landing-section-subtitle">Dernière mise à jour : 25 septembre 2026</p>
        </div>

        <article className="landing-legal-card">
          <section>
            <h2>1. Données collectées</h2>
            <p>Selon les fonctionnalités utilisées, MIHAJA ERP PRO peut traiter des informations d’identification et de contact, des informations nécessaires aux commandes, ainsi que les données liées à l’utilisation du compte.</p>
          </section>
          <section>
            <h2>2. Finalités</h2>
            <p>Ces données peuvent être utilisées pour créer et sécuriser les comptes, exécuter les commandes, fournir les fonctionnalités demandées, assurer le support, prévenir les abus et maintenir la sécurité du service.</p>
          </section>
          <section>
            <h2>3. Conservation et sécurité</h2>
            <p>Les données sont conservées pendant la durée nécessaire aux finalités concernées et selon les obligations applicables. Des mesures de sécurité sont mises en place pour limiter les accès non autorisés et les usages abusifs.</p>
          </section>
          <section>
            <h2>4. Cookies et stockage local</h2>
            <p>L’application peut utiliser des cookies techniques liés à l’authentification ainsi que le stockage local du navigateur pour certaines fonctions, notamment le panier public. Ces mécanismes sont nécessaires au fonctionnement des fonctionnalités concernées.</p>
          </section>
          <section>
            <h2>5. Prestataires tiers</h2>
            <p>Certaines fonctions peuvent s’appuyer sur des prestataires techniques externes, notamment l’hébergement, les paiements ou l’envoi d’e-mails. Les données transmises sont limitées à ce qui est nécessaire au fonctionnement de la fonctionnalité concernée.</p>
          </section>
          <section>
            <h2>6. Vos demandes</h2>
            <p>Pour toute demande relative à vos données personnelles, utilisez la <Link to="/contact">page Contact</Link> en précisant l’adresse e-mail associée à votre demande.</p>
          </section>
          <section>
            <h2>7. Mise à jour</h2>
            <p>Cette politique peut évoluer avec le service ou les exigences applicables. La date de dernière mise à jour figure en haut de la page.</p>
          </section>
        </article>
      </main>
    </div>
  </>
);

export default Privacy;
