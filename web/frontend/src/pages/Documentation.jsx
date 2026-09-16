import React from 'react';
import './Pages.css';

const Discovery = ({ id, title, children }) => (
  <section className="card" id={id}>
    <h3>{title}</h3>
    {children}
  </section>
);

const Documentation = () => {
  const toc = [
    ['introduction', '1. Introduction'],
    ['se-connecter', '2. Se connecter et naviguer'],
    ['tableau-de-bord', '3. Tableau de bord'],
    ['produits', '4. Produits'],
    ['clients', '5. Clients'],
    ['ventes', '6. Ventes (ventes, devis, bons de livraison, avoirs)'],
    ['factures', '7. Factures'],
    ['paiements', '8. Paiements'],
    ['stock', '9. Stock / Inventaire'],
    ['fournisseurs', '10. Fournisseurs'],
    ['achats', '11. Achats'],
    ['livraisons', '12. Livraisons'],
    ['rh', '13. Ressources Humaines'],
    ['comptabilite', '14. Comptabilité'],
    ['documents', '15. Documents & modèles PDF'],
    ['ia', '16. Assistant IA'],
    ['utilisateurs', '17. Utilisateurs'],
    ['roles-et-permissions', '18. Rôles & Permissions'],
    ['abonnement', '19. Abonnement'],
    ['paiement-et-vitrine', '20. Paramètres de paiement & vitrine'],
    ['profil', '21. Profil'],
    ['aide', '22. Aide & support'],
  ];

  return (
    <div className="page-container documentation-page">
      <div className="page-header">
        <div>
          <h1>Manuel d'utilisation — MIHAJA ERP PRO</h1>
          <p>Guide complet d'utilisation de l'application de gestion d'entreprise</p>
        </div>
      </div>

      <div className="card card--toc">
        <h3 id="sommaire">📑 Sommaire</h3>
        <ul>
          {toc.map(([id, label]) => (
            <li key={id}><a href={`#${id}`}>{label}</a></li>
          ))}
        </ul>
      </div>

      <Discovery id="introduction" title="1. Introduction">
        <p>
          <strong>MIHAJA ERP PRO</strong> est une solution de gestion complète pour les entreprises
          (PME, commerce, BTP, distribution…) : elle centralise vos produits, clients, ventes,
          factures, paiements, stock, achats, livraisons, ressources humaines, comptabilité et
          documents dans une seule application. Toutes les montants sont exprimés en Ariary (Ar).
        </p>
        <p>
          L'accès aux modules dépend de votre <strong>rôle</strong> (utilisateur, commercial,
          stock, comptable, RH, manager, administrateur, super-administrateur) et de votre{' '}
          <strong>plan d'abonnement</strong> (Gratuit, Pro, Entreprise). Chaque module n'est
          visible que si votre rôle possède les permissions correspondantes et que votre plan
          inclut ce module.
        </p>
        <p>Au lancement, vous atterrissez sur le <strong>Tableau de bord</strong>, votre vue d'ensemble quotidienne.</p>
      </Discovery>

      <Discovery id="se-connecter" title="2. Se connecter et naviguer">
        <h4>Connexion</h4>
        <ul>
          <li>Ouvrez l'application et renseignez votre <strong>identifiant</strong> (email ou nom d'utilisateur) et votre <strong>mot de passe</strong>.</li>
          <li>Si vous venez de créer le compte entreprise, le mot de passe initial vous est communiqué à l'inscription — pensez à le changer.</li>
          <li>Pour les comptes temporaires (<em>must change password</em>), le système vous demande de définir un nouveau mot de passe avant toute autre action.</li>
        </ul>
        <h4>La barre latérale</h4>
        <ul>
          <li>Le menu est organisé en <strong>groupes</strong> : <em>Piloter</em> (tableau de bord, produits, clients, ventes, factures, paiements), <em>Opérations</em> (stock, fournisseurs, achats, livraisons), <em>Gestion</em> (RH, comptabilité, documents, IA) et <em>Admin</em> (utilisateurs, rôles, permissions).</li>
          <li>Un module n'apparaît que s'il est autorisé par votre rôle et votre plan.</li>
          <li>Cliquez sur l'<strong>étoile</strong> d'un menu pour l'ajouter à vos <strong>favoris</strong> (affichés en tête de menu).</li>
          <li>Le bouton flèches réduit/élargit la barre latérale.</li>
          <li>Utilisez la <strong>recherche (⌘K / Ctrl+K)</strong> pour trouver rapidement un module.</li>
          <li>Le panneau de profil (en bas) donne accès au <em>Profil</em>, à l'<em>Abonnement</em>, aux <em>Paramètres de paiement</em>, au mode <em>clair/sombre</em> et à la <em>déconnexion</em>.</li>
        </ul>
        <h4>Astuces générales</h4>
        <ul>
          <li>De nombreuses listes proposent <strong>recherche, filtres avancés, tri par colonnes et export CSV</strong>.</li>
          <li>Les formulaires de création peuvent être sauvegardés en <strong>brouillon</strong> (restauré en cas de fermeture accidentelle).</li>
          <li>Les prix, marges et totaux sont calculés automatiquement (TVA comprise).</li>
        </ul>
      </Discovery>

      <Discovery id="tableau-de-bord" title="3. Tableau de bord">
        <p>Vue d'ensemble de l'activité en temps réel.</p>
        <ul>
          <li><strong>Indicateurs</strong> : produits au catalogue, clients actifs, ventes du jour, alertes stock (avec point rouge si stock critique).</li>
          <li><strong>Chiffre d'affaires du mois</strong> : graphique d'évolution sur 7 jours, meilleur jour annoté, tendance vs période précédente.</li>
          <li><strong>Top produits</strong> : les produits les plus vendus (quantité et valeur), lien vers Produits.</li>
          <li><strong>Activité récente</strong> : les 10 dernières ventes avec horodatage relatif.</li>
          <li><strong>À traiter cette semaine</strong> : alertes (stock critique, factures impayées, ventes du jour) avec liens directs vers Stock, Factures, Ventes.</li>
          <li><strong>Abonnement</strong> : widget avec plan, statut, date de fin et bouton Renouveler / Payer / S'abonner.</li>
          <li><strong>Actions</strong> : bouton <em>Exporter CSV</em> (télécharge les données), <em>Actualiser</em>, accès rapide à l'<em>Assistant IA</em>.</li>
        </ul>
      </Discovery>

      <Discovery id="produits" title="4. Produits">
        <p>Gérez votre catalogue produits et le suivi des stocks par article.</p>
        <h4>Créer / modifier un produit</h4>
        <ul>
          <li>Cliquez sur <strong>+ Ajouter un produit</strong> (ou l'icône crayon pour modifier).</li>
          <li>Renseignez : nom *, référence *, code-barres (mode auto ou manuel), catégorie, prix d'achat HT, prix de vente HT (la marge est calculée), quantité en stock, seuil d'alerte, unité, image (URL ou fichier), et l'état actif.</li>
          <li>Un produit peut être marqué <strong>inactif</strong> : il n'apparaît plus dans les sélections.</li>
        </ul>
        <h4>Suivre et filtrer</h4>
        <ul>
          <li>Indicateurs : total produits, stock critique, stock total, <strong>valeur du stock</strong> (prix d'achat × quantité).</li>
          <li>Recherche texte (nom, code-barres, référence) + filtre par catégorie + <strong>panneau de filtres avancés</strong> (prix, marge, stock, seuil…).</li>
          <li>Le <strong>badge de stock</strong> est coloré : vert (ok), orange (stock ≤ 1,5× seuil), rouge (stock ≤ seuil).</li>
          <li>Sélectionnez plusieurs lignes pour une <strong>action groupée</strong> (export CSV, suppression multiple).</li>
          <li>Le <strong>QR code</strong> est générable par produit.</li>
        </ul>
        <h4>Fiche produit publique</h4>
        <p>Le détail d'un produit est aussi visible sur la <strong>vitrine publique</strong> (« Ajouter au panier » si le stock le permet, sinon « Rupture de stock »).</p>
      </Discovery>

      <Discovery id="clients" title="5. Clients">
        <p>Gérez votre portefeuille de clients et prospects.</p>
        <ul>
          <li><strong>Ajouter un client</strong> : code client, type (boutique, épicerie, revendeur, semi-grossiste, grossiste, supermarché, restaurant, hôtel, entreprise, institution, particulier…), nom, prénom, email, téléphone, adresse, ville, pays (Madagascar par défaut), numéro TVA, etc.</li>
          <li>Indicateurs : total clients, entreprises, particuliers, <strong>panier moyen</strong>.</li>
          <li>Recherche (nom, prénom, email, code) et <strong>filtre par type de client</strong>.</li>
          <li>Le tableau affiche le type (badge coloré), le contact, le nombre de commandes et le total des achats.</li>
          <li>Modifier (crayon) ou supprimer (poubelle, avec confirmation) un client.</li>
        </ul>
      </Discovery>

      <Discovery id="ventes" title="6. Ventes">
        <p>Le module central des opérations commerciales, organisé en 4 onglets : <strong>Ventes</strong>, <strong>Devis</strong>, <strong>Bons de livraison</strong>, <strong>Avoirs</strong>.</p>
        <h4>Ventes</h4>
        <ul>
          <li><strong>Nouvelle vente</strong> : choisissez un client (ou activez « client passager » pour vendre sans client), la date, le mode de paiement (espèces, virement, chèque, MVola, Orange Money, Airtel Money), le type (Détail/Gros) et les lignes : produit, quantité, prix HT, TVA — le total TTC est calculé automatiquement.</li>
          <li><strong>Tarification intelligente</strong> : selon le type de client, le prix unitaire et le type de vente sont appliqués automatiquement (grossiste → prix de gros…).</li>
          <li><strong>Statuts de vente</strong> : en_attente, payée, partielle, annulée.</li>
          <li>À la création, l'application propose de <strong>générer la facture</strong> liée à la vente.</li>
          <li>Recherche et tri multi-colonnes (référence, client, date, total TTC, statut, type, mode).</li>
        </ul>
        <h4>Devis</h4>
        <ul>
          <li>Créez un devis : client, totaux HT/TTC, date de validité, conditions de paiement (30 jours par défaut), remarque.</li>
          <li><strong>Statuts</strong> : en_attente, accepté, refusé, converti, expiré.</li>
          <li><strong>Convertir en vente</strong> : un devis accepté se transforme en vente en un clic (le bouton devient inactif une fois converti).</li>
        </ul>
        <h4>Bons de livraison (BL)</h4>
        <ul>
          <li>Créez un BL lié à une vente : client, adresse de livraison, date prévue, remarque.</li>
          <li><strong>Statuts</strong> : à préparer, expédié, livré.</li>
        </ul>
        <h4>Avoirs</h4>
        <ul>
          <li>Créez un avoir : vente concernée, client, montants HT/TTC, motif.</li>
          <li><strong>Statuts</strong> : en_attente, accepté, remboursé, annulé.</li>
        </ul>
      </Discovery>

      <Discovery id="factures" title="7. Factures">
        <p>Suivi, création et encaissement des factures.</p>
        <ul>
          <li><strong>Nouvelle facture</strong> : choisissez la vente associée — le montant TTC est pré-rempli. La référence est générée automatiquement (ex : FAC-…). Date d'échéance et statut.</li>
          <li><strong>Enregistrer un paiement</strong> : montant (pré-rempli avec le reste dû), mode de paiement, date, remarque. Le bouton est masqué pour les factures déjà payées.</li>
          <li><strong>Statuts</strong> : en_attente, payée, partielle, annulée (badges colorés).</li>
          <li>Indicateurs : total factures, payées, en attente, <strong>total impayé</strong>.</li>
          <li>Dépliez une facture (chevron) pour voir ses <strong>lignes de vente</strong> (produit, quantité, prix HT, TVA, total).</li>
          <li><strong>Créer un document PDF</strong> : le bouton « JSON Documents » prépare automatiquement les données (client, articles, TVA, remise) et ouvre le module Documents pré-rempli.</li>
        </ul>
      </Discovery>

      <Discovery id="paiements" title="8. Paiements">
        <p>Liste des règlements encaissés et enregistrement de nouveaux paiements.</p>
        <ul>
          <li><strong>Ajouter un paiement</strong> : choisissez la facture (le client et le montant restant dû sont pré-remplis), le montant, le mode de paiement, la date, la remarque.</li>
          <li>Pour les modes <strong>MVola / Orange Money / Airtel Money</strong> : renseignez l'opérateur et le numéro de téléphone.</li>
          <li><strong>Statuts</strong> : en_attente, confirmé, échec, remboursé.</li>
          <li>Indicateurs : nombre de paiements, montant total encaissé, paiement moyen. Un paiement peut être supprimé.</li>
        </ul>
      </Discovery>

      <Discovery id="stock" title="9. Stock / Inventaire">
        <p>Suivi de l'inventaire et des mouvements de stock, avec 2 vues : <strong>Inventaire</strong> et <strong>Mouvements</strong>.</p>
        <h4>Inventaire</h4>
        <ul>
          <li>Indicateurs : total produits, stocks critiques, valeur du stock (Ar), unités totales.</li>
          <li>Badges colorés par rapport au seuil : vert (ok), orange (≤ 1,5× seuil), rouge (≤ seuil).</li>
          <li>Filtre rapide « stocks critiques », filtres avancés, export CSV.</li>
        </ul>
        <h4>Mouvements de stock</h4>
        <ul>
          <li><strong>+ Mouvement de stock</strong> : produit, type (Entrée ou Sortie), quantité, raison. Le stock du produit est mis à jour automatiquement.</li>
          <li><strong>Mouvement groupé</strong> : sélectionnez plusieurs produits et appliquez une même quantité (entrée/sortie).</li>
          <li>Chaque mouvement affiche un badge Entrée / Sortie et un historique daté.</li>
        </ul>
      </Discovery>

      <Discovery id="fournisseurs" title="10. Fournisseurs">
        <p>Annuaire des fournisseurs pour vos achats.</p>
        <ul>
          <li><strong>+ Ajouter un fournisseur</strong> : code, raison sociale, nom commercial, type de fournisseur, email, téléphone, SIRET, adresse, ville (Antananarivo par défaut), pays, contact (nom + email).</li>
          <li>Le tableau indique le nombre de produits par fournisseur et le chiffre d'affaires (Ar).</li>
          <li>Recherche texte (raison sociale, email, ville), modification et suppression.</li>
        </ul>
      </Discovery>

      <Discovery id="achats" title="11. Achats">
        <p>Gestion des <strong>commandes d'achat</strong> fournisseurs et des <strong>réceptions</strong> de marchandises (2 onglets).</p>
        <h4>Commandes d'achat</h4>
        <ul>
          <li>Créez une commande : fournisseur, totaux HT/TTC, statut, dates, conditions de paiement (30 jours par défaut), lignes au format JSON (une liste d'articles).</li>
          <li><strong>Statuts</strong> : brouillon, envoyée, confirmée, reçue, partiellement reçue, annulée.</li>
          <li>Modifier (le formulaire se recharge) ou supprimer une commande.</li>
        </ul>
        <h4>Réceptions</h4>
        <ul>
          <li><strong>+ Réception</strong> : choisissez la commande liée, la référence, la quantité reçue, la quantité commandée, une remarque.</li>
          <li>Les réceptions sont supprimables mais non modifiables.</li>
        </ul>
      </Discovery>

      <Discovery id="livraisons" title="12. Livraisons">
        <p>Logistique complète en 5 onglets : <strong>Livraisons</strong>, <strong>Livreurs</strong>, <strong>Véhicules</strong>, <strong>Itinéraires</strong>, <strong>Suivis</strong>.</p>
        <h4>Livraisons</h4>
        <ul>
          <li>Créez une livraison : vente et/ou commande client, itinéraire, livreur, véhicule, destinataire, adresse, ville, téléphone, date prévue, statut, notes.</li>
          <li><strong>Statuts</strong> : en_attente, chargée, en_route, livrée, retournée, échec.</li>
          <li><strong>Avancer le statut</strong> (flèche) : fait passer la livraison à l'étape suivante en un clic.</li>
        </ul>
        <h4>Livreurs</h4>
        <p>Prénom, nom, téléphone, email, n° de permis, statut (actif / inactif / en congés). Association d'un livreur à un compte utilisateur (ID).</p>
        <h4>Véhicules</h4>
        <p>Marque, modèle, plaque, type (camion / van / voiture / moto), capacité charge (kg), capacité volume (L), statut (disponible / en mission / en maintenance).</p>
        <h4>Itinéraires</h4>
        <p>Nom, description, dates de départ/retour, points intermédiaires (un par ligne), livreur, véhicule, statut (planifié / en cours / terminé / annulé).</p>
        <h4>Suivis (tracking)</h4>
        <p>Timeline chronologique de chaque livraison : statut, date, commentaire, géolocalisation (latitude/longitude). Ajoutez un suivi (statut + commentaire + position) à tout moment.</p>
      </Discovery>

      <Discovery id="rh" title="13. Ressources Humaines">
        <p>Gestion sociale en 5 onglets : <strong>Employés</strong>, <strong>Stagiaires</strong>, <strong>Présences</strong>, <strong>Salaires</strong>, <strong>Primes</strong>.</p>
        <h4>Employés</h4>
        <ul>
          <li><strong>+ Nouvel employé</strong> : infos personnelles (matricule, nom, prénom, sexe, naissance, adresse, contact), contrat (poste, département, type CDI/CDD/Stage/Freelance, statut, dates), rémunération & banque (salaire base, banque, IBAN, BIC).</li>
          <li><strong>Statuts</strong> : actif, inactif, en congés, départ.</li>
        </ul>
        <h4>Stagiaires</h4>
        <p>Matricule, identité, établissement, formation, type de stage (initiation, fin d'études, professionnel, apprentissage), dates, indemnité, tuteur (un employé), département, note.</p>
        <h4>Présences</h4>
        <ul>
          <li>Pointage par employé : date, heures d'arrivée/départ, pauses, statut, remarque.</li>
          <li><strong>Statuts</strong> : présent, absent, en retard, congé, maladie. Export CSV disponible.</li>
        </ul>
        <h4>Salaires</h4>
        <ul>
          <li><strong>+ Nouveau salaire</strong> : employé, mois, année, salaire de base, primes, indemnités, déductions, avances, mode et statut de paiement.</li>
          <li><strong>Générer les salaires</strong> (mois/année) : crée automatiquement les bulletins pour tous les employés actifs.</li>
          <li><strong>Marquer payé</strong> : confirme le règlement d'un salaire.</li>
          <li><strong>Statuts de paiement</strong> : payé, non payé, partiel. Export CSV disponible.</li>
        </ul>
        <h4>Primes</h4>
        <p>Employé, type (Performance, Ancienneté, Objectif, Exceptionnel), montant, date d'octroi, motif.</p>
        <p>Recherche commune : par nom, matricule, poste/département (employés) ou établissement/formation (stagiaires).</p>
      </Discovery>

      <Discovery id="comptabilite" title="14. Comptabilité">
        <p>Comptabilité générale en 5 onglets : <strong>Comptes</strong>, <strong>Écritures</strong>, <strong>Trésorerie</strong>, <strong>Résultats</strong>, <strong>Journal</strong>.</p>
        <h4>Comptes du plan comptable</h4>
        <ul>
          <li>Créez un compte : numéro (ex : 701), nom, type (<em>actif / passif / charge / produit</em>), compte parent (hiérarchie récursive).</li>
          <li><strong>Import CSV/Excel</strong> (aperçu des 6 premières lignes avant validation) et <strong>export CSV</strong>.</li>
        </ul>
        <h4>Écritures comptables</h4>
        <ul>
          <li>Date, compte, débit, crédit, libellé, référence externe, entité liée, pièce jointe.</li>
          <li><strong>Statuts</strong> : brouillon, validé, annulé — avec boutons Valider / Annuler.</li>
          <li>Import / export CSV.</li>
        </ul>
        <h4>Trésorerie</h4>
        <p>Mouvements d'entrée/sortie : date, type, montant, mode de paiement, libellé, compte bancaire, référence. Le <strong>solde</strong> est affiché en tête d'onglet.</p>
        <h4>Résultats</h4>
        <p>Sélectionnez une période (dates début/fin) et une granularité (jour / mois / année) : total produits, total charges, <strong>résultat net</strong> (vert si positif, rouge sinon), détail par période et par compte.</p>
        <h4>Journal</h4>
        <p>Vue chronologique des écritures, solde courant par ligne, résumé des soldes par compte, export CSV.</p>
      </Discovery>

      <Discovery id="documents" title="15. Documents & modèles PDF">
        <p>Créez des documents professionnels (factures, devis, contrats, bons de livraison, avoirs) à partir de modèles personnalisables (2 onglets : <strong>Modèles</strong> et <strong>Documents</strong>).</p>
        <h4>Créer un modèle</h4>
        <ul>
          <li>Nom, <strong>type de document</strong> (facture / devis / contrat / bon de livraison / avoir), contenu HTML avec des placeholders, logo (URL), mentions légales, conditions générales.</li>
          <li><strong>Placeholders</strong> : insérez des variables remplacées à la génération, par ex. <code>{'{'}client_nom{'}'}</code>, <code>{'{'}total_ttc{'}'}</code>.</li>
          <li>Cochez <em>Défaut</em> pour proposer ce modèle par défaut.</li>
        </ul>
        <h4>Générer un document</h4>
        <ul>
          <li>Sélectionnez un modèle *, une référence *, le type, l'<strong>entité liée</strong> (vente, facture, commande, abonnement) + son ID, puis les <strong>données JSON</strong>.</li>
          <li>Cliquez sur <strong>Générer le PDF</strong>. Le document apparaît dans la liste.</li>
          <li>Actions : <strong>Prévisualiser</strong> (aperçu PDF), <strong>Télécharger</strong>, <strong>Imprimer</strong>, <strong>Supprimer</strong>.</li>
          <li>Depuis une facture, le bouton « Créer JSON pour Documents » pré-remplit automatiquement le formulaire.</li>
        </ul>
      </Discovery>

      <Discovery id="ia" title="16. Assistant IA">
        <p>Assistant conversationnel qui interroge vos données ERP (stocks, ventes, clients, factures, prévisions).</p>
        <ul>
          <li>Posez une question en langage naturel ; l'IA répond avec l'historique complet de la conversation comme contexte.</li>
          <li><strong>Suggestions cliquables</strong> : état du stock, chiffre d'affaires, prévisions de ventes, top produits, factures impayées, nombre de clients.</li>
          <li>Les réponses sont rendues en Markdown et citent leurs <strong>sources</strong>.</li>
          <li>Actions : copier une réponse, <strong>Nouvelle conversation</strong> (effacer l'historique), suggestions de suivi.</li>
          <li>L'assistant peut recevoir un prompt pré-rempli depuis d'autres modules (icône IA).</li>
        </ul>
      </Discovery>

      <Discovery id="utilisateurs" title="17. Utilisateurs">
        <p>Gérez les comptes des collaborateurs de votre entreprise.</p>
        <ul>
          <li><strong>+ Nouvel employé</strong> : nom, prénom, identifiant, email, mot de passe (un <strong>mot de passe temporaire</strong> est affiché à la création), téléphone, rôle (utilisateur, manager, commercial, stock, comptable, RH), statut, ou rôle personnalisé.</li>
          <li><strong>Statuts</strong> : actif / inactif.</li>
          <li>La <strong>limite du plan</strong> (nombre max d'employés) est respectée automatiquement : le bouton d'enregistrement est bloqué quand elle est atteinte.</li>
          <li>Recherche et filtre par rôle ; modifications et suppression avec confirmation.</li>
        </ul>
      </Discovery>

      <Discovery id="roles-et-permissions" title="18. Rôles & Permissions">
        <h4>Rôles</h4>
        <ul>
          <li>Créez un rôle : nom (verrouillé en édition), nom d'affichage, description, rôle par défaut (check), et une <strong>grille de permissions</strong> à cocher, groupée par module.</li>
          <li>Utilisez un <strong>preset</strong> (admin, manager, commercial, stock, comptable, RH, utilisateur) pour pré-remplir les permissions.</li>
          <li>Les rôles <strong>système</strong> sont protégés (non supprimables).</li>
        </ul>
        <h4>Permissions</h4>
        <ul>
          <li>Liste des permissions système : code, module, action, description.</li>
          <li>Filtrez par module, par rôle ou via le filtre « Admin + Employés (Tenant) ».</li>
          <li>La colonne <strong>Rôles</strong> indique quels rôles possèdent chaque permission ; le badge <strong>Admin</strong> signale les permissions du rôle administrateur.</li>
        </ul>
      </Discovery>

      <Discovery id="abonnement" title="19. Abonnement">
        <p>Gérez votre plan, vos paiements et vos renouvellements.</p>
        <ul>
          <li><strong>Plans</strong> : Gratuit (3 utilisateurs, 2 employés), Pro (7 utilisateurs, 6 employés, assistant IA…), Entreprise (illimité, formation, SLA).</li>
          <li><strong>Statuts</strong> : ACTIF, EN_ATTENTE, EXPIRE — avec badges colorés.</li>
          <li><strong>Payer maintenant</strong> (statut en attente) : choix d'un moyen de paiement puis redirection vers la plateforme <strong>Papi</strong> (MVola, Orange Money, Airtel Money, etc.).</li>
          <li><strong>Renouveler / Passer à un plan payant</strong> : choisissez le plan et la méthode, un résumé compare l'ancien et le nouveau plan (des majorations d'expiration peuvent s'appliquer).</li>
          <li><strong>Paiement hors ligne</strong> : si demandé, un bulletin de paiement s'affiche avec la référence et les instructions.</li>
          <li>Consultez les consommations (utilisateurs/employés utilisés vs maximum) et l'historique des paiements dans cette page.</li>
        </ul>
      </Discovery>

      <Discovery id="paiement-et-vitrine" title="20. Paramètres de paiement & vitrine">
        <p>Configurez votre compte marchand <strong>Papi</strong> et votre vitrine publique MIHAJA.</p>
        <ul>
          <li>Renseignez la <strong>clé API Papi</strong> et éventuellement le <strong>secret webhook</strong>, choisissez l'environnement (<em>sandbox</em> ou <em>production</em>).</li>
          <li><strong>Tester la connexion</strong> : vérifie que la configuration est valide (badge « Configuré »).</li>
          <li><strong>Activer la vitrine</strong> : publie vos produits sur la vitrine publique MIHAJA (le toggle est désactivé sans configuration Papi).</li>
          <li><strong>Supprimer la configuration</strong> : efface la clé et désactive la vitrine.</li>
          <li>La configuration Papi n'est pas obligatoire pour utiliser l'application.</li>
        </ul>
      </Discovery>

      <Discovery id="profil" title="21. Profil">
        <p>Consultez et modifiez vos informations personnelles.</p>
        <ul>
          <li>Champs modifiables : nom, prénom, email, téléphone, mobile.</li>
          <li>Informations en lecture seule : votre rôle, votre identifiant, et les coordonnées de votre entreprise.</li>
          <li><strong>Enregistrer</strong> applique la modification (le profil est mis à jour partout).</li>
          <li><strong>Changer de compte</strong> : déconnexion vers l'écran de connexion (une confirmation est demandée).</li>
        </ul>
      </Discovery>

      <Discovery id="aide" title="22. Aide & support">
        <ul>
          <li>Parcourez ce manuel par sections via le <a href="#sommaire">sommaire</a>.</li>
          <li>Chaque module de l'application s'ouvre depuis la barre latérale ; en cas de doute sur un champ, lisez la section correspondante ci-dessus.</li>
          <li>Pour les questions liées à votre compte ou à votre abonnement, rendez-vous dans <a href="/subscription">Abonnement</a>.</li>
          <li>Pour les besoins techniques supplémentaires, contactez votre administrateur ou le support de la plateforme.</li>
        </ul>
      </Discovery>
    </div>
  );
};

export default Documentation;