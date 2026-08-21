# Analyse du Design - MIHAJA_ERP_PRO

> Analyse mise à jour le 21/08/2026 — état actuel du dépôt `C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO` après commits récents (DESK design correction, rôles, final bug fixes)

---

## 1. Vue d'ensemble du projet

**MIHAJA_ERP_PRO** est un ERP commercial multi-tenant articulé autour de **3 applications** partageant un même backend :

| Couche | Techno | Emplacement | État estimé |
|--------|--------|-------------|-------------|
| Backend API | Python / Flask 2.3 + Flask-RESTx + SQLAlchemy 2.0 | `web/backend/` | Avancé (~88%) |
| Frontend Web | React 18 (CRA) + React Router 7 + axios | `web/frontend/` | Bon (~70%) |
| App Desktop | Electron + React + Tailwind CSS | `desk/` | Avancé (~65%) |

**Stack technique détaillée :**
- **Backend** : Flask 2.3, Flask-RESTx (Swagger), Flask-JWT-Extended, Flask-SQLAlchemy, Flask-Migrate, Flask-CORS, Celery + Redis (tâches asynchrones), bcrypt, dotenv
- **Frontend Web** : React 18.3.1, React Router 7.18, Axios 1.19, React Hook Form 7.85, Framer Motion 13.0, React Toastify 11.1, Yup 1.7 (validation), @hookform/resolvers 5.7
- **Desktop** : Electron 38.8, @tanstack/react-virtual 3.14 (virtualisation), electron-builder 26.0 (packaging Windows NSIS / macOS DMG / Linux AppImage), **Tailwind CSS 3.4** (configuré avec variables CSS custom)
- **IA** : Python pur (numpy, pandas, régression linéaire, z-score), modèles `.pkl` pour stock/vente
- **Paiement** : Intégration PAPI (Papi Payment Gateway Madagascar) via service dédié `papi/`

---

## 2. Architecture du Backend

### 2.1 Structure globale

```
web/backend/
├── app/
│   ├── __init__.py          # Factory Flask, extensions, namespaces, auto-seeding
│   ├── api/v1/              # 22 namespaces REST (Flask-RESTx)
│   ├── models/              # 37 modèles SQLAlchemy (BaseModel + modèles métier)
│   ├── services/            # 20 services métier (logique métier)
│   ├── security/            # Auth JWT, RBAC, tenant isolation, plan limits, encryption
│   ├── ai/                  # Modules IA (prévisions, anomalies, recommandations, assistant)
│   ├── utils/               # PDF, Excel, QR, barcode, validators, logger, compta_import
│   ├── tasks/               # Tâches Celery (backups, emails, rapports)
│   └── config/              # Configuration (settings.py, database.py)
├── scripts/                 # Scripts utilitaires (init_db, seed_*, train_ai, migrate_tenant)
├── tests/                   # 11 fichiers de tests pytest
├── migrations/              # Migrations Alembic
├── instance/                # Base de données SQLite (dev)
├── run.py                   # Point d'entrée
└── requirements.txt         # Dépendances Python
```

### 2.2 Architecture logicielle - Patterns identifiés

**a) Architecture en couches (Layered Architecture)**
```
[API Layer] → [Service Layer] → [Model Layer] → [Database]
```
- **API Layer** (`api/v1/`) : Namespaces Flask-RESTx avec ressources RESTful, décorateurs `tenant_required`, `admin_required`, `super_admin_required`, `permission_required`, `subscription_required`
- **Service Layer** (`services/`) : Logique métier encapsulée, `base_service.py` fournit un CRUD générique avec filtrage tenant automatique
- **Model Layer** (`models/`) : Modèles SQLAlchemy avec `BaseModel` abstrait (tenant_id, timestamps, soft-delete, created_by/updated_by)

**b) Multi-tenancy par isolation de données (Shared Database, Shared Schema)**
- Isolation via `tenant_id` présent sur tous les modèles métier (via `BaseModel`)
- Filtrage global automatique via event listener SQLAlchemy `do_orm_execute` (`security/tenant.py:24-62`)
- `SUPER_ADMIN` bypass le filtrage tenant
- Résolution de tenant via headers HTTP (`X-Tenant-Slug`, `X-Tenant-Domaine`) ou JWT claims

**c) RBAC (Role-Based Access Control)**
- 7 rôles natifs : `SUPER_ADMIN`, `ADMIN`, `MANAGER`, `SALES`, `STOCK`, `ACCOUNTANT`, `USER`
- Rôles personnalisés via modèles `RoleModel` + `Permission` (many-to-many)
- Permissions granulaires par feature (`product.create`, `sale.view`, etc.)
- Comparaison de rôles case-insensitive via `normalize_role()` (`security/roles.py:9-34`)
- Décorateurs `admin_required`, `super_admin_required`, `permission_required`

**d) Sécurité**
- Authentification JWT avec access token (1h) + refresh token (30j)
- Hashage bcrypt des mots de passe
- CORS configuré avec origines explicites (pas de wildcard)
- Intercepteur axios avec refresh automatique côté frontend
- Encryption module (`security/encryption.py`)
- Modèle `PasswordResetToken` pour réinitialisation de mot de passe

**e) Gestion des abonnements**
- Modèle `Abonnement` lié au tenant avec dates, statut, montant, méthode de paiement
- Décorateur `subscription_required` vérifie l'abonnement actif avant l'accès aux modules
- Période d'essai (`EN_ESSAI`) pour nouveaux tenants
- Limites de plan (`max_produits`, `max_clients`, `max_utilisateurs`) vérifiées via `check_plan_limits`

