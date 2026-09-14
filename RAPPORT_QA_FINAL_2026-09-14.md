# RAPPORT QA FINAL — Reprise post-audit du 14/09/2026 (campagne P0/P1)

Branche `V0` — commits `8c9c627f`, `ebdba42d`, `b103e0d0`, `35d29258`, `313f4cbf`.

## 1. Disponibilité (P0)

- **Module** : bootstrap backend + health-check
- **Cause racine** : aucun endpoint de santé dédié ; crash de démarrage possible (`too many values to unpack` sur `public_ns.resources`) bloquant le serveur avant l'écoute → tunnel `ERR_CONNECTION_CLOSED`.
- **Correction** : endpoints `/health`, `/ready`, `/monitor` (visibles depuis le tunnel) ; montage API robusté.
- **Fichiers** : `web/backend/app/__init__.py`, `web/backend/run.py`, `web/backend/app/realtime/socket_server.py`
- **Tests** : démarrage serveur validé (log watchdog : « Health: /health  Ready: /ready  Monitor: /monitor », écoute 0.0.0.0:5000).
- **Résultat** : **CONFIRMÉ** (serveur démarre et répond localement). Stabilité du *tunnel public* (infra externe) : **INCONNU** tant qu'une nouvelle inspection distante n'a pas été faite.
- **Risques restants** : instabilité du tunnel non corrigeable côté code ; à re-mesurer par réinspection externe.

## 2. Commande publique (P1 #2)

- **Cause racine** : échec silencieux de création (500 générique), commande non liée au compte connecté, tenant fallback manquant.
- **Correction** : POST `/public/commandes` fiabilisé (idempotence `Idempotency-Key` avec cache TTL borné, liaison `utilisateur_id` via JWT optionnel, fallback tenant, erreurs 4xx explicites).
- **Fichiers** : `web/backend/app/api/v1/public.py`, `web/backend/app/services/commande_service.py`, `web/frontend/src/pages/Checkout.jsx`
- **Tests** : suite publique backend PASS ; E2E navigateur sur tunnel à 8 500 Ar : **PROBABLE** (corrigé côté code, re-test externe requis une fois la dispo tunnel confirmée).
- **Critère d'acceptation** : panier valide + coordonnées + paiement livraison → 201 + référence affichée.

## 3. Connexion utilisateur simple (P1 #4)

- **Cause racine** : **double instance de React dans le bundle** (`shared/` résolvait `react` depuis le node_modules racine du monorepo) → « Invalid hook call » dans `AuthProvider` → session jamais posée, retour à /login.
- **Correction** : alias webpack `react`/`react-dom` vers `web/frontend/node_modules` ; cache webpack invalidé sur changement de `config-overrides.js`.
- **Fichiers** : `web/frontend/config-overrides.js`, `package.json`, `web/frontend/package.json`
- **Tests** : suite auth backend 2/2 PASS ; bundle web avec une seule instance React.
- **Résultat** : **CONFIRMÉ** côté build/backend ; navigation E2E : **PROBABLE**.

## 4. RH bloqué « Chargement… » (P1 #5)

- **Cause racine** : même crash React (Invalid hook call dans le provider partagé) → le fetch RH ne démarre jamais.
- **Correction** : fix React dupliqué (§3) + état d'erreur visible dans `HR.jsx` (plus de spinner infini).
- **Résultat** : **CONFIRMÉ** côté cause racine ; écran RH final : **PROBABLE** (re-test UI requis).

## 5. Redirections silencieuses (P1 #3)


## 6. Doublons de factures (P1 majeur #6)

- **Cause racine** : `Invoices.jsx` générait une référence aléatoire par clic et `issue_invoice` ne vérifiait pas l'unicité par `vente_id` → 3 factures (#5/#6/#7) pour la même vente.
- **Correction** :
  - Backend : `issue_invoice` refuse un 2e POST sur la même vente (`FactureDejaExistante`) ; POST `/factures/` renvoie **409 avec la facture existante** (jamais 500), 400 explicite sur payload invalide.
  - Frontend : verrou `submitting` (double-clic impossible), boutons désactivés pendant l'envoi, 409 traité avec affichage de la référence existante.
  - Checkout : clé `Idempotency-Key` **stable par intention de commande** (useRef, réutilisée sur retry/refresh, régénérée seulement après succès).
- **Fichiers** : `web/backend/app/services/facturation_service.py`, `web/backend/app/api/v1/factures.py`, `web/frontend/src/pages/Invoices.jsx`, `web/frontend/src/pages/Checkout.jsx`, `web/backend/tests/test_facturation_idempotence.py`
- **Tests exécutés** : `pytest tests/test_facturation_idempotence.py` → **3 passed** (double soumission → 1 seule facture ; payload invalide → 400 ; ventes distinctes → 2 factures).
- **Résultat** : **CONFIRMÉ**.
- **Critère d'acceptation** : impossible de créer 2 factures actives pour la même vente (double-clic, retry réseau, 2 onglets du même tenant).

## 7. Validation serveur 4xx (P1 majeur #7)

- **Correction** : prix/stock/seuils négatifs → 400 avec message exploitable ; JSON invalide sur commande publique → 400 explicite (`get_json(silent=True)`, commit `313f4cbf`).
- **Fichiers** : `public.py`, `comptabilite.py`, services produits/ventes.
- **Résultat** : **CONFIRMÉ** (aucun 500 sur saisie invalide dans les suites ciblées).

## 8. Quotas & mappings (P1 majeur + autres)

- Quota affiché **avant** l'action bloquante (Subscription + banners Clients/Products) — **CONFIRMÉ**.
- Avoirs : `client_id: 10` → nom client réel (mapping réparé) — **CONFIRMÉ**.
- Paiements : mode réel (MVola/Orange/Airtel/BRED/espèces) au lieu de « especes » — **CONFIRMÉ**.
- Date de validité devis vide : plus de double message contradictoire — **PROBABLE** (re-test UI).
- i18n malgache complétée ; panier stabilisé catalogue ↔ fiche produit — **PROBABLE** (re-test UI).

## Ne pas régresser (inchangés, validés par la suite existante)

Isolation multi-tenant (404 cross-tenant), limites plan gratuit (10 clients / 10 produits → 403 backend), vente TVA/MVola avec décrément stock, RBAC personnalisé, reset mot de passe sans énumération de comptes.

## Bilan tests

| Suite | Résultat |
|---|---|
| `pytest tests/` (complète, pré-commit backend) | PASS (exit 0) |
| `pytest tests/test_facturation_idempotence.py` | 3 passed |
| `pytest tests/test_auth.py` | 2 passed |
| `py_compile` (tous fichiers backend modifiés) | OK |
| Démarrage serveur dev (watchdog reload) | OK, health endpoints visibles |

## Statut global

- P0 disponibilité application : **CONFIRMÉ** / tunnel public : **INCONNU** (infra, à re-mesurer).
- P1 commande publique / login / RH : corrections **CONFIRMÉES** (code + tests backend) ; revalidation E2E externe : **PROBABLE** requise.
- Idempotence factures : **CONFIRMÉ** (tests dédiés verts).

- **Correction** : `/inventory`, `/purchases`, `/delivery`, `/accounting`, `/documents`, `/ai` affichent un écran explicite (403 / module absent) dérivé de la matrice de permissions backend→frontend, au lieu de rediriger vers le dashboard.
- **Fichiers** : `web/frontend/src/App.js`, `shared/navConfig.js`, `shared/utils/navPermissions.js`
- **Résultat** : **CONFIRMÉ** (code + navigation locale).
