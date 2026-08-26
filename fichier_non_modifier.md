# ARCHITECTURE COMPLÈTE — MIHAJA ERP PRO (ERP Commercial Multi-Tenant)

> **Fichier de référence pour assistants IA** (ChatGPT, Grok, Gemini, DeepSeek).
> Ce document décrit l'architecture entière du projet pour vous permettre de comprendre le code,
> de naviguer rapidement et de proposer des modifications cohérentes. **Ne modifiez pas ce fichier
> automatiquement** : il sert de source de vérité partagée. Si vous devez le mettre à jour, signalez-le.

---

## 1. Vue d'ensemble

**MIHAJA ERP PRO** est une application ERP commerciale **multi-tenant** (une instance, plusieurs entreprises clientes isolées) avec :

- Un **backend API REST** (Flask) partagé par tous les clients.
- Une **application web** (React) pour le travail au navigateur.
- Une **application desktop** (Electron + React) qui réutilise le code web et ajoute le mode hors-ligne.
- Une **interface publique / marketplace** (catalogue multi-entreprises, commande en ligne, suivi).
- Une **console Super Admin privée** pour gérer les tenants (entreprises) et les abonnements.
- Des modules **IA** (prévisions de ventes/stocks, détection d'anomalies, recommandations, assistant).
- Un système **RBAC** (rôles + permissions granulaires) et un **multi-tenancy** par `tenant_id`.

Contexte métier : entreprises de distribution/commerce à Madagascar (devise **MGA / Ar**, paiements mobile money : MVola, Orange Money, Airtel Money).

Langue du code/UI : **français** (libellés, messages d'erreur, commentaires).

---

## 2. Stack technique

| Couche | Technologies |
|--------|-------------|
| Backend | Python 3.11, **Flask 2.3**, Flask-RESTx (Swagger), Flask-JWT-Extended, Flask-SQLAlchemy, SQLAlchemy 2.0, Flask-Migrate (Alembic), Flask-CORS, Flask-SocketIO (optionnel) |
| DB | SQLite (dev) / PostgreSQL via PyMySQL (prod). Migrations Alembic. |
| Sécurité | bcrypt (mots de passe), JWT HS256 (access + refresh), python-dotenv, cryptography |
| Frontend Web | React 18, Axios, React Router, React Hook Form, Framer Motion, React Toastify, Tailwind CSS |
| Desktop | Electron 38, React 18, @tanstack/react-virtual (virtualisation), packaging NSIS/DMG/AppImage |
| IA | numpy, pandas, régression linéaire, z-score (Python pur, sans framework ML lourd) |
| Docs/PDF | reportlab, openpyxl (Excel), qrcode, python-barcode, Pillow, beautifulsoup4 |
| Tâches async | Celery + Redis (backups, emails, rapports) |
| Tests | pytest, pytest-cov, factory-boy, Faker |
| Qualité | black, flake8, mypy, isort |

Variables d'environnement critiques (`.env`) : `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `JWT_ACCESS_TOKEN_EXPIRES`, `JWT_REFRESH_TOKEN_EXPIRES`, `CORS_ORIGINS`, `ENABLE_SOCKETIO`, `FLASK_ENV`, `AUTO_SEED_DATA`, `DEFAULT_ADMIN_PASSWORD`. **Jamais de secrets commités.**

---

## 3. Arborescence du projet (racine = `MIHAJA_ERP_PRO/`)

```
MIHAJA_ERP_PRO/
├── README.md                      # Présentation stack + installation
├── SHARED_ARCHITECTURE.md         # Architecture web/desktop partagée (offline sync)
├── Analyse_Projet_Actuel.md       # Analyse fonctionnelle
├── MLD_ERP_Multi_Tenant.pdf       # Modèle logique de données
├── fichier_non_modifier.md        # CE fichier (architecture complète)
├── .env                           # Variables d'environnement (non commité idéalement)
├── erp.db                         # SQLite racine (si présent)
│
├── web/                           # ⭐ Cœur applicatif
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── backend/
│       ├── run.py                 # Point d'entrée Flask (create_app)
│       ├── run_socket.py          # Entrée Socket.IO si activé
│       ├── manage.py
│       ├── app/
│       │   ├── __init__.py        # create_app(), CORS, JWT, namespaces, tenant context, auto-seed
│       │   ├── constants.py       # Modes paiement, unités, devise MGA
│       │   ├── config/            # settings.py, database.py
│       │   ├── models/            # 45+ modèles SQLAlchemy (BaseModel / BaseTenantModel)
│       │   ├── api/v1/            # Endpoints REST (namespaces Flask-RESTx)
│       │   ├── security/          # auth, tenant, roles, permissions, plans, encryption
│       │   ├── services/          # Logique métier (couche service)
│       │   ├── ai/                # Prévisions, anomalies, recommandations, assistant, training
│       │   ├── utils/             # PDF, Excel, QR, barcode, audit, validators, logger
│       │   ├── tasks/             # Celery: backups, emails, reports
│       │   ├── websockets/        # socket_events.py (Socket.IO)
│       │   └── realtime/          # socket_server.py
│       ├── migrations/            # Alembic (env.py, versions/)
│       ├── scripts/               # Seeds, création tenants, migrations manuelles
│       ├── tests/                 # pytest (auth, stocks, RH, papi, multi-tenant, sécurité…)
│       └── venv/                  # Environnement virtuel Python (ignoré)
│
├── desk/                          # ⭐ Application Desktop Electron + React
│   ├── electron/                  # main.js (BrowserWindow/IPC), preload.js, run.js
│   ├── build/                     # Build de production (static/)
│   ├── public/
│   ├── shared/                    # ⚠️ Copie locale des modules partagés (voir dossier shared/ racine)
│   └── src/
│       ├── App.js / index.js
│       ├── pages/                 # Pages desktop (réutilisent logique web)
│       ├── components/            # layout (Sidebar 260px, TopBar, SplitView, CommandPalette), auth, desktop
│       ├── contexts/              # AuthContext, DesktopContext, CartContext
│       ├── hooks/                 # useTheme, useKeyboardShortcuts, useSplitView, useAutoSaveDraft…
│       ├── services/              # api.js, desktopApi.js (offline via syncEngine)
│       ├── shared/                # réexport de shared/ racine
│       ├── utils/                 # notify, filterUtils, exportUtils, localStore
│       └── styles/                # tokens.css, landing.css
│
├── shared/                        # ⭐ Code partagé web ↔ desktop (source unique)
│   ├── contexts/                  # AuthContext.jsx
│   ├── hooks/                     # useAuth, useOnlineStatus, useRealtime, useRealtimeSync
│   ├── storage/                   # authStorage, storageAdapter, tokenStore
│   ├── utils/                     # localStore, syncEngine, hydration, migrateLocalStorage
│   ├── services/                  # api, apiClient, preferences, syncApi
│   ├── realtime/                  # socketClient.js
│   ├── websockets/                # socketClient.js (Socket.IO)
│   └── index.js
│
├── super-admin/                   # ⭐ Console Super Admin (React, build séparé)
│   ├── build/
│   ├── public/
│   └── src/
│       ├── App.js / index.js
│       ├── pages/                 # Dashboard, Tenants, TenantDetail, Plans, Subscriptions, Audit, Profile
│       ├── components/            # layout/SuperAdminLayout, common/ConfirmModal
│       ├── contexts/             # SuperAdminAuthContext
│       └── services/api.js
│
├── docs/                          # Documentation
│   ├── api/README.md
│   ├── technical/README.md
│   ├── technical/WEB_DESKTOP_SYNC.md
│   └── user/README.md
│
├── scripts/                       # migrate_localStorage_sync.js (migration shared)
└── .kilo/                         # Config Kilo (IDE)
```

> Les dossiers `node_modules/`, `venv/`, `__pycache__/`, `build/`, `instance/`, `*.db` sont ignorés (non pertinents pour la compréhension).

---

## 4. Backend (Flask) — détail

### 4.1 Cycle de vie / `app/__init__.py` (`create_app`)
- Initialise `db`, `migrate`, `jwt`, `CORS`, l'`Api` Flask-RESTx (Swagger sur `/docs/`).
- Enregistre un **event listener SQLAlchemy global** (`register_tenant_filter_event`) qui filtre automatiquement toutes les requêtes SELECT par `tenant_id` (sauf `Tenant`, sauf `SUPER_ADMIN`).
- `before_request` : résout le tenant courant via header `X-Tenant-Slug` ou `X-Tenant-Domaine` → `g.current_tenant`.
- JWT claims additionnels : `username`, `email`, `role`, `tenant_id`.
- `db.create_all()` au démarrage (dev). Auto-seed désactivé en prod (sauf `AUTO_SEED_DATA=1` en dev/test).
- Socket.IO initialisé seulement si `ENABLE_SOCKETIO=1`.

### 4.2 Modèles (`app/models/`) — héritent de `BaseModel` / `BaseTenantModel`
`BaseModel` (abstrait) : `id`, `tenant_id` (FK tenants), `created_at`, `updated_at`, `is_active` (soft delete), `created_by`, `updated_by`. `BaseTenantModel` rend `tenant_id` obligatoire.

Modèles principaux (≈45) :
- **Tenants & auth** : `tenant.py` (Tenant, StatutTenant), `utilisateur.py` (Utilisateur, Role, StatutUtilisateur), `abonnement.py` (Abonnement, StatutAbonnement, Plan), `password_reset_token.py`, `audit_log.py`.
- **Commerce** : `produit.py`, `client.py`, `fournisseur.py`, `vente.py`, `ligne_vente.py`, `commande_client.py`, `commande_achat.py`, `commande_fournisseur.py`, `ligne_achat.py`, `facture.py`, `facture_fournisseur.py`, `paiement.py`, `payment_event.py`.
- **Stocks** : `stock.py`, `itineraire.py`, `livraison.py`, `livreur.py`, `vehicule.py`, `suivi_livraison.py`.
- **RH** : `employe.py`, `presence.py`, `salaire.py`, `prime.py`, `stagiaire.py`.
- **Comptabilité** : `compte_comptable.py`, `ecriture_comptable.py`, `tresorerie.py`.
- **Documents** : `devis_avoir_bl.py`, `document_genere.py`, `modele_document.py`.
- **Divers** : `notification.py`, `desk_state.py` (état synchronisation desktop/web).

### 4.3 Couche API (`app/api/v1/`) — namespaces Flask-RESTx
Chaque fichier expose un/des namespaces montés sur un préfixe. Liste des routes principales :

| Préfixe | Fichier | Contenu |
|---------|---------|---------|
| `/api/v1/auth` | `auth.py` | login, register (entreprise+user), refresh, reset password, me |
| `/api/v1/clients` | `clients.py` | CRUD clients (7 types) |
| `/api/v1/fournisseurs` | `fournisseurs.py` | CRUD fournisseurs (6 types) |
| `/api/v1/produits` | `produits.py` | CRUD produits, prix, codes-barres, QR, catégories |
| `/api/v1/stocks` | `stocks.py` | mouvements, alertes, inventaire, seuils |
| `/api/v1/ventes` | `ventes.py` | ventes gros/détail, factures, devis, BL, statuts |
| `/api/v1/factures` | `factures.py` | factures + paiements |
| `/api/v1/paiements` | `paiements.py` | multi-modes, partiels |
| `/api/v1/dashboard` | `dashboard.py` | CA, bénéfices, top produits, alertes |
| `/api/v1/ai` | `ai.py` | prévisions, anomalies, recommandations, assistant |
| `/public` | `public.py` | catalogue public, commande invité, suivi (sans auth) |
| `/api/v1/tenants` | `tenants.py` | gestion tenants (super admin) |
| `/api/v1/abonnements` | `abonnements.py` | plans, demande, paiement, renouvellement |
| `/api/v1/livreurs` `/vehicules` `/itineraires` `/livraisons` | `livraisons.py` | module livraison + temps réel |
| `/api/v1/employes` `/stagiaires` `/presences` `/salaires` `/primes` | `rh.py` | RH |
| `/api/v1/comptes` `/ecritures` `/tresorerie` | `comptabilite.py` | compta |
| `/api/v1/modeles-documents` `/documents` | `documents.py` | génération PDF/contrats |
| `/api/v1/commandes-achat` `/receptions` `/devis` `/bons-livraison` `/avoirs` | `achats_devis.py` | achats & devis |
| `/api/v1/roles` `/permissions` | `roles.py`, `permissions.py` | RBAC |
| `/api/v1/users` | `users.py` | gestion utilisateurs du tenant |
| `/api/v1/papi` | `papi.py` | passerelle paiement mobile money (MVola/Orange/Airtel) |
| `/api/v1/notifications` | `notifications.py` | notifications |
| `/api/v1/super-admin` | `super_admin.py` | console privée super admin |
| `/api/v1/desk` (blueprint `desk_bp`) | `desk.py` | sync desktop/web (favoris, colonnes, filtres, incrémental) |

### 4.4 Sécurité (`app/security/`)
- `auth.py` : `hash_password`/`verify_password` (bcrypt), génération/validation JWT.
- `tenant.py` : `tenant_required`, `tenant_admin_required`, `subscription_required`, `resolve_tenant_from_header`, filtre global par `tenant_id`. Le `SUPER_ADMIN` n'est pas filtré (accès global). Vérifie l'abonnement actif (sauf `EN_ESSAI`).
- `roles.py` : helpers `is_super_admin`, `is_admin`, `is_manager`.
- `permissions.py` / `permission_matrix.py` : matrice de permissions granulaires par rôle.
- `plans.py` / `plan_limits.py` : limites par plan d'abonnement (starter/pro/enterprise).
- `encryption.py` : chiffrement de champs sensibles.

### 4.5 Services (`app/services/`)
Logique métier découplée des routes : `auth_service`, `produit_service`, `vente_service`, `achat_service`, `commande_service`, `client_service`, `fournisseur_service`, `facturation_service`, `paiement_service`, `comptabilite_service`, `rh_service`, `stagiaire_service`, `livraison_service`, `abonnement_service`, `devis_avoir_service`, `document_service`, `dashboard_service`, `base_service`. Sous-dossier `papi/` (client mobile money : `client.py`, `payment.py`, `webhook.py`, `errors.py`).

### 4.6 IA (`app/ai/`)
- `previsions.py` : prévisions de ventes/stocks (régression linéaire sur séries numpy/pandas).
- `anomalies.py` : détection par z-score.
- `recommendations.py` : reco produits/clients.
- `assistant.py` : assistant conversationnel (prompt + appels LLM optionnels via `external_services.py`).
- `training.py` : entraînement des modèles `stock_model.pkl` / `vente_model.pkl` (joblib/pickle).
- Modèles servis depuis `app/ai/models/`.

### 4.7 Utils (`app/utils/`)
`pdf_generator.py`, `excel_generator.py`, `qr_generator.py`, `barcode_generator.py`, `audit.py`, `validators.py`, `logger.py`, `malagasy_data.py` (données de seed localisées), `compta_import.py`.

### 4.8 Tâches (`app/tasks/`)
Celery : `backups.py`, `emails.py`, `reports.py`. (Redis requis.)

### 4.9 Temps réel
`app/websockets/socket_events.py` + `app/realtime/socket_server.py` : Socket.IO activé par `ENABLE_SOCKETIO=1`. Canaux par tenant et par utilisateur (notifications, favorites, colonnes, filtres).

---

## 5. Multi-tenancy

- Isolation par `tenant_id` (colonne sur presque tous les modèles via `BaseTenantModel`).
- Résolution du tenant : header `X-Tenant-Slug` / `X-Tenant-Domaine` → `g.current_tenant` (voir `app/__init__.py` `before_request` et `security/tenant.py`).
- Filtre SQL automatique (`do_orm_execute`) ajouté à toutes les requêtes SELECT sauf `SUPER_ADMIN`.
- `SUPER_ADMIN` : `g.current_tenant = None` → accès global à tous les tenants.
- Abonnement : un tenant doit avoir un `Abonnement` ACTIF (non expiré) pour publier/produire ; sinon `403 Abonnement requis` (sauf statut `EN_ESSAI`).
- Plans : `starter` / `pro` / `enterprise` avec limites (`plan_limits.py`).

---

## 6. Authentification & RBAC

- JWT HS256, `Authorization: Bearer <access>` + refresh token (cookie/stockage). Access court (3600s), refresh long (30j), configurables.
- `Role` (enum) : `SUPER_ADMIN`, `ADMIN`, `MANAGER`, `SALES`, `STOCK`, `ACCOUNTANT`, `USER`.
- Rôles dynamiques + permissions granulaires (`roles.py`, `permissions.py`, `permission_matrix.py`).
- Stockage tokens côté client : `shared/storage/authStorage.js` (clés `access_token`, `refresh_token`, `user`, `tenant`, `subscription`).
- Mots de passe : bcrypt. Reset via `password_reset_token`.

---

## 7. Frontend Web (`web/...` présent, mais ici `desk/src` est l'équivalent web)

> ⚠️ Note : le dossier `web/frontend/` n'apparaît pas dans cette arborescence ; le frontend web **est partagé** avec le code de `desk/src/` via le dossier racine `shared/`. `desk/` contient l'app React (web + electron).

Architecture React :
- `src/App.js` : routeur + providers (Auth, Cart, Desktop).
- `src/pages/` : une page par module (Dashboard, Produits, Clients, Ventes, Stock, Inventory, Factures, Paiements, Achats, RH, Accounting, Comptabilite, Livraison/Delivery, Documents, Catalogue, Cart, Checkout, Users, Roles, Permissions, Subscription, SuperAdmin, AI, Suivi, OrderTracking, Contact, Home, Documentation…).
- `src/components/` :
  - `layout/` : `DesktopLayout`, `DesktopSidebar` (260px), `DesktopTopBar`, `TitleBar`, `CommandPalette` (Cmd+K), `Breadcrumbs`, `NotificationDropdown`, `SplitView`, `ResizablePanel`, `ThemeToggle`, `DarkModeToggle`, `ChatInput`, `navConfig.js` (arbre de navigation).
  - `auth/` : `Login`, `Register`, `RegisterCompany`, `RegisterUser`, `ForgotPassword`, `ResetPassword`.
  - `desktop/` : `DataTable` (virtualisé), `FilterPanel`, `FormGrid`, `FAB`.
  - `landing/` : `Catalog`, `LandingLayout`, `OrderTracking`.
  - `common/` : `Icon`.
- `src/contexts/` : `AuthContext`, `CartContext`, `DesktopContext`.
- `src/hooks/` : `useTheme`, `useMediaQuery`, `useKeyboardShortcuts`, `useSplitView`, `useAutoSaveDraft`, `useFormDraft`.
- `src/services/` : `api.js` (Axios + intercepteurs token/refresh), `desktopApi.js` (offline via syncEngine), `publicApi.js`, `draftService.js`.
- `src/utils/` : `notify` (toast), `filterUtils`, `exportUtils`, `localStore`.
- `src/styles/` : `tokens.css`, `landing.css`.

---

## 8. Desktop Electron (`desk/`)

- `desk/electron/main.js` : fenêtre principale, IPC, intégration système (TitleBar custom).
- `desk/electron/preload.js` : bridge sécurisé (contextIsolation).
- `desk/electron/run.js` : bootstrap.
- React identique au web + ajouts desktop (FAB, SplitView, CommandPalette, virtualisation `@tanstack/react-virtual`).
- **Mode hors-ligne** : `shared/utils/syncEngine.js` met en file (`syncQueue` dans localStorage) les mutations échouées et les rejoue à la reconnexion (stratégie LWW = last-write-wins). `useOnlineStatus` / `useRealtimeSync` gèrent l'état réseau et Socket.IO.
- Packaging : `npm run dist` (NSIS/DMG/AppImage) via config electron-builder.

---

## 9. Module partagé (`shared/`) — source unique web↔desktop

- `shared/contexts/AuthContext.jsx` : contexte auth unique (login/register/logout, refresh auto, permissions).
- `shared/storage/authStorage.js` : abstraction localStorage auth (clés `access_token`, `refresh_token`, `user`, `tenant`, `subscription`).
- `shared/hooks/` : `useAuth`, `useOnlineStatus`, `useRealtime`, `useRealtimeSync`.
- `shared/utils/` : `localStore` (wrapper tolérant), `syncEngine` (file d'attente offline), `hydration` (résolution conflits), `migrateLocalStorage`.
- `shared/services/` : `api`, `apiClient`, `preferences`, `syncApi`.
- `shared/websockets/socketClient.js` : client Socket.IO (reconnexion auto, JWT, canaux tenant/user).
- Les fichiers `desk/src/shared/*` et `desk/shared/*` sont des **réexports** de ce dossier (ne pas dupliquer la logique).

---

## 10. Console Super Admin (`super-admin/`)

- React isolé, build séparé. Pages : Dashboard, Tenants, TenantDetail, Plans, Subscriptions, Audit, Profile.
- `SuperAdminAuthContext` : auth dédiée `SUPER_ADMIN`.
- Appelle `/api/v1/super-admin/*` et `/api/v1/tenants`, `/abonnements`.
- **Privée** : seul le compte `SUPER_ADMIN` y accède.

---

## 11. Flux de données typiques

1. **Requête authentifiée** : client envoie `Authorization: Bearer` + `X-Tenant-Slug`. `before_request` résout `g.current_tenant`. Le décorateur `tenant_required` vérifie tenant actif + abonnement. Le listener SQLAlchemy filtre automatiquement par `tenant_id`.
2. **Création produit** : `POST /api/v1/produits` → `produits_ns` → `produit_service` → `Produit` (tenant_id injecté) → commit → QR/barcode générés (`utils/`).
3. **Vente** : `POST /api/v1/ventes` → `vente_service` (lignes, stock décrémenté, facture, écriture compta) → notif Socket.IO.
4. **Commande publique** : `/public` (sans JWT) → validation après paiement complet (PAPI mobile money) → QR/code-barre pour scan.
5. **Offline (desktop)** : mutation → `syncEngine.enqueue` → rejouée à la reconnexion.
6. **IA** : `/api/v1/ai` → `previsions/anomalies/recommendations` (modèles `.pkl` ou calcul numpy/pandas).

---

## 12. Conventions & règles à respecter (pour vos modifications)

- **Soft delete** : utiliser `is_active = False` (`.delete()`), jamais de `hard_delete` sauf justification.
- **Tenant** : tout nouveau modèle métier doit hériter de `BaseTenantModel` et posséder `tenant_id`. Ne jamais contourner le filtre global (sauf `SUPER_ADMIN` intentionnel).
- **Audit** : actions sensibles → `app/utils/audit.py` (log `audit_log`).
- **Services** : mettez la logique métier dans `app/services/`, pas dans les routes API.
- **RBAC** : protégez les routes avec `tenant_required` / `tenant_admin_required` / `subscription_required` + vérification permissions.
- **Frontend** : code partagé → `shared/` (pas de duplication dans `desk/src`/`web`). Re-export plutôt que copie.
- **Devise** : toujours `MGA` / `Ar` (`app/constants.py`).
- **Vérification** : backend → `cd web/backend && pytest`. Frontend/desktop → `npm run build` / `npm test` (Jest pour `desk`).
- **Secrets** : `.env` uniquement, jamais commités.

---

## 13. Lancement rapide

```bash
# Backend
cd web/backend
python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt
flask run                 # http://localhost:5000  (Swagger: /docs/)

# Frontend web (via desk)
cd desk && npm install && npm start        # http://localhost:3000
# Desktop Electron
cd desk && npm run electron:dev
npm run dist              # packaging

# Super Admin
cd super-admin && npm install && npm start
```

---

## 14. Conseils pour les assistants IA travaillant sur ce projet

- Pour comprendre une route, cherchez d'abord le namespace dans `web/backend/app/api/v1/<module>.py`, puis le service correspondant dans `web/backend/app/services/`.
- Pour ajouter un champ à une entité : modèle (`models/`) + migration Alembic (`migrations/versions/`) + `to_dict()` auto + service + route + (si UI) page React + (si partagé) `shared/`.
- Les libellés d'erreur sont en **français** : gardez la cohérence linguistique.
- Le multi-tenant est central : toute requête directe (`db.session.query`) sans passer par le filtre global peut fuiter des données d'un autre tenant — préférez les helpers `tenant_filtered_get` / `set_tenant_filter`.
- Le desktop et le web partagent la même API ; une correction backend profite aux deux.
- Les fichiers `*.pkl` (IA) sont générés par `scripts/train_ai.py` / `app/ai/training.py`, ne pas éditer à la main.

---
*Document généré pour faciliter l'aide de ChatGPT, Grok, Gemini et DeepSeek sur MIHAJA ERP PRO.*
