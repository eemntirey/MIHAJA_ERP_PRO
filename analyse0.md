# Analyse du projet MIHAJA_ERP_PRO

> Analyse générée le 21/08/2026 — état actuel du dépôt `C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO`

## 1. Vue d'ensemble

Projet ERP multi-tenant (gestion commerciale) articulé autour de **3 applications** partageant un même backend :

| Couche | Techno | Emplacement | État estimé |
|--------|--------|-------------|-------------|
| Backend API | Python / Flask 2.3 + Flask-RESTx + SQLAlchemy 2.0 | `web/backend/` | Avancé (~85%) |
| Frontend Web | React 18 (CRA) + React Router 7 + axios | `web/frontend/` | Moyen (~60%) |
| App Desktop | Electron + React (même code web) | `desk/` | Faible (~40%) |
| Scripts utilitaires | Python | `root_scripts/` | Divers |

Statistiques mesurées :
- **Backend** : 164 fichiers `.py` (hors `venv`, `instance`, caches)
- **Frontend web** : 97 fichiers `.js`/`.jsx`
- **Desktop** : 149 fichiers `.js`/`.jsx`
- **Tests backend** : 11 fichiers (`tests/`) — auth, clients, produits, stocks, tenancy, users, ai, papi, mission_5

## 2. Backend (`web/backend/app/`)

### Architecture
- **Factory Flask** dans `app/__init__.py` : JWT, RESTX (Swagger), CORS, auto-seeding.
- **Multi-tenancy** complet : `models/base.py` (tenant_id, soft-delete), `security/tenant.py` (isolation), `security/plan_limits.py` (limites de plan).
- **Sécurité/RBAC** : `security/auth.py` (JWT+bcrypt), `security/roles.py`, `security/permissions.py`, `security/encryption.py`.

### API (22 namespaces `api/v1/`)
`test, auth, clients, produits, fournisseurs, ventes, stocks, factures, paiements, dashboard, ai, public, tenants, abonnements, livraisons, rh, comptabilite, documents, achats_devis, roles, permissions, users, notifications, papi`

### Modèles (37) — `app/models/`
Tenant, Utilisateur, Client, Fournisseur, Produit, Vente/LigneVente, Vente, Stock, Facture, Paiement, CommandeAchat/Fournisseur/Client, Livraison/Livreur/Véhicule/Itinéraire/Suivi, RH (Employe/Presence/Salaire/Prime), Compta (Compte/Ecriture/Trésorerie), Documents (Modele/Genere), Abonnement, Devis/Avoir/BL, RolePermission, Notification, PasswordResetToken, PaymentEvent.

### Services métier (20) — `app/services/`
Générique `base_service` + auth, produit, client, fournisseur, vente, stock, facturation, paiement, dashboard, abonnement, commande, livraison, rh, comptabilite, document, achat, devis_avoir, **papi** (intégration paiement externe avec `client/errors/payment/webhook`).

### Modules transverses
- **IA** (`app/ai/`) : `previsions`, `anomalies`, `recommendations`, `assistant`, `training` — modèles `.pkl` présents (stock/vente) → partiellement réel.
- **Tâches** (`app/tasks/`) : backups, emails, reports (Celery, workers non actifs).
- **Utils** (`app/utils/`) : pdf, excel, qr, barcode, validators, logger, compta_import, malagasy_data.
- **Scripts** (`scripts/`) : init_db, seed_database, migrate_tenant, train_ai.

## 3. Frontend Web (`web/frontend/src/`)

- **Routing** : `App.js` (React Router 7).
- **Pages (35+)** : Dashboard, Products, Clients, Suppliers, Sales, Inventory, Invoices, Payments, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, Roles, Permissions, Users, SuperAdmin (+ profil), Catalogue, Checkout, Cart, OrderTracking, UserOrders, Suivi, Home, Contact, Documentation, Landing (Catalog/Hero/Footer/Header/Testimonials/TrustBar).
- **Layouts** : `MainLayout`, `DesktopLayout`, `TopBar`, `Sidebar`, `DashboardRail`, `CommandPalette`, `DarkModeToggle`.
- **Contextes** : `AuthContext`, `CartContext`, `NotificationContext`.
- **Hooks** : `useAuth`, `useMediaQuery`.
- **Formulaires/validation** : `react-hook-form` + `yup` + `@hookform/resolvers`, schémas dans `schemas/validationSchemas.js`.
- **Services API** : `services/api.js` (axios + intercepteurs JWT + refresh), `constants/erpConstants.js`, `navConfig.js`.

