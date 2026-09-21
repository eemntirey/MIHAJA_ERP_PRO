# PROMPT COMPLET — Correction des défauts du TEST FINAL (parcours réels localhost, 18/09/2026)

> À donner tel quel à un agent de codage (ou à un développeur) travaillant dans ce dépôt.
> Objectif : corriger **tous** les défauts B1→B3 et F1→F12 du rapport `test_Final.md`, sans régression,
> en respectant les conventions existantes du projet MIHAJA ERP PRO.

---

## 0. Rôle et mission

Tu es ingénieur full-stack senior sur **MIHAJA ERP PRO** (ERP commercial multi-tenant, Madagascar, MGA, UI en français).
Ta mission : rendre les parcours utilisateurs réels décrits dans `test_Final.md` **fonctionnels et compréhensibles**,
du formulaire de vente jusqu'à la facture, en passant par la déconnexion, la vitrine publique et les messages d'erreur.

Contraintes de mission :
- Corriger **la cause racine**, jamais masquer le symptôme.
- Diff minimal et idiomatique, aligné sur le code existant (pas de refonte, pas de nouvelle lib sans nécessité).
- Zéro régression : suite `pytest` verte, build frontend OK, isolation multi-tenant préservée.
- Chaque correction est **prouvée** (commande + résultat observé) et **testée** (test automatisé quand c'est possible).
- Livrable final = rapport structuré (voir §5), pas seulement du code.

---

## 1. Contexte projet à maîtriser AVANT de coder

### 1.1 Architecture et ports
| Composant | Chemin | Port / Lancement |
|---|---|---|
| Backend Flask (RESTx, SQLAlchemy, Celery, Socket.IO) | `web/backend` | `:5000` — dev server, Swagger `/docs` |
| Frontend web React 18 (CRA + `react-app-rewired`) | `web/frontend` | `:3000`, proxy `/api` → `:5000` |
| Desk Electron 38 + Vite | `desk` | `:3001`, `npm run electron:dev` |
| Console super-admin (Vite) | `super-admin` | `:3002` |
| Mobile React Native / Expo | `mobile` | — |
| Bibliothèque partagée (auth, storage, sync, RBAC nav) | `shared/` | importée par **web ET desk** |

Règles structurantes (AGENTS.md, à respecter strictement) :
- `shared/navConfig.js` et `shared/utils/navPermissions.js` sont **la source unique de vérité** navigation/RBAC : **ne jamais les dupliquer par application**.
- `shared/contexts/AuthContext.jsx` et `shared/services/api.js` sont partagés web/desk : toute modification impacte les deux clients.
- Web s'authentifie par **cookies HttpOnly**, Electron/desk par `Authorization: Bearer` ; le backend accepte les deux (`JWT_TOKEN_LOCATION = ['cookies', 'headers']`).
- Multi-tenant : presque tous les modèles portent `tenant_id` ; `web/backend/app/security/tenant.py` ajoute le filtre `tenant_id = <courant>` à **tous** les SELECT ; contournement uniquement via `execution_options(_skip_tenant_filter=True)` ; `SUPER_ADMIN` a `tenant_id = NULL` et n'est pas filtré. Réutiliser les décorateurs existants (`app/security/tenant.py`, `app/security/roles.py`) — jamais réimplémenter.
- Migrations Alembic dans `web/backend/migrations`, pilotées par `flask --app 'app:create_app' db ...`.
- SUPER_ADMIN créé via `python manage.py create-superadmin` → `scripts/create_superadmin.py` (source unique).
- Messages destinés à l'utilisateur, erreurs d'API et commentaires : **en français** (y compris les nouveaux).

### 1.2 Environnement d'exécution / commandes utiles
- OS **Windows / PowerShell** ; dépôt `c:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO` ; branche `V0`.
- PostgreSQL local via Docker : conteneur `erp-pg` sur `localhost:55432` (base `erp`, base de tests `erp_test`).
- Dépendances Python : `pip install -r web/requirements.txt` (attention : `web/`, pas `web/backend/`).
- Backend : `python run.py` depuis `web/backend` (⚠️ `create_app()` lève `ValueError` si `SECRET_KEY` ou `JWT_SECRET_KEY` manque → un `.env` est requis ; `FLASK_ENV=production` refuse SQLite, le debug et `/docs`).
- Frontend : `npm start` dans `web/frontend`. ⚠️ `web/frontend/config-overrides.js` alias `@shared` → `shared/` racine et fixe une copie unique de `react`/`react-dom` ; après modification, purger le cache webpack sinon bundle obsolète / « Invalid hook call ».
- Tests backend : `cd web/backend; pytest` (nécessite PostgreSQL ; l'isolation est un SAVEPOINT par test, `db.drop_all` est monkeypatché en `reset_schema` dans `tests/conftest.py` à cause de cycles de FK ; **ne jamais hardcoder d'identifiants DB dans les tests** — un ancien secret scanné a cassé la suite).
- Tests E2E : Playwright (`.github/workflows/playwright.yml`) ; à la racine, des scripts existants (`test_e2e_unified.js`) peuvent servir de base.
- Graphify : après modification de code, `graphify update .` (AST-only). Pour une question de code, préférer `graphify query "<question>"`.

### 1.3 État de départ à reprendre (constaté pendant le test)
- Backend **stable** : `/health`, `/ready`, `/docs` OK, erreurs API propres et en français, isolation tenant OK, décrément de stock après vente OK (50 → 48).
- Tenant de test : **TOVOHERY** (abonnement « gratuit » `ACTIF` jusqu'au 18/10/2026, 1 produit publié).
- Comptes créés pour le test (mot de passe `Test1234!`) : `admin_test@mihaja.test`, `user_test@mihaja.test`, `sales_test@mihaja.test`, `sa_test@mihaja.test`.
- Les comptes « démo » du README ne répondent à aucun mot de passe documenté (voir **F10**).

---

## 2. Méthode de travail imposée

### 2.1 Boucle par défaut (obligatoire)
1. **Reproduire** le défaut avec la commande/le parcours exact indiqué dans la fiche.
2. **Localiser la cause racine** (pas le symptôme) ; si le rapport donne une cause, la **vérifier** et la corriger, sans la prendre pour argent comptant.
3. **Corriger** avec le diff le plus petit possible, en respectant les conventions (français, tenant, RBAC, composants UI existants).
4. **Tester** : test backend (`pytest`) et/ou test frontend, plus vérification manuelle (navigateur/curl/console).
5. **Consigner** : fiche remplie (voir §5) avec preuve avant/après.
6. Une fois le lot terminé : `graphify update .` puis `pytest` complet, puis build frontend.

### 2.2 Règles de correction transverses
- **Frontend React** : le projet utilise `react-hook-form` (`register`, `setValue`, `watch`, `useFieldArray`) + `yup` (schémas dans `web/frontend/src/schemas/validationSchemas.js`). Ne jamais poser un `onChange` **après** un `{...register(...)}` : soit on intègre le handler **avant** le spread qu'il complète, soit on utilise la forme `register('champ', { onChange })`, soit on passe par `setValue`/`Controller`.
- **Corrections à appliquer identiquement dans `desk/src/pages/Sales.jsx`** quand le même bug y existe (le desk duplique la logique du web : `desk/src/pages/Sales.jsx` lignes ~250, ~319, `handleClientChange`/`handleProduitChange`). Ne pas dupliquer les *helpers partagés*, mais corriger les deux écrans.
- **Backend** : toute route protégée doit passer par les décorateurs existants (`app/security/tenant.py`, `app/security/roles.py`, `app/security/rate_limit.py`). Ne pas contourner le filtre tenant ; si un accès cross-tenant est nécessaire (ex. SUPER_ADMIN, vitrine publique), le faire explicitement via `_skip_tenant_filter=True` en le justifiant en commentaire français.
- **Migrations** : tout changement de modèle passe par une révision Alembic (`flask --app 'app:create_app' db migrate -m "..."` puis `db upgrade`), jamais par `create_all` en base existante.
- **Idempotence** : toute génération automatique (facture) doit être idempotente (une facture active max par vente) ; cf. `tests/test_facturation_idempotence.py` existant.
- **Langue** : nouveaux libellés UI, messages d'erreur API et commentaires **en français**, avec accents corrects (voir F6).
- **Aucune régression** : ne pas casser `tests/test_parcours_ventes_stocks_papi.py`, `tests/test_facturation_idempotence.py`, ni la vitrine publique existante.

---

## 3. Bloquants à corriger (P0)

### B1 — Formulaire de vente inutilisable (aucun POST envoyé)
**Fichiers** : `web/frontend/src/pages/Sales.jsx` (lignes ~320-328 produit, ~250-258 client) et `desk/src/pages/Sales.jsx` (lignes ~250, ~319).
**Symptôme** : clic sur « Créer » sans requête POST ; erreur affichée dans la cellule produit :
`lignes[0].produit_id must be a 'number' type, but the final value was: NaN (cast from the value "")`.
**Cause** : `onChange={(e) => handleProduitChange(index, e.target.value)}` est déclaré **après** `{...register('lignes.<i>.produit_id')}` et **écrase** donc le `onChange` de react-hook-form → RHF ne reçoit jamais la valeur, le champ reste `''`, le cast yup échoue en `NaN`. Idem pour le `<select>` client plus haut.

**Travail demandé**
1. Corriger l'ordre/la composition des handlers sur le `<select>` produit **et** le `<select>` client (web **et** desk).
2. S'assurer que la valeur du `<select>` est bien liée à RHF et que `setValue` (prix HT, TVA, prix selon type de vente) continue de fonctionner.
3. Vérifier que le schéma de validation accepte bien un `produit_id` numérique issu d'un `<select>` (typiquement coercition `yup.number().required()`), et que `client_id` nullable reste cohérent avec `client_passager`.
4. **Preuve attendue** : création d'une vente **depuis l'UI web** (client + produit + quantité) → POST `201` visible dans l'onglet réseau, vente listée, stock décrémenté, dashboard mis à jour. Ajouter si possible un test de non-régression qui valide le parcours (Playwright existant, ou test unitaire sur la composition des props du select).

### B2 — Bouton de déconnexion introuvable / sans effet
**Fichiers** : `shared/contexts/AuthContext.jsx` (`logout`, lignes ~278-299), `web/frontend/src/components/layout/TopBar.jsx` (bouton `title="Déconnexion"` → `onLogout`), `DesktopSidebar.jsx`, `MainLayout.jsx`, `DesktopLayout.jsx`, `shared/services/api.js` (`authService.logout`), `web/backend/app/api/v1/auth.py` (route de logout + cookies).
**Symptôme** : après connexion (dashboard complet), aucun élément cliquable « Se déconnecter » identifiable ; navigation forcée vers `/login` → l'utilisateur reste authentifié ; seul le vidage manuel des cookies déconnecte.

**Travail demandé**
1. Reproduire et déterminer la cause exacte : bouton absent du DOM (rendu conditionnel/masqué par CSS), non atteignable (sidebar repliée / menu utilisateur non déplié), ou handler cassé.
2. Rendre la déconnexion **discoverable** et **fonctionnelle** :
   - bouton/menu utilisateur visible dans la coque (TopBar **et** rail latéral) avec `aria-label="Se déconnecter"` et une icône `ti-logout` ;
   - `logout()` du contexte partagé doit nettoyer l'état local **et** faire invalider la session côté serveur.
3. **Côté backend** : vérifier que la route de logout efface réellement les cookies HttpOnly (`unset_jwt_cookies` / `clear_jwt_cookies` / `delete_cookie` pour `access_token_cookie`, `refresh_token_cookie`, `csrf_access_token`, `csrf_refresh_token`) et qu'elle est appelable avec le cookie seul (web) comme avec le bearer (desk). Corriger si l'un des cookies persiste.
4. Vérifier qu'après logout, un appel à un endpoint protégé (ex. `GET /api/v1/auth/me` ou les stats du dashboard) renvoie bien **401**, et que `/login` n'affiche plus l'utilisateur.
5. **Preuve attendue** : en-têtes `Set-Cookie` d'expiration visibles + 401 après logout ; un `user_test` peut se connecter juste après sur le même navigateur.

### B3 — Le serveur CRA (port 3000) s'arrête seul
**Symptôme** : le process node/CRA disparaît 2 fois pendant le test ; le log `/tmp/cra_3000.log` se termine sur « webpack compiled successfully » + warning `util._extend` ; le navigateur affiche `chrome-error://chromewebdata`.

**Travail demandé** (diagnostic puis garde-fous, pas de « fix » à l'aveugle)
1. Reproduire avec instrumentation : lancer le frontend avec log verbeux et suivi mémoire, ex. sous PowerShell
   `$env:NODE_OPTIONS='--max-old-space-size=4096'; npm start 2>&1 | Tee-Object -FilePath cra_3000.log`
   et surveiller périodiquement l'usage mémoire (`Get-Process node | Select-Object Id,WS,PM`).
2. Trancher entre les hypothèses : OOM node, conflit de watchers (nombre de fichiers/`watchman`), arrêt du terminal parent (le process est enfant du shell), antivirus/OneDrive sur `node_modules`, cache webpack corrompu.
3. Appliquer le correctif adapté au diagnostic :
   - OOM → `NODE_OPTIONS=--max-old-space-size=...`, nettoyer `web/frontend/node_modules/.cache`, réduire le périmètre de watch ;
   - watchers → exclusions `.watchmanconfig`, ou `WATCHPACK_POLLING` ;
   - arrêt du parent → documenter le lancement en fenêtre dédiée (et/ou script `.ps1` qui relance), afin que le mode opératoire soit reproductible.
4. **Rapporter la cause réelle constatée** (pas seulement des hypothèses) et documenter la procédure de démarrage fiable, y compris la purge du cache webpack après toute modification de `config-overrides.js` (sinon bundle obsolète / « Invalid hook call »).

---

## 4. Incohérences fonctionnelles à corriger (P1 → P2)

### F1 — Vitrine publique muette alors que l'abonnement est ACTIF (P1)
**Fichiers** : `web/backend/app/models/tenant.py` (`is_vitrine_active`, colonnes `vitrine_enabled`/`vitrine_enabled_at`), `web/backend/app/api/v1/public.py`, `web/backend/app/api/v1/tenant_papi.py`, `super-admin/src/pages/PaymentSettings.jsx`, `web/frontend/src/pages/Dashboard.jsx`, `web/frontend/src/pages/Subscription.jsx`.
**Symptôme** : accueil public → « Aucun produit disponible pour le moment. Aucun vendeur n'est actif. » alors que TOVOHERY a un abonnement `ACTIF` jusqu'au 18/10/2026 et un produit publié.
**Réalité** : l'exposition exige **3 conditions cumulatives** — abonnement actif non expiré **+** clé marchand Papi configurée **+** `vitrine_enabled=True`. Nulle part l'UI n'explique ce prérequis.

**Travail demandé**
1. **Côté marchand (dashboard)** : ajouter un état explicite « Vitrine publique » avec les **raisons** de non-exposition, calculées par le backend (ne pas réimplémenter la logique côté React). Prévoir une route back renvoyant un diagnostic du type :
   `{ 'vitrine_active': bool, 'vitrine_enabled': bool, 'abonnement_actif': bool, 'papi_configure': bool, 'raisons': ['Papi non configuré', 'Vitrine non activée', ...] }`
   Réutiliser/centraliser la logique de `Tenant.is_vitrine_active()` (ex. méthode `vitrine_status()` sur le modèle ou fonction du service) pour rester **DRY** avec `_get_active_tenant_ids()`.
2. **Côté UI marchand** : afficher ce diagnostic (dashboard et/ou page abonnement + paramètres paiement) avec un lien d'action direct vers la configuration Papi / le toggle vitrine (`tenant_papi`). Chaque raison doit être lisible par un non-technicien.
3. **Côté message public** : corriger le libellé trompeur « Aucun vendeur n'est actif » → formulation neutre et exacte, p.ex. « Aucun produit n'est actuellement disponible à la vente. » (ne pas révéler d'informations internes du tenant).
4. **Preuve attendue** : avec Papi non configuré / toggle off, le dashboard affiche les raisons exactes ; après configuration + toggle on, la vitrine expose le produit.

### F2 — Colonne « CODE » des produits = ID SQL au lieu de la référence (P1)
**Fichier** : `web/frontend/src/pages/Products.jsx`, ligne ~190 : `accessor: (row) => row.code_barre || row.id`.
**Symptôme** : produit créé avec référence `RIZ-25`, la table affiche `CODE = 1` ; la référence métier n'apparaît nulle part.

**Travail demandé**
1. Faire afficher la **référence métier** (`reference`) en priorité, puis le code-barre, et **jamais** l'ID SQL comme identifiant métier.
2. Si aucune référence n'existe, afficher un état explicite (« — » ou « Non renseignée ») ou générer/garantir une référence à la création (voir point 3), mais **ne pas** retomber sur `id`.
3. **Décider et implémenter** où la référence est produite : soit saisie obligatoire à la création, soit génération automatique côté backend (en respectant le mode « Manuel » / code-barre existant et `web/backend/app/models/produit.py`). Si un changement de modèle/contrainte est nécessaire → migration Alembic.
4. Contrôler les autres colonnes/écrans utilisant ce même raccourci `|| row.id` (recherche globale) et les corriger de la même façon.
5. **Preuve attendue** : la table Produits affiche `RIZ-25` pour le produit de test, et la recherche/scan ne renvoie plus « 1 ».

### F3 — Aucune facture générée après une vente (P1)
**Fichiers** : `web/backend/app/api/v1/ventes.py`, `web/backend/app/services/vente_service.py`, `web/backend/app/services/facturation_service.py` (`generate_from_vente`), `web/frontend/src/pages/Invoices.jsx`.
**Symptôme** : vente `VENT-20260918035615-8352` créée, mais page Factures vide ; facture à créer manuellement. L'API accepte un flag `facture_auto` (utilisé dans les tests) mais l'UI ne l'envoie pas.

**Travail demandé**
1. Clarifier le comportement cible : **toute vente confirmée génère sa facture** (option par défaut), ou génération pilotée par un paramètre tenant / une case à cocher dans le formulaire de vente — dans tous les cas, l'utilisateur ne doit pas avoir à saisir deux fois.
2. Implémenter via `facturation_service.generate_from_vente(vente_id)` **idempotent** (pas de doublon en cas de double soumission ni de retry) ; s'appuyer sur le test existant `tests/test_facturation_idempotence.py` comme contrat.
3. Propager la référence/le lien vente → facture de façon visible (colonne « Vente d'origine » ou référence de vente sur la facture, accès direct depuis la vente vers sa facture).
4. Si le README promet un QR code par commande, vérifier que la facture générée le porte bien ; sinon ajuster la documentation pour refléter la réalité.
5. **Preuve attendue** : créer une vente depuis l'UI → 1 facture exactement en base et à l'écran, montants TTC identiques, aucune duplication après deux clics rapprochés.

### F4 — Le « CA du mois » compte les ventes non payées (P1)
**Fichiers** : `web/backend/app/api/v1/dashboard.py` (calcul des indicateurs), `web/frontend/src/pages/Dashboard.jsx`, `web/frontend/src/pages/dashboard/dashboardUtils.js`.
**Symptôme** : vente au statut `en_attente` (non payée) → dashboard affiche « CA du mois : 330 000 MGA » et « 330 000 MGA générés ».

**Travail demandé**
1. Distinguer explicitement **CA facturé** (valeur des ventes du mois) et **CA encaissé** (somme des paiements confirmés du mois) — calculer les deux côté backend, en réutilisant les modèles/services existants (ventes, factures, paiements) et **sans** casser l'isolation tenant.
2. Étiqueter l'indicateur affiché de manière non ambiguë en français (« CA facturé », « CA encaissé », ou les deux côte à côte).
3. Vérifier la cohérence des autres KPI dérivés du même calcul (marge, « X MGA générés », etc.) et les libeller de la même manière.
4. **Preuve attendue** : avec une seule vente `en_attente`, « CA facturé » = montant de la vente et « CA encaissé » = 0 ; après enregistrement d'un paiement confirmé, « CA encaissé » devient égal au montant payé.

### F5 — TVA par défaut d'une ligne de vente incohérente avec le produit (P1)
**Fichiers** : `web/frontend/src/schemas/validationSchemas.js` (`saleLineSchema`), `web/frontend/src/pages/Sales.jsx` (`handleProduitChange`, `append({ ... taux_tva: 20 })` ligne ~380), `web/backend/app/models/produit.py` (`taux_tva` par défaut 10).
**Symptôme** : produit enregistré à `taux_tva = 10`, nouvelle ligne de vente à 20 % ; l'écart ne se corrige que si l'on choisit le produit (risque de vendre avec une TVA erronée si l'ordre des actions diffère).

**Travail demandé**
1. Supprimer la constante `20` dupliquée côté frontend : la TVA par défaut d'une ligne doit venir du **produit** sélectionné, ou à défaut d'un **paramètre tenant** de TVA par défaut (prévoir un fallback documenté et une seule source de vérité, alignée sur le défaut backend).
2. S'assurer que le passage produit → ligne met à jour `prix_unitaire`, `taux_tva` (et le prix selon le type de vente) de manière **cohérente même si l'utilisateur modifie ensuite la ligne / la resélectionne / supprime puis recrée**.
3. Vérifier que le backend recalcule de toute façon correctement la TVA (ne pas faire confiance aveuglément au client : validation/arrondis côté serveur) et que le `GET` d'une vente renvoie bien les taux réellement appliqués.
4. **Preuve attendue** : une ligne neuve affiche la TVA du produit dès sa sélection et la vente enregistrée porte le même taux que le produit.

### F6 — Suivi public : « Commande non trouvee » (message erroné/mal orthographié) (P2)
**Fichiers** : `web/frontend/src/pages/Suivi.jsx`, `web/backend/app/api/v1/public.py`, composants de suivi dans `web/frontend/src/components/landing/`.
**Symptôme** : référence de vente ERP `VENT-2026...` saisie sur `/suivi` → « Commande non trouvee » (sans accents).

**Travail demandé**
1. Corriger l'orthographe/typographie **et** les accents de tous les messages de cette page (« Commande non trouvée »), en français.
2. Rendre l'erreur **compréhensible** : distinguer explicitement les deux familles de références (commande e-commerce publique vs vente interne ERP) et le dire dans le message : p.ex. « Cette référence correspond à une vente interne. Le suivi public concerne uniquement les commandes passées sur la vitrine. » Ajouter le format attendu et/ou un exemple.
3. Vérifier que le comportement de secours est honnête : si la référence est valide mais appartient à un autre canal/tenant, ne pas répondre une « introuvable » générique trompeuse.
4. **Preuve attendue** : message exact et accentué pour une référence de vente interne ; une vraie référence de commande publique continue de fonctionner.

### F7 — Carte ABONNEMENT : un « 0 » sans unité (P1)
**Fichiers** : `web/frontend/src/pages/Subscription.jsx` (carte ABONNEMENT ~lignes 340-445), `web/frontend/src/pages/Dashboard.jsx` (~636-700), données d'abonnement (`shared/contexts/AuthContext.jsx` → `getMonAbonnement`).
**Symptôme** : plan « gratuit », statut ACTIF, date de fin, puis un « 0 » isolé, sans unité ni contexte.

**Travail demandé**
1. Identifier la donnée réellement affichée et lui donner une **unité et un libellé** clairs (« utilisateurs : 2 / 3 », « produits : 1 / 50 », « jours restants : 30 », « 0 commande »…). Aucun nombre nu à l'écran.
2. Sur le plan gratuit (quotas documentés : 3 utilisateurs / 50 produits / 100 clients), afficher les **compteurs réels vs limites** du tenant, idéalement avec le restant. Récupérer les valeurs depuis le backend (éviter les recalculs approximatifs côté React) en respectant l'isolation tenant.
3. Aligner les libellés sur le vocabulaire déjà utilisé dans l'app (français) et gérer les cas limites : donnée absente (« — » + explication), quota illimité (« illimité »), abonnement expiré.
4. **Preuve attendue** : la carte n'affiche plus aucun nombre orphelin ; les compteurs correspondent aux données réelles en base.

### F8 — Rate-limit login : 5 tentatives/5 min **par IP**, succès comptés (P0/P1 sécurité)
**Fichier** : `web/backend/app/security/rate_limit.py` (+ décorateur appliqué à la route de login dans `web/backend/app/api/v1/auth.py`), fallback mémoire `_memory_limit`.
**Symptôme** : 5 échecs → 429 au 6ᵉ ; une connexion **réussie** consomme aussi le quota et a bloqué les connexions suivantes (dont `user_test` et le super-admin) avec « Trop de requêtes ».

**Travail demandé**
1. Rendre le compteur **par identité de connexion** plutôt que strictement par IP : clé combinant l'IP **et** l'identifiant soumis (email/username normalisé), via le paramètre `key_func` déjà supporté par le décorateur — pour ne pas verrouiller tout un open space / une sortie NAT partagée. Prévoir une limite IP globale plus permissive en garde-fou anti-bruteforce.
2. **Ne pas compter les connexions réussies** dans le quota d'échecs : incrémenter uniquement en cas d'échec d'authentification (et remettre le compteur à zéro après un succès pour cette identité).
3. Appliquer la même logique au **fallback mémoire** (dev/test) et à la voie **Redis**, avec des clés cohérentes ; garder le comportement fail-closed en production et le passage direct en `TESTING`/`DEBUG` (ne pas casser la suite de tests).
4. Renseigner un en-tête `Retry-After` (secondes restantes) sur la réponse 429 et **conserver** le message français « Trop de requêtes… ».
5. Ajouter des tests : (a) N échecs → 429 au N+1 ; (b) un succès puis un échec ne bloquent pas un autre compte ; (c) un succès ne consomme pas le quota ; (d) deux comptes derrière la même IP ne se bloquent pas mutuellement.
6. **Preuve attendue** : les tests ci-dessus verts + vérification manuelle (6 échecs sur un compte → 429 ; un autre compte se connecte immédiatement).

### F9 — Champs de formulaire inadaptés à Madagascar (P1)
**Fichiers** : `web/frontend/src/components/ClientModal.jsx` (champs `SIRET`, « TVA INTRACOMMUNAUTAIRE », placeholders `123 456 789 00010` / `FRXX 123456789`), `web/frontend/src/pages/Clients.jsx`, `web/frontend/src/pages/Sales.jsx` (type de vente auto-dérivé + champ « Type de vente » ligne ~292-299).
**Symptôme** : identifiants européens inexistants à Madagascar (NIF / STAT / RCS attendus) avec pays par défaut « Madagascar » ; le type de vente se dit « auto-dérivé du client » mais l'information n'est plus visible/cohérente si l'on change le client après coup (client « Particulier » → type forcé « Détail »).

**Travail demandé**
1. Remplacer/compléter les identifiants fiscaux par les **identifiants malgaches** : NIF, STAT, RCS (et n° de carte fiscale si pertinent), avec des libellés et placeholders réalistes (format malgache), en français. Si les colonnes backend existent pour SIRET/TVA intracommunautaire, vérifier ce qu'il faut conserver en base (ne pas casser l'existant) : ajouter les nouveaux champs avec migration Alembic si nécessaire, et **masquer** les champs européens dans le formulaire.
2. Rendre le **type de vente** cohérent et explicite : quand il est auto-dérivé du client, le dire (badge/mention « dérivé du client : … »), et si l'utilisateur le modifie manuellement, ne pas l'écraser silencieusement ; si le client change après coup, **recalculer ou signaler** l'écart. Le type retenu doit être visible sur la vente enregistrée.
3. Vérifier les autres formulaires avec des champs franco-européens inadaptés (fournisseurs, entreprise/paramètres, inscription) et appliquer la même correction.
4. **Preuve attendue** : le formulaire client ne propose plus SIRET/TVA intra ; NIF/STAT/RCS présents et enregistrés ; le type de vente affiché correspond au type finalement appliqué.

### F10 — Comptes démo non fonctionnels / documentation obsolète (P1)
**Fichiers** : `README.md` (comptes `distrifood@erp.com`, `grosriz@erp.com`, phrase incohérente « mot de passe : défini par l'utilisateur lors du premier accès / changé au premier boot »), `web/backend/scripts/seed_mada_business.py`, `web/backend/manage.py` (`create-superadmin` → `scripts/create_superadmin.py`), `.env`/`.env.example`.
**Symptôme** : aucun mot de passe documenté ne fonctionne sur les comptes réels (`superadmin@mihaja.mg`, `lokomada@gmail.com`) ; `distrifood@erp.com`/`grosriz@erp.com` n'existent pas en base → impossible de se connecter au premier démarrage sans lire les scripts.

**Travail demandé**
1. Rendre la **documentation vraie** : lister les commandes réelles de provisionnement (`python manage.py create-superadmin`, appels au seed réel) et les comptes effectivement créés par les seeds, avec la source du mot de passe (variable d'environnement, paramètre CLI, valeur de dev explicitement marquée non productive).
2. Interdire tout mot de passe en dur en production : si les seeds créent un mot de passe, il doit venir d'une variable d'environnement (et être refusé par défaut en production). Ne jamais committer de secret.
3. Supprimer/corriger la phrase incohérente sur le « premier accès », et harmoniser le mode opératoire « première installation » (base + seed + super-admin + premier login).
4. **Preuve attendue** : en suivant **uniquement** le README depuis une base vierge, on obtient un compte capable de se connecter. Citer les commandes réellement exécutées et le résultat.

### F11 — Erreurs backend invisibles dans l'UI de connexion (P1)
**Fichiers** : `web/frontend/src/components/auth/Login.jsx` (aucun état d'erreur serveur affiché ; `onSubmit` ne fait qu'un `console.error`), `shared/contexts/AuthContext.jsx` (`login` → `toast.error(message)`, lignes ~249-271), montage éventuel du `ToastContainer`.
**Symptôme** : le 429 (F8) est bien renvoyé mais l'écran de connexion n'affiche **rien** ; idem pour les erreurs de validation serveur.

**Travail demandé**
1. Afficher dans le formulaire de connexion un **message d'erreur serveur visible** (bloc `role="alert"`), avec le message reçu du backend (français), en complément du toast ; gérer au minimum 429 (`Retry-After` → « Trop de tentatives. Réessayez dans X s. »), 401 (identifiants invalides), 403 (compte désactivé/droits), 5xx (erreur serveur), erreur réseau (backend injoignable).
2. Vérifier que le toast est réellement rendu sur cet écran (React-Toastify monté au bon niveau, conteneur `ToastContainer`) — sinon le corriger. Ne pas se contenter de `console.error`.
3. Ne jamais afficher de message technique brut (pas de stacktrace) ; message en français, actionnable.
4. Même traitement sur l'écran d'inscription et de changement de mot de passe si le défaut existe.
5. **Preuve attendue** : capture/description de l'écran de connexion affichant le message du 429 et celui du 401 (aucun clic « dans le vide »).

### F12 — Incohérence de langue des routes + titre d'onglet en dur (P2)
**Fichiers** : `web/frontend/src/App.js` (routes `/products`, `/sales`, `/invoices`, `/inventory`, `/suppliers`, `/hr` vs `/produits/:id`), `web/frontend/public/index.html` (`<title>TIA INFO WHOLESALE / ERP PRO</title>` codé en dur), `shared/navConfig.js` (source unique de la navigation).
**Symptôme** : modules ERP en anglais, fiche produit publique en français (`/produits/:id`) ; un francophone qui saisit `/produits` retombe sur l'accueil public sans explication ; le titre d'onglet expose le nom d'un tiers dans une app multi-tenant.

**Travail demandé**
1. **Titre/onglet dynamique par tenant** : supprimer le nom de société codé en dur de `index.html` et définir le titre depuis les données du tenant (`document.title` via un effet, ou composant dédié), avec un fallback neutre (ex. « ERP PRO » / « Espace professionnel »).
2. **Routes** : rendre l'expérience cohérente en français **sans casser les liens existants**. Option privilégiée : ajouter des **alias français** (`/produits`, `/ventes`, `/factures`, `/stock`, `/fournisseurs`, `/rh`) redirigeant vers les routes canoniques, en dérivant la navigation de `shared/navConfig.js` (source unique — ne pas forker la config par application, web **et** desk restent alignés).
3. Toute route inconnue doit afficher une page explicite (404 « Page introuvable » avec lien de retour) au lieu d'une redirection silencieuse vers l'accueil public ; vérifier en particulier `/produits` (singulier/pluriel).
4. Vérifier que les redirections n'introduisent ni boucle ni perte du layout dashboard, et que les deep links (`/ventes/:id`) fonctionnent.
5. **Preuve attendue** : `/produits` (connecté) → écran produits ou redirection explicite ; le titre de l'onglet affiche le nom du tenant connecté, et un nom neutre en public.

---

## 5. Livrable attendu (format de restitution)

Pour **chaque** point (B1-B3, F1-F12), produire une fiche :

```
### <ID> — <titre court>            Statut : CORRIGÉ | PARTIEL | NON REPRODUIT | À ARBITRER
Cause racine réelle :
  - ce qui a été observé (fichier + ligne + extrait)
  - en quoi la cause du rapport était exacte / incomplète / fausse
Fichiers modifiés :
  - chemin (lignes) — nature du changement
Correctif :
  - explication technique en 2-5 phrases (français)
Preuve AVANT / APRÈS :
  - commande(s) ou manipulation exacte + sortie observée
Tests ajoutés / mis à jour :
  - chemin du test + nom + résultat
Risques / régressions possibles :
  - et ce qui a été fait pour les prévenir
Reste à faire (si PARTIEL) :
```

Le document final doit être rédigé **en français**, avec les commandes exactes tapées et leurs résultats, et commencer par un tableau de synthèse :

| ID | Titre | Priorité | Statut | Fichiers | Test |
|---|---|---|---|---|---|

---

## 6. Ordre d'exécution imposé

1. **B1** (vendre) — bloquant métier, faibles risques.
2. **B2** (déconnexion) — sécurité.
3. **F11** puis **F8** (message d'erreur login **avant** le durcissement du rate-limit, pour rendre le 429 lisible).
4. **F3** (facture auto) + **F4** (CA facturé/encaissé) — même famille métier.
5. **F2** (colonne CODE) puis **F5** (TVA) — cohérence produit/vente.
6. **F1** (diagnostic vitrine) puis **F7** (carte abonnement) — même écran côté marchand.
7. **F6**, **F9**, **F12** — messages, champs locaux, routes/titre.
8. **F10** (documentation + comptes démo).
9. **B3** (environnement CRA) — diagnostic en parallèle des autres lots si besoin.

Règle : terminer et prouver un point avant de passer au suivant ; ne pas empiler des corrections non vérifiées.

---

## 7. Rappels de vérification finale (avant de rendre)

- [ ] `cd web/backend; pytest` **vert** (aucun test supprimé, aucune régression).
- [ ] Build frontend OK (`npm run build` dans `web/frontend`) et `npm start` stable sur la durée du parcours.
- [ ] Parcours complet rejoué dans le navigateur : connexion → créer un client → créer un produit → **créer une vente depuis l'UI** → facture générée → dashboard cohérent (« CA facturé » vs « CA encaissé ») → **déconnexion** → reconnexion avec un autre compte.
- [ ] Après logout : endpoint protégé → **401** ; comptes différents non bloqués par le rate-limit.
- [ ] Vitrine : raisons de non-exposition visibles côté marchand ; message public non trompeur.
- [ ] Colonne CODE = référence métier ; TVA de vente = TVA produit ; suivi public accentué et explicatif.
- [ ] Titre d'onglet = tenant connecté (neutre en public) ; routes françaises ou 404 explicite, sans boucle de redirection.
- [ ] Aucun secret en clair ajouté ; aucun identifiant DB hardcodé dans les tests ; isolation tenant intacte.
- [ ] `graphify update .` exécuté après les modifications de code.
- [ ] Rapport final produit au format §5, en français, avec preuves.

---

## 8. Interdits explicites

- ❌ Masquer une erreur pour « faire passer » un test (try/except silencieux, `console.log` à la place d'un message utilisateur).
- ❌ Désactiver le rate-limit, le RBAC, le filtre tenant ou une validation pour contourner un symptôme.
- ❌ Forker `shared/navConfig.js` / `shared/utils/navPermissions.js` par application.
- ❌ Corriger uniquement `web/frontend` en laissant `desk` avec le même bug quand la logique est dupliquée (et inversement).
- ❌ Introduire une nouvelle librairie sans nécessité démontrée ni alignement sur l'existant.
- ❌ Livrer une correction sans preuve d'exécution (commande + sortie) ni test.