**f) Configuration**
- `config/settings.py` : Configuration centralisée avec classes `Config`, `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`
- Variables d'environnement via `python-dotenv`
- `SECRET_KEY` et `JWT_SECRET_KEY` obligatoires (levée d'erreur si absents)
- Configuration CORS, Celery/Redis, email, upload, pagination, localisation Madagascar (MGA)

### 2.3 Modèles de données (37 modèles)

**Modèle de base (`BaseModel`) :**
- `id` (PK), `tenant_id` (FK → tenants), `created_at`, `updated_at`, `is_active` (soft-delete), `created_by`, `updated_by`

**Modèles métier :**

| Catégorie | Modèles |
|-----------|---------|
| **Core** | `Tenant`, `Utilisateur`, `Role`, `Client`, `Fournisseur`, `Produit`, `Vente`, `LigneVente`, `Stock` (MouvementStock), `Facture`, `Paiement` |
| **Abonnements** | `Abonnement`, `PaymentEvent` |
| **Marketplace** | `CommandeClient` |
| **Livraison** | `Livreur`, `Vehicule`, `Itineraire`, `Livraison`, `SuiviLivraison` |
| **RH** | `Employe`, `Presence`, `Salaire`, `Prime` |
| **Comptabilité** | `CompteComptable`, `EcritureComptable`, `Tresorerie` |
| **Documents** | `ModeleDocument`, `DocumentGenere` |
| **Achats** | `CommandeFournisseur`, `FactureFournisseur`, `LigneAchat`, `CommandeAchat`, `ReceptionAchat` |
| **Devis/AVOIR/BL** | `Devis`, `BonLivraison`, `Avoir` |
| **RBAC** | `RoleModel`, `Permission` |
| **Auth** | `PasswordResetToken` |
| **Notifications** | `Notification` |

**Enums identifiés :**
- `Role` (SUPER_ADMIN, ADMIN, MANAGER, SALES, STOCK, ACCOUNTANT, USER)
- `StatutTenant` (ACTIF, EN_ESSAI, SUSPENDU, ARCHIVE)
- `StatutAbonnement` (ACTIF, INACTIF, EN_ATTENTE, EXPIRE, ANNULE)
- `TypeClient` (7 types), `TypeFournisseur` (6 types)
- `StatutPaiement`, `TypePaiement`
- `StatutCommande`, `TypeMouvement`
- `TypeContrat`, `Sexe`, `StatutEmploye`, `StatutPresence`, `StatutPaiementSalaire`, `TypePrime`
- `TypeCompte`, `StatutEcriture`, `TypeTresorerie`
- `QualiteAchat`, `StatutCommandeAchat`, `StatutAvoir`

### 2.4 API REST (22 namespaces)

| Namespace | Path | Description |
|-----------|------|-------------|
| `auth` | `/api/v1/auth` | Login, register, refresh, logout, forgot/reset password, super-admin me |
| `clients` | `/api/v1/clients` | CRUD clients |
| `produits` | `/api/v1/produits` | CRUD produits |
| `fournisseurs` | `/api/v1/fournisseurs` | CRUD fournisseurs |
| `ventes` | `/api/v1/ventes` | CRUD ventes + summary |
| `stocks` | `/api/v1/stocks` | CRUD stocks, mouvements, stats, alerts |
| `factures` | `/api/v1/factures` | CRUD factures |
| `paiements` | `/api/v1/paiements` | CRUD paiements |
| `dashboard` | `/api/v1/dashboard` | Stats, ventes, top produits/clients, alerts |
| `ai` | `/api/v1/ai` | Health, prévisions, anomalies, recommandations, assistant, train |
| `public` | `/public` | Catalogue, commandes anonymes, suivi, notifications |
| `tenants` | `/api/v1/tenants` | CRUD tenants (SUPER_ADMIN) |
| `abonnements` | `/api/v1/abonnements` | Gestion abonnements |
| `livreurs` | `/api/v1/livreurs` | CRUD livreurs |
| `vehicules` | `/api/v1/vehicules` | CRUD véhicules |
| `itineraires` | `/api/v1/itineraires` | CRUD itinéraires |
| `livraisons` | `/api/v1/livraisons` | CRUD livraisons, suivi, assignation, statuts |
| `employes` | `/api/v1/employes` | CRUD employés |
| `presences` | `/api/v1/presences` | CRUD présences, registre, export |
| `salaires` | `/api/v1/salaires` | CRUD salaires, génération, paiement, export |
| `primes` | `/api/v1/primes` | CRUD primes |
| `comptes` | `/api/v1/comptes` | CRUD plan comptable, import/export |
| `ecritures` | `/api/v1/ecritures` | CRUD écritures, valider/annuler, journal, import/export |
| `tresorerie` | `/api/v1/tresorerie` | CRUD trésorerie, solde, mouvements, import/export |
| `modeles-documents` | `/api/v1/modeles-documents` | CRUD modèles de documents |
| `documents` | `/api/v1/documents` | CRUD documents, génération |
| `commandes-achat` | `/api/v1/commandes-achat` | CRUD commandes d'achat |
| `receptions` | `/api/v1/receptions` | CRUD réceptions |
| `devis` | `/api/v1/devis` | CRUD devis, conversion |
| `bons-livraison` | `/api/v1/bons-livraison` | CRUD bons de livraison |
| `avoirs` | `/api/v1/avoirs` | CRUD avoirs |
| `roles` | `/api/v1/roles` | CRUD rôles personnalisés |
| `permissions` | `/api/v1/permissions` | CRUD permissions |
| `users` | `/api/v1/users` | CRUD utilisateurs |
| `papi` | `/api/v1/papi` | Intégration paiement PAPI |
| `notifications` | `/api/v1/notifications` | CRUD notifications |
| `test` | `/api/v1/test` | **Uniquement en DEBUG/TESTING** (cond. dans `app/__init__.py:181-186`) |

**Note** : Namespace `/test/` protégé en production via condition `DEBUG`/`TESTING`.

### 2.5 Services métier (20 services)

| Service | Responsabilité |
|---------|---------------|
| `base_service` | CRUD générique avec filtrage tenant automatique |
| `auth_service` | Authentification, inscription, profil |
| `produit_service` | Gestion produits, prix multiples, QR/barcode |
| `client_service` | Gestion clients, adresses, historique |
| `fournisseur_service` | Gestion fournisseurs |
| `vente_service` | Gestion ventes, devis, facturation |
| `stock_service` | Mouvements, alertes, inventaire, seuils |
| `facturation_service` | Génération factures, statuts |
| `paiement_service` | Paiements, modes multiples, partiels |
| `dashboard_service` | Statistiques, KPIs, top produits/clients |
| `abonnement_service` | Gestion abonnements, plans, paiement |
| `commande_service` | Commandes marketplace |
| `livraison_service` | Livreurs, véhicules, itinéraires, livraisons |
| `rh_service` | Employés, présences, salaires, primes |
| `comptabilite_service` | Plan comptable, écritures, trésorerie, import CSV |
| `document_service` | Modèles documents, génération PDF |
| `achat_service` | Commandes fournisseurs, réceptions |
| `devis_avoir_service` | Devis, avoirs, bons de livraison |
| `papi/*` | Client PAPI, webhooks, errors, payment |

---

## 3. Analyse du Frontend Web

### 3.1 Structure du projet

```
web/frontend/
├── public/
│   └── index.html
├── src/
│   ├── index.js              # Point d'entrée
│   ├── index.css             # Styles globaux
│   ├── App.js                # Routing, ProtectedRoute, modales globales
│   ├── contexts/
│   │   ├── AuthContext.jsx   # Authentification, rôle, subscription
│   │   ├── CartContext.jsx   # Panier d'achat public
│   │   └── NotificationContext.jsx  # Notifications temps réel
│   ├── hooks/
│   │   └── useMediaQuery.js  # Hook responsive (desktop vs mobile)
│   ├── services/
│   │   ├── api.js            # Axios + intercepteurs JWT/refresh + tous les services API
│   │   └── validationSchemas.js  # Schémas Yup pour validation
│   ├── constants/
│   │   └── erpConstants.js   # Constantes métier
│   ├── components/
│   │   ├── layout/           # MainLayout, DesktopLayout, Sidebar, TopBar, DashboardRail, CommandPalette, DarkModeToggle, ChatInput
│   │   ├── auth/             # Login, Register, ForgotPassword, ResetPassword
│   │   └── [modals]          # ClientModal, etc.
│   ├── pages/                # 35+ pages
│   └── styles/
│       └── landing.css
└── package.json
```

### 3.2 Routing et protection

**App.js (211 lignes)** :
- **BrowserRouter** avec `Routes`/`Route`
- **ProtectedRoute** composant avec :
  - Vérification `isAuthenticated` ou présence token dans `localStorage`
  - Redirection rôle-based : `SUPER_ADMIN` → `/super-admin`, `USER` → `/`, autres → `/dashboard`
  - Vérification abonnement actif (sauf page `/subscription`)
- **Routes publiques** : `/`, `/login`, `/register`, `/catalogue`, `/checkout`, `/cart`, `/produits/:id`, `/suivi`, `/contact`, `/mes-commandes`
- **Routes protégées** : dashboard, products, clients, sales, inventory, suppliers, invoices, payments, ai, documentation, subscription, delivery, hr, accounting, documents, purchases, super-admin, users, roles, permissions

### 3.3 Layouts

**Deux layouts principaux** :

1. **Mobile/Tablette (`MainLayout`)** :
   - `DashboardRail` en sidebar (260px)
   - `DarkModeToggle` + `ChatInput` flottants
   - Responsive avec `useMediaQuery('(min-width: 1280px)')`

2. **Desktop (`DesktopLayout`)** :
   - `DesktopSidebar` (260px, collapsible, state dans `localStorage`)
   - `TopBar` avec notifications, compteurs, recherche
   - `CommandPalette` (CMD+K) pour navigation rapide
   - `DarkModeToggle` + `ChatInput`

**Pattern** : Layout switcher dans `MainLayout.jsx:125-138` — bascule automatiquement selon la taille d'écran.

### 3.4 Pages identifiées (35+)

| Page | Route | Rôle | Description |
|------|-------|------|-------------|
| `Home` | `/` | PUBLIC | Landing page |
| `Login` | `/login` | PUBLIC | Connexion |
| `Register` | `/register` | PUBLIC | Inscription (simple/company) |
| `ForgotPassword` | `/forgot-password` | PUBLIC | Réinitialisation |
| `ResetPassword` | `/reset-password/:token` | PUBLIC | Réinitialisation |
| `Dashboard` | `/dashboard` | AUTH | Tableau de bord avec KPIs, graphiques, exports |
| `Products` | `/products` | AUTH | CRUD produits, prix, catégories |
| `Clients` | `/clients` | AUTH | CRUD clients, types, adresses |
| `Sales` | `/sales` | AUTH | CRUD ventes, devis, factures |
| `Inventory` | `/inventory` | AUTH | Stocks, mouvements, alertes |
| `Suppliers` | `/suppliers` | AUTH | CRUD fournisseurs |
| `Invoices` | `/invoices` | AUTH | Factures, statuts |
| `Payments` | `/payments` | AUTH | Paiements, modes multiples |
| `AI` | `/ai` | AUTH | Assistant IA, prévisions, anomalies |
| `Documentation` | `/documentation` | AUTH | Documentation technique |
| `Subscription` | `/subscription` | AUTH | Plans, demande, paiement, renouvellement |
| `Delivery` | `/delivery` | AUTH | Livreurs, véhicules, itinéraires, livraisons |
| `HR` | `/hr` | AUTH | Employés, présences, salaires, primes |
| `Accounting` | `/accounting` | AUTH | Plan comptable, écritures, trésorerie |
| `Documents` | `/documents` | AUTH | Modèles, génération PDF |
| `Purchases` | `/purchases` | AUTH | Commandes d'achat, réceptions |
| `SuperAdmin` | `/super-admin` | SUPER_ADMIN | Gestion tenants, abonnements |
| `SuperAdminProfile` | `/super-admin/profile` | SUPER_ADMIN | Profil Super Admin |
| `Users` | `/users` | ADMIN/MANAGER | Gestion utilisateurs |
| `Roles` | `/roles` | ADMIN | Rôles personnalisés |
| `Permissions` | `/permissions` | ADMIN | Permissions granulaires |
| `Checkout` | `/checkout` | PUBLIC | Tunnel de commande |
| `Cart` | `/cart` | PUBLIC | Panier |
| `ProductDetail` | `/produits/:id` | PUBLIC | Détail produit |
| `OrderTracking` | `/order-tracking/:ref` | PUBLIC | Suivi commande |
| `Catalogue` | `/catalogue` | PUBLIC | Catalogue multi-entreprises |
| `Suivi` | `/suivi` | PUBLIC | Suivi commandes |
| `Contact` | `/contact` | PUBLIC | Contact |
| `UserOrders` | `/mes-commandes` | USER | Historique commandes utilisateur |

### 3.5 Contextes React

**AuthContext** (`contexts/AuthContext.jsx`, 360 lignes) :
- État : `user`, `tenant`, `loading`, `isAuthenticated`, `subscription`
- Méthodes : `login()`, `register()`, `logout()`, `hasPermission()`, `hasRole()`, `getRedirectPath()`, `fetchSubscriptionStatus()`
- Gestion tokens JWT dans `localStorage` (access, refresh, user, tenant, subscription)
- Écouteur `auth:logout` pour déconnexion forcée (token expiré/invalide)
- Redirection post-login basée sur rôle

**CartContext** (`contexts/CartContext.jsx`) :
- Panier d'achat public pour marketplace
- État : items, quantité, calcul total
- Méthodes : `addToCart()`, `removeFromCart()`, `updateQuantity()`, `clearCart()`

**NotificationContext** (`contexts/NotificationContext.jsx`) :
- Notifications temps réel
- État : `notifications`, `unreadCount`
- Méthodes : `markAsRead()`, `markAllAsRead()`

### 3.6 Services API

**Fichier unique `services/api.js` (788 lignes)** :
- Instance Axios avec intercepteur request (Bearer token automatique)
- Intercepteur response avec refresh automatique sur 401
- 20+ services exportés : `authService`, `productService`, `clientService`, `saleService`, `stockService`, `factureService`, `paiementService`, `dashboardService`, `subscriptionService`, `tenantService`, `superAdminService`, `userService`, `roleService`, `permissionService`, `livreurService`, `vehiculeService`, `itineraireService`, `livraisonService`, `employeService`, `presenceService`, `salaireService`, `primeService`, `compteService`, `ecritureService`, `tresorerieService`, `modeleDocumentService`, `documentService`, `commandeAchatService`, `receptionService`, `devisService`, `bonLivraisonService`, `avoirService`, `notificationService`, `aiService`, `papiService`, `publicCatalogueService`

### 3.7 Styles et Design System

**Pas de design system documenté** — styles inline par composant :
- CSS par page (`Dashboard.css`, `Products.css`, etc.)
- CSS par composant layout (`MainLayout.css`, `DesktopLayout.css`, `TopBar.css`, `Sidebar.css`, `DashboardRail.css`, `CommandPalette.css`, `DarkModeToggle.css`, `ChatInput.css`)
- Dark mode via attribut `data-theme="dark"`
- Mode AI via attribut `data-ai="true"`
- Utilisation de `framer-motion` pour animations
- Icônes via `tabler-icons` (classe `ti ti-*`)
- Pas de Tailwind configuré côté web (seulement sur desk/)

---

## 4. Analyse de l'Application Desktop (Electron)

### 4.1 Structure

```
desk/
├── electron/
│   ├── main.js             # Processus principal Electron
│   └── run.js               # Script de lancement
├── src/
│   ├── App.js               # Routing desktop
│   ├── pages/               # Mêmes pages que web + layout desktop
│   ├── components/
│   │   ├── layout/          # DesktopLayout, DesktopSidebar, DesktopTopBar, TitleBar, SplitView, CommandPalette, FAB, DarkModeToggle, ChatInput, NotificationDropdown
│   │   ├── desktop/         # FAB (Floating Action Button)
│   │   └── auth/            # Login, Register (styles dédiés)
│   ├── contexts/            # AuthContext, DesktopContext
│   ├── hooks/               # useKeyboardShortcuts, useMediaQuery, useTheme
│   ├── services/            # desktopApi.js (API + notifications natives)
│   └── utils/               # notify.js (notifications natives Electron)
├── tailwind.config.js       # Config Tailwind CSS 3.4 avec variables CSS
├── postcss.config.js        # Config PostCSS
├── package.json             # Electron + electron-builder + Tailwind
└── build/                   # Ressources de build
```

### 4.2 Design System Desktop

**Stack CSS** :
- **Tailwind CSS 3.4** configuré avec `darkMode: 'class'`
- Design tokens centralisés via **variables CSS custom** (`--erp-gold`, `--erp-onyx`, `--erp-white`, `--erp-line`, etc.)
- Mapping Tailwind → variables CSS dans `tailwind.config.js:8-49`
- Fonts : `--erp-body-font` (sans-serif), `--erp-heading-font` (heading)
- Couleurs sémantiques : `primary`, `secondary`, `muted`, `accent`, `destructive`, `border`, `ring`

**Composants layout desktop** :

| Composant | Fichier | Responsabilité |
|-----------|---------|---------------|
| `DesktopLayout` | `DesktopLayout.jsx` | Layout principal, SplitView, TitleBar, FAB, raccourcis clavier |
| `DesktopSidebar` | `DesktopSidebar.jsx` + `.css` | Navigation latérale collapsible, groupes, badges, profil |
| `DesktopTopBar` | `DesktopTopBar.jsx` | Barre supérieure avec breadcrumbs, indicateurs, recherche, notifications |
| `TitleBar` | `TitleBar.jsx` + `.css` | Barre de titre Electron native (drag region, contrôles fenêtre) |
| `SplitView` | `SplitView.jsx` + `.css` | Vue maître-détail pour modules éligibles (resizable) |
| `CommandPalette` | `CommandPalette.jsx` + `.css` | Palette de commandes CMD+K |
| `FAB` | `FAB.jsx` + `.css` | Bouton d'action flottant |
| `NotificationDropdown` | `NotificationDropdown.jsx` + `.css` | Dropdown notifications |
| `ThemeToggle` | `ThemeToggle.jsx` + `.css` | Toggle thème clair/sombre |
| `DarkModeToggle` | `DarkModeToggle.jsx` + `.css` | Ancien toggle (remplacé par ThemeToggle) |
| `ChatInput` | `ChatInput.jsx` + `.css` | Input chat (masqué sur AI view) |

### 4.3 Fonctionnalités desktop récentes

**a) SplitView (Master-Detail)**
- Modules éligibles : `/products`, `/clients`, `/sales`, `/invoices`, `/inventory` (`DesktopLayout.jsx:19`)
- Actif quand `splitView[moduleKey].enabled === true` (`DesktopLayout.jsx:28`)
- Divider redimensionnable avec curseur `col-resize`
- Gauche : liste (Outlet), Droite : détail (placeholder "Sélectionnez un élément...")
- État persistant dans `localStorage` via `DesktopContext`

