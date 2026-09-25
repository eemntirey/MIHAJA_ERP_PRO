import React from 'react';
import { Link } from 'react-router-dom';
import Seo from '../components/Seo';
import '../styles/landing.css';
import PublicHeader from '../components/PublicHeader';

const SITE_URL = 'https://erp.sekoliko.com';

const Terms = () => (
  <>
    <Seo
      title="Conditions d’utilisation | MIHAJA ERP PRO"
      description="Conditions d’utilisation du service MIHAJA ERP PRO."
      canonical={`${SITE_URL}/terms`}
    />
    <div className="landing-root"><PublicHeader />\n\n      <main className="landing-container landing-legal-page">
        <div className="landing-section-header">
          <span className="vit-section-tag">Informations légales</span>
          <h1 className="landing-section-title">Conditions d’utilisation</h1>
          <p className="landing-section-subtitle">Dernière mise à jour : 25 septembre 2026</p>
        </div>

        <article className="landing-legal-card">
          <section>
            <h2>1. Objet</h2>
            <p>MIHAJA ERP PRO fournit une plateforme de gestion commerciale accessible sur le Web ainsi que des applications Desktop et Mobile. Les présentes conditions définissent les règles générales d’accès et d’utilisation du service.</p>
          </section>
          <section>
            <h2>2. Compte utilisateur</h2>
            <p>L’utilisateur est responsable de l’exactitude des informations fournies lors de son inscription et de la confidentialité de ses identifiants. Il doit signaler toute utilisation non autorisée de son compte.</p>
          </section>
          <section>
            <h2>3. Utilisation du service</h2>
            <p>Le service doit être utilisé conformément à sa finalité, aux fonctionnalités proposées et aux lois applicables. Toute tentative d’accès non autorisé, d’altération des données ou de perturbation du service est interdite.</p>
          </section>
          <section>
            <h2>4. Abonnements et paiements</h2>
            <p>Les fonctionnalités disponibles peuvent dépendre du plan d’abonnement souscrit. Les conditions tarifaires, la durée et les modalités de paiement sont affichées dans l’espace Abonnement au moment de la souscription.</p>
          </section>
          <section>
            <h2>5. Données et contenu</h2>
            <p>L’utilisateur reste responsable des données qu’il saisit dans le service. MIHAJA ERP PRO met en œuvre des mesures techniques et organisationnelles destinées à protéger les données contre les accès non autorisés.</p>
          </section>
          <section>
            <h2>6. Disponibilité</h2>
            <p>Des interruptions peuvent survenir pour maintenance, évolution du service ou en raison d’événements indépendants de la volonté de l’éditeur. Les limitations propres à l’hébergement ou aux réseaux tiers peuvent également affecter l’accès.</p>
          </section>
          <section>
            <h2>7. Évolution des conditions</h2>
            <p>Les présentes conditions peuvent être mises à jour pour refléter l’évolution du service ou des exigences applicables. La date de mise à jour est indiquée en haut de cette page.</p>
          </section>
          <section>
            <h2>8. Contact</h2>
            <p>Pour toute question concernant ces conditions, utilisez la <Link to="/contact">page Contact</Link>.</p>
          </section>
        </article>
      </main>
    </div>
  </>
);

export default Terms;
