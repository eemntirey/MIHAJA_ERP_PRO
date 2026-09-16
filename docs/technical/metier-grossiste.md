# Spécification : Météiers = Fonction de Grossiste

> **Statut :** V1 — audit vérifié dans le code le 2026-09-16.
> **Portée :** `web/backend` + `web/frontend`. Le desk (`desk/`) et `mobile/` suivront dans une V2.

## 1. Constat vérifié dans le code

Tous les "météiers" du projet ne correspondent pas à une vraie fonction de
grossiste. Audit direct (fichiers lus, pas une hypothèse) :

| Module | Fonction grossiste attendue | Verdict | Preuve |
|---|---|---|---|
| Produits | Prix multi-niveaux `grossiste < demi-gros < revendeur < détail` | OUI | `models/produit.py:63-65` + `utils/malagasy_data.py:104-106` |
| Ventes | Vente `gros / détail` | PARTIEL — faille | `models/vente.py:17` colonne `type_vente` ; `api/v1/ventes.py:17-24` modèle non exposé ; `vente_service.py:89-102` saisie manuelle de `prix_unitaire`, aucune auto-sélection |
| Clients | Chaîne de distribution | OUI | `models/client.py:6-17` 11 types + `plafond_credit` / `echeance_credit` 7/15/30j |
| Fournisseurs | Amont grossiste | OUI | `models/fournisseur.py:6-13` 7 types |
| Stocks / Entrepôts | Dépôts, seuils, valorisation | OUI | `models/produit.py:38-42`, `entrepot.py`, `stock_entrepot.py` |
| Achats | Réassort, réception, écart | OUI | `achat_service.py`, `achats_devis.py` |
| Livraison | Tournées distribution | OUI | `livreur.py`, `vehicule.py`, `itineraire.py`, `livraison.py` |
| Paiements | Espèces, Mobile Money, crédit | OUI | `models/paiement.py` + `mvola` / `orange_money` / `airtel_money` |
| RH / Compta / Documents / Dashboard / IA | Transverses | NEUTRE | Utiles à un grossiste mais non spécifiques |

### La faille « chaînage prix »

Les 3 prix existent en base (`prix_grossiste`, `prix_demi_gros`,
`prix_revendeur`) mais ne sont **jamais appliqués automatiquement** à la
vente selon `client.type` ou `type_vente`. Le vendeur saisit `prix_unitaire`
à la main → risque d'erreur de marge. `type_vente` est une colonne fantôme :
présente en base, invisible dans l'API (Flask-RESTx ne l'expose pas) et dans
l'UI (`pages/Sales.jsx` n'a aucun sélecteur gros/détail).

## 2. Règle métier implémentée : grille prix-client

Type de vente dérivé automatiquement du type de client :

| Type de client | `type_vente` | Niveau de prix appliqué |
|---|---|---|
| `grossiste` | `gros` | `prix_grossiste` |
| `semi_grossiste` | `gros` | `prix_demi_gros` |
| `revendeur` | `gros` | `prix_revendeur` |
| tous les autres (`boutique`, `epicerie`, `supermarche`, `restaurant`, `hotel`, `entreprise`, `institution`, `particulier`) | `detail` | `prix_vente_ht` |

Règles d'application dans `vente_service.create_with_lignes` :

1. `type_vente` non fourni → dérivé de `client.type` (tableau ci-dessus).
   Fourni → validé dans `{gros, detail}` sinon `ValueError` (HTTP 400).
2. Prix d'une ligne : si `prix_unitaire` est absent, `None` ou `0` →
   auto-sélection du niveau selon `type_vente` + `client.type`.
3. Un `prix_unitaire` explicite non nul est **toujours respecté**
   (surcharge manuelle possible).
4. Niveau absent sur un produit → repli en cascade : pour `gros`
   `prix_revendeur → prix_demi_gros → prix_grossiste → prix_vente_ht` ;
   pour `detail` → `prix_vente_ht`.

## 3. Honnêteté des seeds (décision : supprimer les faux-météiers)

`scripts/seed_entreprises.py` mélange vrais grossistes PGC et labels non
supportés par le schéma. Un métier doit être une vraie fonction du produit,
pas un label sur un modèle PGC. Décision : **supprimer** les tenants déguisés.

| Tenant seed | Avant | Après |
|---|---|---|
| `DistriFood Madagascar` | grossiste PGC | conservé |
| `GrosRiz Import` | grossiste PGC | conservé |
| `Epicerie Solidaire` | détaillant | supprimé (détaillant) |
| `Boutique en Ligne` | détaillant e-commerce | supprimé (détaillant) |
| `PharmaDistribution` | PGC déguisé en pharma (aucun lot/DLC/traçabilité) | supprimé |
| `Grossiste BTP` (README) | aucun produit/unité BTP dans le catalogue | retiré de la doc |
| `Tech Solutions / Green Import / DistriPlus / Global Trade / MegaStock` | tenants génériques multi-tenant (`reset_enterprise_passwords.py`) | conservés : infrastructure de test, pas une prétention de métier |

Si Pharma/BTP redevenaient un objectif produit, il faudra leur schéma propre
(lots/DLC/traçabilité ; unités/tonnage/m3), pas un label.

## 4. API et contrats

- `POST /api/v1/ventes/` : accepte (optionnel) `type_vente` ∈ `{gros, detail}`.
  Retourne `type_vente` dans la réponse.
- `GET /api/v1/ventes/` et `GET /api/v1/ventes/<id>` : `type_vente` présent dans
  chaque vente (via `Vente.to_dict`, déjà couvert par `BaseModel.to_dict`).
- `lignes[].prix_unitaire` devient optionnel dans le contrat Swagger : il
  reste accepté (surcharge) mais peut être omis (auto-sélection).
- `prix_grossiste`, `prix_demi_gros`, `prix_revendeur` déjà exposés par
  `GET /api/v1/produits/` (`Produit.to_dict` → `BaseModel.to_dict`).

## 5. Frontend (web/frontend uniquement pour cette V)

- Sélecteur **Type de vente** (Gros / Détail) dans `pages/Sales.jsx`.
- Sélection d'un client → `type_vente` proposé automatiquement selon son type.
- Changement de type de vente ou de client → re-calcul des `prix_unitaire` de
  toutes les lignes avec le niveau applicable.
- Colonne `Type` (Gros / Détail) dans le tableau des ventes et la vue détail.

## 6. Hors périmètre V1 (documenté pour plus tard)

- Desk Electron (`desk/src/pages/Sales.jsx`) et mobile.
- Spécificités Pharma (lot/DLC) et BTP (unités/tonnage).
- Sélection prix par seuil de quantité (ex. `>= X` cartons → niveau suivant).