**b) TitleBar Electron**
- `TitleBar.jsx` + `TitleBar.css` : barre de titre native Electron
- `-webkit-app-region: drag` pour le drag de fenêtre
- Contrôles fenêtre (minimize, maximize, close) avec états hover/active
- Brand : logo ERP + "MIHAJA ERP" + sous-titre
- Couleurs adaptées dark/light mode

**c) FAB (Floating Action Button)**
- `FAB.jsx` + `FAB.css` : bouton flottant en bas à droite
- Menu dépliant avec items d'action rapide
- Animation `fabIn` (opacity + translateY + scale)
- Styles : fond `--erp-onyx`, hover `--erp-onyx-soft`

**d) Raccourcis clavier globaux**
- Hook `useKeyboardShortcuts.js` :
  - `CMD+K` / `CTRL+K` : Ouvrir palette de commandes
  - `CMD+B` / `CTRL+B` : Basculer sidebar
  - `CMD+N` / `CTRL+N` : Nouvelle entrée (contexte-dépendant)
  - `CMD+F` / `CTRL+F` : Focus recherche (palette)
  - `CMD+1` à `CMD+9` : Navigation rapide modules (`/dashboard`, `/products`, `/clients`, `/sales`, `/invoices`, `/inventory`, `/suppliers`, `/hr`, `/accounting`)
