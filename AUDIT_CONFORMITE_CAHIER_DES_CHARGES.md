# Audit de conformité — Cahier des charges TIA INFO WHOLESALE

> Audit réalisé le 2026-09-11 via graphify (graphe `graphify-out/`, 5 254 nœuds) + lecture directe des modèles, API et pages.
> Périmètre : `web/backend`, `web/frontend`, `desk` (Electron), `shared`, `super-admin`.

## Verdict global : ~93 % conforme

Tous les modules opérationnels du cahier des charges existent en backend + frontend web + desktop Electron.
4 écarts résiduels identifiés (voir section « Écarts »).

---

## 1. Modules conformes (vérifiés dans le code)

### 1.1 Gestion des Produits ✅
`app/models/produit.py` :
- Catégories : `categorie`, `sous_categorie`, `famille` ✅
- Marques : `marque`, `modele` ✅ · Unités : `unite` ✅
- Codes-barres : `code_barre`, `code_interne` + `utils/barcode_generator.py` ✅
- QR Code : `qr_code_data` + `utils/qr_generator.py` ✅ · Photos : `image_url` ✅
- Prix : `prix_achat_ht/ttc`, `prix_vente_ht/ttc`, `prix_grossiste`, `prix_revendeur`, `prix_demi_gros`, `taux_tva`, `marge_standard` ✅
- Frontend : QR/code-barre affichés dans `Products.jsx` et `Inventory.jsx` (web + desk) ✅

### 1.2 Gestion des Fournisseurs ✅
`fournisseur.py`, `commande_fournisseur.py`, `facture_fournisseur.py`, `paiement.py` (FK `fournisseur_id`), `fournisseur_service.py`, API `fournisseurs.py`. Historique via commandes/factures/paiements liés. ✅

### 1.3 Gestion des Achats ✅
`commande_achat.py`, `ligne_achat.py`, services `CommandeAchatService` + `ReceptionAchatService`, API `achats_devis.py`.
- Bons de commande ✅ · Réception avec contrôle d'écart `quantite_recue` vs `quantite_commandee` (`Purchases.jsx`) ✅
- Entrée en stock automatique à la réception (MouvementStock ENTREE) ✅ · Historique ✅

### 1.4 Gestion des Stocks ✅ (2 réserves, voir écarts)
`stock.py` : `MouvementStock` — types `ENTREE, SORTIE, INVENTAIRE, AJUSTEMENT, RETOUR, TRANSFERT` ✅
- Inventaire ✅ · Alertes `seuil_alerte` + `seuil_critique` ✅ (≈ stock minimum)
- Valorisation : `Produit.valeur_stock` = `quantite_stock × prix_achat_ht` ✅
- ❌ Multi-entrepôts : absent (uniquement `emplacement/rayon/etagere`)
- ❌ Stock maximum : aucun champ `stock_max`

### 1.5 Gestion des Clients ✅
`client.py` : 11 types dont `boutique`, `revendeur`, `semi_grossiste`, `grossiste`, `entreprise` (+ epicerie, supermarche, restaurant, hotel, institution, particulier) ✅
- Historique : relation `ventes` + paiements ✅ · Solde : `solde`, `plafond_credit`, `echeance_credit`, `points_fidelite` ✅

### 1.6 Gestion des Ventes ✅
`vente.py` (`type_vente` = gros/detail ✅), `facture.py`, `devis_avoir_bl.py` avec `DevisService`, `BonLivraisonService`, `AvoirService` (retours) ✅ — API `ventes.py` + `achats_devis.py`.


### 1.7 Paiements ✅
`paiement.py` : `mode_paiement` especes / virement / cheque / mvola / orange_money / airtel_money ✅
- Paiement partiel : `date_echeance`, statut facture recalculé (`_recompute_facture_status`) ✅
- Intégration PAPI (mobile money) : `papi.py`, `ProviderPaiement` ✅

### 1.8 Comptabilité ✅ (réserve sur « Résultats »)
`compte_comptable.py`, `ecriture_comptable.py`, `tresorerie.py`.
- Recettes/Dépenses : `TypeTresorerie` = `ENTREE` / `SORTIE` ✅
- Journal : endpoint `/ecritures/journal` + vue frontend ✅ · Trésorerie ✅
- ⚠️ « Résultats » : pas d'endpoint dédié ; données dérivables du journal/trésorerie.

