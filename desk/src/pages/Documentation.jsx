// src/pages/Documentation.jsx
import React from 'react';
import './Pages.css';

const Documentation = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Documentation du site</h1>
          <p>Tout ce dont vous avez besoin pour utiliser l'application ERP Pro.</p>
        </div>
      </div>

      <div className="card">
        <h3>Pages et accès</h3>
        <p>
          - Utilisateur simple : accès à la gestion des ventes, des clients et de l'inventaire.
        </p>
        <p>
          - Entreprise : accès complet avec gestion des factures, fournisseurs, paiements et tableaux de bord avancés.
        </p>
      </div>

      <div className="card">
        <h3>Espace public</h3>
        <p>
          - Catalogue : parcourez les produits publics, ajoutez-les à votre panier et passez commande.
        </p>
        <p>
          - Suivi : consultez l'état d'une commande à l'aide de sa référence.
        </p>
        <p>
          - Contact : envoyez un message à notre équipe support.
        </p>
      </div>

      <div className="card">
        <h3>Authentification</h3>
        <p>
          Connectez-vous en utilisant votre email et mot de passe. Le site conserve votre session avec un token sécurisé.
        </p>
      </div>

      <div className="card">
        <h3>Support</h3>
        <p>
          Si vous avez besoin d'aide, consultez la documentation technique du projet dans le dossier <code>docs/</code>.
        </p>
      </div>
    </div>
  );
};

export default Documentation;