- Synchronisation `meta`/`ctrl` pour Mac/Windows

**e) DesktopContext (state management desktop)**
- `DesktopContext.jsx` : contexte dédié pour l'application desktop
- État :
  - `sidebarCollapsed` : état sidebar (persisté dans `localStorage`)
  - `splitView` : configuration SplitView par module (enabled, leftWidth)
  - `commandPaletteOpen` : palette ouverte/fermée
  - `notifications` : liste notifications (persistée + badge Electron)
- Méthodes : `toggleSidebar()`, `toggleSplitView(module)`, `setSplitWidth(module, width)`, `addNotification()`, `removeNotification()`, `markNotificationRead()`
- Intégration notifications natives Electron via `notificationService`

**f) DesktopTopBar**
- `DesktopTopBar.jsx` : barre supérieure unifiée
- Composants : `Breadcrumbs`, `NotificationDropdown`, `ThemeToggle`
- Indicateurs temps réel : Stock critique, Impayés, Ventes du jour (badges cliquables)
- Recherche globale (bouton + raccourci CMD+K)
- Profil Super Admin (icône + redirection `/super-admin/profile`)
- Déconnexion
- Synchronisation badge Electron dock (`notificationService.setBadge`)

**g) DesktopSidebar améliorée**
- `DesktopSidebar.css` (420 lignes) : design system CSS variables
- Support dark/light via `:root` et `.dark`
- Mobile drawer (fixed, transform translateX, backdrop)
- Groupes de navigation avec labels uppercase
- Items actifs (fond `--erp-gold`)
- Badges (dot + numérique)
- Profil utilisateur en footer (avatar, nom, rôle, menu déroulant)
- Scroll personnalisé (thin, thumb/track colors)
- Transitions fluides (width 0.18s, transform 0.25s)