## 4. Desktop (`desk/`)
Application Electron réutilisant la logique React. `package.json` configuré pour build Windows/macOS/Linux. Mêmes services API. Composants spécifiques : `DesktopLayout`, `DesktopSidebar`, `DesktopContext`. **À finaliser** : fonctionnalités natives (impression, notifications système, drag & drop), virtualisation `@tanstack/react-virtual`.

## 5. Documentation existante
`README.md`, `resumer.md`, `Analyse_Fonctionnalite.md`, `Analyse_Parite_Desktop_Web.md`, `Analyse_Web_vs_Desktop.md`, `Ecart_Fonctionnalite_Desktop.md`, `Plan_Desktop.md`, `WEB_VS_DESK_GAP_REPORT.md`, `PROMPT_IA_AGENT_BUGS.md`, + `docs/{api,technical,user}/README.md` (à rédiger).

## 6. Points forts
- Modèle de données large et cohérent (37 modèles), multi-tenancy et RBAC solides.
- Couverture API large (24 namespaces) avec Swagger.
- Intégration paiement externe (`papi`) et IA (modèles entraînés présents).
- Trois canaux de distribution (web, desktop, marketplace publique).
- Suite de tests backend présente.

## 7. Points faibles / risques
- **Désynchronisation Desktop/Web** : analyse `WEB_VS_DESK_GAP_REPORT.md` signale des écarts de parité (état desktop ~40%).
- **Endpoints partiels** : certains namespaces renvoient des messages génériques, logique non branchée aux services.
- **Frontend partiellement maquetté** : pages utilisant encore des données simulées ; formulaires CRUD incomplets ; tableaux sans tri/filtres/virtualisation.
- **IA** : modules en partie placeholders malgré modèles `.pkl`.
- **Tâches Celery** non actives (backups/emails/rapports).
- **Limites de plan** (`max_produits`, etc.) définies mais non appliquées partout.
- **Reset password** : modèle + token présents, endpoints à finaliser.

## 8. Recommandations prioritaires
1. **Finaliser le backend** : brancher endpoints → services (ventes, stocks, facturation, paiement) ; appliquer plan_limits.
2. **Combler l'écart Desktop/Web** : réutiliser les pages web via un layout desktop commun ; activer les fonctionnalités natives.
3. **Connecter le frontend aux API réelles** : remplacer les données simulées, compléter formulaires CRUD + tableaux.
4. **CI/Qualité** : linter/typecheck frontend (aucun ESLint/TS configuré), lancer `pytest` régulièrement.
5. **Rédiger `docs/{user,technical,api}/README.md`**.

---
*Sources : arborescence du dépôt, `resumer.md`, `web/backend/README.md`, `web/frontend/package.json`, rapports d'écart existants.*

## 9. Anomalies détaillées dans l'état du code

Cette section liste des anomalies **concrètes** repérées par lecture directe du code (référencées par `fichier:ligne`).

### 9.1 Références de fichiers cassées / orphelines
- Les onglets ouverts référencent `web/backend/_verify_users_module.py` et `web/backend/test_users_api.py`, mais :
  - `test_users_api.py` se trouve en réalité dans `web/backend/tests/test_users_api.py`.
  - **`_verify_users_module.py` n'existe nulle part dans le dépôt** → fichier orphelin ou chemin invalide (référence morte).
- Conséquence : maintenance égarée, scripts de vérification non retrouvables.

### 9.2 Masquage silencieux d'erreurs (`except: pass`)
- `web/backend/app/__init__.py:406-407` : dans le hook `before_request`, `resolve_tenant_from_header()` est enveloppé dans `try/except Exception: pass`. Un échec de résolution de tenant est **avalé sans log**, `g.current_tenant` reste `None`.
- `web/backend/app/services/paiement_service.py:22,34,44,50` : parsing de dates et conversion d'enums `StatutPaiement`/`TypePaiement` en `except ...: pass` → une valeur invalide est **silencieusement ignorée** (statut non défini, date non parsée).
- `web/backend/app/services/achat_service.py:54` et `web/backend/app/services/papi/payment.py:102,120,250` : branches `pass` vides.
- Risque : comportements erronés non détectables, données corrompues sans trace.

### 9.3 Prédictions IA fabriquées (faux positifs)
- `web/backend/app/ai/previsions.py:24-54` : `predict_sales()` renvoie une prévision **baseline inventée** (`np.sin(i/3)` comme variation) quand il y a < 2 ventes, avec `confidence_score: 0.65` et `trend: 'stable'`.
- Conséquence : l'assistant IA (`ai/assistant.py:118-122`) affiche des chiffres chiffrés « prévisionnels » sans aucune base réelle → **risque de décision sur données fictives**. Modèles `.pkl` présents mais apparemment non chargés dans ce chemin.