### 1.9 Livraison ✅
`livreur.py` (chauffeurs), `vehicule.py`, `itineraire.py`, `livraison.py`, `suivi_livraison.py`, `livraison_service.py`, API `livraisons.py`, pages `Delivery.jsx` + `Suivi.jsx`. ✅

### 1.10 Ressources Humaines ✅
`employe.py`, `salaire.py`, `presence.py`, `prime.py` (+ `stagiaire.py`), API `rh.py`/`employes.py`, page `HR.jsx`. ✅

### 1.11 Documents ✅
`modele_document.py`, `document_genere.py`, `utils/modeles_systeme.py` (modèles seed : facture, devis, **contrat**, bon_livraison, avoir), `utils/pdf_generator.py`, API `documents.py`, page `Documents.jsx`. ✅

### 1.12 Tableau de bord ✅
`services/dashboard_service.py` + API `dashboard.py` :
- Ventes du jour / mensuelles ✅ · CA (`ca_total`, `ca_mois`, `panier_moyen`) ✅ · Bénéfice (`benefice_mois`) ✅
- Produits populaires (`top_products`) ✅ · Clients actifs (`top_clients`) ✅
- Évolution des ventes (`evolution_ventes`, 7 jours) ✅ · Alertes (`alertes_stock`) ✅
- Créances (`creances_clients`) ✅ · Fournisseurs (`nombre_fournisseurs`) ✅

### 1.13 Intelligence Artificielle (Premium) ✅
`app/ai/` : `ai_predictions.py` (`predict_sales`, `predict_stock_rupture`) ✅, `recommendations.py` (`suggest_reorders` = réapprovisionnement) ✅, `anomalies.py` (détection) ✅, `assistant.py` (conversationnel) ✅, `ai_insights.py` (tableau de bord intelligent) ✅, API `ai.py` (`/ai/stock-ruptures`, `/ai/assistant`, `/ai/anomalies`…), gating par domaines/permissions (`ai_permissions.py` : `can_access_domain`, `require_domain_access`). ✅

### 1.14 Sécurité ✅ (réserve sur la planification des backups)
- Authentification JWT (access + refresh, blocklist tokens) ✅ · Gestion des rôles : `roles.py`, `permissions.py`, `role_permission.py`, RBAC granulaire ✅
- Journal des activités : `audit_log.py` (25+ types d'actions) + `utils/audit.py` ✅
- Chiffrement : `security/encryption.py` + `password_policy.py` + `rate_limit.py` ✅
- Sauvegarde : `tasks/backups.py` (snapshot SQLite WAL-safe, rétention 7 jours, fallback pg/mysqldump) ✅ — ⚠️ Celery configuré (`CELERY_BROKER_URL`) mais **pas de beat schedule** dans la config → l'exécution « automatique » repose sur un ordonnancement externe.

---

## 2. Écarts identifiés (4)

| # | Élément manquant | Constat | Impact | Effort suggéré |
|---|---|---|---|---|
| E1 | **Multi-entrepôts** | Aucune occurrence de « entrepot/warehouse » dans tout le repo | Stock global par produit ; impossible de ventiler par dépôt | Modèle `Entrepot` + FK sur `MouvementStock`/`Produit` + écrans |
| E2 | **Stock maximum** | Aucun champ `stock_max` | Pas de plafond ni d'alerte de sur-stock | Colonnes `stock_min`/`stock_max` (mapper `seuil_alerte`→min) + alerte sur-stock |
| E3 | **Résultats comptables** | Pas d'endpoint/modèle dédié | Résultat = calcul manuel via journal/trésorerie | Endpoint `/comptabilite/resultats` (produits-charges par période) |
| E4 | **Version Mobile native/PWA** | `manifest.json` présent (PWA nominale) **mais** service workers désenregistrés activement dans `web/frontend/src/index.js` L8-14 ; aucune app mobile (React Native/Flutter) | Mobile = responsive web uniquement ; pas d'offline ni d'installation | Réactiver le service worker + manifest complet (icônes, offline), ou app mobile dédiée (Consultation/Vente/Inventaire/Livraison) |

## 3. Remarques mineures
- « Contrôle » des achats : assuré par comparaison quantité reçue/commandée à la réception (pas de contrôle qualité par lot — suffisant pour le périmètre).
- Sauvegarde automatique : ajouter un `celery beat schedule` ou un cron externe appelant `backup_database`.
- Le desktop (`desk/`) partage le code React avec le web : toute nouvelle fonctionnalité est disponible sur les deux plateformes.