**h) Intégration Electron native**
- `desktopApi.js` : service API dédié pour fonctionnalités natives
- `notify.js` : utilitaire notifications natives (`triggerNative()`)
- Badge dock Electron : synchronisation avec `unreadCount`
- `TitleBar` avec `-webkit-app-region: drag/no-drag`

### 4.4 Packaging et build

- **electron-builder 26.0** configuré dans `package.json:43-63`
- Targets : Windows (NSIS), macOS (DMG), Linux (AppImage)
- Scripts : `npm run electron:dev`, `npm run pack`, `npm run dist`, `npm run release`
- `homepage: "."` pour compatibilité Electron

### 4.5 État actuel et dette technique

**Points forts** :
- Layout desktop mature avec composants spécialisés
- SplitView implémenté pour modules core
- Raccourcis clavier complets (CMD+K, CMD+B, CMD+1-9)
- TitleBar Electron native avec drag region
- FAB pour actions rapides
- DesktopContext pour state management isolé
- Tailwind CSS configuré avec design tokens
- Dark mode supporté via CSS variables
- Mobile responsive (drawer, backdrop)

**Points à finaliser** :
- Virtualisation `@tanstack/react-virtual` dans les tableaux
- Fonctionnalités natives : impression, drag & drop fichiers, notifications système avancées
- Parité complète des pages web → desktop (quelques pages manquent encore)
- Tests desktop spécifiques (Electron IPC, raccourcis)
- `desktopApi.js` : nettoyage des fichiers `.backup`, `.bak`, `.old`