### 9.4 Isolation multi-tenant non garantie côté IA/dashboard
- `web/backend/app/ai/assistant.py` : `_build_context_block()` et `_answer_internal()` filtrent par `tenant_id` **uniquement si fourni**. Si `get_current_tenant_id()` renvoie `None` (super-admin, token absent, ou suite à l'anomalie 9.2), les requêtes portent sur **toutes les données de tous les tenants** → fuite inter-tenant potentielle dans l'assistant et le dashboard.

### 9.5 Réinitialisation de mot de passe simulée
- `web/backend/app/api/v1/auth.py:355` : « Simulated password reset email sent » → aucun envoi réel (cohérent avec Celery `emails` non actif). Endpoint `ForgotPassword/ResetPassword` côté frontend présent mais backend incomplet.

### 9.6 Sécurité : modèles pickle versionnés
- `web/backend/app/ai/models/stock_model.pkl` et `vente_model.pkl` sont commités. Chargement de pickle non fiable + obsolescence par rapport au schéma des modèles → à régénérer via `scripts/train_ai.py` plutôt qu'à versionner.

### 9.7 Redondance / divergence des scripts de seed
- Multiples scripts de peuplement redondants à la racine `web/backend/scripts/` : `seed_database.py`, `seed_entreprises.py`, `seed_mada_business.py`, `seed_produits_demo.py`, `seed_roles.py`, `seed_test_users.py`. Risque de divergence des données de référence selon le script exécuté.
- `root_scripts/App.js` et autres fichiers racine dupliquent potentiellement la logique des apps (`desk/`, `web/frontend/`) → source de divergence.

### 9.8 Frontend : état réel vs `resumer.md`
- **Correction** : contrairement à `resumer.md` (§ « Frontend Web » : « données simulées »), les pages actuelles utilisent majoritairement des appels API réels (`useState([])` + `response.data`, ex. `pages/Products.jsx`, `Clients.jsx`, `Inventory.jsx`, `Purchases.jsx`, `Delivery.jsx`). Le frontend est **plus câblé** qu'indiqué.
- Restent à vérifier : complétude des formulaires CRUD et des tableaux (tri/filtres/virtualisation), et l'absence de configuration ESLint/TypeScript (`web/frontend/package.json` n'en déclare aucune).

### 9.9 Qualité globale / manque d'automatisation
- Aucun linter ni typecheck configuré côté frontend (`web/frontend/package.json` : pas de `eslint`, ni `tsc`).
- Pas de CI visible ; les tests backend (`web/backend/tests/`, 11 fichiers) ne sont pas reliés à une étape automatisée connue.
- Fichiers résiduels : `web/frontend/src/pages/Untitled-1.txt`, `web/backend/Untitled-1.txt`, `web/backend/inspect_db.py`, `verify_*`/`validate_*` scripts de mission ponctuelle à nettoyer ou déplacer.

### 9.10 Tableau récapitulatif des anomalies

| # | Anomalie | Gravité | Fichier(s) |
|---|----------|---------|-----------|
| 9.1 | Références de fichiers cassées / orphelines | Moyenne | `_verify_users_module.py` (inexistant), `tests/test_users_api.py` |
| 9.2 | `except: pass` masque les erreurs | Élevée | `app/__init__.py:407`, `services/paiement_service.py:22,34,44,50` |
| 9.3 | Prédictions IA fabriquées | Élevée | `app/ai/previsions.py:24-54` |
| 9.4 | Isolation tenant non garantie (IA/dashboard) | Critique | `app/ai/assistant.py` |
| 9.5 | Reset password simulé | Moyenne | `app/api/v1/auth.py:355` |
| 9.6 | `.pkl` versionnés (sécurité/obsolescence) | Moyenne | `app/ai/models/*.pkl` |
| 9.7 | Scripts de seed redondants | Faible | `web/backend/scripts/seed_*.py` |
| 9.8 | Frontend plus câblé que documenté | Info | `web/frontend/src/pages/*` |
| 9.9 | Pas de lint/typecheck/CI | Moyenne | `web/frontend/package.json`, dépôt |
| 9.10 | Fichiers résiduels (Untitled, inspect_*) | Faible | `web/backend/Untitled-1.txt`, `web/frontend/src/pages/Untitled-1.txt` |