---

## 5. Analyse de la Sécurité

### 5.1 Authentification

- **JWT** avec access token (1h) + refresh token (30j)
- Tokens stockés dans `localStorage` (XSS vulnérable — pas de httpOnly cookies)
- Refresh automatique via intercepteur axios
- Hashage bcrypt des mots de passe
- `PasswordResetToken` pour réinitialisation (token avec expiration)

### 5.2 Autorisation

- **RBAC** avec 7 rôles natifs + rôles personnalisés
- **Permissions granulaires** par feature (`product.create`, `sale.view`, etc.)
- Décorateurs : `tenant_required`, `tenant_admin_required`, `admin_required`, `super_admin_required`, `permission_required`, `subscription_required`
- `SUPER_ADMIN` bypass tous les filtres tenant et plan limits

### 5.3 Multi-tenancy

- Isolation via `tenant_id` sur tous les modèles métier
- Filtrage global automatique via event listener SQLAlchemy
- Soft-delete (`is_active`) pour suppression logique
- `SUPER_ADMIN` voit toutes les données (pas de filtrage tenant)
- Résolution tenant via headers HTTP ou JWT claims

### 5.4 CORS

- Configuré avec origines explicites (pas de wildcard)
- `supports_credentials=True`
- `max_age=3600`

### 5.5 Vulnérabilités identifiées

| # | Vulnérabilité | Gravité | Emplacement |
|---|---------------|---------|-------------|
| 1 | Tokens JWT dans `localStorage` (XSS) | Élevée | Frontend (tous les contexts) |
| 2 | `except: pass` masque erreurs | Élevée | `app/__init__.py:411`, `services/paiement_service.py` |
| 3 | Isolation tenant IA/dashboard non garantie | Critique | `app/ai/assistant.py` |
| 4 | Prédictions IA fabriquées | Élevée | `app/ai/previsions.py` |
| 5 | `.pkl` versionnés (pickle unsafe) | Moyenne | `app/ai/models/*.pkl` |

---

## 6. Analyse de la Base de Données

### 6.1 Modélisation

**Approche** : Shared Database, Shared Schema (multi-tenancy par `tenant_id`)

**BaseModel abstrait** (`models/base.py`) :
```python
class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
```

**Avantages** :
- Isolation logique par `tenant_id`
- Soft-delete natif
- Audit trail (created_by, updated_by, timestamps)
- Index sur `tenant_id` pour performances

**Inconvénients** :
- Toutes les données dans une seule base (pas d'isolation physique)
- Risque de fuite si filtrage oublié
- Tables volumineuses avec croissance multi-tenant

### 6.2 Relations principales

```
Tenant (1) ──→ (N) Utilisateur
Tenant (1) ──→ (N) Abonnement
Tenant (1) ──→ (N) Produit
Tenant (1) ──→ (N) Client
Tenant (1) ──→ (N) Fournisseur
Tenant (1) ──→ (N) Vente
Tenant (1) ──→ (N) Facture
Tenant (1) ──→ (N) Paiement
Tenant (1) ──→ (N) Employe
...

Utilisateur (1) ──→ (N) Produit (created_by)
Utilisateur (N) ──→ (N) Permission (via RoleModel)

Vente (1) ──→ (N) LigneVente
CommandeFournisseur (1) ──→ (N) LigneAchat
Livraison (1) ──→ (N) SuiviLivraison
Employe (1) ──→ (N) Presence
Employe (1) ──→ (N) Salaire
Employe (1) ──→ (N) Prime
```

### 6.3 Migrations

- **Alembic** configuré via `Flask-Migrate`
- Dossier `migrations/` présent
- Scripts de seed multiples dans `scripts/` (risque de divergence)

---

## 7. Analyse de l'Architecture Logicielle

### 7.1 Patterns architecturaux

| Pattern | Utilisation | Emplacement |
|---------|-------------|-------------|
| **Factory** | `create_app()` dans `app/__init__.py` | Backend |
| **Repository/DAO** | `base_service.py` + services métier | Backend |
| **Decorator** | `tenant_required`, `admin_required`, `check_plan_limits`, `permission_required` | Backend |
| **Context API** | `AuthContext`, `CartContext`, `NotificationContext` | Frontend |
| **Interceptor** | Axios request/response interceptors | Frontend |
| **Provider** | `AuthProvider`, `CartProvider`, `NotificationProvider` | Frontend |
| **Custom Hook** | `useMediaQuery`, `useAuth` | Frontend |
| **Event-driven** | `auth:logout`, `plan-limit-reached` | Frontend |

### 7.2 Convention de nommage

**Backend (Python)** :
- Fichiers : `snake_case`
- Classes : `PascalCase`
- Fonctions/variables : `snake_case`
- Constantes : `UPPER_SNAKE_CASE`
- Modèles : suffixe `_service.py` pour services, `_model.py` implicite pour modèles

**Frontend (JavaScript)** :
- Composants : `PascalCase` (ex: `MainLayout.jsx`)
- Pages : `PascalCase` (ex: `Dashboard.jsx`)
- Contexts : `PascalCase` + suffixe `Context` (ex: `AuthContext.jsx`)
- Services : `camelCase` + suffixe `Service` (ex: `authService`)
- Hooks : `camelCase` + préfixe `use` (ex: `useMediaQuery`)

### 7.3 Gestion d'état

**Backend** :
- État global via Flask `g` (request-scoped) : `g.current_tenant`, `g.current_user`, `g.current_tenant_id`
- État applicatif via SQLAlchemy (base de données)
- Pas de cache applicatif (Redis utilisé uniquement pour Celery)

**Frontend** :
- État local via `useState` dans composants
- État global via Context API (Auth, Cart, Notifications)
- Persistence via `localStorage` (tokens, dark mode, sidebar collapsed, subscription)
- Pas de state management global (Redux, Zustand, etc.)

### 7.4 Gestion des erreurs

**Backend** :
- Try/except générique dans `before_request` masque les erreurs
- Gestionnaires d'erreurs JWT centralisés dans `app/__init__.py:105-139`
- Réponses JSON uniformes : `{'message': '...'}, status_code`

**Frontend** :
- Toast notifications via `react-toastify`
- Intercepteur axios pour erreurs 401/refresh
- Écouteur `auth:logout` pour déconnexion forcée

### 7.5 Qualité de code

| Aspect | État |
|--------|------|
| Tests backend | 11 fichiers pytest (auth, clients, produits, stocks, tenancy, users, ai, papi, mission_5, critical_api) |
| Tests frontend | Configuration `react-scripts test` présente mais pas de fichiers de test identifiés |
| Linter | Aucun ESLint configuré (`package.json` sans eslint) |
| TypeScript | Non utilisé (JavaScript pur) |
| Prettier | Non configuré |
| CI/CD | Aucun pipeline visible |
| Documentation API | Swagger via Flask-RESTx (`/docs/`) |
| Documentation code | Docstrings minimales, pas de Sphinx |

### 7.6 Dette technique identifiée

1. **Masquage d'erreurs** : `except: pass` dans plusieurs fichiers critiques
2. **Données simulées** : Certains endpoints/services retournent des placeholders (IA)
3. **Isolation tenant** : Non garantie dans modules IA/dashboard si `get_current_tenant_id()` retourne `None`
4. **Frontend sans lint/typecheck** : Aucune validation de code automatisée
5. **Scripts redondants** : Multiples scripts de seed dans `web/backend/scripts/`
6. **Modèles pickle** : `.pkl` versionnés dans le dépôt (sécurité/obsolescence)
7. **Auto-seeding en développement** : Données de test générées automatiquement (risque de contamination)
8. **Tokens dans localStorage** : Vulnérable XSS, pas de httpOnly cookies
9. **Pas de pagination coté client** :Certains services fetch toutes les données

---

## 8. Synthèse - Points Forts et Points Faibles

### 8.1 Points forts

- **Modèle de données large et cohérent** : 37 modèles couvrant l'ensemble des besoins ERP
- **Multi-tenancy solide** : Isolation par `tenant_id` avec filtrage global automatique
- **RBAC complet** : 7 rôles + rôles personnalisés + permissions granulaires + `normalize_role()` case-insensitive
- **Couverture API large** : 22+ namespaces avec Swagger
- **Architecture en couches claire** : API → Services → Models
- **Intégration paiement externe** : PAPI (Papi Payment Gateway)
- **Trois canaux de distribution** : Web, Desktop, Marketplace publique
- **Auto-seeding** : Données de test au premier démarrage
- **Intercepteur JWT robuste** : Refresh automatique côté frontend
- **Localisation Madagascar** : Devise MGA, formats adaptés
- **Desktop mature** : SplitView, TitleBar Electron, FAB, raccourcis clavier complets, DesktopContext, Tailwind CSS configuré
- **Formulaires validés** : Yup + React Hook Form sur pages web (Sales, Clients, etc.)

### 8.2 Points faibles

- **Frontend sans quality gate** : Pas de ESLint, Prettier, TypeScript
- **IA en mode placeholder** : Malgré modèles `.pkl` présents
- **Tâches Celery inactives** : Backups, emails, rapports non fonctionnels
- **Limites de plan partielles** : Vérifiées seulement pour produits, clients, utilisateurs
- **Tokens JWT dans localStorage** : Risque XSS
- **Scripts de seed redondants** : Risque de divergence
- **Erreurs masquées** : `except: pass` dans plusieurs fichiers critiques
- **Pas de pagination systématique** : Certains endpoints retournent toutes les données
- **Documentation technique incomplète** : `docs/{user,technical,api}/README.md` à rédiger
- **Virtualisation non implémentée** : `@tanstack/react-virtual` installé mais pas utilisé dans les tableaux desktop

---

## 9. Évolutions récentes (commits récents)

### 9.1 Desktop Design Correction (`d727bfa`)
- **DesktopSidebar.css** (420 lignes) : refonte complète avec CSS variables, dark mode, mobile drawer
- **DesktopTopBar.jsx** : nouveau composant avec breadcrumbs, indicateurs temps réel, recherche, notifications
- **DesktopLayout.jsx** : intégration SplitView, TitleBar, FAB, useKeyboardShortcuts
- **Tailwind CSS 3.4** configuré dans `desk/tailwind.config.js` avec mapping vers variables CSS custom
- **Design tokens** : variables sémantiques (`--erp-gold`, `--erp-onyx`, `--erp-white`, `--erp-line`, etc.)

### 9.2 Mise en place des rôles (`cc8deab`)
- **Backend** : `normalize_role()` pour comparaison case-insensitive dans `security/roles.py`
- **Backend** : propriétés `is_admin`, `is_super_admin`, `is_manager` dans `models/utilisateur.py` avec support `custom_role_id`
- **Backend** : permissions granulaires via `RoleModel` + `Permission` (many-to-many)
- **Frontend** : améliorations formulaires (Sales.jsx avec Yup, ClientModal.jsx)

### 9.3 Final Bug Fixes Desktop (`a3af12b`)
- Layout desktop finalisé : DesktopLayout, DesktopSidebar, DesktopTopBar
- Services desktop : `desktopApi.js` pour API + notifications natives
- Electron IPC : intégration notifications natives, badge dock
- Raccourcis clavier : `useKeyboardShortcuts.js` (CMD+K, CMD+B, CMD+1-9)

### 9.4 Update Web Archi Finaliste (`134fdc4`)
- Frontend web : pages connectées aux APIs réelles
- Services API mis à jour (`api.js`)
- Formulaires CRUD avec React Hook Form + Yup

---

## 10. Recommandations

### 10.1 Priorité Haute

1. **Sécuriser l'authentification** : Migrer les tokens JWT vers httpOnly cookies pour mitiguer XSS
2. **Éliminer les `except: pass`** : Remplacer par logging + gestion d'erreur explicite
3. **Garantir l'isolation tenant** : Vérifier que tous les modules (IA, dashboard) filtrent systématiquement par `tenant_id`
4. **Connecter le frontend aux APIs réelles** : Remplacer les données simulées, compléter les formulaires CRUD

### 10.2 Priorité Moyenne

5. **Ajouter lint/typecheck** : ESLint + Prettier pour le frontend, mypy pour le backend
6. **Étendre plan_limits** : Appliquer à ventes, fournisseurs, factures, etc.
7. **Finaliser l'IA** : Charger les modèles `.pkl`, supprimer les prédictions fabriquées
8. **Activer Celery** : Workers pour backups, emails, rapports
9. **Réduire les scripts de seed** : Consolider en un seul script principal

### 10.3 Priorité Basse

10. **Ajouter TypeScript** : Migration progressive du frontend
11. **Implémenter la virtualisation** : `@tanstack/react-virtual` dans les tableaux desktop
12. **Rédiger la documentation** : `docs/{user,technical,api}/README.md`
13. **Ajouter CI/CD** : GitHub Actions ou GitLab CI avec lint, tests, build

---

## 11. Matrice de couverture fonctionnelle

| Module | Backend API | Frontend Web | Desktop | Tests |
|--------|:-----------:|:------------:|:-------:|:-----:|
| Authentification | ✅ | ✅ | ✅ | ✅ |
| Multi-tenancy | ✅ | ✅ | ✅ | ✅ |
| RBAC | ✅ | ✅ | ✅ | ⚠️ |
| Produits | ✅ | ✅ | ✅ | ✅ |
| Clients | ✅ | ✅ | ✅ | ✅ |
| Fournisseurs | ✅ | ✅ | ✅ | ✅ |
| Ventes | ✅ | ✅ | ✅ | ⚠️ |
| Stocks | ✅ | ✅ | ✅ | ✅ |
| Factures | ✅ | ✅ | ✅ | ⚠️ |
| Paiements | ✅ | ✅ | ✅ | ⚠️ |
| Dashboard | ✅ | ✅ | ✅ | ⚠️ |
| Abonnements | ✅ | ✅ | ✅ | ⚠️ |
| Livraison | ✅ | ✅ | ✅ | ⚠️ |
| RH | ✅ | ✅ | ✅ | ⚠️ |
| Comptabilité | ✅ | ✅ | ✅ | ⚠️ |
| Documents | ✅ | ✅ | ✅ | ⚠️ |
| Achats/Devis | ✅ | ✅ | ✅ | ⚠️ |
| Marketplace | ✅ | ✅ | ✅ | ⚠️ |
| IA | ⚠️ | ✅ | ✅ | ⚠️ |
| PAPI Paiement | ✅ | ✅ | ✅ | ⚠️ |
| Notifications | ✅ | ✅ | ✅ | ⚠️ |

**Légende** : ✅ Complet, ⚠️ Partiel/Placeholder, ❌ Absent

---

*Fin de l'analyse.*
